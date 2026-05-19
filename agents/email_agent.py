import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from config import Config
from datetime import datetime

logger = logging.getLogger(__name__)

def send_notification(subject, body, to_email=None):
    """
    Send email using SendGrid (free tier, 100 emails/day)
    """
    if not Config.SENDGRID_API_KEY or not Config.FROM_EMAIL:
        logger.error("SendGrid credentials not configured")
        return False

    recipient = to_email if to_email else Config.EMAIL_RECEIVER
    
    try:
        message = Mail(
            from_email=Config.FROM_EMAIL,
            to_emails=recipient,
            subject=subject,
            html_content=body
        )
        sg = SendGridAPIClient(Config.SENDGRID_API_KEY)
        response = sg.send(message)
        if response.status_code == 202:
            logger.info(f"Email sent successfully to {recipient}")
            return True
        else:
            logger.error(f"SendGrid error: {response.status_code} - {response.body}")
            return False
    except Exception as e:
        logger.error(f"SendGrid exception: {str(e)}")
        return False