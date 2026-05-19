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
    api_key = getattr(Config, 'SENDGRID_API_KEY', None)
    from_email = getattr(Config, 'FROM_EMAIL', None)
    
    if not api_key or not from_email:
        logger.error("SendGrid credentials not configured: missing API key or FROM_EMAIL")
        return False

    # Strip any whitespace/newlines from the API key
    api_key = api_key.strip()
    if not api_key:
        logger.error("SendGrid API key is empty after stripping")
        return False

    recipient = to_email if to_email else getattr(Config, 'EMAIL_RECEIVER', None)
    if not recipient:
        logger.error("No recipient email provided")
        return False

    try:
        message = Mail(
            from_email=from_email,
            to_emails=recipient,
            subject=subject,
            html_content=body
        )
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        if response.status_code == 202:
            logger.info(f"Email sent successfully to {recipient}")
            return True
        else:
            logger.error(f"SendGrid error: {response.status_code} - {response.body}")
            return False
    except Exception as e:
        logger.error(f"SendGrid exception: {str(e)}")
        # Log first few chars of API key for debugging (not the whole key)
        logger.error(f"API key starts with: {api_key[:10]}... length: {len(api_key)}")
        return False