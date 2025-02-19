from functools import wraps
from flask import session, redirect, url_for
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import base64
from datetime import datetime, timedelta

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

# Dictionary to store the last notification time for each event
last_notification = {}

def can_send_notification(event_key, cooldown_minutes=5):
    current_time = datetime.utcnow()
    last_time = last_notification.get(event_key)
    
    if last_time is None or (current_time - last_time) > timedelta(minutes=cooldown_minutes):
        last_notification[event_key] = current_time
        return True
    return False

def send_email(to_email, subject, body, image_data=None):
    # Email configuration
    sender_email = "abhijithsnair2025@mca.ajce.in"  # Replace with your email
    sender_password = "yybvyohzgjqwjajz"   # Replace with your app password

    # Create message
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = to_email
    message["Subject"] = subject

    # Add body to email
    message.attach(MIMEText(body, "plain"))

    if image_data:
        # Remove the "data:image/jpeg;base64," prefix if present
        if "base64," in image_data:
            image_data = image_data.split("base64,")[1]
        
        # Decode base64 image
        image_bytes = base64.b64decode(image_data)
        image = MIMEImage(image_bytes)
        image.add_header('Content-ID', '<image1>')
        message.attach(image)

    try:
        # Create SMTP session
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        
        # Login to the server
        server.login(sender_email, sender_password)

        # Send email
        text = message.as_string()
        server.sendmail(sender_email, to_email, text)
        
        # Close session
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False