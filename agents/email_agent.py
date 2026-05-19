import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from config import Config
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def send_notification(subject, body, to_email=None):
    if not Config.EMAIL_PASSWORD or not Config.EMAIL_SENDER:
        logger.error("Email credentials not configured")
        return False
        
    recipient = to_email if to_email else Config.EMAIL_RECEIVER
    
    try:
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = Config.EMAIL_SENDER
        msg['To'] = recipient
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        html = f"""<html><body>
            <h2>Learning System Notification</h2>
            <p>{body}</p>
            <p><strong>System:</strong> Personalized Learning Agent</p>
            <p><strong>Timestamp:</strong> {timestamp}</p>
        </body></html>"""
        
        msg.attach(MIMEText(html, 'html'))
        
        # Use SMTP_SSL with port 465 (or starttls with 587)
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(Config.EMAIL_SENDER, Config.EMAIL_PASSWORD)
            server.send_message(msg)
            
        logger.info(f"Notification email sent to {recipient}")
        return True
    except Exception as e:
        logger.error(f"Email error to {recipient}: {str(e)}")
        # Log full traceback for debugging
        import traceback
        logger.error(traceback.format_exc())
        return False