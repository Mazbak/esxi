"""
Serializers for multi-tenant models
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Plan, Organization, OrganizationMember, PaymentMethod,
    Order, Payment, Invoice, UsageMetrics, Coupon
)


class PlanSerializer(serializers.ModelSerializer):
    """Serializer for subscription plans"""

    class Meta:
        model = Plan
        fields = [
            'id', 'name', 'display_name', 'description',
            'monthly_price', 'yearly_price',
            'max_esxi_servers', 'max_vms', 'max_backups_per_month',
            'max_storage_gb', 'max_users',
            'has_replication', 'has_surebackup', 'has_email_notifications',
            'has_advanced_monitoring', 'has_api_access', 'has_priority_support',
            'snapshot_retention_days', 'backup_retention_days',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user information"""

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = fields


class OrganizationMemberSerializer(serializers.ModelSerializer):
    """Serializer for organization members"""
    user = UserBasicSerializer(read_only=True)
    invited_by_name = serializers.CharField(source='invited_by.username', read_only=True)

    class Meta:
        model = OrganizationMember
        fields = [
            'id', 'user', 'role', 'invited_by', 'invited_by_name',
            'invited_at', 'joined_at', 'is_active'
        ]
        read_only_fields = ['invited_at', 'invited_by']


class OrganizationSerializer(serializers.ModelSerializer):
    """Serializer for organizations"""
    plan_details = PlanSerializer(source='plan', read_only=True)
    owner_details = UserBasicSerializer(source='owner', read_only=True)
    members_count = serializers.SerializerMethodField()
    is_subscription_active = serializers.SerializerMethodField()
    days_until_expiry = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'slug', 'plan', 'plan_details',
            'status', 'subscription_start', 'subscription_end',
            'is_trial', 'trial_end', 'billing_cycle', 'next_billing_date',
            'auto_renew', 'owner', 'owner_details', 'email', 'phone',
            'address', 'city', 'country',
            'created_at', 'updated_at', 'provisioned_at',
            'members_count', 'is_subscription_active', 'days_until_expiry'
        ]
        read_only_fields = [
            'slug', 'subscription_start', 'subscription_end',
            'provisioned_at', 'created_at', 'updated_at'
        ]

    def get_members_count(self, obj):
        """Get count of active members"""
        return obj.members.filter(is_active=True).count()

    def get_is_subscription_active(self, obj):
        """Check if subscription is active"""
        return obj.is_active()

    def get_days_until_expiry(self, obj):
        """Get days until subscription expires"""
        return obj.days_until_expiry()


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Serializer for payment methods"""

    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'name', 'display_name', 'is_active',
            'is_automatic', 'description', 'created_at'
        ]
        read_only_fields = ['created_at']


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for orders"""
    plan_details = PlanSerializer(source='plan', read_only=True)
    payment_method_details = PaymentMethodSerializer(source='payment_method', read_only=True)
    organization_details = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'organization', 'organization_details',
            'user', 'plan', 'plan_details', 'billing_cycle',
            'subtotal', 'tax_amount', 'discount_amount', 'total_amount', 'currency',
            'payment_method', 'payment_method_details', 'payment_status', 'payment_date',
            'payment_reference', 'status', 'customer_name', 'customer_email', 'customer_phone',
            'provisioned_at', 'provisioning_error', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'order_number', 'payment_status', 'payment_date', 'payment_reference',
            'provisioned_at', 'provisioning_error', 'created_at', 'updated_at'
        ]

    def get_organization_details(self, obj):
        """Get organization name"""
        if obj.organization:
            return {'id': str(obj.organization.id), 'name': obj.organization.name}
        return None


