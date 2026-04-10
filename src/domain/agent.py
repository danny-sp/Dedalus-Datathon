import json

from langchain.agents import create_agent
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool
from langchain_experimental.sql import SQLDatabaseChain
from langchain_ollama import ChatOllama

from src.persistance.avisador import enviar_mail, enviar_sms


def get_agent_executor():
    """
    Inicializa y devuelve el agente ejecutor de LangChain configurado
    con SQLite y ChatOllama.
    """
    db = SQLDatabase.from_uri("sqlite:///hospital.db")

    # Usamos kimi-k2.5:cloud como en app.py (o puedes cambiar a llama3.1)
    llm = ChatOllama(
        model="kimi-k2.5:cloud",
        temperature=0,
    )

    sql_prompt_template = """
    Eres un Arquitecto de Datos experto en SQLite y análisis de registros médicos electrónicos. Tu única tarea es traducir la pregunta del usuario en una consulta SQL sintácticamente correcta y optimizada para SQLite.

    REGLAS PARA LA GENERACIÓN DEL SQL:
    1. FORMATO ESTRICTO: Devuelve ÚNICAMENTE la consulta SQL en texto plano. NO incluyas delimitadores de bloque de código (como ```sql o ```). NO proporciones explicaciones, saludos ni comentarios adicionales.
    2. RESTRICCIÓN DE ESQUEMA: Utiliza exclusivamente las tablas y columnas detalladas en el esquema proporcionado. No asumas la existencia de otros campos.
    3. NOMENCLATURA DE TABLAS: Recuerda que las tablas disponibles se nombran sin el prefijo 'cohorte_' (las tablas exactas son: alergias, condiciones, encuentros, medicationes, pacientes, procedimientos).
    4. RELACIONES (JOINs): La clave primaria y foránea que conecta todas las tablas es la columna `PacienteID`. Usa esta columna de forma explícita al realizar sentencias JOIN.
    5. OPTIMIZACIÓN: Si la pregunta implica filtrado temporal, ten en cuenta el formato de fecha estándar de las columnas de fechas (`Fecha_inicio`, `Fecha_diagnostico`, etc.).
    6. SELECCIÓN DE COLUMNAS: Si el usuario pide "personas", "pacientes" o "quiénes", SIEMPRE haz `SELECT` de campos identificativos como `PacienteID` y opcionalmente nombre, no solo la condición.
    7. CONDICIONES MÚLTIPLES: Para consultas con "Y" (AND lógico en distintas filas, ej: Asma Y Diabetes), asegúrate de usar `INTERSECT` o un `GROUP BY PacienteID HAVING COUNT(DISTINCT condicion) = 2` para encontrar pacientes que cumplan AMBAS.
    8. CÓDIGOS SNOMED: Si la pregunta no menciona explícitamente "Códigos SNOMED", busca por la descripción de la condición, procedimiento o medicación. Solo usa los códigos SNOMED si el usuario los incluye en su pregunta.
    9. CONTEO DISTINTO: Cuando se pregunte "cuántos" pacientes, asegúrate siempre de usar `COUNT(DISTINCT PacienteID)`, ya que un mismo paciente puede tener múltiples registros.
    10. EXPANSIÓN SEMÁNTICA DE GRUPOS/CATEGORÍAS: Si el usuario menciona conceptos amplios, regiones generales o categorías (ej: "andaluces", "castellanomanchegos", "antibióticos", etc.), usa tu conocimiento del mundo para identificar los valores específicos que componen ese grupo. Usa la lógica en tus búsquedas de strings y no seas ingenuo en las peticiones.

    ESQUEMA DE LA BASE DE DATOS:
    {table_info}

    Pregunta del usuario: {input}
    Consulta SQL:
    """

    PROMPT_SQL = PromptTemplate(
        input_variables=["input", "table_info", "top_k"], template=sql_prompt_template
    )

    db_chain = SQLDatabaseChain.from_llm(
        llm, db, prompt=PROMPT_SQL, verbose=True, top_k=50, return_direct=True
    )

    @tool("buscar_pacientes")
    def buscar_pacientes(query: str) -> str:
        """Busca información médica en la base de datos de pacientes crónicos. Pasa SIEMPRE un único argumento de texto con la pregunta clínica completa."""
        try:
            resultado = db_chain.invoke(query)
            return str(resultado["result"])
        except Exception as e:
            return f"Error en DB: No he podido realizar la consulta. Detalles: {str(e)}"

    @tool("enviar_sms")
    def enviar_sms_tool(numero: str, mensaje: str) -> str:
        """Envía un mensaje SMS a un número de teléfono."""
        try:
            enviar_sms(numero, mensaje)
            return f"SMS enviado a {numero}"
        except Exception as e:
            print(f"Error al enviar SMS: {str(e)}")
            return f"Error al enviar SMS: {str(e)}"

    @tool("enviar_mail")
    def enviar_mail_tool(correos: str, mensaje: str) -> str:
        """Envía un correo electrónico a uno o varios destinatarios. Pasa los correos separados por comas."""
        try:
            return enviar_mail(correos, mensaje)
        except Exception as e:
            print(f"Error al enviar mail: {str(e)}")
            return f"Error al enviar correo: {str(e)}"

    tools = [buscar_pacientes, enviar_sms_tool, enviar_mail_tool]

    system_prompt = """
    Eres un asistente médico experto en análisis de bases de datos de cohortes clínicas, dotado de razonamiento clínico avanzado. Tu objetivo es entender la intención del usuario, asistir en la formulación de consultas complejas y proporcionar respuestas precisas basadas en los datos.

    REGLAS ESTRICTAS E INTELIGENCIA CLÍNICA:
    1. CAPA DE RAZONAMIENTO CLÍNICO (METACOGNICIÓN):
       - Si el usuario emplea términos clínicos abstractos, sindrómicos o subjetivos (ej. "citopenias relevantes", "enfermedad inestable", "diabético descompensado", "insuficiencia severa"), RECONOCE que estos no se pueden buscar directamente en la base de datos sin parámetros numéricos o métricas exactas (como niveles de creatinina, hemoglobina, dosis, etc.).
       - En estos casos, NO ejecutes la herramienta de búsqueda de inmediato. Usa tu conocimiento médico para descomponer el concepto complejo en variables medibles, y PREGUNTA proactivamente al usuario qué umbrales o criterios estándar desea aplicar. (Ejemplo de tono: "He notado que buscas 'citopenias relevantes'. Debido a que esto depende de múltiples factores, ¿quieres aplicar los criterios estándar o definir umbrales personalizados para:\\n• Hemoglobina\\n• Plaquetas\\n• Dosis de ruxolitinib?").
       - Esta capacidad de diálogo aplica a CUALQUIER enfermedad. Usa tu juicio clínico para guiar al usuario a definir búsquedas precisas. Solo después de aclarar los criterios, ejecuta la búsqueda.
    2. CERO ALUCINACIONES DE DATOS: Puedes y debes usar tu conocimiento médico previo ÚNICAMENTE para interpretar la pregunta, sugerir umbrales y dialogar. NUNCA inventes nombres de pacientes, identificadores (IDs), fechas o resultados de bases de datos.
    3. USO DE HERRAMIENTAS: Para obtener datos reales de pacientes, DEBES usar la herramienta provista (`buscar_pacientes`). Si la herramienta falla o devuelve registros vacíos tras una búsqueda bien parametrizada, sugiere variaciones en el diálogo, pero no inventes datos.
    4. IDENTIFICACIÓN DE PACIENTES: El identificador único del paciente es un número entero en la columna `PacienteID`. Muestra los IDs de pacientes únicos como una lista limpia, sin duplicados.
    5. DIFERENCIACIÓN DE CÓDIGOS: Valores alfanuméricos o códigos SNOMED NUNCA son equivalentes a `PacienteID`.
    6. FORMATO DE RESPUESTA: Mantén un tono clínico, conciso y profesional, promoviendo la aclaración cuando sea necesaria.
    7. MÚLTIPLES GRÁFICOS Y VISUALIZACIONES (VEGA-LITE): Si el usuario pide varios gráficos o visualizaciones, DEBES generar un bloque ```json independiente para cada gráfico, usando la especificación de Vega-Lite e incluyendo siempre los datos en "data": {"values": [...]}. No juntes todo en un solo bloque. Elige gráficos lógicos ("bar", "line", etc.).
    """

    return create_agent(llm, tools, system_prompt=system_prompt)
