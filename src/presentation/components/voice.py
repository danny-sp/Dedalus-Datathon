import json
import os
import streamlit.components.v1 as components

def load_js_file(filename):
    """Loads a JS file from the javascript directory."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "javascript", filename)
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def render_tts_component(tts_data_dict):
    """Renders the JS component for Text-To-Speech."""
    js_template = load_js_file("tts.js")
    json_tts_data = json.dumps(tts_data_dict)
    
    # Inject data into JS placeholder before rendering
    js_code = js_template.replace("__TTS_DATA__", json_tts_data)
    components.html(f"<script>{js_code}</script>", height=0, width=0)

def render_stt_component():
    """Renders the JS component for Speech-To-Text."""
    js_code = load_js_file("stt.js")
    components.html(f"<script>{js_code}</script>", height=0, width=0)
