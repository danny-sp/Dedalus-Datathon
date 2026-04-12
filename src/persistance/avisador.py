import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()


def enviar_sms(numero: str, mensaje: str):
    # guardar en sms/numero.txt
    with open(f"sms/{numero}.txt", "a") as f:
        f.write(mensaje + "\n")

    # Aquí iría la lógica real para enviar el SMS, por ejemplo, usando una API de terceros.


def enviar_mail(destinatarios_str: str, mensaje: str, adjunto_path: str = None):
    """
    Envía un correo real a una lista de emails (separados por coma).
    Útil para notificar a la cohorte identificada, con opción a adjuntar un PDF.
    """
    try:
        EMAIL_BOT = os.getenv("BOT_MAIL")
        PASSWORD_BOT = os.getenv("BOT_PASSWORD")

        lista_correos = [email.strip() for email in destinatarios_str.split(",")]

        for correo in lista_correos:
            msg = EmailMessage()
            msg.set_content(mensaje)
            msg["Subject"] = "Notificación Importante - Servicio de Salud"
            msg["From"] = EMAIL_BOT
            msg["To"] = correo

            if adjunto_path and os.path.exists(adjunto_path):
                with open(adjunto_path, "rb") as f:
                    pdf_data = f.read()
                msg.add_attachment(
                    pdf_data,
                    maintype="application",
                    subtype="pdf",
                    filename=os.path.basename(adjunto_path),
                )

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(EMAIL_BOT, PASSWORD_BOT)
                smtp.send_message(msg)

        return f"Éxito: Se han enviado {len(lista_correos)} correos a la cohorte."
    except Exception as e:
        return f"Error al enviar correos: {str(e)}"
