from datetime import datetime

from langchain.agents import create_agent
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool
from langchain_experimental.sql import SQLDatabaseChain
from langchain_ollama import ChatOllama

from src.persistance.avisador import enviar_mail, enviar_sms
from src.persistance.generador_pdf import crear_pdf


def get_agent_executor():
    """
    Inicializa y devuelve el agente ejecutor de LangChain configurado
    con SQLite y ChatOllama.
    """
    db = SQLDatabase.from_uri("sqlite:///hospital.db")

    # Usamos kimi-k2.5:cloud como en app.py
    llm = ChatOllama(
        model="kimi-k2.5:cloud",
        temperature=0.3,
    )

    sql_prompt_template = """
    Eres un Arquitecto de Datos experto en SQLite y análisis de registros médicos electrónicos. Tu única tarea es traducir la pregunta del usuario en una consulta SQL sintácticamente correcta y optimizada para SQLite.

    REGLAS PARA LA GENERACIÓN DEL SQL:
    1. FORMATO ESTRICTO: Devuelve ÚNICAMENTE la consulta SQL en texto plano. NO incluyas delimitadores de bloque de código (como ```sql o ```). NO proporciones explicaciones, saludos ni comentarios adicionales.
    2. RESTRICCIÓN DE ESQUEMA: Utiliza exclusivamente las tablas y columnas detalladas en el esquema proporcionado. No asumas la existencia de otros campos.
    3. NOMENCLATURA DE TABLAS: Recuerda que las tablas disponibles se nombran sin el prefijo 'cohorte_' (las tablas exactas son: alergias, condiciones, encuentros, medicationes, pacientes, procedimientos, doctores).
    4. RELACIONES (JOINs): La clave primaria y foránea que conecta las tablas de salud es la columna `PacienteID`. Usa esta columna de forma explícita al realizar sentencias JOIN entre ellas. La tabla `doctores` puede relacionarse con los pacientes a través de la columna `provincia` (o `Provincia` en pacientes) y el área de especialidad médica correspondiente.
    5. OPTIMIZACIÓN: Si la pregunta implica filtrado temporal, ten en cuenta el formato de fecha estándar de las columnas de fechas (`Fecha_inicio`, `Fecha_diagnostico`, etc.).
    6. SELECCIÓN DE COLUMNAS: Si la consulta involucra pacientes o personas, SIEMPRE haz `SELECT` de TODOS los campos identificativos posibles de la tabla pacientes (como `PacienteID`, nombre, apellidos, teléfono, correo) además de los datos solicitados. Esto es vital para mantener un rico contexto histórico de los individuos durante la conversación.
    7. CONDICIONES MÚLTIPLES: Para consultas con "Y" (AND lógico en distintas filas, ej: Asma Y Diabetes), asegúrate de usar `INTERSECT` o un `GROUP BY PacienteID HAVING COUNT(DISTINCT condicion) = 2` para encontrar pacientes que cumplan AMBAS.
    8. CÓDIGOS SNOMED: Si la pregunta no menciona explícitamente "Códigos SNOMED", busca por la descripción de la condición, procedimiento o medicación. Solo usa los códigos SNOMED si el usuario los incluye en su pregunta.
    9. CONTEO DISTINTO: Cuando se pregunte "cuántos" pacientes, asegúrate siempre de usar `COUNT(DISTINCT PacienteID)`, ya que un mismo paciente puede tener múltiples registros.
    10. EXPANSIÓN SEMÁNTICA DE GRUPOS/CATEGORÍAS: Si el usuario menciona conceptos amplios, regiones generales o categorías (ej: "andaluces", "castellanomanchegos", "antibióticos", etc.), usa tu conocimiento del mundo para identificar los valores específicos que componen ese grupo. Usa la lógica en tus búsquedas de strings y no seas ingenuo en las peticiones.
    11. NOMBRES Y APELLIDOS: Los nombres y apellidos de los pacientes están en minúsculas, sin acentos, y con guiones bajos en lugar de espacios (ej: "juan_perez"). Si el usuario pregunta por nombres o apellidos, asegúrate de reflejar este formato en tu consulta.
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

    @tool("consultar_base_datos")
    def consultar_base_datos(query: str) -> str:
        """Consulta información en la base de datos clínica. Útil para buscar pacientes, encuentros, diagnósticos, medicaciones y médicos. Pasa SIEMPRE un único argumento de texto con la pregunta completa."""
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
    def enviar_mail_tool(correos: str, mensaje: str, ruta_archivo: str = None) -> str:
        """Envía un correo electrónico a uno o varios destinatarios. REGLA DE PRIVACIDAD: NUNCA envíes PDFs, listas de pacientes o información de salud de otros pacientes a un paciente. Los informes médicos y agendas de citas SOLO deben enviarse a los médicos. Pasa los correos separados por comas. El mensaje es el cuerpo del correo, y ruta_archivo es la ruta al PDF que quieres adjuntar (puede ser None si no hay adjunto)."""
        try:
            return enviar_mail(correos, mensaje, ruta_archivo)
        except Exception as e:
            print(f"Error al enviar mail: {str(e)}")
            return f"Error al enviar correo: {str(e)}"

    @tool("guardar_pdf")
    def guardar_pdf_tool(texto: str, nombre_archivo: str) -> str:
        """Genera y guarda un documento PDF. El parámetro 'texto' DEBE estar en formato Markdown (usa # para títulos, ** para negrita, y el formato de tablas Markdown si hay datos tabulares)."""
        return crear_pdf(texto, nombre_archivo)

    tools = [consultar_base_datos, enviar_sms_tool, enviar_mail_tool, guardar_pdf_tool]

    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    dia_semana = datetime.now().strftime("%A")
    system_prompt = f"""
    Eres un asistente médico experto en análisis de bases de datos de cohortes clínicas, dotado de razonamiento clínico avanzado. Tu objetivo es entender la intención del usuario, asistir en la formulación de consultas complejas y proporcionar respuestas precisas basadas en los datos.
    Tu nombre es Chismoso.

    LA FECHA ACTUAL ES: {fecha_hoy} (Día evaluado como: {dia_semana}). Usa esta fecha para entender correctamente referencias temporales relativas como "ayer", "mañana", "el próximo lunes" o "el mes que viene".

    REGLAS ESTRICTAS E INTELIGENCIA CLÍNICA:
    1. CAPA DE RAZONAMIENTO CLÍNICO (METACOGNICIÓN):
       - Si el usuario emplea términos clínicos abstractos, sindrómicos o subjetivos (ej. "citopenias relevantes", "enfermedad inestable", "diabético descompensado", "insuficiencia severa"), RECONOCE que estos no se pueden buscar directamente en la base de datos sin parámetros numéricos o métricas exactas (como niveles de creatinina, hemoglobina, dosis, etc.).
       - En estos casos, NO ejecutes la herramienta de búsqueda de inmediato. Usa tu conocimiento médico para descomponer el concepto complejo en variables medibles, y PREGUNTA proactivamente al usuario qué umbrales o criterios estándar desea aplicar. (Ejemplo de tono: "He notado que buscas 'citopenias relevantes'. Debido a que esto depende de múltiples factores, ¿quieres aplicar los criterios estándar o definir umbrales personalizados para:\\n• Hemoglobina\\n• Plaquetas\\n• Dosis de ruxolitinib?").
       - Esta capacidad de diálogo aplica a CUALQUIER enfermedad. Usa tu juicio clínico para guiar al usuario a definir búsquedas precisas. Solo después de aclarar los criterios, ejecuta la búsqueda.
    2. CERO ALUCINACIONES DE DATOS: Puedes y debes usar tu conocimiento médico previo ÚNICAMENTE para interpretar la pregunta, sugerir umbrales y dialogar. NUNCA inventes nombres de pacientes, identificadores (IDs), fechas o resultados de bases de datos.
    3. USO DE HERRAMIENTAS: Para obtener datos reales (de pacientes, médicos, patologías, etc.), DEBES usar la herramienta provista (`consultar_base_datos`). Si la herramienta falla o devuelve registros vacíos tras una búsqueda bien parametrizada, sugiere variaciones en el diálogo, pero no inventes datos.
    4. IDENTIFICACIÓN DE PACIENTES: El identificador único del paciente es un número entero en la columna `PacienteID`. Muestra los IDs de pacientes únicos como una lista limpia, sin duplicados.
    5. DIFERENCIACIÓN DE CÓDIGOS: Valores alfanuméricos o códigos SNOMED NUNCA son equivalentes a `PacienteID`.
    6. FORMATO DE RESPUESTA: Mantén un tono clínico, conciso y profesional, promoviendo la aclaración cuando sea necesaria.
    7. MÚLTIPLES GRÁFICOS Y VISUALIZACIONES (VEGA-LITE): Si el usuario pide varios gráficos o visualizaciones, DEBES generar un bloque ```json independiente para cada gráfico, usando la especificación de Vega-Lite e incluyendo siempre los datos en "data": {{"values": [...]}}. No juntes todo en un solo bloque. Elige gráficos lógicos ("bar", "line", etc.).
    8. IDENTIDAD Y PRESENTACIÓN: Si el usuario saluda, pregunta quién eres o es el primer intercambio de la conversación, preséntate como Chismoso en una frase breve. No uses siempre la misma redacción; varía la presentación de forma natural.
    9. PRIVACIDAD - ALERTA ROJA (HIPAA/GDPR): NUNCA distribuyas informes, ficheros PDF con listas de pacientes, historiales médicos ni agendas globales a los PACIENTES. Cualquier listado o PDF médico debe ser enviado única y exclusivamente a los MÉDICOS correspondientes por correo. Los pacientes solo pueden recibir mensajes personalizados de sus propias citas, normalmente mediante SMS y en formato puramente textual (sin adjuntos).
    """

    return create_agent(llm, tools, system_prompt=system_prompt)
