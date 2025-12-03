"""
Automatic provisioning service for new organizations
Creates workspace, sets permissions, and initializes default settings
"""
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class ProvisioningException(Exception):
    """Exception raised during provisioning"""
    pass


class ProvisioningService:
    """
    Service to automatically provision organization workspace after payment
    """

    @transaction.atomic
    def provision_organization(self, order):
        """
        Provision organization workspace after successful payment

        Steps:
        1. Update/Create organization
        2. Set subscription dates
        3. Create organization owner membership
        4. Initialize default settings (email, notifications, etc.)
        5. Create usage metrics for current period
        6. Send welcome email
        7. Update order status

        Args:
            order: Order model instance with payment completed

        Returns:
            Organization: The provisioned organization instance

        Raises:
            ProvisioningException: If provisioning fails
        """
        from ..models import Organization, OrganizationMember, UsageMetrics
        from esxi.models import EmailSettings

        try:
            logger.info(f"Starting provisioning for order {order.order_number}")

            # Step 1: Create or update organization
            if order.organization:
                # Update existing organization (renewal)
                org = order.organization
                org.plan = order.plan
                org.billing_cycle = order.billing_cycle
                logger.info(f"Updating existing organization: {org.name}")
            else:
                # Create new organization
                from django.utils.text import slugify
                base_slug = slugify(order.customer_name)
                slug = base_slug
                counter = 1

                # Ensure unique slug
                while Organization.objects.filter(slug=slug).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1

                org = Organization.objects.create(
                    name=order.customer_name,
                    slug=slug,
                    plan=order.plan,
                    owner=order.user,
                    email=order.customer_email,
                    phone=order.customer_phone,
                    billing_cycle=order.billing_cycle
                )
                logger.info(f"Created new organization: {org.name} ({org.slug})")

                # Link organization to order
                order.organization = org

            # Step 2: Set subscription dates
            now = timezone.now()
            org.status = 'active'
            org.subscription_start = now

            # Calculate subscription end date
            if order.billing_cycle == 'monthly':
                org.subscription_end = now + timedelta(days=30)
                org.next_billing_date = (now + timedelta(days=30)).date()
            else:  # yearly
                org.subscription_end = now + timedelta(days=365)
                org.next_billing_date = (now + timedelta(days=365)).date()

            org.provisioned_at = now
            org.save()

            logger.info(f"Set subscription: {org.subscription_start} to {org.subscription_end}")

            # Step 3: Create owner membership (if new organization)
            if not order.organization:
                OrganizationMember.objects.get_or_create(
                    organization=org,
                    user=order.user,
                    defaults={
                        'role': 'owner',
                        'joined_at': now,
                        'is_active': True
                    }
                )
                logger.info(f"Created owner membership for user: {order.user.username}")

            # Step 4: Initialize organization settings
            # Note: We don't create separate EmailSettings per org yet (still global singleton)
            # In future, could create org-specific settings here

            # Step 5: Create usage metrics for current billing period
            period_start = now.date()
            if order.billing_cycle == 'monthly':
                period_end = (now + timedelta(days=30)).date()
            else:
                period_end = (now + timedelta(days=365)).date()

            UsageMetrics.objects.get_or_create(
                organization=org,
                period_start=period_start,
                defaults={
                    'period_end': period_end,
                    'esxi_servers_count': 0,
                    'vms_count': 0,
                    'backups_count': 0,
                    'storage_used_gb': 0.0,
                    'users_count': 1  # Owner
                }
            )
            logger.info(f"Created usage metrics for period: {period_start} to {period_end}")

            # Step 6: Send welcome email
            try:
                self._send_welcome_email(org, order)
            except Exception as e:
                logger.warning(f"Failed to send welcome email: {str(e)}")
                # Don't fail provisioning if email fails

            # Step 7: Update order status
            order.status = 'completed'
            order.provisioned_at = now
            order.save()

            logger.info(f"Provisioning completed successfully for order {order.order_number}")

            return org

        except Exception as e:
            logger.error(f"Provisioning failed for order {order.order_number}: {str(e)}")
            order.status = 'failed'
            order.provisioning_error = str(e)
            order.save()
            raise ProvisioningException(f"Échec du provisionnement: {str(e)}")

    def _send_welcome_email(self, organization, order):
        """Send welcome email to new organization"""
        from esxi.email_service import EmailService

        email_service = EmailService()

        subject = f"Bienvenue sur ESXi Backup Manager - {organization.plan.display_name}"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .plan-info {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #667eea; }}
                .feature-list {{ list-style: none; padding: 0; }}
                .feature-list li {{ padding: 8px 0; padding-left: 25px; position: relative; }}
                .feature-list li:before {{ content: "✓"; position: absolute; left: 0; color: #667eea; font-weight: bold; }}
                .cta-button {{ display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Bienvenue sur ESXi Backup Manager!</h1>
                </div>
                <div class="content">
                    <p>Bonjour <strong>{organization.name}</strong>,</p>

                    <p>Félicitations ! Votre espace de travail a été créé avec succès.</p>

                    <div class="plan-info">
                        <h3>📋 Détails de votre abonnement</h3>
                        <p><strong>Plan:</strong> {organization.plan.display_name}</p>
                        <p><strong>Cycle:</strong> {order.get_billing_cycle_display()}</p>
                        <p><strong>Début:</strong> {organization.subscription_start.strftime('%d/%m/%Y')}</p>
                        <p><strong>Fin:</strong> {organization.subscription_end.strftime('%d/%m/%Y')}</p>
                    </div>

                    <h3>✨ Fonctionnalités incluses:</h3>
                    <ul class="feature-list">
                        <li>Jusqu'à {organization.plan.max_esxi_servers} serveurs ESXi</li>
                        <li>Jusqu'à {organization.plan.max_vms} machines virtuelles</li>
                        <li>{organization.plan.max_backups_per_month} sauvegardes par mois</li>
                        <li>{organization.plan.max_storage_gb} GB de stockage</li>
                        <li>Rétention des sauvegardes: {organization.plan.backup_retention_days} jours</li>
                        {'<li>Réplication inter-sites</li>' if organization.plan.has_replication else ''}
                        {'<li>Vérification SureBackup</li>' if organization.plan.has_surebackup else ''}
                        {'<li>Monitoring avancé</li>' if organization.plan.has_advanced_monitoring else ''}
                        {'<li>Accès API</li>' if organization.plan.has_api_access else ''}
                        {'<li>Support prioritaire</li>' if organization.plan.has_priority_support else ''}
                    </ul>

                    <div style="text-align: center;">
                        <a href="{self._get_app_url(organization)}" class="cta-button">
                            Accéder à mon espace
                        </a>
                    </div>

                    <h3>🚀 Prochaines étapes:</h3>
                    <ol>
                        <li>Connectez-vous à votre espace avec vos identifiants</li>
                        <li>Ajoutez vos serveurs ESXi dans la section "Serveurs ESXi"</li>
                        <li>Configurez vos premières sauvegardes</li>
                        <li>Planifiez vos sauvegardes automatiques</li>
                    </ol>

                    <p>Si vous avez des questions, n'hésitez pas à contacter notre support.</p>

                    <p>Cordialement,<br>
                    <strong>L'équipe ESXi Backup Manager</strong></p>
                </div>
                <div class="footer">
                    <p>© {timezone.now().year} ESXi Backup Manager. Tous droits réservés.</p>
                </div>
            </div>
        </body>
        </html>
        """

        email_service.send_email(
            subject=subject,
            message=f"Bienvenue sur ESXi Backup Manager!",
            recipient_list=[organization.email],
            html_message=html_content
        )

        logger.info(f"Welcome email sent to {organization.email}")

    def _get_app_url(self, organization):
        """Get application URL for organization"""
        from django.conf import settings
        base_url = getattr(settings, 'APP_BASE_URL', 'http://localhost:5173')
        return f"{base_url}/login"

    def suspend_organization(self, organization, reason=""):
        """
        Suspend organization (payment failed, quota exceeded, etc.)

        Args:
            organization: Organization instance
            reason: Reason for suspension
        """
        try:
            organization.status = 'suspended'
            organization.save()

            logger.info(f"Organization {organization.name} suspended. Reason: {reason}")

            # Send suspension notification email
            self._send_suspension_email(organization, reason)

            return True
        except Exception as e:
            logger.error(f"Failed to suspend organization {organization.name}: {str(e)}")
            return False

    def _send_suspension_email(self, organization, reason):
        """Send suspension notification email"""
        from esxi.email_service import EmailService

        email_service = EmailService()

        subject = "⚠️ Votre compte ESXi Backup Manager a été suspendu"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #dc3545; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .warning-box {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 5px; }}
                .cta-button {{ display: inline-block; background: #dc3545; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⚠️ Compte Suspendu</h1>
                </div>
                <div class="content">
                    <p>Bonjour <strong>{organization.name}</strong>,</p>

                    <div class="warning-box">
                        <p><strong>Votre compte a été suspendu.</strong></p>
                        <p>Raison: {reason or 'Non spécifiée'}</p>
                    </div>

                    <p>Pour réactiver votre compte, veuillez:</p>
                    <ul>
                        <li>Vérifier l'état de votre paiement</li>
                        <li>Mettre à jour vos informations de facturation</li>
                        <li>Contacter notre support si nécessaire</li>
                    </ul>

                    <div style="text-align: center;">
                        <a href="{self._get_app_url(organization)}" class="cta-button">
                            Gérer mon compte
                        </a>
                    </div>

                    <p>Cordialement,<br>
                    <strong>L'équipe ESXi Backup Manager</strong></p>
                </div>
            </div>
        </body>
        </html>
        """

        email_service.send_email(
            subject=subject,
            message="Votre compte a été suspendu",
            recipient_list=[organization.email],
            html_message=html_content
        )

    def renew_subscription(self, organization, new_order):
        """
        Renew organization subscription

        Args:
            organization: Organization instance
            new_order: New order for renewal
        """
        try:
            now = timezone.now()

            # Extend subscription
            if new_order.billing_cycle == 'monthly':
                organization.subscription_end = organization.subscription_end + timedelta(days=30)
                organization.next_billing_date = (now + timedelta(days=30)).date()
            else:  # yearly
                organization.subscription_end = organization.subscription_end + timedelta(days=365)
                organization.next_billing_date = (now + timedelta(days=365)).date()

            # Update plan if changed
            if organization.plan != new_order.plan:
                old_plan = organization.plan
                organization.plan = new_order.plan
                logger.info(f"Organization {organization.name} upgraded from {old_plan.name} to {new_order.plan.name}")

            organization.status = 'active'
            organization.save()

            logger.info(f"Subscription renewed for {organization.name} until {organization.subscription_end}")

            # Send renewal confirmation email
            self._send_renewal_email(organization, new_order)

            return True
        except Exception as e:
            logger.error(f"Failed to renew subscription for {organization.name}: {str(e)}")
            return False

    def _send_renewal_email(self, organization, order):
        """Send renewal confirmation email"""
        from esxi.email_service import EmailService

        email_service = EmailService()

        subject = "✅ Votre abonnement ESXi Backup Manager a été renouvelé"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .info-box {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #28a745; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✅ Abonnement Renouvelé</h1>
                </div>
                <div class="content">
                    <p>Bonjour <strong>{organization.name}</strong>,</p>

                    <p>Votre abonnement a été renouvelé avec succès!</p>

                    <div class="info-box">
                        <p><strong>Plan:</strong> {organization.plan.display_name}</p>
                        <p><strong>Nouvelle date d'expiration:</strong> {organization.subscription_end.strftime('%d/%m/%Y')}</p>
                        <p><strong>Prochain paiement:</strong> {organization.next_billing_date.strftime('%d/%m/%Y')}</p>
                    </div>

                    <p>Merci pour votre confiance!</p>

                    <p>Cordialement,<br>
                    <strong>L'équipe ESXi Backup Manager</strong></p>
                </div>
            </div>
        </body>
        </html>
        """

        email_service.send_email(
            subject=subject,
            message="Votre abonnement a été renouvelé",
            recipient_list=[organization.email],
            html_message=html_content
        )
