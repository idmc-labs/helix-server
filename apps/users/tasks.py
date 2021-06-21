from celery import shared_task
from helix.settings import DEFAULT_FROM_EMAIL
from django.core.mail import send_mail
from django.template import loader


@shared_task
def send_email(subject, message, recipient_list, html_context=None):
    """ A generic background task for sending emails """

    email_data = {
        "subject": subject,
        "message": message,
        "from_email": f"Helix {DEFAULT_FROM_EMAIL}",
        "recipient_list": recipient_list,
        "fail_silently": False,
    }

    # Send email as HTML context supplied
    if html_context:
        template = loader.get_template("emails/generic_email.html")
        email_data["html_message"] = template.render(html_context)

    send_mail(**email_data)
