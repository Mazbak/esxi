"""
Custom model managers for automatic tenant filtering
"""
from django.db import models
import threading

# Thread-local storage for current tenant
_thread_locals = threading.local()


def get_current_tenant():
    """Get current tenant from thread-local storage"""
    return getattr(_thread_locals, 'tenant', None)


def set_current_tenant(tenant_id):
    """Set current tenant in thread-local storage"""
    _thread_locals.tenant = tenant_id


def clear_current_tenant():
    """Clear current tenant from thread-local storage"""
    if hasattr(_thread_locals, 'tenant'):
        delattr(_thread_locals, 'tenant')


class TenantManager(models.Manager):
    """
    Custom manager that automatically filters querysets by current tenant
    """

    def get_queryset(self):
        """Override to add tenant filter"""
        queryset = super().get_queryset()
        tenant_id = get_current_tenant()

        if tenant_id:
            # Filter by organization
            return queryset.filter(organization_id=tenant_id)

        return queryset


class TenantManagerWithAll(TenantManager):
    """
    Manager with 'all_tenants()' method to bypass tenant filtering
    Useful for superuser access or admin operations
    """

    def all_tenants(self):
        """Get queryset without tenant filtering"""
        return super(TenantManager, self).get_queryset()


# Middleware integration helper
class TenantMiddlewareHelper:
    """
    Helper to integrate with TenantMiddleware
    Sets tenant in thread-local from request
    """

    @staticmethod
    def set_tenant_from_request(request):
        """Extract tenant from request and set in thread-local"""
        if hasattr(request, 'tenant') and request.tenant:
            set_current_tenant(request.tenant)
        else:
            clear_current_tenant()

    @staticmethod
    def clear_tenant():
        """Clear tenant from thread-local"""
        clear_current_tenant()
