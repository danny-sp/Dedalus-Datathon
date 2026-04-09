# Dedalus-Datathon - Asistente Médico IA

Repositorio para Datathon de Dedalus 2026 CLM: https://www.dedalushackathon.com/dedalus-datathon-castilla-la-mancha-2026/

Este proyecto implementa un agente conversacional inteligente capaz de realizar consultas precisas a una base de datos de historia clínica, asistido por una capa de metacognición para comprender conceptos clínicos complejos.

## Requisitos Previos: Instalación de Ollama

El agente utiliza modelos de lenguaje locales mediatos por **Ollama**. Es necesario tenerlo instalado y descargar el modelo específico utilizado por el proyecto (`kimi-k2.5:cloud`). Puedes usar cualquier otro modelo descargado cambiando el parametro `model` en `agent.py`.

### En Windows

1. Descarga el instalador desde la [página oficial de Ollama](https://ollama.com/download/windows).
2. Ejecuta el archivo `.exe` para finalizar la instalación.
3. Abre una terminal (PowerShell o CMD) y descarga el modelo ejecutando:
   ```bash
   ollama pull kimi-k2.5:cloud
   ```

### En Linux

1. Abre tu terminal e instala Ollama con el siguiente comando:
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```
2. Una vez finalizada la instalación, inicia el servicio (si no arranca solo) y descarga el modelo:
   ```bash
   ollama pull kimi-k2.5:cloud
   ```

## Instalación de dependencias en Python

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
