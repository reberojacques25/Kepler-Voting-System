from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.conf import settings
from django.urls import reverse
from django.core.mail import send_mail

signer = TimestampSigner(salt=settings.SIGNING_SALT)

def make_email_token(user_id: int) -> str:
    return signer.sign(str(user_id))

def parse_email_token(token: str, max_age_seconds: int = 60 * 60 * 72) -> int:
    # 72 hours default
    try:
        value = signer.unsign(token, max_age=max_age_seconds)
        return int(value)
    except (BadSignature, SignatureExpired) as e:
        raise e

def send_verification_email(user, request=None):
    token = make_email_token(user.id)
    path = reverse("accounts:verify_email", kwargs={"token": token})
    link = f"{settings.SITE_URL}{path}"

    subject = "Confirm your Kepler Voting Account"
    message = (
        f"Hello,\n\n"
        f"Please confirm your email to activate your Kepler Student Guild Voting account.\n\n"
        f"Verification link: {link}\n\n"
        f"If you did not request this, you can ignore this email."
    )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
    return link
