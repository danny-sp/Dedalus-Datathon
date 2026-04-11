import os

import markdown
from fpdf import FPDF


def crear_pdf(texto_md: str, nombre_archivo: str) -> str:
    """
    Convierte texto en Markdown (incluyendo tablas) a un archivo PDF
    y lo guarda en la carpeta 'adjuntos'.
    """
    try:
        # 1. Preparar el directorio y la ruta
        os.makedirs("adjuntos", exist_ok=True)
        ruta_pdf = os.path.join("adjuntos", os.path.basename(nombre_archivo))
        # DEBUG (guardar en .txt):
        with open(ruta_pdf.replace(".pdf", ".txt"), "w", encoding="utf-8") as f:
            f.write(texto_md)

        # 2. Convertir Markdown a HTML
        # IMPORTANTE: Añadimos la extensión 'tables' para que reconozca el formato de tabla de MD
        html_texto = markdown.markdown(texto_md, extensions=["tables"])

        # 3. Inicializar el PDF
        pdf = FPDF()
        pdf.add_page(orientation="P")

        # Opcional: configurar una fuente base (fpdf2 usará esto para el texto normal)
        pdf.set_font("helvetica", size=11)

        # 4. Inyectar el HTML directamente
        # fpdf2 leerá los <h1>, <strong>, <table>, etc., y los dibujará
        pdf.write_html(html_texto)

        # 5. Guardar el PDF
        pdf.output(ruta_pdf)

        return f"PDF guardado exitosamente con formato completo en: {ruta_pdf}"

    except Exception as e:
        return f"Error al generar el PDF: {str(e)}"
