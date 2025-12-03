"""
Email notification service for ESXi Backup Manager
Handles sending email notifications for backups, SureBackup verification, and replication events.
"""
import logging
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from smtplib import SMTPException
from .models import EmailSettings

logger = logging.getLogger(__name__)


class EmailNotificationService:
    """Service for sending email notifications"""

    @staticmethod
    def get_email_settings():
        """Get the email settings from database"""
        try:
            return EmailSettings.get_settings()
        except Exception as e:
            logger.error(f"[EMAIL] Error getting email settings: {str(e)}")
            return None

    @staticmethod
    def is_enabled():
        """Check if email notifications are enabled"""
        email_settings = EmailNotificationService.get_email_settings()
        if not email_settings:
            return False
        return (
            email_settings.email_notifications_enabled and
            email_settings.admin_email and
            email_settings.smtp_host and
            email_settings.from_email
        )

    @staticmethod
    def get_smtp_backend_settings(email_settings):
        """Get SMTP backend settings dictionary"""
        return {
            'EMAIL_BACKEND': 'django.core.mail.backends.smtp.EmailBackend',
            'EMAIL_HOST': email_settings.smtp_host,
            'EMAIL_PORT': email_settings.smtp_port,
            'EMAIL_HOST_USER': email_settings.smtp_username,
            'EMAIL_HOST_PASSWORD': email_settings.smtp_password,
            'EMAIL_USE_TLS': email_settings.smtp_use_tls,
            'EMAIL_USE_SSL': email_settings.smtp_use_ssl,
            'DEFAULT_FROM_EMAIL': email_settings.from_email,
        }

    @staticmethod
    def send_email(subject, message, html_message=None, recipient_list=None):
        """
        Send an email using the configured SMTP settings

        Args:
            subject (str): Email subject
            message (str): Plain text message
            html_message (str, optional): HTML message
            recipient_list (list, optional): List of recipient emails (defaults to admin_email)

        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        if not EmailNotificationService.is_enabled():
            logger.warning("[EMAIL] Email notifications are disabled or not configured")
            return False

        email_settings = EmailNotificationService.get_email_settings()

        # Use admin email if no recipients specified
        if not recipient_list:
            recipient_list = [email_settings.admin_email]

        try:
            # Configure SMTP settings temporarily
            smtp_settings = EmailNotificationService.get_smtp_backend_settings(email_settings)

            # Update Django settings temporarily
            for key, value in smtp_settings.items():
                setattr(settings, key, value)

            # Send email
            if html_message:
                email = EmailMessage(
                    subject=subject,
                    body=html_message,
                    from_email=email_settings.from_email,
                    to=recipient_list,
                )
                email.content_subtype = 'html'
                email.send()
            else:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=email_settings.from_email,
                    recipient_list=recipient_list,
                    fail_silently=False,
                )

            logger.info(f"[EMAIL] Email sent successfully to {recipient_list}: {subject}")
            return True

        except SMTPException as e:
            logger.error(f"[EMAIL] SMTP error sending email: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"[EMAIL] Error sending email: {str(e)}")
            return False

    @staticmethod
    def send_backup_success_notification(vm_name, backup_path, duration_seconds=None):
        """Send notification for successful backup"""
        email_settings = EmailNotificationService.get_email_settings()
        if not email_settings or not email_settings.notify_backup_success:
            return False

        subject = f"✅ Sauvegarde réussie - {vm_name}"

        duration_text = ""
        if duration_seconds:
            minutes = int(duration_seconds // 60)
            seconds = int(duration_seconds % 60)
            duration_text = f"\nDurée: {minutes}m {seconds}s"

        message = f"""
Sauvegarde réussie
==================

Machine virtuelle: {vm_name}
Chemin de sauvegarde: {backup_path}{duration_text}
Date: {EmailNotificationService._get_current_datetime()}

La sauvegarde a été complétée avec succès.

