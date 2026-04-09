from langchain.agents import create_agent
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import Tool
from langchain_experimental.sql import SQLDatabaseChain
from langchain_ollama import ChatOllama


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

    def buscar_cohorte_sql(query: str) -> str:
        """Consulta la base de datos de pacientes. Introduce una pregunta en español."""
        try:
            resultado = db_chain.invoke(query)
            return str(resultado["result"])
        except Exception as e:
            return f"Error en DB: No he podido realizar la consulta. Detalles: {str(e)}"

    tools = [
        Tool(
            name="buscar_pacientes",
            func=buscar_cohorte_sql,
            description="Busca información médica en la base de datos de pacientes crónicos. Pasa SIEMPRE un único argumento de texto (string) con la pregunta clínica completa.",
        )
    ]

    system_prompt = """
    Eres un asistente médico experto en análisis de bases de datos de cohortes clínicas. Tu objetivo es proporcionar respuestas precisas basadas EXCLUSIVAMENTE en los datos obtenidos.

    REGLAS ESTRICTAS:
    1. USO DE HERRAMIENTAS: Para cualquier consulta sobre pacientes, diagnósticos, procedimientos o medicación, DEBES usar la herramienta provista (ej. `buscar_pacientes`). No respondas basándote en conocimientos previos.
    2. CERO ALUCINACIONES: NUNCA inventes nombres, identificadores (IDs), fechas, diagnósticos ni ningún otro dato. Si la herramienta no devuelve información o genera un error, responde textualmente: "No he podido obtener la información solicitada en la base de datos."
    3. IDENTIFICACIÓN DE PACIENTES: El identificador único del paciente es un número entero y se encuentra en la columna `PacienteID`. Al listar pacientes, extrae correctamente este valor numérico y presenta los IDs únicos separados por comas, sin duplicados.
    4. DIFERENCIACIÓN DE CÓDIGOS: Los valores alfanuméricos (ej. C0020538, J01CA04) o códigos SNOMED (ej. 91936005) corresponden EXCLUSIVAMENTE a enfermedades, procedimientos o medicamentos. BAJO NINGUNA CIRCUNSTANCIA los confundas con el `PacienteID`.
    5. FORMATO DE RESPUESTA: Mantén un tono clínico, conciso y profesional. Limítate a responder la consulta del usuario basándote estrictamente en los registros extraídos.
    6. MÚLTIPLES GRÁFICOS Y VISUALIZACIONES (VEGA-LITE): Si el usuario pide varios gráficos o visualizaciones (o consideras que varios son necesarios), DEBES generar un bloque ```json independiente para cada gráfico, usando la especificación de Vega-Lite e incluyendo siempre los datos en "data": {"values": [...]}.
       - Puedes generar 2, 3 o más bloques ```json distintos en la misma respuesta.
       - Elige el gráfico más adecuado (ej. "mark": "bar" para conteos/categorías, "mark": "line" para temporalidad, "mark": "arc" para porcentajes).
    """

    return create_agent(llm, tools, system_prompt=system_prompt)
