"""
Tenant isolation middleware
Automatically filters queries based on current user's organization
"""
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)


class TenantMiddleware(MiddlewareMixin):
    """
    Middleware to set current tenant (organization) in thread-local storage
    Makes tenant context available throughout request lifecycle
    """

    def process_request(self, request):
        """
        Extract tenant from request and store in thread-local

        Tenant can be determined from:
        1. User's primary organization (from OrganizationMember)
        2. Organization ID in request headers (X-Organization-ID)
        3. Organization slug in subdomain (org.example.com)
        """
        from .models import Organization, OrganizationMember

        # Set default tenant to None
        request.tenant = None
        request.organization = None

        # Skip for anonymous users
        if not request.user or not request.user.is_authenticated:
            return None

        # Skip for superusers (they can access all tenants)
        if request.user.is_superuser:
            # Check if specific organization is requested
            org_id = request.META.get('HTTP_X_ORGANIZATION_ID')
            if org_id:
                try:
                    request.organization = Organization.objects.get(id=org_id)
                    request.tenant = request.organization.id
                except Organization.DoesNotExist:
                    pass
            return None

        # Method 1: Check for organization in request headers
        org_id = request.META.get('HTTP_X_ORGANIZATION_ID')
        if org_id:
            try:
                # Verify user has access to this organization
                membership = OrganizationMember.objects.get(
                    organization_id=org_id,
                    user=request.user,
                    is_active=True
                )
                request.organization = membership.organization
                request.tenant = request.organization.id
                logger.debug(f"Tenant set from header: {request.organization.name}")
                return None
            except OrganizationMember.DoesNotExist:
                logger.warning(f"User {request.user.username} attempted to access organization {org_id} without permission")
                return JsonResponse({'error': 'Accès non autorisé à cette organisation'}, status=403)

        # Method 2: Get user's primary organization (owner or first membership)
        try:
            # Try to get owned organization first
            owned_org = Organization.objects.filter(owner=request.user).first()
            if owned_org:
                request.organization = owned_org
                request.tenant = owned_org.id
                logger.debug(f"Tenant set from ownership: {owned_org.name}")
                return None

            # Otherwise, get first active membership
            membership = OrganizationMember.objects.filter(
                user=request.user,
                is_active=True
            ).select_related('organization').first()

            if membership:
                request.organization = membership.organization
                request.tenant = membership.organization.id
                logger.debug(f"Tenant set from membership: {membership.organization.name}")
                return None

        except Exception as e:
            logger.error(f"Error determining tenant for user {request.user.username}: {str(e)}")

        # No organization found - user might be in setup phase
        # Don't block the request, but tenant will be None
        logger.debug(f"No tenant found for user {request.user.username}")
        return None

    def process_response(self, request, response):
        """Clean up thread-local tenant context"""
        # Clean up tenant context
        if hasattr(request, 'tenant'):
            delattr(request, 'tenant')
        if hasattr(request, 'organization'):
            delattr(request, 'organization')

        return response


class TenantAccessMiddleware(MiddlewareMixin):
    """
    Middleware to enforce tenant access control
    Blocks requests if user's organization is not active
    """

    EXEMPT_PATHS = [
        '/api/auth/',
        '/api/metrics',
        '/admin/',
        '/static/',
        '/media/',
    ]

    def process_request(self, request):
        """Check if user's organization has active subscription"""
        # Skip for exempt paths
        for exempt_path in self.EXEMPT_PATHS:
            if request.path.startswith(exempt_path):
                return None

        # Skip for anonymous or superusers
        if not request.user or not request.user.is_authenticated or request.user.is_superuser:
            return None

        # Check if organization is active
        if hasattr(request, 'organization') and request.organization:
            org = request.organization

            # Check subscription status
            if org.status != 'active':
                return JsonResponse({
                    'error': 'Votre abonnement n\'est pas actif',
                    'status': org.status,
                    'message': self._get_status_message(org.status)
                }, status=403)

            # Check if subscription has expired
            if not org.is_active():
                return JsonResponse({
                    'error': 'Votre abonnement a expiré',
                    'expired_at': org.subscription_end.isoformat() if org.subscription_end else None,
                    'message': 'Veuillez renouveler votre abonnement pour continuer'
                }, status=403)

        return None

    def _get_status_message(self, status):
        """Get user-friendly message for organization status"""
        messages = {
            'pending': 'Votre compte est en attente d\'activation. Veuillez compléter le paiement.',
            'suspended': 'Votre compte a été suspendu. Veuillez contacter le support.',
            'cancelled': 'Votre abonnement a été annulé.',
            'expired': 'Votre abonnement a expiré. Veuillez le renouveler pour continuer.',
        }
        return messages.get(status, 'Accès non autorisé')
