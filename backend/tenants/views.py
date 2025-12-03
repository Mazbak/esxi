"""
ViewSets for multi-tenant API endpoints
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from decimal import Decimal

from .models import (
    Plan, Organization, OrganizationMember, PaymentMethod,
    Order, Payment, Invoice, UsageMetrics, Coupon
)
from .serializers import (
    PlanSerializer, OrganizationSerializer, OrganizationMemberSerializer,
    PaymentMethodSerializer, OrderSerializer, OrderCreateSerializer,
    PaymentSerializer, PaymentInitiateSerializer,
    InvoiceSerializer, UsageMetricsSerializer,
    CouponSerializer, CouponValidateSerializer
)
from .services.payment_service import PaymentService, PaymentException
from .services.provisioning_service import ProvisioningService, ProvisioningException
import logging

logger = logging.getLogger(__name__)


class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for subscription plans
    Read-only for regular users
    """
    queryset = Plan.objects.filter(is_active=True)
    serializer_class = PlanSerializer
    permission_classes = [permissions.AllowAny]  # Public access to view plans

    @action(detail=True, methods=['get'])
    def features(self, request, pk=None):
        """Get detailed features for a plan"""
        plan = self.get_object()

        features = {
            'name': plan.display_name,
            'pricing': {
                'monthly': float(plan.monthly_price),
                'yearly': float(plan.yearly_price),
                'currency': 'XAF'
            },
            'quotas': {
                'esxi_servers': plan.max_esxi_servers,
                'vms': plan.max_vms,
                'backups_per_month': plan.max_backups_per_month,
                'storage_gb': plan.max_storage_gb,
                'users': plan.max_users
            },
            'features': {
                'replication': plan.has_replication,
                'surebackup': plan.has_surebackup,
                'email_notifications': plan.has_email_notifications,
                'advanced_monitoring': plan.has_advanced_monitoring,
                'api_access': plan.has_api_access,
                'priority_support': plan.has_priority_support
            },
            'retention': {
                'snapshots_days': plan.snapshot_retention_days,
                'backups_days': plan.backup_retention_days
            }
        }

        return Response(features)


