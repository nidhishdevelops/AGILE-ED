import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from config import Config
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def send_notification(subject, body, to_email=None):
    """
    Send an email notification.
    
    Args:
        subject: Email subject
        body: HTML email body
        to_email: Recipient email address. If None, uses Config.EMAIL_RECEIVER
    """
    if not Config.EMAIL_PASSWORD or not Config.EMAIL_SENDER:
        logger.error("Email credentials not configured")
        return False
        
    # Use provided email or fallback
    recipient = to_email if to_email else Config.EMAIL_RECEIVER
    
    try:
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = Config.EMAIL_SENDER
        msg['To'] = recipient
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Ensure body is already HTML (as generated in quiz_agent)
        html = f"""<html><body>
            <h2>Learning System Notification</h2>
            <p>{body}</p>
            <p><strong>System:</strong> Personalized Learning Agent</p>
            <p><strong>Timestamp:</strong> {timestamp}</p>
        </body></html>"""
        
        msg.attach(MIMEText(html, 'html'))
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(Config.EMAIL_SENDER, Config.EMAIL_PASSWORD)
            server.send_message(msg)
            
        logger.info(f"Notification email sent to {recipient}")
        return True
    except Exception as e:
        logger.error(f"Email error to {recipient}: {str(e)}")
        return False