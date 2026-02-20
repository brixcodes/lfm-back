from typing import Optional
import os
import smtplib
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from pyfcm import FCMNotification
from src.config import settings
import httpx
from celery import shared_task


push_service = FCMNotification(
        service_account_file="src/lafaom.json",
        credentials=None,
        project_id="laakam-487e5"
    )

env = Environment(loader=FileSystemLoader('src/templates'))


def clean_cinetpay_string(value: str, max_length: int = 150, allow_dashes: bool = True) -> str:
    """
    Nettoie une chaîne de caractères pour CinetPay en retirant les caractères spéciaux non autorisés.
    
    Args:
        value (str): La chaîne originale.
        max_length (int): Longueur maximale (défaut: 150).
        allow_dashes (bool): Autoriser les tirets simples (défaut: True).
    
    Returns:
        str: La chaîne nettoyée.
    """
    if not value:
        return ""
    
    # Remplacer les tirets cadratins (–, —) par des tirets simples (-)
    value = value.replace('–', '-').replace('—', '-')
    
    # Supprimer les apostrophes
    value = value.replace("'", "").replace("'", "").replace("'", "")
    
    # Supprimer les parenthèses mais garder leur contenu
    value = value.replace('(', '').replace(')', '')
    
    # Supprimer les autres caractères spéciaux non autorisés
    if allow_dashes:
        # Garder lettres, chiffres, espaces, tirets simples et points
        value = re.sub(r'[^a-zA-Z0-9\s\-.]', '', value)
    else:
        # Garder seulement lettres, chiffres, espaces et points (pas de tirets)
        value = re.sub(r'[^a-zA-Z0-9\s.]', '', value)
    
    # Remplacer les espaces multiples par un seul espace
    value = re.sub(r'\s+', ' ', value)
    
    # Supprimer les espaces en début et fin
    value = value.strip()
    
    # Limiter la longueur
    if len(value) > max_length:
        value = value[:max_length].rsplit(' ', 1)[0]
    
    return value


def clean_payment_description(description: str, max_length: int = 150) -> str:
    """
    Nettoie la description de paiement en retirant les caractères spéciaux non autorisés.
    
    L'opérateur de paiement n'autorise pas les caractères spéciaux dans le paramètre "description".
    Cette fonction retire les caractères spéciaux et les remplace par des équivalents simples.
    
    Args:
        description (str): La description originale avec potentiellement des caractères spéciaux.
        max_length (int): Longueur maximale de la description (défaut: 150 caractères).
    
    Returns:
        str: La description nettoyée sans caractères spéciaux, limitée à max_length caractères.
    
    Examples:
        >>> clean_payment_description("Formation d'Auxiliaires (AVUJ) – January 2026")
        "Formation dAuxiliaires AVUJ - January 2026"
    """
    if not description:
        return "Payment"
    
    cleaned = clean_cinetpay_string(description, max_length, allow_dashes=True)
    
    # S'assurer que la description n'est pas vide après nettoyage
    if not cleaned or len(cleaned.strip()) == 0:
        return "Payment"
    
    return cleaned


