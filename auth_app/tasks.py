"""Utility functions for the auth_app API.

Contains helpers for sending transactional e-mails (account activation
and password reset) with an embedded inline logo.
"""

import os
from email.mime.image import MIMEImage

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags


LOGO_PATH = os.path.join(
    settings.BASE_DIR, 'static', 'videoflix', 'images', 'logo_icon.svg'
)
LOGO_CONTENT_ID = '<logo>'


def get_logo_data():
    """Return the inline logo as a ``MIMEImage`` or ``None`` if missing."""
    if not os.path.exists(LOGO_PATH):
        return None

    with open(LOGO_PATH, 'rb') as logo_file:
        image_data = logo_file.read()

    logo = MIMEImage(image_data, _subtype='svg+xml')
    logo.add_header('Content-ID', LOGO_CONTENT_ID)
    return logo


def _send_html_mail(subject, template_name, context, recipient_email):
    """Render an HTML template and send it as a multipart e-mail.

    A plain-text alternative is generated from the HTML and the inline
    logo is attached when available.
    """
    html_message = render_to_string(template_name, context)
    plain_message = strip_tags(html_message)

    message = EmailMultiAlternatives(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [recipient_email],
    )
    message.attach_alternative(html_message, 'text/html')

    logo = get_logo_data()
    if logo is not None:
        message.attach(logo)

    message.send(fail_silently=False)


def job_send_activation_mail(recipient_email, activation_link):
    """Send the account activation e-mail to ``recipient_email``."""
    _send_html_mail(
        subject='Aktiviere dein Videoflix Konto',
        template_name='activation_mail.html',
        context={'email': recipient_email, 'link': activation_link},
        recipient_email=recipient_email,
    )


def job_send_reset_password_mail(recipient_email, reset_link):
    """Send the password reset e-mail to ``recipient_email``."""
    _send_html_mail(
        subject='Passwort zurücksetzen für dein Videoflix Konto',
        template_name='reset_password.html',
        context={'email': recipient_email, 'link': reset_link},
        recipient_email=recipient_email,
    )



