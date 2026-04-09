import streamlit as st

from domain.agent import get_agent_executor

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

# Mostrar el historial de chat existente
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
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
                message = event["messages"][-1]
                if message.type == "ai" and message.content:
                    respuesta_final = message.content

            st.markdown(respuesta_final)

    # Agregar la respuesta del agente al historial de sesión
    st.session_state.messages.append({"role": "assistant", "content": respuesta_final})
