import logging
import resend

from config.settings import RESEND_API_KEY, APP_URL

logger = logging.getLogger(__name__)

FROM_EMAIL = "onboarding@resend.dev"

class EmailService:

    def __init__(self):
        if not RESEND_API_KEY:
            self.available = False
            logger.warning("RESEND_API_KEY not set — email sending disabled")
        else:
            resend.api_key = RESEND_API_KEY
            self.available = True

    def send_password_reset(
        self,
        to_email: str,
        reset_token: str,
        user_name: str = "there",
    ) -> bool:

        if not self.available:
            logger.error("Cannot send email — Resend not configured")
            return False

        reset_link = f"{APP_URL}/Reset_Password?token={reset_token}"

        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto;">
            <h2 style="color: #1a1a2e;">Reset Your Password</h2>
            <p>Hi {user_name},</p>
            <p>We received a request to reset your password for your
            AI Trading Journal account.</p>
            <p>Click the button below to set a new password.
            This link expires in 1 hour.</p>
            <div style="margin: 24px 0;">
                <a href="{reset_link}"
                   style="background: #4f7cff; color: white;
                          padding: 12px 24px; border-radius: 6px;
                          text-decoration: none; display: inline-block;">
                    Reset Password
                </a>
            </div>
            <p style="color: #666; font-size: 13px;">
            If you did not request this, you can safely ignore this email.
            Your password will not change.</p>
            <p style="color: #999; font-size: 12px;">
            If the button does not work, copy this link:<br>
            {reset_link}</p>
        </div>
        """

        try:
            resend.Emails.send({
                "from": FROM_EMAIL,
                "to": to_email,
                "subject": "Reset your AI Trading Journal password",
                "html": html_body,
            })
            logger.info(f"Password reset email sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send reset email to {to_email}: {e}")
            return False