class NotificationHelper :
    @staticmethod
    @shared_task  
    def send_in_app_notification(notify_data : dict):
        """
        Send an in app notification to a user, given the notification data.

        Args:
        data (Notification): The notification data.

        Returns:
        None
        """
        
        NotificationHelper.send_push_notification(data=notify_data)


    @staticmethod
    @shared_task  
    def send_push_notification(notify_data : dict):
        """
            Send an in app notification to a user, given the notification data.

            Args:
            data (Notification): The notification data.

            Returns:
            None
        """
        
        #data = {
        #    "channel": "notify-" + notify_data["user_id"],   
        #    "content" :  {
        #        "type":"notification",
        #        "data": notify_data
        #    }
        #}
        
        #NotificationHelper.send_ws_message(data=data)
        
        print(notify_data)
        response = push_service.notify( 
                fcm_token=notify_data["device_id"],
                notification_title=notify_data["title"],
                notification_body=notify_data["message"],
                notification_image=notify_data["image"],
                data_payload=notify_data["action"]
            )
        

    @staticmethod  
    @shared_task      
    def send_smtp_email(data : dict):
    
        """
        Send an email using SMTP.

        This function sends an email to the given address using an SMTP server.
        The email body can be either a plain text string or an HTML string
        rendered from a template.

        Args:
        to_email (str): The email address to send the email to.
        subject (str): The email subject.
        body (str): The email body (optional).
        template_name (str): The name of the template to use for the email body (optional).
        context (dict): The context to pass to the template (optional).

        Returns:
        None
        """
        message = MIMEMultipart()
        message["From"] = settings.EMAILS_FROM_EMAIL
        message["To"] = data["to_email"]
        message["Subject"] =  data["subject"]
        if "context" not in data:
            data["context"] = {}
        data["context"]["app_name"] = settings.EMAILS_FROM_NAME
        data["context"]["current_year"] = datetime.now().year

        body = data.get("body", "")
        if data.get("template_name") :
            template = env.get_template(data["lang"] + "/" + data["template_name"])
            body = template.render(data["context"])

            try:
                # Attach logo image for CID reference
                if os.path.exists("src/static/logo.png"):
                    with open("src/static/logo.png", "rb") as f:
                        logo_data = f.read()
                        image = MIMEImage(logo_data)
                        image.add_header('Content-ID', '<logo>')
                        image.add_header('Content-Disposition', 'inline', filename='logo.png')
                        message.attach(image)
            except Exception as e:
                print(f"Could not attach logo: {e}")

        message.attach(MIMEText(body, "html" if data.get("template_name") else "plain"))     
            
        try:
            if settings.SMTP_ENCRYPTION == "TLS":
                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                    server.starttls()
                    
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.send_message(message)
                    
                    print('email send ' + data["to_email"] )
            else:
                with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                    
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.send_message(message)
                    
                    print('email send ' + data["to_email"] )
                
    
                
        except smtplib.SMTPAuthenticationError as e:
            print(f"Authentication error with {settings.SMTP_HOST}:{settings.SMTP_PORT} ({settings.SMTP_ENCRYPTION}): {e}")
            if "5.7.9" in str(e):
                print("HINT: This error (5.7.9) usually means an App Password is required, or Gmail is blocking the connection. Visit https://accounts.google.com/DisplayUnlockCaptcha while logged in as " + settings.SMTP_USER)
        except Exception as e:
            print(f"An error occurred while sending email via {settings.SMTP_HOST}:{settings.SMTP_PORT}: {e}")    


    @staticmethod  
    @shared_task
    def send_mailgun_email(data: dict):
        """
        Send an email using Mailgun API.

        This function sends an email to the given address using the Mailgun API.
        The email body can be either a plain text string or an HTML string
        rendered from a template.

        Args:
        data (dict): A dictionary containing:
            - to_email (str): The email address to send the email to.
            - subject (str): The email subject.
            - body (str): The email body (optional).
            - template_name (str): The name of the template to use for the email body (optional).
            - context (dict): The context to pass to the template (optional).

        Returns:
        None
        """
        # Prepare the body
        body = data.get("body", "")
    
        if data.get("template_name") :
            template = env.get_template(data["lang"] + "/"  + data["template_name"])
            body = template.render(data["context"])
            
        url = f"https://{settings.MAILGUN_ENDPOINT}/v3/{settings.MAILGUN_DOMAIN}/messages"

        # Email payload
        payload = {
            "from": settings.EMAILS_FROM_EMAIL,
            "to": data["to_email"],
            "subject": data["subject"],
            "text": body if not data.get("template_name") else None,
            "html": body if data.get("template_name") else None,
        }
        
    
        
        try:
            with httpx.Client() as client:
                response =   client.post(url, data=payload,auth=("api", settings.MAILGUN_SECRET))
            
                if response.status_code == 200:
                    
                    print(f"Email sent successfully to {data['to_email']} with Mailgun API")
                else:
                    print(f"Failed to send email: {response.status_code} - {response.text} with Mailgun API")


        except httpx.HTTPError as e:
            print(f"An error occurred while sending the email: {e}")


    @staticmethod  
    @shared_task
    def send_brevo_email(data: dict):
        """
        Send an email using Brevo API.

        Args:
        data (dict): A dictionary containing:
            - to_email (str): The email address to send the email to.
            - subject (str): The email subject.
            - body (str): The email body (optional).
            - template_name (str): The name of the template to use for the email body (optional).
            - context (dict): The context to pass to the template (optional).
            - lang (str): Language code.

        Returns:
        None
        """
        body = data.get("body", "")
    
        if "context" not in data:
            data["context"] = {}
        data["context"]["current_year"] = datetime.now().year
    
        if data.get("template_name") :
            template = env.get_template(data["lang"] + "/"  + data["template_name"])
            body = template.render(data["context"])
            
        url = "https://api.brevo.com/v3/smtp/email"

        payload = {
            "sender": {"name": settings.EMAILS_FROM_NAME, "email": settings.EMAILS_FROM_EMAIL},
            "to": [{"email": data["to_email"]}],
            "subject": data["subject"],
            "htmlContent": body if data.get("template_name") or body.startswith("<") else None,
            "textContent": body if not data.get("template_name") and not body.startswith("<") else None,
        }
        
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": settings.BREVO_API_KEY
        }
        
        try:
            with httpx.Client() as client:
                response = client.post(url, json=payload, headers=headers)
            
                if response.status_code in [200, 201]:
                    print(f"Email sent successfully to {data['to_email']} with Brevo API")
                else:
                    print(f"Failed to send email: {response.status_code} - {response.text} with Brevo API")

        except httpx.HTTPError as e:
            print(f"An error occurred while sending the email with Brevo: {e}")