class OrganizationViewSet(viewsets.ModelViewSet):
    """ViewSet for organizations"""
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter organizations by user membership"""
        user = self.request.user

        if user.is_superuser:
            return Organization.objects.all()

        # Get organizations where user is member
        return Organization.objects.filter(
            members__user=user,
            members__is_active=True
        ).distinct()

    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """Get organization members"""
        org = self.get_object()
        members = org.members.filter(is_active=True)
        serializer = OrganizationMemberSerializer(members, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def invite_member(self, request, pk=None):
        """Invite new member to organization"""
        org = self.get_object()

        # Check if user has permission to invite (owner or admin)
        membership = org.members.filter(
            user=request.user,
            role__in=['owner', 'admin']
        ).first()

        if not membership:
            return Response(
                {'error': 'Vous n\'avez pas la permission d\'inviter des membres'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check quota
        current_members = org.members.filter(is_active=True).count()
        if current_members >= org.plan.max_users:
            return Response(
                {'error': f'Limite de {org.plan.max_users} utilisateurs atteinte'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create invitation (simplified - in production, send email with token)
        email = request.data.get('email')
        role = request.data.get('role', 'member')

        # TODO: Implement proper invitation flow with email
        return Response({
            'message': 'Invitation envoyée',
            'email': email,
            'role': role
        })

    @action(detail=True, methods=['get'])
    def usage(self, request, pk=None):
        """Get current usage metrics"""
        org = self.get_object()

        # Get current period metrics
        current_metrics = org.usage_metrics.order_by('-period_start').first()

        if not current_metrics:
            return Response({
                'error': 'Aucune métrique disponible'
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = UsageMetricsSerializer(current_metrics)
        return Response(serializer.data)


class OrderViewSet(viewsets.ModelViewSet):
    """ViewSet for orders"""
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter orders by user"""
        user = self.request.user

        if user.is_superuser:
            return Order.objects.all()

        return Order.objects.filter(user=user)

    def get_serializer_class(self):
        """Use different serializer for create action"""
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Create new order"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        # Get plan
        plan = Plan.objects.get(id=data['plan_id'])

        # Calculate amounts
        if data['billing_cycle'] == 'monthly':
            subtotal = plan.monthly_price
        else:
            subtotal = plan.yearly_price

        # Apply coupon if provided
        discount_amount = Decimal('0.00')
        if 'coupon_code' in data and data['coupon_code']:
            try:
                coupon = Coupon.objects.get(code=data['coupon_code'].upper())
                is_valid, message = coupon.is_valid()

                if not is_valid:
                    return Response(
                        {'error': f'Code promo invalide: {message}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Check minimum amount
                if coupon.minimum_amount and subtotal < coupon.minimum_amount:
                    return Response(
                        {'error': f'Montant minimum requis: {coupon.minimum_amount} XAF'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Check applicable plans
                if coupon.applicable_plans.exists() and plan not in coupon.applicable_plans.all():
                    return Response(
                        {'error': 'Ce code promo n\'est pas applicable à ce plan'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                discount_amount = coupon.calculate_discount(subtotal)

            except Coupon.DoesNotExist:
                return Response(
                    {'error': 'Code promo invalide'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Calculate total
        tax_amount = Decimal('0.00')  # Add tax calculation if needed
        total_amount = subtotal - discount_amount + tax_amount

        # Create order
        order = Order.objects.create(
            user=request.user,
            plan=plan,
            billing_cycle=data['billing_cycle'],
            customer_name=data['customer_name'],
            customer_email=data['customer_email'],
            customer_phone=data.get('customer_phone', ''),
            subtotal=subtotal,
            tax_amount=tax_amount,
            discount_amount=discount_amount,
            total_amount=total_amount,
            currency='XAF',
            status='pending'
        )

        # Increment coupon usage
        if discount_amount > 0:
            coupon.uses_count += 1
            coupon.save()

        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def initiate_payment(self, request, pk=None):
        """Initiate payment for order"""
        order = self.get_object()

        # Validate order can be paid
        if order.status not in ['pending', 'payment_pending']:
            return Response(
                {'error': 'Cette commande ne peut pas être payée'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = PaymentInitiateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        payment_method = PaymentMethod.objects.get(id=data['payment_method_id'])

        # Initiate payment
        payment_service = PaymentService()

        try:
            result = payment_service.initiate_payment(
                order=order,
                payment_method=payment_method,
                phone_number=data.get('phone_number'),
                return_url=data.get('return_url'),
                cancel_url=data.get('cancel_url')
            )

            # Update order status
            order.status = 'payment_pending'
            order.payment_method = payment_method
            order.save()

            return Response(result)

        except PaymentException as e:
            logger.error(f"Payment initiation failed: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def verify_payment(self, request, pk=None):
        """Verify payment status and complete provisioning"""
        order = self.get_object()

        # Get latest payment for this order
        payment = order.payments.order_by('-created_at').first()

        if not payment:
            return Response(
                {'error': 'Aucun paiement trouvé pour cette commande'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verify payment
        payment_service = PaymentService()
        result = payment_service.verify_payment(payment)

        if result['success'] and result['status'] == 'completed':
            # Update order
            order.payment_status = 'paid'
            order.payment_date = timezone.now()
            order.status = 'processing'
            order.save()

            # Provision organization
            provisioning_service = ProvisioningService()

            try:
                org = provisioning_service.provision_organization(order)

                return Response({
                    'success': True,
                    'message': 'Paiement confirmé et espace de travail créé',
                    'organization': {
                        'id': str(org.id),
                        'name': org.name,
                        'slug': org.slug
                    }
                })

            except ProvisioningException as e:
                logger.error(f"Provisioning failed: {str(e)}")
                return Response(
                    {'error': f'Paiement confirmé mais provisionnement échoué: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return Response(result)


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for payments (read-only for users)"""
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter payments by user"""
        user = self.request.user

        if user.is_superuser:
            return Payment.objects.all()

        # Get payments for user's orders
        return Payment.objects.filter(order__user=user)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def verify_bank_transfer(self, request, pk=None):
        """Admin action to verify bank transfer"""
        payment = self.get_object()

        if payment.payment_method.name != 'bank_transfer':
            return Response(
                {'error': 'Cette action est réservée aux virements bancaires'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from .services.payment_service import BankTransferPaymentService

        success = BankTransferPaymentService.verify_bank_transfer(payment, request.user)

        if success:
            # Update order and trigger provisioning
            order = payment.order
            order.payment_status = 'paid'
            order.payment_date = timezone.now()
            order.status = 'processing'
            order.save()

            # Provision organization
            provisioning_service = ProvisioningService()

            try:
                org = provisioning_service.provision_organization(order)

                return Response({
                    'success': True,
                    'message': 'Virement vérifié et organisation provisionnée',
                    'organization_id': str(org.id)
                })

            except ProvisioningException as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return Response(
            {'error': 'Échec de la vérification'},
            status=status.HTTP_400_BAD_REQUEST
        )


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for invoices"""
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter invoices by organization"""
        user = self.request.user

        if user.is_superuser:
            return Invoice.objects.all()

        # Get invoices for user's organizations
        return Invoice.objects.filter(
            organization__members__user=user,
            organization__members__is_active=True
        ).distinct()

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download invoice PDF"""
        invoice = self.get_object()

        if not invoice.pdf_file:
            return Response(
                {'error': 'PDF non disponible'},
                status=status.HTTP_404_NOT_FOUND
            )

        # TODO: Return file download response
        return Response({
            'url': invoice.pdf_file.url
        })


class UsageMetricsViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for usage metrics"""
    queryset = UsageMetrics.objects.all()
    serializer_class = UsageMetricsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter metrics by organization"""
        user = self.request.user

        if user.is_superuser:
            return UsageMetrics.objects.all()

        # Get metrics for user's organizations
        return UsageMetrics.objects.filter(
            organization__members__user=user,
            organization__members__is_active=True
        ).distinct()


class CouponViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for coupons (admin manage, users can validate)"""
    queryset = Coupon.objects.filter(is_active=True)
    serializer_class = CouponSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['post'])
    def validate(self, request):
        """Validate coupon code"""
        serializer = CouponValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        try:
            coupon = Coupon.objects.get(code=data['code'])

            # Check validity
            is_valid, message = coupon.is_valid()

            if not is_valid:
                return Response({
                    'valid': False,
                    'message': message
                }, status=status.HTTP_400_BAD_REQUEST)

            # Check minimum amount
            if coupon.minimum_amount and data['order_amount'] < coupon.minimum_amount:
                return Response({
                    'valid': False,
                    'message': f'Montant minimum requis: {coupon.minimum_amount} XAF'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Check applicable plans
            if 'plan_id' in data and coupon.applicable_plans.exists():
                plan = Plan.objects.get(id=data['plan_id'])
                if plan not in coupon.applicable_plans.all():
                    return Response({
                        'valid': False,
                        'message': 'Ce code promo n\'est pas applicable à ce plan'
                    }, status=status.HTTP_400_BAD_REQUEST)

            # Calculate discount
            discount_amount = coupon.calculate_discount(data['order_amount'])

            return Response({
                'valid': True,
                'code': coupon.code,
                'discount_type': coupon.discount_type,
                'discount_value': float(coupon.discount_value),
                'discount_amount': float(discount_amount),
                'final_amount': float(data['order_amount'] - discount_amount)
            })

        except Coupon.DoesNotExist:
            return Response({
                'valid': False,
                'message': 'Code promo invalide'
            }, status=status.HTTP_404_NOT_FOUND)
