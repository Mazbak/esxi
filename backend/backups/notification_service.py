"""
Notification Service - Gestion des notifications Email et Webhook

Ce service envoie des notifications pour les événements de backup :
- Email: Via Django email backend
- Webhook: HTTP POST/GET vers URL configurée
- Slack: Format spécifique Slack
- Teams: Format spécifique Microsoft Teams
"""

import logging
import json
import requests
from typing import Dict, List, Optional, Any
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone

from backups.models import NotificationConfig, NotificationLog, BackupJob, VirtualMachine

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service centralisé pour l'envoi de notifications
    """

    # Mapping des événements vers des niveaux de sévérité
    EVENT_SEVERITY = {
        'backup_success': 'success',
        'backup_failure': 'error',
        'backup_warning': 'warning',
        'schedule_missed': 'warning',
        'storage_full': 'error',
        'chain_broken': 'error',
        'retention_applied': 'info'
    }

    # Emojis pour les différents types d'événements
    EVENT_EMOJIS = {
        'backup_success': '✅',
        'backup_failure': '❌',
        'backup_warning': '⚠️',
        'schedule_missed': '⏰',
        'storage_full': '💾',
        'chain_broken': '🔗',
        'retention_applied': '🗑️'
    }

    def __init__(self):
        self.configs = NotificationConfig.objects.filter(is_enabled=True)

    def send_notification(
        self,
        event_type: str,
        vm: Optional[VirtualMachine] = None,
        backup_job: Optional[BackupJob] = None,
        **context
    ):
        """
        Envoie des notifications pour un événement donné

        Args:
            event_type: Type d'événement (backup_success, backup_failure, etc.)
            vm: Machine virtuelle concernée
            backup_job: Job de backup concerné
            **context: Contexte additionnel pour le template
        """
        logger.info(f"[NOTIFICATION] Envoi de notifications pour événement: {event_type}")

        # Récupérer toutes les configs actives pour cet événement
        matching_configs = self._get_matching_configs(event_type, vm, backup_job)

        if not matching_configs:
            logger.info(f"[NOTIFICATION] Aucune configuration trouvée pour {event_type}")
            return

        # Préparer le contexte
        full_context = self._build_context(event_type, vm, backup_job, context)

        # Envoyer pour chaque configuration
        for config in matching_configs:
            try:
                if config.notification_type == 'email':
                    self._send_email(config, full_context)
                elif config.notification_type == 'webhook':
                    self._send_webhook(config, full_context)
                elif config.notification_type == 'slack':
                    self._send_slack(config, full_context)
                elif config.notification_type == 'teams':
                    self._send_teams(config, full_context)
                else:
                    logger.warning(f"[NOTIFICATION] Type inconnu: {config.notification_type}")

            except Exception as e:
                logger.error(f"[NOTIFICATION] Erreur envoi notification {config.id}: {e}", exc_info=True)
                self._log_notification(config, event_type, vm, backup_job, 'failed', str(e))

    def _get_matching_configs(
        self,
        event_type: str,
        vm: Optional[VirtualMachine],
        backup_job: Optional[BackupJob]
    ) -> List[NotificationConfig]:
        """
        Récupère les configurations de notification qui correspondent à l'événement

        Returns:
            Liste des configurations matching
        """
        matching = []

        for config in self.configs:
            # Vérifier si l'événement est dans la liste
            if event_type not in config.event_types:
                continue

            # Vérifier le filtre VM
            if config.filter_vms.exists() and vm:
                if not config.filter_vms.filter(id=vm.id).exists():
                    continue

            # Vérifier le filtre schedule
            if config.filter_schedules.exists() and backup_job and backup_job.scheduled_by:
                if not config.filter_schedules.filter(id=backup_job.scheduled_by.id).exists():
                    continue

            matching.append(config)

        return matching

    def _build_context(
        self,
        event_type: str,
        vm: Optional[VirtualMachine],
        backup_job: Optional[BackupJob],
        extra_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Construit le contexte complet pour les templates

        Returns:
            Dictionnaire de contexte
        """
        context = {
            'event_type': event_type,
            'event_label': self._get_event_label(event_type),
            'severity': self.EVENT_SEVERITY.get(event_type, 'info'),
            'emoji': self.EVENT_EMOJIS.get(event_type, '📢'),
            'timestamp': timezone.now(),
            'vm_name': vm.name if vm else 'N/A',
            'vm_id': vm.id if vm else None,
        }

        # Ajouter les infos du job si disponible
        if backup_job:
            context.update({
                'job_id': backup_job.id,
                'job_type': backup_job.job_type,
                'backup_mode': backup_job.backup_mode,
                'status': backup_job.status,
                'progress': backup_job.progress_percentage,
                'error_message': backup_job.error_message,
                'backup_size_mb': backup_job.backup_size_mb,
                'duration_seconds': backup_job.duration_seconds,
                'created_at': backup_job.created_at,
                'completed_at': backup_job.completed_at,
            })

        # Ajouter le contexte extra
        context.update(extra_context)

        return context

    def _get_event_label(self, event_type: str) -> str:
        """Retourne le label lisible de l'événement"""
        labels = {
            'backup_success': 'Backup réussi',
            'backup_failure': 'Échec du backup',
            'backup_warning': 'Avertissement backup',
            'schedule_missed': 'Planification manquée',
            'storage_full': 'Stockage plein',
            'chain_broken': 'Chaîne de backup rompue',
            'retention_applied': 'Politique de rétention appliquée'
        }
        return labels.get(event_type, event_type)

    def _send_email(self, config: NotificationConfig, context: Dict[str, Any]):
        """
        Envoie une notification par email

        Args:
            config: Configuration de notification
            context: Contexte pour le template
        """
        logger.info(f"[NOTIFICATION] Envoi email via config {config.id}")

        # Récupérer les destinataires
        recipients = [email.strip() for email in config.email_recipients.split(',') if email.strip()]

        if not recipients:
            logger.warning(f"[NOTIFICATION] Aucun destinataire pour config {config.id}")
            return

        # Générer le sujet
        subject = config.email_subject_template.format(**context)

        # Générer le corps (texte et HTML)
        text_message = self._generate_email_text(context)
        html_message = self._generate_email_html(context)

        try:
            # Utiliser EmailMultiAlternatives pour envoyer HTML + texte
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@esxi-backup.local'),
                to=recipients
            )
            email.attach_alternative(html_message, "text/html")
            email.send()

            logger.info(f"[NOTIFICATION] ✓ Email envoyé à {', '.join(recipients)}")
            self._log_notification(
                config,
                context['event_type'],
                context.get('vm_id'),
                context.get('job_id'),
                'sent',
                f"Envoyé à {', '.join(recipients)}",
                subject,
                text_message
            )

        except Exception as e:
            logger.error(f"[NOTIFICATION] Erreur envoi email: {e}", exc_info=True)
            self._log_notification(config, context['event_type'], None, None, 'failed', str(e))
            raise

    def _generate_email_text(self, context: Dict[str, Any]) -> str:
        """Génère le corps de l'email en texte brut"""
        lines = [
            f"{context['emoji']} {context['event_label']}",
            "",
            f"VM: {context['vm_name']}",
            f"Date: {context['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}",
        ]

        if context.get('job_id'):
            lines.extend([
                "",
                f"Job ID: {context['job_id']}",
                f"Type: {context['job_type']} ({context['backup_mode']})",
                f"Statut: {context['status']}",
            ])

            if context.get('backup_size_mb'):
                lines.append(f"Taille: {context['backup_size_mb']:.2f} MB")

            if context.get('duration_seconds'):
                minutes = context['duration_seconds'] // 60
                seconds = context['duration_seconds'] % 60
                lines.append(f"Durée: {minutes}m {seconds}s")

            if context.get('error_message'):
                lines.extend([
                    "",
                    "Erreur:",
                    context['error_message']
                ])

        return "\n".join(lines)

    def _generate_email_html(self, context: Dict[str, Any]) -> str:
        """Génère le corps de l'email en HTML"""
        severity_colors = {
            'success': '#10b981',
            'error': '#ef4444',
            'warning': '#f59e0b',
            'info': '#3b82f6'
        }

        color = severity_colors.get(context['severity'], '#6b7280')

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: {color}; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                .content {{ background-color: #f9fafb; padding: 20px; border-radius: 0 0 8px 8px; }}
                .info-row {{ margin: 10px 0; }}
                .label {{ font-weight: bold; color: #6b7280; }}
                .value {{ color: #111827; }}
                .error {{ background-color: #fee2e2; padding: 10px; border-left: 4px solid #ef4444; margin-top: 15px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>{context['emoji']} {context['event_label']}</h2>
                </div>
                <div class="content">
                    <div class="info-row">
                        <span class="label">VM:</span>
                        <span class="value">{context['vm_name']}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">Date:</span>
                        <span class="value">{context['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}</span>
                    </div>
        """

        if context.get('job_id'):
            html += f"""
                    <div class="info-row">
                        <span class="label">Job ID:</span>
                        <span class="value">{context['job_id']}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">Type:</span>
                        <span class="value">{context['job_type']} ({context['backup_mode']})</span>
                    </div>
                    <div class="info-row">
                        <span class="label">Statut:</span>
                        <span class="value">{context['status']}</span>
                    </div>
            """

            if context.get('backup_size_mb'):
                html += f"""
                    <div class="info-row">
                        <span class="label">Taille:</span>
                        <span class="value">{context['backup_size_mb']:.2f} MB</span>
                    </div>
                """

            if context.get('error_message'):
                html += f"""
                    <div class="error">
                        <strong>Erreur:</strong><br>
                        {context['error_message']}
                    </div>
                """

        html += """
                </div>
            </div>
        </body>
        </html>
        """

        return html

    def _send_webhook(self, config: NotificationConfig, context: Dict[str, Any]):
        """
        Envoie une notification par webhook

        Args:
            config: Configuration de notification
            context: Contexte
        """
        logger.info(f"[NOTIFICATION] Envoi webhook via config {config.id}")

        if not config.webhook_url:
            logger.warning(f"[NOTIFICATION] Pas d'URL webhook pour config {config.id}")
            return

        # Préparer le payload
        payload = {
            'event_type': context['event_type'],
            'event_label': context['event_label'],
            'severity': context['severity'],
            'timestamp': context['timestamp'].isoformat(),
            'vm_name': context['vm_name'],
            'vm_id': context.get('vm_id'),
        }

        if context.get('job_id'):
            payload['backup_job'] = {
                'id': context['job_id'],
                'type': context['job_type'],
                'mode': context['backup_mode'],
                'status': context['status'],
                'size_mb': context.get('backup_size_mb'),
                'duration_seconds': context.get('duration_seconds'),
                'error_message': context.get('error_message'),
            }

        try:
            # Préparer les headers
            headers = {'Content-Type': 'application/json'}
            headers.update(config.webhook_headers or {})

            # Envoyer la requête
            if config.webhook_method == 'POST':
                response = requests.post(
                    config.webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=10
                )
            elif config.webhook_method == 'GET':
                response = requests.get(
                    config.webhook_url,
                    params=payload,
                    headers=headers,
                    timeout=10
                )
            else:
                response = requests.request(
                    config.webhook_method,
                    config.webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=10
                )

            response.raise_for_status()

            logger.info(f"[NOTIFICATION] ✓ Webhook envoyé à {config.webhook_url}: {response.status_code}")
            self._log_notification(
                config,
                context['event_type'],
                context.get('vm_id'),
                context.get('job_id'),
                'sent',
                f"Status: {response.status_code}",
                recipient=config.webhook_url
            )

        except Exception as e:
            logger.error(f"[NOTIFICATION] Erreur envoi webhook: {e}", exc_info=True)
            self._log_notification(config, context['event_type'], None, None, 'failed', str(e))
            raise

    def _send_slack(self, config: NotificationConfig, context: Dict[str, Any]):
        """Envoie une notification Slack (format spécifique)"""
        logger.info(f"[NOTIFICATION] Envoi Slack via config {config.id}")

        if not config.webhook_url:
            logger.warning(f"[NOTIFICATION] Pas d'URL Slack pour config {config.id}")
            return

        # Format Slack avec blocks
        severity_colors = {
            'success': '#10b981',
            'error': '#ef4444',
            'warning': '#f59e0b',
            'info': '#3b82f6'
        }

        payload = {
            "text": f"{context['emoji']} {context['event_label']} - {context['vm_name']}",
            "attachments": [
                {
                    "color": severity_colors.get(context['severity'], '#6b7280'),
                    "fields": [
                        {"title": "VM", "value": context['vm_name'], "short": True},
                        {"title": "Événement", "value": context['event_label'], "short": True},
                    ]
                }
            ]
        }

        if context.get('job_id'):
            payload["attachments"][0]["fields"].extend([
                {"title": "Job ID", "value": str(context['job_id']), "short": True},
                {"title": "Type", "value": f"{context['job_type']} ({context['backup_mode']})", "short": True},
                {"title": "Statut", "value": context['status'], "short": True},
            ])

            if context.get('backup_size_mb'):
                payload["attachments"][0]["fields"].append(
                    {"title": "Taille", "value": f"{context['backup_size_mb']:.2f} MB", "short": True}
                )

        try:
            response = requests.post(config.webhook_url, json=payload, timeout=10)
            response.raise_for_status()

            logger.info(f"[NOTIFICATION] ✓ Slack notification envoyée")
            self._log_notification(
                config,
                context['event_type'],
                context.get('vm_id'),
                context.get('job_id'),
                'sent',
                f"Slack: {response.status_code}",
                recipient=config.webhook_url
            )

        except Exception as e:
            logger.error(f"[NOTIFICATION] Erreur envoi Slack: {e}", exc_info=True)
            self._log_notification(config, context['event_type'], None, None, 'failed', str(e))
            raise

    def _send_teams(self, config: NotificationConfig, context: Dict[str, Any]):
        """Envoie une notification Microsoft Teams (format spécifique)"""
        logger.info(f"[NOTIFICATION] Envoi Teams via config {config.id}")

        if not config.webhook_url:
            logger.warning(f"[NOTIFICATION] Pas d'URL Teams pour config {config.id}")
            return

        # Format Microsoft Teams (Adaptive Card)
        severity_colors = {
            'success': 'good',
            'error': 'attention',
            'warning': 'warning',
            'info': 'accent'
        }

        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": severity_colors.get(context['severity'], 'default'),
            "summary": f"{context['event_label']} - {context['vm_name']}",
            "sections": [{
                "activityTitle": f"{context['emoji']} {context['event_label']}",
                "activitySubtitle": context['vm_name'],
                "facts": [
                    {"name": "VM", "value": context['vm_name']},
                    {"name": "Date", "value": context['timestamp'].strftime('%Y-%m-%d %H:%M:%S')},
                ]
            }]
        }

        if context.get('job_id'):
            payload["sections"][0]["facts"].extend([
                {"name": "Job ID", "value": str(context['job_id'])},
                {"name": "Type", "value": f"{context['job_type']} ({context['backup_mode']})"},
                {"name": "Statut", "value": context['status']},
            ])

        try:
            response = requests.post(config.webhook_url, json=payload, timeout=10)
            response.raise_for_status()

            logger.info(f"[NOTIFICATION] ✓ Teams notification envoyée")
            self._log_notification(
                config,
                context['event_type'],
                context.get('vm_id'),
                context.get('job_id'),
                'sent',
                f"Teams: {response.status_code}",
                recipient=config.webhook_url
            )

        except Exception as e:
            logger.error(f"[NOTIFICATION] Erreur envoi Teams: {e}", exc_info=True)
            self._log_notification(config, context['event_type'], None, None, 'failed', str(e))
            raise

    def _log_notification(
        self,
        config: NotificationConfig,
        event_type: str,
        vm_id: Optional[int],
        job_id: Optional[int],
        status: str,
        response: str = '',
        subject: str = '',
        message: str = '',
        recipient: str = ''
    ):
        """
        Enregistre la notification dans l'historique

        Args:
            config: Configuration utilisée
            event_type: Type d'événement
            vm_id: ID de la VM
            job_id: ID du job
            status: Statut (sent, failed, skipped)
            response: Réponse ou erreur
            subject: Sujet (email)
            message: Message envoyé
            recipient: Destinataire
        """
        try:
            vm = VirtualMachine.objects.get(id=vm_id) if vm_id else None
            job = BackupJob.objects.get(id=job_id) if job_id else None

            if not recipient:
                recipient = config.email_recipients if config.notification_type == 'email' else config.webhook_url

            NotificationLog.objects.create(
                config=config,
                event_type=event_type,
                backup_job=job,
                virtual_machine=vm,
                status=status,
                subject=subject,
                message=message or f"Notification {event_type}",
                recipient=recipient or 'N/A',
                response=response
            )

        except Exception as e:
            logger.error(f"[NOTIFICATION] Erreur log notification: {e}", exc_info=True)


# Instance globale du service
notification_service = NotificationService()
