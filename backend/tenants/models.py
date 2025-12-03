"""
Multi-tenant models for SaaS architecture
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
import uuid


class Plan(models.Model):
    """Subscription plans (Bronze, Silver, Gold)"""
    PLAN_TYPES = [
        ('bronze', 'Bronze'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
    ]

    name = models.CharField(max_length=50, choices=PLAN_TYPES, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField()

    # Pricing
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2)
    yearly_price = models.DecimalField(max_digits=10, decimal_places=2)

    # Quotas & Limits
    max_esxi_servers = models.IntegerField(help_text="Nombre max de serveurs ESXi")
    max_vms = models.IntegerField(help_text="Nombre max de VMs")
    max_backups_per_month = models.IntegerField(help_text="Nombre max de sauvegardes/mois")
    max_storage_gb = models.IntegerField(help_text="Stockage max en GB")
    max_users = models.IntegerField(help_text="Nombre max d'utilisateurs par organisation")

    # Features
    has_replication = models.BooleanField(default=False)
    has_surebackup = models.BooleanField(default=False)
    has_email_notifications = models.BooleanField(default=True)
    has_advanced_monitoring = models.BooleanField(default=False)
    has_api_access = models.BooleanField(default=False)
    has_priority_support = models.BooleanField(default=False)

    # Retention policies
    snapshot_retention_days = models.IntegerField(default=7)
    backup_retention_days = models.IntegerField(default=30)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['monthly_price']

    def __str__(self):
        return self.display_name


class Organization(models.Model):
    """Tenant/Workspace/Client organization"""
    STATUS_CHOICES = [
        ('pending', 'En Attente'),  # After order, before payment
        ('active', 'Actif'),        # After payment, provisioned
        ('suspended', 'Suspendu'),  # Payment failed
        ('cancelled', 'Annulé'),    # User cancelled
        ('expired', 'Expiré'),      # Subscription expired
    ]

    # Identity
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text="Nom de l'organisation")
    slug = models.SlugField(max_length=100, unique=True, help_text="Identifiant unique (URL)")

    # Subscription
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='organizations')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    subscription_start = models.DateTimeField(null=True, blank=True)
    subscription_end = models.DateTimeField(null=True, blank=True)
    is_trial = models.BooleanField(default=False)
    trial_end = models.DateTimeField(null=True, blank=True)

    # Billing
    billing_cycle = models.CharField(max_length=20, choices=[('monthly', 'Mensuel'), ('yearly', 'Annuel')], default='monthly')
    next_billing_date = models.DateField(null=True, blank=True)
    auto_renew = models.BooleanField(default=True)

    # Owner
    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name='owned_organizations')

    # Contact info
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)

    # Address
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    provisioned_at = models.DateTimeField(null=True, blank=True, help_text="Date de provisionnement automatique")

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.name} ({self.plan.display_name})"

    def is_active(self):
        """Check if organization has active subscription"""
        if self.status != 'active':
            return False
        if self.subscription_end and self.subscription_end < timezone.now():
            return False
        return True

    def days_until_expiry(self):
        """Calculate days until subscription expires"""
        if self.subscription_end:
            delta = self.subscription_end - timezone.now()
            return delta.days
        return None


class OrganizationMember(models.Model):
    """Users belonging to an organization"""
    ROLE_CHOICES = [
        ('owner', 'Propriétaire'),
        ('admin', 'Administrateur'),
        ('member', 'Membre'),
        ('viewer', 'Observateur'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organization_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')

    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='invited_members')
    invited_at = models.DateTimeField(auto_now_add=True)
    joined_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ['organization', 'user']
        ordering = ['-invited_at']

    def __str__(self):
        return f"{self.user.username} @ {self.organization.name} ({self.role})"


class PaymentMethod(models.Model):
    """Payment methods supported"""
    METHOD_TYPES = [
        ('paypal', 'PayPal'),
        ('mtn_momo', 'MTN Mobile Money'),
        ('bank_transfer', 'Virement Bancaire'),
        ('credit_card', 'Carte de Crédit'),
    ]

    name = models.CharField(max_length=50, choices=METHOD_TYPES, unique=True)
    display_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    is_automatic = models.BooleanField(default=False, help_text="Paiement automatique ou manuel")
    description = models.TextField(blank=True)

    # Configuration (JSON field for API keys, etc.)
    config = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name


class Order(models.Model):
    """Customer orders for plans"""
    STATUS_CHOICES = [
        ('pending', 'En Attente'),           # Order created, awaiting payment
        ('payment_pending', 'Paiement en Attente'),  # Payment initiated
        ('paid', 'Payé'),                    # Payment confirmed
        ('processing', 'En Traitement'),     # Provisioning in progress
        ('completed', 'Terminé'),            # Provisioned successfully
        ('failed', 'Échoué'),                # Payment or provisioning failed
        ('cancelled', 'Annulé'),             # User cancelled
        ('refunded', 'Remboursé'),           # Payment refunded
    ]

    # Order identification
    order_number = models.CharField(max_length=50, unique=True, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='orders', null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='orders')

    # Order details
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    billing_cycle = models.CharField(max_length=20, choices=[('monthly', 'Mensuel'), ('yearly', 'Annuel')])

    # Pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='XAF')  # XAF for Central Africa

    # Payment
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT, null=True, blank=True)
    payment_status = models.CharField(max_length=20, default='pending')
    payment_date = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=255, blank=True, help_text="Transaction ID from payment provider")

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Customer info (snapshot at order time)
    customer_name = models.CharField(max_length=255)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=50, blank=True)

    # Provisioning
    provisioned_at = models.DateTimeField(null=True, blank=True)
    provisioning_error = models.TextField(blank=True)

    # Metadata
    notes = models.TextField(blank=True, help_text="Notes internes admin")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['status']),
            models.Index(fields=['payment_status']),
        ]

    def __str__(self):
        return f"Order {self.order_number} - {self.plan.display_name} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate order number: ORD-YYYYMMDD-XXXXX
            from django.utils import timezone
            import random
            date_str = timezone.now().strftime('%Y%m%d')
            random_str = ''.join([str(random.randint(0, 9)) for _ in range(5)])
            self.order_number = f"ORD-{date_str}-{random_str}"
        super().save(*args, **kwargs)


class Payment(models.Model):
    """Payment transactions"""
    STATUS_CHOICES = [
        ('pending', 'En Attente'),
        ('processing', 'En Traitement'),
        ('completed', 'Terminé'),
        ('failed', 'Échoué'),
        ('cancelled', 'Annulé'),
        ('refunded', 'Remboursé'),
    ]

    # Payment identification
    transaction_id = models.CharField(max_length=255, unique=True)
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name='payments')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='payments', null=True)

    # Payment details
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='XAF')

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Provider details (PayPal, MTN, etc.)
    provider_transaction_id = models.CharField(max_length=255, blank=True, help_text="ID from payment provider")
    provider_response = models.JSONField(default=dict, blank=True, help_text="Raw response from provider")

    # Bank transfer specific
    bank_reference = models.CharField(max_length=255, blank=True)
    bank_receipt = models.FileField(upload_to='payment_receipts/', null=True, blank=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_payments')
    verified_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Error handling
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Payment {self.transaction_id} - {self.amount} {self.currency} ({self.status})"


class Invoice(models.Model):
    """Invoices for completed orders"""
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('sent', 'Envoyé'),
        ('paid', 'Payé'),
        ('overdue', 'En Retard'),
        ('cancelled', 'Annulé'),
    ]

    # Invoice identification
    invoice_number = models.CharField(max_length=50, unique=True, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='invoices')
    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name='invoice', null=True, blank=True)

    # Invoice details
    issue_date = models.DateField()
    due_date = models.DateField()
    paid_date = models.DateField(null=True, blank=True)

    # Amounts
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='XAF')

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    # PDF file
    pdf_file = models.FileField(upload_to='invoices/', null=True, blank=True)

    # Metadata
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-issue_date']
        indexes = [
            models.Index(fields=['invoice_number']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.organization.name}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            # Generate invoice number: INV-YYYYMM-XXXXX
            from django.utils import timezone
            import random
            date_str = timezone.now().strftime('%Y%m')
            random_str = ''.join([str(random.randint(0, 9)) for _ in range(5)])
            self.invoice_number = f"INV-{date_str}-{random_str}"
        super().save(*args, **kwargs)


class UsageMetrics(models.Model):
    """Track usage metrics per organization for billing and quotas"""
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='usage_metrics')

    # Period
    period_start = models.DateField()
    period_end = models.DateField()

    # Usage counters
    esxi_servers_count = models.IntegerField(default=0)
    vms_count = models.IntegerField(default=0)
    backups_count = models.IntegerField(default=0)
    storage_used_gb = models.FloatField(default=0.0)
    users_count = models.IntegerField(default=0)

    # Feature usage
    replications_count = models.IntegerField(default=0)
    surebackup_verifications_count = models.IntegerField(default=0)
    api_calls_count = models.IntegerField(default=0)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-period_start']
        unique_together = ['organization', 'period_start']
        indexes = [
            models.Index(fields=['organization', 'period_start']),
        ]

    def __str__(self):
        return f"Usage {self.organization.name} - {self.period_start}"

    def is_over_quota(self):
        """Check if organization has exceeded plan quotas"""
        plan = self.organization.plan
        violations = []

        if self.esxi_servers_count > plan.max_esxi_servers:
            violations.append(f"ESXi Servers: {self.esxi_servers_count}/{plan.max_esxi_servers}")
        if self.vms_count > plan.max_vms:
            violations.append(f"VMs: {self.vms_count}/{plan.max_vms}")
        if self.backups_count > plan.max_backups_per_month:
            violations.append(f"Backups: {self.backups_count}/{plan.max_backups_per_month}")
        if self.storage_used_gb > plan.max_storage_gb:
            violations.append(f"Storage: {self.storage_used_gb}/{plan.max_storage_gb} GB")
        if self.users_count > plan.max_users:
            violations.append(f"Users: {self.users_count}/{plan.max_users}")

        return violations


class Coupon(models.Model):
    """Discount coupons"""
    DISCOUNT_TYPES = [
        ('percentage', 'Pourcentage'),
        ('fixed', 'Montant Fixe'),
    ]

    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    # Discount
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)

    # Validity
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    # Usage limits
    max_uses = models.IntegerField(null=True, blank=True, help_text="Nombre max d'utilisations (null = illimité)")
    uses_count = models.IntegerField(default=0)
    max_uses_per_user = models.IntegerField(default=1)

    # Restrictions
    applicable_plans = models.ManyToManyField(Plan, blank=True, help_text="Plans éligibles (vide = tous)")
    minimum_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.code} - {self.discount_value}{'%' if self.discount_type == 'percentage' else ' XAF'}"

    def is_valid(self):
        """Check if coupon is currently valid"""
        now = timezone.now()
        if not self.is_active:
            return False, "Coupon désactivé"
        if now < self.valid_from:
            return False, "Coupon pas encore actif"
        if now > self.valid_until:
            return False, "Coupon expiré"
        if self.max_uses and self.uses_count >= self.max_uses:
            return False, "Nombre maximum d'utilisations atteint"
        return True, "Valide"

    def calculate_discount(self, amount):
        """Calculate discount amount for given order amount"""
        if self.discount_type == 'percentage':
            return amount * (self.discount_value / Decimal('100'))
        else:
            return min(self.discount_value, amount)  # Never discount more than order amount
