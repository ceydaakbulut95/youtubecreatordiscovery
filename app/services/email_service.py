import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from app.core.config import settings


def send_password_reset_email(to_email: str, reset_link: str) -> None:
    if not settings.SENDGRID_API_KEY:
        raise ValueError("SENDGRID_API_KEY is missing")

    if not settings.EMAIL_FROM:
        raise ValueError("EMAIL_FROM is missing")

    message = Mail(
        from_email=settings.EMAIL_FROM,
        to_emails=to_email,
        subject="Reset your password",
        html_content=f"""
        <p>You requested a password reset.</p>
        <p>Click the link below to set a new password:</p>
        <p><a href="{reset_link}">{reset_link}</a></p>
        <p>If you did not request this, you can ignore this email.</p>
        """
    )

    sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
    sg.send(message)