---
ESXi Backup Manager
        """.strip()

        html_message = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 10px;">
                    <h2 style="color: #10b981; border-bottom: 2px solid #10b981; padding-bottom: 10px;">
                        ✅ Sauvegarde réussie
                    </h2>
                    <p><strong>Machine virtuelle:</strong> {vm_name}</p>
                    <p><strong>Chemin de sauvegarde:</strong> <code style="background: #f3f4f6; padding: 2px 6px; border-radius: 4px;">{backup_path}</code></p>
                    {f'<p><strong>Durée:</strong> {minutes}m {seconds}s</p>' if duration_seconds else ''}
                    <p><strong>Date:</strong> {EmailNotificationService._get_current_datetime()}</p>
                    <div style="margin-top: 20px; padding: 15px; background-color: #d1fae5; border-left: 4px solid #10b981; border-radius: 4px;">
                        <p style="margin: 0;">La sauvegarde a été complétée avec succès.</p>
                    </div>
                    <hr style="margin: 20px 0; border: none; border-top: 1px solid #e0e0e0;">
                    <p style="color: #6b7280; font-size: 12px; text-align: center;">ESXi Backup Manager</p>
                </div>
            </body>
        </html>
        """

        return EmailNotificationService.send_email(subject, message, html_message)

    @staticmethod
    def send_backup_failure_notification(vm_name, error_message):
        """Send notification for failed backup"""
        email_settings = EmailNotificationService.get_email_settings()
        if not email_settings or not email_settings.notify_backup_failure:
            return False

        subject = f"❌ Échec de sauvegarde - {vm_name}"

        message = f"""
Échec de sauvegarde
===================

Machine virtuelle: {vm_name}
Erreur: {error_message}
Date: {EmailNotificationService._get_current_datetime()}

La sauvegarde a échoué. Veuillez vérifier les logs pour plus de détails.

---
ESXi Backup Manager
        """.strip()

        html_message = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 10px;">
                    <h2 style="color: #ef4444; border-bottom: 2px solid #ef4444; padding-bottom: 10px;">
                        ❌ Échec de sauvegarde
                    </h2>
                    <p><strong>Machine virtuelle:</strong> {vm_name}</p>
                    <p><strong>Date:</strong> {EmailNotificationService._get_current_datetime()}</p>
                    <div style="margin-top: 20px; padding: 15px; background-color: #fee2e2; border-left: 4px solid #ef4444; border-radius: 4px;">
                        <p style="margin: 0;"><strong>Erreur:</strong></p>
                        <p style="margin: 5px 0 0 0; font-family: monospace; background: #fff; padding: 10px; border-radius: 4px;">{error_message}</p>
                    </div>
                    <div style="margin-top: 20px; padding: 15px; background-color: #fef3c7; border-left: 4px solid #f59e0b; border-radius: 4px;">
                        <p style="margin: 0;">⚠️ La sauvegarde a échoué. Veuillez vérifier les logs pour plus de détails.</p>
                    </div>
                    <hr style="margin: 20px 0; border: none; border-top: 1px solid #e0e0e0;">
                    <p style="color: #6b7280; font-size: 12px; text-align: center;">ESXi Backup Manager</p>
                </div>
            </body>
        </html>
        """

        return EmailNotificationService.send_email(subject, message, html_message)

    @staticmethod
    def send_surebackup_success_notification(vm_name, verification_details):
        """Send notification for successful SureBackup verification"""
        email_settings = EmailNotificationService.get_email_settings()
        if not email_settings or not email_settings.notify_surebackup_success:
            return False

        subject = f"✅ Vérification SureBackup réussie - {vm_name}"

        message = f"""
Vérification SureBackup réussie
================================

Machine virtuelle: {vm_name}
Date: {EmailNotificationService._get_current_datetime()}

Détails de la vérification:
{verification_details}

La vérification SureBackup a été complétée avec succès.

---
ESXi Backup Manager
        """.strip()

        html_message = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 10px;">
                    <h2 style="color: #10b981; border-bottom: 2px solid #10b981; padding-bottom: 10px;">
                        ✅ Vérification SureBackup réussie
                    </h2>
                    <p><strong>Machine virtuelle:</strong> {vm_name}</p>
                    <p><strong>Date:</strong> {EmailNotificationService._get_current_datetime()}</p>
                    <div style="margin-top: 20px; padding: 15px; background-color: #f3f4f6; border-radius: 4px;">
                        <p style="margin: 0 0 10px 0;"><strong>Détails de la vérification:</strong></p>
                        <pre style="margin: 0; white-space: pre-wrap; font-family: monospace; font-size: 13px;">{verification_details}</pre>
                    </div>
                    <div style="margin-top: 20px; padding: 15px; background-color: #d1fae5; border-left: 4px solid #10b981; border-radius: 4px;">
                        <p style="margin: 0;">La vérification SureBackup a été complétée avec succès.</p>
                    </div>
                    <hr style="margin: 20px 0; border: none; border-top: 1px solid #e0e0e0;">
                    <p style="color: #6b7280; font-size: 12px; text-align: center;">ESXi Backup Manager</p>
                </div>
            </body>
        </html>
        """

        return EmailNotificationService.send_email(subject, message, html_message)

    @staticmethod
    def send_surebackup_failure_notification(vm_name, error_message):
        """Send notification for failed SureBackup verification"""
        email_settings = EmailNotificationService.get_email_settings()
        if not email_settings or not email_settings.notify_surebackup_failure:
            return False

        subject = f"❌ Échec de vérification SureBackup - {vm_name}"

        message = f"""
Échec de vérification SureBackup
=================================

Machine virtuelle: {vm_name}
Erreur: {error_message}
Date: {EmailNotificationService._get_current_datetime()}

La vérification SureBackup a échoué. Veuillez vérifier les logs pour plus de détails.

---
ESXi Backup Manager
        """.strip()

        html_message = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 10px;">
                    <h2 style="color: #ef4444; border-bottom: 2px solid #ef4444; padding-bottom: 10px;">
                        ❌ Échec de vérification SureBackup
                    </h2>
                    <p><strong>Machine virtuelle:</strong> {vm_name}</p>
                    <p><strong>Date:</strong> {EmailNotificationService._get_current_datetime()}</p>
                    <div style="margin-top: 20px; padding: 15px; background-color: #fee2e2; border-left: 4px solid #ef4444; border-radius: 4px;">
                        <p style="margin: 0;"><strong>Erreur:</strong></p>
                        <p style="margin: 5px 0 0 0; font-family: monospace; background: #fff; padding: 10px; border-radius: 4px;">{error_message}</p>
                    </div>
                    <div style="margin-top: 20px; padding: 15px; background-color: #fef3c7; border-left: 4px solid #f59e0b; border-radius: 4px;">
                        <p style="margin: 0;">⚠️ La vérification SureBackup a échoué. Veuillez vérifier les logs pour plus de détails.</p>
                    </div>
                    <hr style="margin: 20px 0; border: none; border-top: 1px solid #e0e0e0;">
                    <p style="color: #6b7280; font-size: 12px; text-align: center;">ESXi Backup Manager</p>
                </div>
            </body>
        </html>
        """

        return EmailNotificationService.send_email(subject, message, html_message)

    @staticmethod
    def send_replication_failure_notification(vm_name, source_server, destination_server, error_message):
        """Send notification for failed replication"""
        email_settings = EmailNotificationService.get_email_settings()
        if not email_settings or not email_settings.notify_replication_failure:
            return False

        subject = f"❌ Échec de réplication - {vm_name}"

        message = f"""
