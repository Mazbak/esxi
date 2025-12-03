"""
URL configuration for tenants app
"""
from django.urls import path, include
from rest_framework import routers
from .views import (
    PlanViewSet, OrganizationViewSet, OrderViewSet,
    PaymentViewSet, InvoiceViewSet, UsageMetricsViewSet,
    CouponViewSet
)

router = routers.DefaultRouter()
router.register(r'plans', PlanViewSet, basename='plans')
router.register(r'organizations', OrganizationViewSet, basename='organizations')
router.register(r'orders', OrderViewSet, basename='orders')
router.register(r'payments', PaymentViewSet, basename='payments')
router.register(r'invoices', InvoiceViewSet, basename='invoices')
router.register(r'usage-metrics', UsageMetricsViewSet, basename='usage-metrics')
router.register(r'coupons', CouponViewSet, basename='coupons')

urlpatterns = [
    path('', include(router.urls)),
]
