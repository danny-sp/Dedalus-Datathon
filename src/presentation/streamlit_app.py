import json
import os
import re
import io
from datetime import datetime

import streamlit as st

from src.domain.agent import get_agent_executor
from src.persistance.avisador import enviar_mail
from src.presentation.components.voice import render_tts_component, render_stt_component

st.set_page_config(
    page_title="Asistente Médico IA", page_icon="assets/chismoso.png", layout="centered"
)

st.title("Asistente Médico de Cohortes Clínicas")
st.markdown(
    "Consulta información médica basada en la base de datos de pacientes en lenguaje natural."
)


# Cacheamos la carga de la base de datos, llm y agente para no iniciarlos en cada interacción
@st.cache_resource
def load_agent():
    return get_agent_executor()


agent_executor = load_agent()


@st.dialog("Reportar Incidencia")
def reportar_incidencia_dialog():
    st.write(
        "Escribe aquí tu comentario o descripción del problema. Se adjuntará automáticamente el log de esta sesión."
    )
    comentario = st.text_area("Comentario", placeholder="¿Qué ha ido mal?")
    email_destino = "soporte-chismoso@yopmail.com"
    st.text_input("Correo de soporte", value=email_destino, disabled=True)

    if st.button("Enviar", use_container_width=True, type="primary"):
        if comentario.strip():
            log_path = None
            if "log_filename" in st.session_state and os.path.exists(st.session_state.log_filename):
                log_path = st.session_state.log_filename
            
            cuerpo_correo = f"=== REPORTE DE INCIDENCIA ===\n\nComentario proporcionado:\n{comentario}"
            
            try:
                res = enviar_mail(email_destino, cuerpo_correo, adjunto_path=log_path)
                st.success(f"Reporte enviado. Detalles: {res}")
            except Exception as e:
                st.error(f"Ocurrió un error al enviar: {e}")
        else:
            st.warning("Debes escribir un comentario antes de enviar.")


def _build_conversation_title(messages, fallback):
    """Crea un titulo corto a partir del primer mensaje del usuario."""
    for msg in messages:
        if msg["role"] == "user" and msg["content"].strip():
            title = msg["content"].strip().replace("\n", " ")
            return title[:40] + "..." if len(title) > 40 else title
    return fallback


def _initialize_chat_state():
    """Inicializa el estado para manejar multiples conversaciones."""
    if "log_filename" not in st.session_state:
        os.makedirs("logs", exist_ok=True)
        st.session_state.log_filename = (
            f"logs/{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
        )

    if "conversations" not in st.session_state:
        st.session_state.conversations = [
            {
                "id": "conv_1",
                "title": "Conversación 1",
                "created_at": datetime.now().strftime("%d/%m %H:%M"),
                "folder_id": "root",
                "messages": [],
            }
        ]
    if "folders" not in st.session_state:
        st.session_state.folders = [
            {
                "id": "root",
                "name": "Sin carpeta",
            }
        ]
    if "conversation_order" not in st.session_state:
        st.session_state.conversation_order = [
            conv["id"] for conv in st.session_state.conversations
        ]
    if "active_conversation_id" not in st.session_state:
        st.session_state.active_conversation_id = st.session_state.conversations[0][
            "id"
        ]


def _get_active_conversation():
    """Obtiene la conversación activa o crea una nueva si no existe."""
    for conv in st.session_state.conversations:
        if conv["id"] == st.session_state.active_conversation_id:
            return conv

    new_conv = {
        "id": f"conv_{len(st.session_state.conversations) + 1}",
        "title": f"Conversación {len(st.session_state.conversations) + 1}",
        "created_at": datetime.now().strftime("%d/%m %H:%M"),
        "folder_id": "root",
        "messages": [],
    }
    st.session_state.conversations.append(new_conv)
    st.session_state.conversation_order.append(new_conv["id"])
    st.session_state.active_conversation_id = new_conv["id"]
    return new_conv


def _get_folder_name(folder_id):
    for folder in st.session_state.folders:
        if folder["id"] == folder_id:
            return folder["name"]
    return "Sin carpeta"


def _move_active_conversation(step):
    """Mueve la conversación activa arriba o abajo en el historial."""
    conv_id = st.session_state.active_conversation_id
    order = st.session_state.conversation_order
    if conv_id not in order:
        return

    idx = order.index(conv_id)
    new_idx = idx + step
    if 0 <= new_idx < len(order):
        order[idx], order[new_idx] = order[new_idx], order[idx]


