"""
Management command to create default subscription plans and payment methods
"""
from django.core.management.base import BaseCommand
from tenants.models import Plan, PaymentMethod


class Command(BaseCommand):
    help = 'Create default subscription plans and payment methods'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Creating default plans and payment methods...'))

        # Create Plans
        bronze, created = Plan.objects.get_or_create(
            name='bronze',
            defaults={
                'display_name': 'Bronze',
                'description': 'Idéal pour les petites entreprises',
                'monthly_price': 25000,  # XAF
                'yearly_price': 250000,
                'max_esxi_servers': 2,
                'max_vms': 10,
                'max_backups_per_month': 100,
                'max_storage_gb': 100,
                'max_users': 2,
                'has_replication': False,
                'has_surebackup': False,
                'has_email_notifications': True,
                'has_advanced_monitoring': False,
                'has_api_access': False,
                'has_priority_support': False,
                'snapshot_retention_days': 7,
                'backup_retention_days': 30,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created Bronze plan'))
        else:
            self.stdout.write(self.style.WARNING(f'- Bronze plan already exists'))

        silver, created = Plan.objects.get_or_create(
            name='silver',
            defaults={
                'display_name': 'Silver',
                'description': 'Pour les moyennes entreprises',
                'monthly_price': 50000,
                'yearly_price': 500000,
                'max_esxi_servers': 5,
                'max_vms': 50,
                'max_backups_per_month': 500,
                'max_storage_gb': 500,
                'max_users': 5,
                'has_replication': True,
                'has_surebackup': True,
                'has_email_notifications': True,
                'has_advanced_monitoring': True,
                'has_api_access': False,
                'has_priority_support': False,
                'snapshot_retention_days': 14,
                'backup_retention_days': 60,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created Silver plan'))
        else:
            self.stdout.write(self.style.WARNING(f'- Silver plan already exists'))

        gold, created = Plan.objects.get_or_create(
            name='gold',
            defaults={
                'display_name': 'Gold',
                'description': 'Pour les grandes entreprises',
                'monthly_price': 100000,
                'yearly_price': 1000000,
                'max_esxi_servers': 20,
                'max_vms': 200,
                'max_backups_per_month': 2000,
                'max_storage_gb': 2000,
                'max_users': 20,
                'has_replication': True,
                'has_surebackup': True,
                'has_email_notifications': True,
                'has_advanced_monitoring': True,
                'has_api_access': True,
                'has_priority_support': True,
                'snapshot_retention_days': 30,
                'backup_retention_days': 90,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created Gold plan'))
        else:
            self.stdout.write(self.style.WARNING(f'- Gold plan already exists'))

        # Create Payment Methods
        paypal, created = PaymentMethod.objects.get_or_create(
            name='paypal',
            defaults={
                'display_name': 'PayPal',
                'is_active': True,
                'is_automatic': True,
                'description': 'Paiement sécurisé via PayPal'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created PayPal payment method'))
        else:
            self.stdout.write(self.style.WARNING(f'- PayPal payment method already exists'))

        mtn, created = PaymentMethod.objects.get_or_create(
            name='mtn_momo',
            defaults={
                'display_name': 'MTN Mobile Money',
                'is_active': True,
                'is_automatic': True,
                'description': 'Paiement via MTN Mobile Money'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created MTN Mobile Money payment method'))
        else:
            self.stdout.write(self.style.WARNING(f'- MTN Mobile Money payment method already exists'))

        bank, created = PaymentMethod.objects.get_or_create(
            name='bank_transfer',
            defaults={
                'display_name': 'Virement Bancaire',
                'is_active': True,
                'is_automatic': False,
                'description': 'Virement bancaire (vérification manuelle)'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created Bank Transfer payment method'))
        else:
            self.stdout.write(self.style.WARNING(f'- Bank Transfer payment method already exists'))

        self.stdout.write(self.style.SUCCESS('\n✅ All plans and payment methods are ready!'))
        self.stdout.write(self.style.SUCCESS(f'\nPlans created: Bronze, Silver, Gold'))
        self.stdout.write(self.style.SUCCESS(f'Payment methods: PayPal, MTN MoMo, Bank Transfer'))