class OrderCreateSerializer(serializers.Serializer):
    """Serializer for creating new orders"""
    plan_id = serializers.IntegerField(required=True)
    billing_cycle = serializers.ChoiceField(choices=['monthly', 'yearly'], required=True)
    customer_name = serializers.CharField(max_length=255, required=True)
    customer_email = serializers.EmailField(required=True)
    customer_phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    coupon_code = serializers.CharField(max_length=50, required=False, allow_blank=True)

    def validate_plan_id(self, value):
        """Validate plan exists and is active"""
        try:
            plan = Plan.objects.get(id=value, is_active=True)
        except Plan.DoesNotExist:
            raise serializers.ValidationError("Plan invalide ou inactif")
        return value


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for payments"""
    order_details = serializers.SerializerMethodField()
    payment_method_details = PaymentMethodSerializer(source='payment_method', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'transaction_id', 'order', 'order_details',
            'organization', 'payment_method', 'payment_method_details',
            'amount', 'currency', 'status', 'provider_transaction_id',
            'bank_reference', 'bank_receipt', 'verified_by', 'verified_at',
            'created_at', 'updated_at', 'completed_at', 'error_message', 'retry_count'
        ]
        read_only_fields = [
            'transaction_id', 'verified_at', 'created_at', 'updated_at',
            'completed_at', 'error_message', 'retry_count'
        ]

    def get_order_details(self, obj):
        """Get order number"""
        return {'id': obj.order.id, 'order_number': obj.order.order_number}


class PaymentInitiateSerializer(serializers.Serializer):
    """Serializer for initiating payments"""
    order_id = serializers.IntegerField(required=True)
    payment_method_id = serializers.IntegerField(required=True)
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    return_url = serializers.URLField(required=False, allow_blank=True)
    cancel_url = serializers.URLField(required=False, allow_blank=True)

    def validate_order_id(self, value):
        """Validate order exists"""
        try:
            Order.objects.get(id=value)
        except Order.DoesNotExist:
            raise serializers.ValidationError("Commande introuvable")
        return value

    def validate_payment_method_id(self, value):
        """Validate payment method exists and is active"""
        try:
            PaymentMethod.objects.get(id=value, is_active=True)
        except PaymentMethod.DoesNotExist:
            raise serializers.ValidationError("Méthode de paiement invalide")
        return value


class InvoiceSerializer(serializers.ModelSerializer):
    """Serializer for invoices"""
    organization_details = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'organization', 'organization_details',
            'order', 'issue_date', 'due_date', 'paid_date',
            'subtotal', 'tax_amount', 'discount_amount', 'total_amount', 'currency',
            'status', 'pdf_file', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'invoice_number', 'pdf_file', 'created_at', 'updated_at'
        ]

    def get_organization_details(self, obj):
        """Get organization name"""
        return {'id': str(obj.organization.id), 'name': obj.organization.name}


class UsageMetricsSerializer(serializers.ModelSerializer):
    """Serializer for usage metrics"""
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    plan_limits = serializers.SerializerMethodField()
    quota_violations = serializers.SerializerMethodField()

    class Meta:
        model = UsageMetrics
        fields = [
            'id', 'organization', 'organization_name', 'period_start', 'period_end',
            'esxi_servers_count', 'vms_count', 'backups_count',
            'storage_used_gb', 'users_count', 'replications_count',
            'surebackup_verifications_count', 'api_calls_count',
            'plan_limits', 'quota_violations', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_plan_limits(self, obj):
        """Get plan limits for comparison"""
        plan = obj.organization.plan
        return {
            'max_esxi_servers': plan.max_esxi_servers,
            'max_vms': plan.max_vms,
            'max_backups_per_month': plan.max_backups_per_month,
            'max_storage_gb': plan.max_storage_gb,
            'max_users': plan.max_users
        }

    def get_quota_violations(self, obj):
        """Get list of quota violations"""
        return obj.is_over_quota()


class CouponSerializer(serializers.ModelSerializer):
    """Serializer for discount coupons"""
    applicable_plans_details = PlanSerializer(source='applicable_plans', many=True, read_only=True)
    is_currently_valid = serializers.SerializerMethodField()

    class Meta:
        model = Coupon
        fields = [
            'id', 'code', 'description', 'discount_type', 'discount_value',
            'valid_from', 'valid_until', 'is_active', 'max_uses', 'uses_count',
            'max_uses_per_user', 'applicable_plans', 'applicable_plans_details',
            'minimum_amount', 'is_currently_valid', 'created_at', 'updated_at'
        ]
        read_only_fields = ['uses_count', 'created_at', 'updated_at']

    def get_is_currently_valid(self, obj):
        """Check if coupon is currently valid"""
        is_valid, message = obj.is_valid()
        return {'valid': is_valid, 'message': message}


class CouponValidateSerializer(serializers.Serializer):
    """Serializer for validating coupon codes"""
    code = serializers.CharField(max_length=50, required=True)
    order_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    plan_id = serializers.IntegerField(required=False)

    def validate_code(self, value):
        """Check if coupon code exists"""
        try:
            Coupon.objects.get(code=value.upper())
        except Coupon.DoesNotExist:
            raise serializers.ValidationError("Code promo invalide")
        return value.upper()
