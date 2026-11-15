from email.message import EmailMessage

import aiosmtplib
from loguru import logger

from src.core import Settings
from src.domain.interfaces import EmailTransportProtocol


class ConsoleStubEmailTransport:
    async def send_email(self, to_email: str, subject: str, body_text: str) -> None:
        logger.info(
            "email: {body_text} [to: {to_email}, subject: {subject}]",
            body_text=body_text,
            to_email=to_email,
            subject=subject,
        )


class SmtpEmailTransport:
    def __init__(self, settings: Settings | None = None) -> None:
        if settings is None:
            from src.core import settings as default_settings

            settings = default_settings
        self.settings = settings

    async def send_email(self, to_email: str, subject: str, body_text: str) -> None:
        msg = EmailMessage()
        msg["From"] = self.settings.smtp_from
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body_text)

        await aiosmtplib.send(
            msg,
            hostname=self.settings.smtp_host,
            port=self.settings.smtp_port,
            username=self.settings.smtp_user or None,
            password=self.settings.smtp_password or None,
            start_tls=self.settings.smtp_use_tls,
        )


def get_email_transport(settings: Settings | None = None) -> EmailTransportProtocol:
    if settings is None:
        from src.core import settings as default_settings

        settings = default_settings

    if settings.email_backend == "smtp":
        return SmtpEmailTransport(settings=settings)
    return ConsoleStubEmailTransport()
