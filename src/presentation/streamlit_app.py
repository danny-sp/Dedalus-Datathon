import streamlit as st
import re
import json

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

# Inicialización del historial de chat en Streamlit
if "messages" not in st.session_state:
    st.session_state.messages = []

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
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            render_content(message["content"])
        else:
            st.markdown(message["content"])

# Entrada de usuario
if prompt := st.chat_input("Escribe tu consulta médica aquí..."):
    # Agregar la pregunta al historial y mostrarla
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Contenedor para mostrar la respuesta en progreso o spinner
    with st.chat_message("assistant"):
        with st.spinner("Consultando la base de datos de pacientes..."):
            # Enviar solo los últimos N mensajes para no saturar la memoria del modelo ni ralentizarlo
            MAX_MENSAJES = 10
            historial_mensajes = [
                (msg["role"], msg["content"])
                for msg in st.session_state.messages[-MAX_MENSAJES:]
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
    st.session_state.messages.append({"role": "assistant", "content": respuesta_final})