def _delete_conversation(conv_id):
    """Elimina una conversación y actualiza el estado."""
    st.session_state.conversations = [
        c for c in st.session_state.conversations if c["id"] != conv_id
    ]
    if conv_id in st.session_state.conversation_order:
        st.session_state.conversation_order.remove(conv_id)

    if not st.session_state.conversations:
        new_conv = {
            "id": f"conv_{int(datetime.now().timestamp())}",
            "title": "Conversación 1",
            "created_at": datetime.now().strftime("%d/%m %H:%M"),
            "folder_id": "root",
            "messages": [],
        }
        st.session_state.conversations.append(new_conv)
        st.session_state.conversation_order.append(new_conv["id"])
        st.session_state.active_conversation_id = new_conv["id"]
    elif st.session_state.active_conversation_id == conv_id:
        st.session_state.active_conversation_id = st.session_state.conversation_order[0]


_initialize_chat_state()

st.markdown(
    """
    <style>
    .history-scroll {
        max-height: 52vh;
        overflow-y: auto;
        border: 1px solid rgba(125, 125, 125, 0.25);
        border-radius: 10px;
        padding: 0.35rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.subheader("Historial de conversaciones")

    if st.button("Nueva conversación", icon=":material/add:", use_container_width=True):
        new_id = f"conv_{len(st.session_state.conversations) + 1}"
        st.session_state.conversations.append(
            {
                "id": new_id,
                "title": f"Conversación {len(st.session_state.conversations) + 1}",
                "created_at": datetime.now().strftime("%d/%m %H:%M"),
                "folder_id": "root",
                "messages": [],
            }
        )
        st.session_state.conversation_order.append(new_id)
        st.session_state.active_conversation_id = new_id
        st.rerun()

    st.caption("Organiza tus chats en carpetas")
    with st.form("new_folder_form", clear_on_submit=True):
        new_folder_name = st.text_input("Nueva carpeta", placeholder="Ej: Alergias")
        if st.form_submit_button(
            "Crear carpeta",
            icon=":material/create_new_folder:",
            use_container_width=True,
        ):
            folder_name = new_folder_name.strip()
            existing_names = {f["name"].lower() for f in st.session_state.folders}
            if folder_name and folder_name.lower() not in existing_names:
                new_folder_id = f"folder_{len(st.session_state.folders) + 1}"
                st.session_state.folders.append(
                    {
                        "id": new_folder_id,
                        "name": folder_name,
                    }
                )
                active_conv = _get_active_conversation()
                active_conv["folder_id"] = new_folder_id
                st.rerun()

    active_conversation_preview = _get_active_conversation()
    folder_options = [folder["id"] for folder in st.session_state.folders]
    selected_folder_id = st.selectbox(
        "Carpeta de la conversación activa",
        options=folder_options,
        index=folder_options.index(
            active_conversation_preview.get("folder_id", "root")
        ),
        format_func=_get_folder_name,
    )
    if selected_folder_id != active_conversation_preview.get("folder_id", "root"):
        active_conversation_preview["folder_id"] = selected_folder_id
        st.rerun()

    col_up, col_down = st.columns(2)
    with col_up:
        if st.button("Subir", icon=":material/arrow_upward:", use_container_width=True):
            _move_active_conversation(-1)
            st.rerun()
    with col_down:
        if st.button(
            "Bajar", icon=":material/arrow_downward:", use_container_width=True
        ):
            _move_active_conversation(1)
            st.rerun()

    conv_by_id = {conv["id"]: conv for conv in st.session_state.conversations}

    st.markdown("<div class='history-scroll'>", unsafe_allow_html=True)
    for folder in st.session_state.folders:
        with st.expander(folder["name"], expanded=True):
            for conv_id in st.session_state.conversation_order:
                conv = conv_by_id.get(conv_id)
                if not conv:
                    continue
                if conv.get("folder_id", "root") != folder["id"]:
                    continue

                label = f"{conv['title']} · {conv['created_at']}"
                is_active = conv["id"] == st.session_state.active_conversation_id

                col_btn, col_del = st.columns([0.85, 0.15])
                with col_btn:
                    if st.button(
                        label,
                        key=f"history_{conv['id']}",
                        use_container_width=True,
                        type="primary" if is_active else "secondary",
                    ):
                        st.session_state.active_conversation_id = conv["id"]
                        st.rerun()
                with col_del:
                    if st.button(
                        "",
                        icon=":material/delete:",
                        key=f"del_{conv['id']}",
                        help="Eliminar conversación",
                    ):
                        _delete_conversation(conv["id"])
                        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    if st.button(
        "Reportar Incidencia", icon=":material/bug_report:", use_container_width=True
    ):
        reportar_incidencia_dialog()

active_conversation = _get_active_conversation()
messages = active_conversation["messages"]


def render_content(content):
    """Extrae bloques JSON de Vega-Lite del contenido y los dibuja, mostrando el texto restante."""
    texto_pantalla = content
    bloques_json = []

    for match in re.finditer(r"```json\s*(.*?)\s*```", content, re.DOTALL):
        bloques_json.append(match.group(1))
        texto_pantalla = texto_pantalla.replace(match.group(0), "")

    # Imprimimos el texto que queda después de limpiar los bloques JSON
    texto_limpio = texto_pantalla.strip()
    if texto_limpio:
        st.markdown(texto_limpio)

    # Iteramos sobre todos los JSON (gráficos) y los dibujamos
    for idx, json_str in enumerate(bloques_json):
        try:
            vega_dict = json.loads(json_str)
            st.vega_lite_chart(vega_dict, use_container_width=True)
        except json.JSONDecodeError:
            st.error(
                f"El bloque JSON número {idx+1} para el gráfico no es válido.",
                icon=":material/error:",
            )
            st.code(json_str, language="json")


def log_message(role, content):
    """Guarda un mensaje en el archivo de log de la sesión."""
    if "log_filename" in st.session_state:
        with open(st.session_state.log_filename, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {role.upper()}:\n{content}\n{'-'*40}\n")


# Mostrar el historial de chat existente
tts_data = {}

for i, message in enumerate(messages):
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            render_content(message["content"])
            
            # Ancla invisible para inyectar nuestro botón TTS nativo mediante JS
            st.markdown(f'<div id="tts-anchor-{i}" style="display: flex; justify-content: flex-end; margin-top: -10px;"></div>', unsafe_allow_html=True)
            
            # Preparar el texto limpio para JS
            texto_legible = re.sub(r"```json\s*.*?\s*```", "", message["content"], flags=re.DOTALL)
            
            # 1. Eliminar tablas (borrar líneas que contengan '|' que es característico de Markdown tables)
            texto_legible = "\n".join([line for line in texto_legible.split('\n') if "|" not in line])
            
            # 2. Eliminar emojis y caracteres especiales, dejando solo texto y puntuación leíble
            texto_legible = re.sub(r'[^\w\s.,;:!?¡¿áéíóúÁÉÍÓÚñÑüÜ()+\-$€%]', ' ', texto_legible)
            
            # 3. Limpiar espacios extra
            texto_legible = re.sub(r'\s+', ' ', texto_legible).strip()
            if texto_legible:
                safe_text = texto_legible.replace("'", "\\'").replace("\n", " ").replace("\r", " ").replace('"', '\\"')
                tts_data[i] = safe_text
        else:
            st.markdown(message["content"])

# Renderizar componente de Texto a Voz (TTS)
render_tts_component(tts_data)

# --- Lógica de Entrada de Usuario (STT integrado nativamente en chat bar vía JS) ---

prompt = st.chat_input("Escribe tu consulta médica aquí...")

# Inyectamos script JS para añadir el botón de micrófono nativamente al chat_input
render_stt_component()

final_user_input = prompt

if final_user_input:
    # Agregar la pregunta al historial y mostrarla
    log_message("user", prompt)
    messages.append({"role": "user", "content": prompt})

    default_title = active_conversation["title"].startswith("Conversación ")
    if default_title:
        active_conversation["title"] = _build_conversation_title(
            messages,
            active_conversation["title"],
        )

    with st.chat_message("user"):
        st.markdown(final_user_input)

    # Contenedor para mostrar la respuesta en progreso o spinner
    with st.chat_message("assistant"):
        with st.spinner("Chismoso está pensando..."):
            # Enviar solo los últimos N mensajes para no saturar la memoria del modelo ni ralentizarlo
            MAX_MENSAJES = 10
            historial_mensajes = [
                (msg["role"], msg["content"]) for msg in messages[-MAX_MENSAJES:]
            ]
            inputs = {"messages": historial_mensajes}
            respuesta_final = ""

            # Ejecutar el agente y guardar la respuesta
            for event in agent_executor.stream(inputs, stream_mode="values"):
                message = event["messages"][-1]
                if message.type == "ai" and message.content:
                    respuesta_final = message.content

            # Mostrar contenido
            render_content(respuesta_final)
            
    # Agregar la respuesta original del agente al historial de sesión
    log_message("assistant", respuesta_final)

    messages.append({"role": "assistant", "content": respuesta_final})
    st.rerun()  # Rerun para integrar permanentemente la respuesta y mostrar controles (ej. TTS)