Échec de réplication
====================

Machine virtuelle: {vm_name}
Serveur source: {source_server}
Serveur destination: {destination_server}
Erreur: {error_message}
Date: {EmailNotificationService._get_current_datetime()}

La réplication a échoué. Veuillez vérifier les logs pour plus de détails.

---
ESXi Backup Manager
        """.strip()

        html_message = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 10px;">
                    <h2 style="color: #ef4444; border-bottom: 2px solid #ef4444; padding-bottom: 10px;">
                        ❌ Échec de réplication
                    </h2>
                    <p><strong>Machine virtuelle:</strong> {vm_name}</p>
                    <p><strong>Serveur source:</strong> {source_server}</p>
                    <p><strong>Serveur destination:</strong> {destination_server}</p>
                    <p><strong>Date:</strong> {EmailNotificationService._get_current_datetime()}</p>
                    <div style="margin-top: 20px; padding: 15px; background-color: #fee2e2; border-left: 4px solid #ef4444; border-radius: 4px;">
                        <p style="margin: 0;"><strong>Erreur:</strong></p>
                        <p style="margin: 5px 0 0 0; font-family: monospace; background: #fff; padding: 10px; border-radius: 4px;">{error_message}</p>
                    </div>
                    <div style="margin-top: 20px; padding: 15px; background-color: #fef3c7; border-left: 4px solid #f59e0b; border-radius: 4px;">
                        <p style="margin: 0;">⚠️ La réplication a échoué. Veuillez vérifier les logs pour plus de détails.</p>
                    </div>
                    <hr style="margin: 20px 0; border: none; border-top: 1px solid #e0e0e0;">
                    <p style="color: #6b7280; font-size: 12px; text-align: center;">ESXi Backup Manager</p>
                </div>
            </body>
        </html>
        """

        return EmailNotificationService.send_email(subject, message, html_message)

    @staticmethod
    def send_test_email(recipient_email=None):
        """Send a test email to verify SMTP configuration"""
        subject = "🧪 Test - ESXi Backup Manager"

        message = f"""
Email de test
=============

Ceci est un email de test pour vérifier la configuration SMTP.

Si vous recevez cet email, la configuration est correcte.

Date: {EmailNotificationService._get_current_datetime()}

---
ESXi Backup Manager
        """.strip()

        html_message = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 10px;">
                    <h2 style="color: #3b82f6; border-bottom: 2px solid #3b82f6; padding-bottom: 10px;">
                        🧪 Email de test
                    </h2>
                    <p>Ceci est un email de test pour vérifier la configuration SMTP.</p>
                    <div style="margin-top: 20px; padding: 15px; background-color: #dbeafe; border-left: 4px solid #3b82f6; border-radius: 4px;">
                        <p style="margin: 0;">✅ Si vous recevez cet email, la configuration est correcte.</p>
                    </div>
                    <p><strong>Date:</strong> {EmailNotificationService._get_current_datetime()}</p>
                    <hr style="margin: 20px 0; border: none; border-top: 1px solid #e0e0e0;">
                    <p style="color: #6b7280; font-size: 12px; text-align: center;">ESXi Backup Manager</p>
                </div>
            </body>
        </html>
        """

        recipient_list = [recipient_email] if recipient_email else None
        return EmailNotificationService.send_email(subject, message, html_message, recipient_list)

    @staticmethod
    def _get_current_datetime():
        """Get current datetime formatted for display"""
        from django.utils import timezone
        return timezone.now().strftime('%d/%m/%Y %H:%M:%S')
