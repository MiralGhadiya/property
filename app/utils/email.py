#app/utils/email.py

import os
import smtplib
from pathlib import Path

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

from app.core.config_manager import get_config

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.utils.logger_config import app_logger as logger

from dotenv import load_dotenv

load_dotenv()

# EMAIL_USER = os.getenv("EMAIL_USER")
# EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
# FRONTEND_URL = os.getenv("FRONTEND_URL", "https://desktopvaluation.in")
# ADMIN_FEEDBACK_EMAILS = (os.getenv("ADMIN_FEEDBACK_EMAILS", "").split(","))


def get_email_user():
    return get_config("EMAIL_USER")

def get_email_password():
    return get_config("EMAIL_PASSWORD")

def get_frontend_url():
    return get_config("FRONTEND_URL", "https://desktopvaluation.in")

def get_admin_feedback_emails():
    return get_config("ADMIN_FEEDBACK_EMAILS", "").split(",")
SMTP_URL = "smtp.gmail.com"

# if not get_email_user() or not get_email_password():
#     logger.error("EMAIL_USER or EMAIL_PASSWORD not configured")
    
    
_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "emails"

_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


def _render(template_name: str, **ctx) -> str:
    """Render a Jinja2 email template with the given context."""
    return _jinja_env.get_template(template_name).render(**ctx)



def send_reset_email(to_email: str, link: str):
    logger.info(f"Sending password reset email to={to_email}")

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Reset your password - Desktop Valuation"
        msg["From"] = get_email_user()
        msg["To"] = to_email

        text_body = f"""
Reset your Desktop Valuation password.

Open the link below:
{link}

This link will expire in 24 hours.
If you didn't request this, ignore this email.
        """

        html_body = f"""
        <html>
        <body style="font-family:Arial;padding:20px">
            <h2>Reset your password</h2>
            <p>Click the button below to reset your password.</p>

            <a href="{link}" 
               style="
               display:inline-block;
               padding:12px 24px;
               background:#0D2B23;
               color:white;
               text-decoration:none;
               border-radius:6px;">
               Reset Password
            </a>

            <p style="margin-top:20px">
            This link will expire in 24 hours.
            </p>

            <p>If you didn't request this email, ignore it.</p>
        </body>
        </html>
        """

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL(SMTP_URL, 465) as server:
            server.login(get_email_user(), get_email_password())
            server.send_message(msg)

    except Exception:
        logger.exception("Failed to send reset email")
        raise
        

# def send_verification_email(to_email: str, link: str):
#     logger.info(f"Sending verification email to={to_email}")

#     try:
#         msg = MIMEText(f"Verify your email address:\n\n{link}")
#         msg["Subject"] = "Verify Your Email"
#         msg["From"] = EMAIL_USER
#         msg["To"] = to_email

#         with smtplib.SMTP_SSL(SMTP_URL, 465) as server:
#             server.login(EMAIL_USER, EMAIL_PASSWORD)
#             server.send_message(msg)
            
#         logger.info(f"Verification email sent to={to_email}")
        
#     except Exception:
#         logger.exception(f"Failed to send verification email to={to_email}")
#         raise


def send_verification_email(to_email: str, link: str):
    logger.info(f"Sending verification email to={to_email}")

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Verify Your Email - Desktop Valuation"
        msg["From"] = get_email_user()
        msg["To"] = to_email

        # Plain-text fallback
        text_body = (
            "Verify your email address for Desktop Valuation.\n\n"
            f"Open this link in your browser:\n{link}\n\n"
            "This link expires in 24 hours.\n"
            "If you did not create an account, please ignore this email."
        )

        # HTML body rendered from template
        html_body = _render(
            "email_verification.html",
            link=link,
            frontend_url=get_frontend_url(),
        )

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL(SMTP_URL, 465) as server:
            server.login(get_email_user(), get_email_password())
            server.send_message(msg)

        logger.info(f"Verification email sent to={to_email}")

    except Exception:
        logger.exception(f"Failed to send verification email to={to_email}")
        raise


