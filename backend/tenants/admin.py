"""
Django admin configuration for tenants app
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Plan, Organization, OrganizationMember, PaymentMethod,
    Order, Payment, Invoice, UsageMetrics, Coupon
)


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    """Admin interface for Plans"""
    list_display = [
        'display_name', 'name', 'monthly_price', 'yearly_price',
        'max_esxi_servers', 'max_vms', 'is_active'
    ]
    list_filter = ['is_active', 'has_replication', 'has_surebackup']
    search_fields = ['name', 'display_name']
    ordering = ['monthly_price']

    fieldsets = (
        ('Informations de Base', {
            'fields': ('name', 'display_name', 'description', 'is_active')
        }),
        ('Tarification', {
            'fields': ('monthly_price', 'yearly_price')
        }),
        ('Quotas', {
            'fields': (
                'max_esxi_servers', 'max_vms', 'max_backups_per_month',
                'max_storage_gb', 'max_users'
            )
        }),
        ('Fonctionnalités', {
            'fields': (
                'has_replication', 'has_surebackup', 'has_email_notifications',
                'has_advanced_monitoring', 'has_api_access', 'has_priority_support'
            )
        }),
        ('Rétention', {
            'fields': ('snapshot_retention_days', 'backup_retention_days')
        }),
    )


class OrganizationMemberInline(admin.TabularInline):
    """Inline for organization members"""
    model = OrganizationMember
    extra = 0
    fields = ['user', 'role', 'is_active', 'invited_at', 'joined_at']
    readonly_fields = ['invited_at']


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    """Admin interface for Organizations"""
    list_display = [
        'name', 'slug', 'plan', 'status_badge', 'owner',
        'subscription_end', 'members_count'
    ]
    list_filter = ['status', 'plan', 'billing_cycle', 'is_trial']
    search_fields = ['name', 'slug', 'email', 'owner__username']
    readonly_fields = ['id', 'slug', 'created_at', 'updated_at', 'provisioned_at']
    inlines = [OrganizationMemberInline]

    fieldsets = (
        ('Informations de Base', {
            'fields': ('id', 'name', 'slug', 'owner', 'email', 'phone')
        }),
        ('Abonnement', {
            'fields': (
                'plan', 'status', 'billing_cycle', 'auto_renew',
                'subscription_start', 'subscription_end', 'next_billing_date'
            )
        }),
        ('Essai Gratuit', {
            'fields': ('is_trial', 'trial_end')
        }),
        ('Adresse', {
            'fields': ('address', 'city', 'country'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at', 'provisioned_at'),
            'classes': ('collapse',)
        }),
    )

    def status_badge(self, obj):
        """Display status as colored badge"""
        colors = {
            'pending': '#ffc107',
            'active': '#28a745',
            'suspended': '#dc3545',
            'cancelled': '#6c757d',
            'expired': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def members_count(self, obj):
        """Display count of active members"""
        count = obj.members.filter(is_active=True).count()
        max_users = obj.plan.max_users
        return f"{count}/{max_users}"
    members_count.short_description = 'Membres'

    actions = ['activate_organizations', 'suspend_organizations']

    def activate_organizations(self, request, queryset):
        """Activate selected organizations"""
        count = queryset.update(status='active')
        self.message_user(request, f"{count} organisation(s) activée(s)")
    activate_organizations.short_description = "Activer les organisations sélectionnées"

    def suspend_organizations(self, request, queryset):
        """Suspend selected organizations"""
        count = queryset.update(status='suspended')
        self.message_user(request, f"{count} organisation(s) suspendue(s)")
    suspend_organizations.short_description = "Suspendre les organisations sélectionnées"


@admin.register(OrganizationMember)
class OrganizationMemberAdmin(admin.ModelAdmin):
    """Admin interface for Organization Members"""
    list_display = ['user', 'organization', 'role', 'is_active', 'invited_at']
    list_filter = ['role', 'is_active']
    search_fields = ['user__username', 'user__email', 'organization__name']
    readonly_fields = ['invited_at']


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    """Admin interface for Payment Methods"""
    list_display = ['display_name', 'name', 'is_active', 'is_automatic']
    list_filter = ['is_active', 'is_automatic']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin interface for Orders"""
    list_display = [
        'order_number', 'customer_name', 'plan', 'billing_cycle',
        'total_amount', 'status_badge', 'payment_status', 'created_at'
    ]
    list_filter = ['status', 'payment_status', 'billing_cycle', 'plan']
    search_fields = ['order_number', 'customer_name', 'customer_email']
    readonly_fields = [
        'order_number', 'created_at', 'updated_at',
        'provisioned_at', 'payment_date'
    ]
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Commande', {
            'fields': ('order_number', 'user', 'organization', 'status')
        }),
        ('Plan', {
            'fields': ('plan', 'billing_cycle')
        }),
        ('Client', {
            'fields': ('customer_name', 'customer_email', 'customer_phone')
        }),
        ('Montants', {
            'fields': (
                'subtotal', 'tax_amount', 'discount_amount',
                'total_amount', 'currency'
            )
        }),
        ('Paiement', {
            'fields': (
                'payment_method', 'payment_status', 'payment_date',
                'payment_reference'
            )
        }),
        ('Provisionnement', {
            'fields': ('provisioned_at', 'provisioning_error')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def status_badge(self, obj):
        """Display status as colored badge"""
        colors = {
            'pending': '#ffc107',
            'payment_pending': '#17a2b8',
            'paid': '#28a745',
            'processing': '#17a2b8',
            'completed': '#28a745',
            'failed': '#dc3545',
            'cancelled': '#6c757d',
            'refunded': '#fd7e14',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Admin interface for Payments"""
    list_display = [
        'transaction_id', 'order', 'payment_method', 'amount',
        'status_badge', 'created_at'
    ]
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = [
        'transaction_id', 'provider_transaction_id',
        'order__order_number', 'bank_reference'
    ]
    readonly_fields = [
        'transaction_id', 'created_at', 'updated_at',
        'completed_at', 'verified_at'
    ]
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Paiement', {
            'fields': (
                'transaction_id', 'order', 'organization',
                'payment_method', 'amount', 'currency', 'status'
            )
        }),
        ('Fournisseur', {
            'fields': (
                'provider_transaction_id', 'provider_response'
            )
        }),
        ('Virement Bancaire', {
            'fields': (
                'bank_reference', 'bank_receipt',
                'verified_by', 'verified_at'
            ),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': (
                'created_at', 'updated_at', 'completed_at',
                'error_message', 'retry_count'
            ),
            'classes': ('collapse',)
        }),
    )

    def status_badge(self, obj):
        """Display status as colored badge"""
        colors = {
            'pending': '#ffc107',
            'processing': '#17a2b8',
            'completed': '#28a745',
            'failed': '#dc3545',
            'cancelled': '#6c757d',
            'refunded': '#fd7e14',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    actions = ['verify_bank_transfers']

    def verify_bank_transfers(self, request, queryset):
        """Verify selected bank transfer payments"""
        from .services.payment_service import BankTransferPaymentService

        count = 0
        for payment in queryset.filter(
            payment_method__name='bank_transfer',
            status='pending'
        ):
            if BankTransferPaymentService.verify_bank_transfer(payment, request.user):
                count += 1

        self.message_user(request, f"{count} virement(s) vérifié(s)")
    verify_bank_transfers.short_description = "Vérifier les virements bancaires sélectionnés"


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    """Admin interface for Invoices"""
    list_display = [
        'invoice_number', 'organization', 'total_amount',
        'status', 'issue_date', 'due_date'
    ]
    list_filter = ['status', 'issue_date']
    search_fields = ['invoice_number', 'organization__name']
    readonly_fields = ['invoice_number', 'created_at', 'updated_at']
    date_hierarchy = 'issue_date'


@admin.register(UsageMetrics)
class UsageMetricsAdmin(admin.ModelAdmin):
    """Admin interface for Usage Metrics"""
    list_display = [
        'organization', 'period_start', 'period_end',
        'esxi_servers_count', 'vms_count', 'backups_count',
        'storage_used_gb'
    ]
    list_filter = ['period_start']
    search_fields = ['organization__name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'period_start'


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    """Admin interface for Coupons"""
    list_display = [
        'code', 'discount_type', 'discount_value',
        'is_active', 'valid_from', 'valid_until',
        'uses_count', 'max_uses'
    ]
    list_filter = ['is_active', 'discount_type', 'valid_from']
    search_fields = ['code', 'description']
    filter_horizontal = ['applicable_plans']
    readonly_fields = ['uses_count', 'created_at', 'updated_at']

    fieldsets = (
        ('Code Promo', {
            'fields': ('code', 'description', 'is_active')
        }),
        ('Remise', {
            'fields': ('discount_type', 'discount_value')
        }),
        ('Validité', {
            'fields': ('valid_from', 'valid_until')
        }),
        ('Limites d\'Utilisation', {
            'fields': ('max_uses', 'uses_count', 'max_uses_per_user')
        }),
        ('Restrictions', {
            'fields': ('applicable_plans', 'minimum_amount')
        }),
        ('Métadonnées', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['activate_coupons', 'deactivate_coupons']

    def activate_coupons(self, request, queryset):
        """Activate selected coupons"""
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} code(s) promo activé(s)")
    activate_coupons.short_description = "Activer les codes promo sélectionnés"

    def deactivate_coupons(self, request, queryset):
        """Deactivate selected coupons"""
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} code(s) promo désactivé(s)")
    deactivate_coupons.short_description = "Désactiver les codes promo sélectionnés"
