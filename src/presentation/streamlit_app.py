import json
import re
import io
from datetime import datetime

import speech_recognition as sr
import streamlit as st
import streamlit.components.v1 as components

from src.domain.agent import get_agent_executor

st.set_page_config(page_title="Asistente Médico IA", page_icon="assets/chismoso.png", layout="centered")

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
    st.session_state.conversations = [c for c in st.session_state.conversations if c["id"] != conv_id]
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
        if st.form_submit_button("Crear carpeta", icon=":material/create_new_folder:", use_container_width=True):
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
        if st.button("Bajar", icon=":material/arrow_downward:", use_container_width=True):
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
                    if st.button("", icon=":material/delete:", key=f"del_{conv['id']}", help="Eliminar conversación"):
                        _delete_conversation(conv["id"])
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
            st.error(f"El bloque JSON número {idx+1} para el gráfico no es válido.", icon=":material/error:")
            st.code(json_str, language="json")


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
            texto_legible = re.sub(r"[#*_\[\]]", "", texto_legible).strip()
            if texto_legible:
                safe_text = texto_legible.replace("'", "\\'").replace("\n", " ").replace("\r", " ").replace('"', '\\"')
                tts_data[i] = safe_text
        else:
            st.markdown(message["content"])

import json
json_tts_data = json.dumps(tts_data)

js_tts_script = f"""
<script>
setInterval(function() {{
    const parentDoc = window.parent.document;
    const ttsData = {json_tts_data};
    
    const speakerSvg = `
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" width="20" height="20">
            <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z" fill="currentColor"/>
        </svg>
    `;
    const stopSvg = `
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" width="20" height="20">
            <path d="M6 6h12v12H6z" fill="currentColor"/>
        </svg>
    `;
    
    for (const [i, text] of Object.entries(ttsData)) {{
        const anchor = parentDoc.getElementById('tts-anchor-' + i);
        if (anchor && !anchor.hasChildNodes()) {{
            const btn = parentDoc.createElement('button');
            btn.className = "tts-custom-btn";
            btn.innerHTML = speakerSvg;
            btn.title = "Escuchar respuesta";
            btn.dataset.playing = "false";
            btn.style.cssText = `
                background: transparent;
                border: 1px solid rgba(125,125,125,0.2);
                border-radius: 5px;
                color: #888;
                cursor: pointer;
                padding: 6px 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.3s;
            `;
            
            btn.onmouseover = () => btn.style.background = 'rgba(125,125,125,0.1)';
            btn.onmouseout = () => btn.style.background = 'transparent';
            
            btn.onclick = () => {{
                const synth = window.parent.speechSynthesis;
                
                if (btn.dataset.playing === "true") {{
                    // Stop playing
                    synth.cancel();
                    btn.dataset.playing = "false";
                    btn.innerHTML = speakerSvg;
                    btn.style.color = "#888";
                    return;
                }}
                
                // Cancel any audio currently playing
                synth.cancel();
                
                // Reset all other TTS buttons
                const allBtns = parentDoc.querySelectorAll('.tts-custom-btn');
                allBtns.forEach(b => {{
                    b.dataset.playing = "false";
                    b.innerHTML = speakerSvg;
                    b.style.color = "#888";
                }});
                
                const msg = new window.parent.SpeechSynthesisUtterance(text);
                msg.lang = 'es-ES';
                
                // Keep global reference to avoid Safari/Chrome garbage collection bug ending speech early
                window.parent._currentTTSUtterance = msg;
                
                msg.onend = () => {{
                    btn.dataset.playing = "false";
                    btn.innerHTML = speakerSvg;
                    btn.style.color = "#888";
                }};
                msg.onerror = () => {{
                    btn.dataset.playing = "false";
                    btn.innerHTML = speakerSvg;
                    btn.style.color = "#888";
                }};
                
                btn.dataset.playing = "true";
                btn.innerHTML = stopSvg;
                btn.style.color = "#ff4b4b"; // Red to indicate playing/stop
                
                synth.speak(msg);
            }};
            
            anchor.appendChild(btn);
        }}
    }}
}}, 1000);
</script>
"""
components.html(js_tts_script, height=0, width=0)

