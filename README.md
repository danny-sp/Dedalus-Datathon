# Dedalus-Datathon - Asistente Médico IA

Repositorio para Datathon de Dedalus 2026 CLM: https://www.dedalushackathon.com/dedalus-datathon-castilla-la-mancha-2026/

Este proyecto implementa un agente conversacional inteligente capaz de realizar consultas precisas a una base de datos de historia clínica, asistido por una capa de metacognición para comprender conceptos clínicos complejos.

## Instalación de dependencias

### Usando `uv` (recomendado)

```bash
uv sync
```

### Usando `pip`

```bash
python -m venv .venv
source .venv/bin/activate  # o .venv\Scripts\activate en Windows

pip install -e .
```

## Inicialización de Base de Datos

Antes de ejecutar la aplicación, debes generar la base de datos `hospital.db` a partir de los datos `csv` proporcionados:
```bash
uv run python setup_db.py
```

## Ejecución de la aplicación

El acceso a la aplicación está centralizado en el módulo `main.py`, el cual está diseñado considerando una arquitectura limpia (separando las capas de dominio y de presentación).

### Interfaz Web con Streamlit

Para iniciar la interfaz gráfica enriquecida con análisis y visualizaciones (Vega-Lite) en el navegador:

```bash
uv run python main.py
```

### Entorno de Consola (CLI)

Si prefieres probar el agente directamente desde tu terminal interactiva:

```bash
uv run python main.py cli
```

## Características Clave
- **Motor LangChain & Local LLM**: Emplea base de conocimientos médica generada por un modelo local (vía Ollama) evitando fugas de privacidad.
- **Razonamiento Meta-Cognitivo**: El modelo detiene la ejecución automática en caso de ambigüedad médica para buscar clarificaciones (ej. ajustar umbrales de hemoglobina, plaquetas).
- **Traducción NLU a SQL**: Permite a profesionales clínicos interrogar datos en lenguaje fluido, generando sentencias altamente precisas.