def send_pdf_email(
    to_email: str,
    subject: str,
    client_name: str,
    pdf_bytes: bytes,
    filename: str,
):
    logger.info(f"Sending PDF email to={to_email} filename={filename}")

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = get_email_user()
        msg["To"] = to_email
        msg["Subject"] = subject

        # ---- Plain text ----
        text_message = f"""
            Dear {client_name},

            Greetings!

            Please find attached your Desktop Valuation Report.

            Best regards,
            Valuation Team
        """

        # ---- HTML ----
        html_message = f"""
            <html>
                <body style="font-family: Arial, sans-serif; font-size: 14px;">
                    <p>Dear <strong>{client_name}</strong>,</p>
                    <p>Please find attached your <strong>Desktop Valuation Report</strong>.</p>
                    <p>Best regards,<br><strong>Valuation Team</strong></p>
                </body>
            </html>
        """

        msg.attach(MIMEText(text_message, "plain"))
        msg.attach(MIMEText(html_message, "html"))

        part = MIMEApplication(pdf_bytes, _subtype="pdf")
        part.add_header(
            "Content-Disposition",
            "attachment",
            filename=filename,  
        )
        msg.attach(part)

        server = smtplib.SMTP(SMTP_URL, 587)
        server.starttls()
        server.login(get_email_user(), get_email_password())
        server.send_message(msg)
        server.quit()

        logger.info(f"PDF email sent to={to_email}")

    except Exception:
        logger.exception(f"Failed to send PDF email to={to_email}")
        raise
    

def send_subscription_expiry_email(to_email: str, plan_name: str, expiry_date):
    logger.info(f"Sending subscription expiry reminder to={to_email}")

    try:
        body = f"""
            Hello,

            Your subscription plan "{plan_name}" will expire on {expiry_date.strftime('%Y-%m-%d')}.

            Please renew your subscription to continue uninterrupted access.

            Thank you.
        """

        msg = MIMEText(body)
        msg["Subject"] = "Your Subscription Expires in 3 Days"
        msg["From"] = get_email_user()
        msg["To"] = to_email

        with smtplib.SMTP_SSL(SMTP_URL, 465) as server:
            server.login(get_email_user(), get_email_password())
            server.send_message(msg)

        logger.info(f"Subscription expiry email sent to={to_email}")

    except Exception:
        logger.exception(f"Failed to send expiry email to={to_email}")
        raise


def send_admin_feedback_email(feedback, user):
    logger.info(
        f"Sending admin feedback email feedback_id={feedback.id}"
    )

    try:
        body = f"""
        New feedback received

        User ID: {user.id}
        Feedback ID: {feedback.id}
        Type: {feedback.type}
        Rating: {feedback.rating or "N/A"}

        Subject:
        {feedback.subject}

        Message:
        {feedback.message}

        Status: {feedback.status}
        """

        msg = MIMEText(body)
        msg["Subject"] = f"[Feedback] {feedback.type} - {feedback.subject}"
        msg["From"] = get_email_user()
        msg["To"] = ", ".join(get_admin_feedback_emails())

        with smtplib.SMTP_SSL(SMTP_URL, 465) as server:
            server.login(get_email_user(), get_email_password())
            server.send_message(msg)

        logger.info(
            f"Admin feedback email sent feedback_id={feedback.id}"
        )

    except Exception:
        logger.exception(
            f"Failed sending admin feedback email feedback_id={feedback.id}"
        )
        

def send_feedback_reply_email(to_email: str, feedback_id: int, reply: str):
    logger.info(
        f"Sending feedback reply email feedback_id={feedback_id}"
    )

    try:
        body = f"""
        Hello,

        Our support team has replied to your feedback.

        Feedback ID: {feedback_id}

        Reply:
        {reply}

        Thank you for helping us improve.
        """

        msg = MIMEText(body)
        msg["Subject"] = "Update on your feedback"
        msg["From"] = get_email_user()
        msg["To"] = to_email

        with smtplib.SMTP_SSL(SMTP_URL, 465) as server:
            server.login(get_email_user(), get_email_password())
            server.send_message(msg)

        logger.info(
            f"Feedback reply email sent feedback_id={feedback_id}"
        )

    except Exception:
        logger.exception(
            f"Failed sending feedback reply email feedback_id={feedback_id}"
        )