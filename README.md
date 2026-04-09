# Dedalus-Datathon
Repositorio para Datathon de Dedalus 2026 CLM: https://www.dedalushackathon.com/dedalus-datathon-castilla-la-mancha-2026/


# Instalación de dependencias

## Usando `uv` (recomendado)

```bash
uv sync
```

## Usando `pip`

```bash
python -m venv .venv
source .venv/bin/activate  # o .venv\Scripts\activate en Windows

pip install .
```

# Ejecución de la aplicación

## Interfaz Web con Streamlit

Para iniciar la interfaz conversacional en el navegador web, ejecuta:

```bash
uv run streamlit run app.py
```

## Entorno de Consola

Si prefieres probar el agente directamente desde tu terminal interactiva:

```bash
uv run python chat.py
```
