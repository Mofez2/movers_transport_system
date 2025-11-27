from django.core.mail.backends.base import BaseEmailBackend
from mailjet_rest import Client
from django.conf import settings


class MailjetBackend(BaseEmailBackend):
    """
    Custom Django email backend that sends mail using Mailjet's HTTP API.
    Perfect for Render since SMTP ports may be blocked.
    """

    def send_messages(self, email_messages):
        mailjet = Client(
            auth=(settings.MAILJET_API_KEY, settings.MAILJET_SECRET_KEY),
            version='v3.1'
        )
        sent_count = 0

        for message in email_messages:
            data = {
                'Messages': [{
                    "From": {
                        "Email": settings.DEFAULT_FROM_EMAIL,
                        "Name": "Movers Transport"
                    },
                    "To": [{"Email": addr} for addr in message.to],
                    "Subject": message.subject,
                    "HTMLPart": message.body,
                }]
            }

            result = mailjet.send.create(data=data)
            if result.status_code == 200:
                sent_count += 1

        return sent_count
