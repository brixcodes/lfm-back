from typing import Optional
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
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
        data["context"]["app_name"] = settings.EMAILS_FROM_NAME

        if data["template_name"] :
            template = env.get_template(data["lang"] + "/" + data["template_name"])
            body = template.render(data["context"])

        message.attach(MIMEText(body, "html" if data["template_name"] else "plain"))     
            
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
            print(f"Authentication error: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")    


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
