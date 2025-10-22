
from pydantic import BaseModel
from src.config import settings

from src.helper.schemas import EMAIL_CHANNEL

from src.helper.utils import NotificationHelper


class NotificationBase(BaseModel):
    email : str
    email_template : str = "email_base"
    lang : str = "en"
    
    def email_data(self):
        return {}
    
    
    
    def send_notification(self) :
        data = self.email_data()
        if settings.EMAIL_CHANNEL == EMAIL_CHANNEL.SMTP :
            NotificationHelper.send_smtp_email.delay( data)
        else : 
            NotificationHelper.send_mailgun_email.delay( data)
        return True
            



class LoginAlertNotification(NotificationBase) :

    subject : str = "Login Alert"
    email_template : str = "login_alert_email.html"
    device : str = ""  
    date : str = ""
    
    def email_data(self)->dict :
        return{
            "to_email" :self.email,
            "subject":self.subject,
            "template_name":self.email_template ,
            "lang":self.lang,
            "context":{
                    "device":self.device,
                    "date": self.date
                } 
        } 
        

class AccountVerifyNotification(NotificationBase) :

    subject : str = "Email Validation"
    email_template : str = "verify_email.html"
    code : str = ""  
    time : int = 30
    
    def email_data(self)->dict :
        return{
            "to_email" :self.email,
            "subject":self.subject,
            "template_name":self.email_template ,
            "lang":self.lang,
            "context":{
                    "code":self.code,
                    "time": self.time
                } 
        } 
        

        
class ForgottenPasswordNotification(NotificationBase) :

    subject : str = "Forgotten Password"
    email_template : str = "forgotten_password.html"
    code : str = ""  
    time : int = 30 
    
    def email_data(self)->dict :
        return{
            "to_email" :self.email,
            "subject":self.subject,
            "template_name":self.email_template ,
            "lang":self.lang,
            "context":{
                    "code":self.code,
                    "time": self.time
                } 
        } 
        

        
        
class ChangeAccountNotification(NotificationBase) :

    subject : str = "Change Email"
    email_template : str = "change_email.html" 
    code : str = ""  
    time : int = 30  
        
        
    def email_data(self)->dict :
        return{
            "to_email" :self.email,
            "subject":self.subject,
            "template_name":self.email_template ,
            "lang":self.lang,
            "context":{
                    "code":self.code,
                    "time": self.time
                } 
        } 

        
        
class TwoFactorAuthNotification(NotificationBase) :

    subject : str = "Two Factor Authentication"
    email_template : str = "2fa_auth_email.html"  
    code : str = ""  
    time : int = 30  
        
        
    def email_data(self)->dict :
        return{
            "to_email" :self.email,
            "subject":self.subject,
            "template_name":self.email_template ,
            "lang":self.lang,
            "context":{
                    "code":self.code,
                    "time": self.time
                } 
        } 
        
        
        
class WelcomeNotification(NotificationBase) :

    subject : str = "Welcome to La'akam"
    email_template : str = "welcome_email.html"  
        
        
    def email_data(self)->dict :
        return{
            "to_email" :self.email,
            "subject":self.subject,
            "template_name":self.email_template ,
            "lang":self.lang,
            "context":{
                } 
        }

class SendPasswordNotification(NotificationBase) :

    subject : str = "Account Password"
    email_template : str = "password_email.html"  
    name : str = ""
    password : str = ""
        
        
    def email_data(self)->dict :
        return{
            "to_email" :self.email,
            "subject":self.subject,
            "template_name":self.email_template ,
            "lang":self.lang,
            "context":{
                    "user_name":self.name,
                    "user_password":self.password
                } 
        }

class JobApplicationConfirmationNotification(NotificationBase) :

    subject : str = "Job Application Confirmation"
    email_template : str = "job_application_confirmation.html"
    application_number : str = ""
    job_title : str = ""
    candidate_name : str = ""
    
    def email_data(self) -> dict :
        return{
            "to_email" :self.email,
            "subject":self.subject,
            "template_name":self.email_template ,
            "lang":self.lang,
            "context":{
                    "application_number":self.application_number,
                    "job_title":self.job_title,
                    "candidate_name":self.candidate_name
                } 
        }


class JobApplicationOTPNotification(NotificationBase) :

    subject : str = "Job Application Update Code"
    email_template : str = "job_application_otp.html"
    code : str = ""
    time : int = 30
    application_number : str = ""
    candidate_name : str = ""
    
    def email_data(self) -> dict :
        return{
            "to_email" :self.email,
            "subject":self.subject,
            "template_name":self.email_template ,
            "lang":self.lang,
            "context":{
                    "code":self.code,
                    "time":self.time,
                    "application_number":self.application_number,
                    "candidate_name":self.candidate_name
                } 
        } 

class CabinetCredentialsNotification(NotificationBase):
    subject: str = "Identifiants de connexion - Cabinet LAFAOM"
    email_template: str = "cabinet_credentials.html"
    username: str = ""
    temporary_password: str = ""
    login_url: str = ""
    company_name: str = ""
    
    def email_data(self) -> dict:
        return {
            "to_email": self.email,
            "subject": self.subject,
            "template_name": self.email_template,
            "lang": self.lang,
            "context": {
                "username": self.username,
                "temporary_password": self.temporary_password,
                "login_url": self.login_url,
                "company_name": self.company_name
            }
        }

class JobApplicationCredentialsNotification(NotificationBase):
    subject: str = "Identifiants de connexion - Candidature d'emploi LAFAOM"
    email_template: str = "job_application_credentials.html"
    username: str = ""
    temporary_password: str = ""
    login_url: str = ""
    candidate_name: str = ""
    
    def email_data(self) -> dict:
        return {
            "to_email": self.email,
            "subject": self.subject,
            "template_name": self.email_template,
            "lang": self.lang,
            "context": {
                "username": self.username,
                "temporary_password": self.temporary_password,
                "login_url": self.login_url,
                "candidate_name": self.candidate_name
            }
        }

class NotificationService:
    def __init__(self):
        pass
    
    async def send_cabinet_credentials_email(self, credentials):
        """Envoyer les identifiants de connexion au cabinet"""
        notification = CabinetCredentialsNotification(
            email=credentials.email,
            username=credentials.username,
            temporary_password=credentials.temporary_password,
            login_url=credentials.login_url,
            company_name=credentials.company_name if hasattr(credentials, 'company_name') else "Cabinet"
        )
        return notification.send_notification()
    
    async def send_job_application_credentials_email(self, credentials_data):
        """Envoyer les identifiants de connexion pour les candidatures d'emploi"""
        notification = JobApplicationCredentialsNotification(
            email=credentials_data["email"],
            username=credentials_data["username"],
            temporary_password=credentials_data["temporary_password"],
            login_url=credentials_data["login_url"],
            candidate_name=credentials_data["candidate_name"]
        )
        return notification.send_notification()
        