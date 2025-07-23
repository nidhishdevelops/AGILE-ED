import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from config import Config
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def send_notification(subject, body):
    if not Config.EMAIL_PASSWORD or not Config.EMAIL_SENDER:
        logger.error("Email credentials not configured")
        return False
        
    try:
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = Config.EMAIL_SENDER
        msg['To'] = Config.EMAIL_RECEIVER
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
            
        logger.info("Notification email sent")
        return True
    except Exception as e:
        logger.error(f"Email error: {str(e)}")
        return False