import json
import re

import streamlit as st

from src.domain.agent import get_agent_executor

st.set_page_config(page_title="Asistente Médico IA", page_icon="🏥", layout="centered")

st.title("Asistente Médico de Cohortes Clínicas")
st.markdown(
    "Consulta información médica basada en la base de datos de pacientes en lenguaje natural."
)


# Cacheamos la carga de la base de datos, llm y agente para no iniciarlos en cada interacción
@st.cache_resource
def load_agent():
    return get_agent_executor()


agent_executor = load_agent()

def _build_conversation_title(messages, fallback):
    """Crea un titulo corto a partir del primer mensaje del usuario."""
    for msg in messages:
        if msg["role"] == "user" and msg["content"].strip():
            title = msg["content"].strip().replace("\n", " ")
            return title[:40] + "..." if len(title) > 40 else title
    return fallback


def _initialize_chat_state():
    """Inicializa el estado para manejar multiples conversaciones."""
    if "conversations" not in st.session_state:
        st.session_state.conversations = [
            {
                "id": "conv_1",
                "title": "Conversacion 1",
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
        st.session_state.active_conversation_id = st.session_state.conversations[0]["id"]


def _get_active_conversation():
    """Obtiene la conversacion activa o crea una nueva si no existe."""
    for conv in st.session_state.conversations:
        if conv["id"] == st.session_state.active_conversation_id:
            return conv

    new_conv = {
        "id": f"conv_{len(st.session_state.conversations) + 1}",
        "title": f"Conversacion {len(st.session_state.conversations) + 1}",
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
    """Mueve la conversacion activa arriba o abajo en el historial."""
    conv_id = st.session_state.active_conversation_id
    order = st.session_state.conversation_order
    if conv_id not in order:
        return

    idx = order.index(conv_id)
    new_idx = idx + step
    if 0 <= new_idx < len(order):
        order[idx], order[new_idx] = order[new_idx], order[idx]


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

    if st.button("+ Nueva conversacion", use_container_width=True):
        new_id = f"conv_{len(st.session_state.conversations) + 1}"
        st.session_state.conversations.append(
            {
                "id": new_id,
                "title": f"Conversacion {len(st.session_state.conversations) + 1}",
                "created_at": datetime.now().strftime("%d/%m %H:%M"),
                "folder_id": "root",
                "messages": [],
            }
        )
        st.session_state.conversation_order.append(new_id)
        st.session_state.active_conversation_id = new_id
        st.rerun()

    st.caption("Organiza tus chats en carpetas")
    new_folder_name = st.text_input("Nueva carpeta", placeholder="Ej: Alergias")
    if st.button("Crear carpeta", use_container_width=True):
        folder_name = new_folder_name.strip()
        existing_names = {f["name"].lower() for f in st.session_state.folders}
        if folder_name and folder_name.lower() not in existing_names:
            st.session_state.folders.append(
                {
                    "id": f"folder_{len(st.session_state.folders) + 1}",
                    "name": folder_name,
                }
            )
            st.rerun()

    active_conversation_preview = _get_active_conversation()
    folder_options = [folder["id"] for folder in st.session_state.folders]
    selected_folder_id = st.selectbox(
        "Carpeta de la conversacion activa",
        options=folder_options,
        index=folder_options.index(active_conversation_preview.get("folder_id", "root")),
        format_func=_get_folder_name,
    )
    if selected_folder_id != active_conversation_preview.get("folder_id", "root"):
        active_conversation_preview["folder_id"] = selected_folder_id
        st.rerun()

    col_up, col_down = st.columns(2)
    with col_up:
        if st.button("Subir", use_container_width=True):
            _move_active_conversation(-1)
            st.rerun()
    with col_down:
        if st.button("Bajar", use_container_width=True):
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
                if st.button(
                    label,
                    key=f"history_{conv['id']}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary",
                ):
                    st.session_state.active_conversation_id = conv["id"]
                    st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

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
            st.error(f"❌ El bloque JSON número {idx+1} para el gráfico no es válido.")
            st.code(json_str, language="json")


# Mostrar el historial de chat existente
for message in messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            render_content(message["content"])
        else:
            st.markdown(message["content"])

# Entrada de usuario
if prompt := st.chat_input("Escribe tu consulta médica aquí..."):
    # Agregar la pregunta al historial y mostrarla
    messages.append({"role": "user", "content": prompt})

    default_title = active_conversation["title"].startswith("Conversacion ")
    if default_title:
        active_conversation["title"] = _build_conversation_title(
            messages,
            active_conversation["title"],
        )

    with st.chat_message("user"):
        st.markdown(prompt)

    # Contenedor para mostrar la respuesta en progreso o spinner
    with st.chat_message("assistant"):
        with st.spinner("Consultando la base de datos de pacientes..."):
            # Enviar solo los últimos N mensajes para no saturar la memoria del modelo ni ralentizarlo
            MAX_MENSAJES = 10
            historial_mensajes = [
                (msg["role"], msg["content"]) for msg in messages[-MAX_MENSAJES:]
            ]
            inputs = {"messages": historial_mensajes}
            respuesta_final = ""

            # Ejecutar el agente y guardar la respuesta
            for event in agent_executor.stream(inputs, stream_mode="values"):
                # Asumo que event["messages"][-1] trae AIMessage Chunk o entero
                message = event["messages"][-1]
                if message.type == "ai" and message.content:
                    respuesta_final = message.content

            # Mostrar contenido (texto y gráficos) procesados adecuadamente
            render_content(respuesta_final)

    # Agregar la respuesta original del agente al historial de sesión
    messages.append({"role": "assistant", "content": respuesta_final})