# --- Lógica de Entrada de Usuario (STT integrado nativamente en chat bar vía JS) ---

prompt = st.chat_input("Escribe tu consulta médica aquí...")

# Inyectamos script JS para añadir el botón de micrófono nativamente al chat_input
stt_js = """
<script>
setInterval(function() {
    const parentDoc = window.parent.document;
    if (parentDoc.getElementById('custom-mic-btn')) return; // already exists
    
    // Find the chat input container
    const chatInputContainer = parentDoc.querySelector('[data-testid="stChatInput"]');
    if (!chatInputContainer) return;
    
    // Find the submit button inside it
    const buttons = chatInputContainer.querySelectorAll('button');
    const submitBtn = buttons[buttons.length - 1]; // usually the last button is send
    if (!submitBtn) return;
    
    const micBtn = parentDoc.createElement("button");
    micBtn.id = 'custom-mic-btn';
    micBtn.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" width="24" height="24">
            <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" fill="currentColor"/>
            <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" fill="currentColor"/>
        </svg>
    `;
    micBtn.style.cssText = `
        background: transparent;
        border: none;
        color: #888;
        cursor: pointer;
        padding: 5px;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: color 0.3s;
        margin-right: 8px;
    `;
    
    // Stop square SVG for recording state
    const stopSvg = `
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" width="24" height="24">
            <path d="M6 6h12v12H6z" fill="currentColor"/>
        </svg>
    `;
    const micSvg = micBtn.innerHTML;

    // Insert before the submit button
    submitBtn.parentNode.insertBefore(micBtn, submitBtn);

    const SpeechRecognition = window.parent.SpeechRecognition || window.parent.webkitSpeechRecognition;
    if (!SpeechRecognition) return;
    
    const recognition = new SpeechRecognition();
    recognition.lang = 'es-ES';
    recognition.continuous = false;
    recognition.interimResults = false;

    let isRecording = false;

    micBtn.onclick = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (isRecording) {
            recognition.stop();
        } else {
            recognition.start();
        }
    };

    recognition.onstart = () => {
        isRecording = true;
        micBtn.innerHTML = stopSvg;
        micBtn.style.color = "red";
    };

    recognition.onresult = (evt) => {
        const transcript = evt.results[0][0].transcript;
        const textArea = chatInputContainer.querySelector('textarea');
        if (textArea) {
            // Set value and trigger React input event
            const nativeSetter = Object.getOwnPropertyDescriptor(window.parent.HTMLTextAreaElement.prototype, 'value').set;
            let currentVal = textArea.value;
            let spacer = currentVal ? " " : "";
            nativeSetter.call(textArea, currentVal + spacer + transcript);
            textArea.dispatchEvent(new window.parent.Event('input', { bubbles: true }));
            
            // Auto click send to submit the voice input automatically
            setTimeout(() => {
                 const sendBtn = chatInputContainer.querySelectorAll('button');
                 const actualSend = sendBtn[sendBtn.length - 1]; // re-query the button
                 if(actualSend && !actualSend.disabled) actualSend.click();
            }, 100);
        }
    };

    recognition.onend = () => {
        isRecording = false;
        micBtn.innerHTML = micSvg;
        micBtn.style.color = "#888";
    };
    
    recognition.onerror = () => {
        isRecording = false;
        micBtn.innerHTML = micSvg;
        micBtn.style.color = "#888";
    };
}, 1000);
</script>
"""
components.html(stt_js, height=0, width=0)

final_user_input = prompt

if final_user_input:
    # Agregar la pregunta al historial y mostrarla
    messages.append({"role": "user", "content": final_user_input})

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
        with st.spinner("Consultando la base de datos de pacientes..."):
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
    messages.append({"role": "assistant", "content": respuesta_final})
    st.rerun()  # Rerun para integrar permanentemente la respuesta y mostrar controles (ej. TTS)
