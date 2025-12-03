from rest_framework import routers
from django.urls import path, include
from .views import (
    ESXiServerViewSet, VirtualMachineViewSet, DatastoreInfoViewSet,
    BackupConfigurationViewSet, BackupJobViewSet, BackupScheduleViewSet,
    SnapshotScheduleViewSet, SnapshotViewSet, RemoteStorageConfigViewSet,
    RestoreViewSet, BackupChainViewSet, DashboardViewSet,
    NotificationConfigViewSet, NotificationLogViewSet, HealthMonitoringViewSet,
    OVFExportJobViewSet, VMBackupJobViewSet, StoragePathViewSet,
    VMReplicationViewSet, FailoverEventViewSet,
    BackupVerificationViewSet, BackupVerificationScheduleViewSet,
    EmailSettingsViewSet,
    login_view, logout_view, current_user_view, prometheus_metrics
)

router = routers.DefaultRouter()
router.register(r'esxi-servers', ESXiServerViewSet)
router.register(r'virtual-machines', VirtualMachineViewSet)
router.register(r'datastores', DatastoreInfoViewSet)
router.register(r'backup-configs', BackupConfigurationViewSet)
router.register(r'backup-jobs', BackupJobViewSet)
router.register(r'backup-schedules', BackupScheduleViewSet)
router.register(r'snapshot-schedules', SnapshotScheduleViewSet)
router.register(r'snapshots', SnapshotViewSet)
router.register(r'remote-storage', RemoteStorageConfigViewSet, basename='remote-storage')
router.register(r'restore', RestoreViewSet, basename='restore')
router.register(r'backup-chains', BackupChainViewSet, basename='backup-chains')
router.register(r'dashboard', DashboardViewSet, basename='dashboard')
router.register(r'notifications', NotificationConfigViewSet, basename='notifications')
router.register(r'notification-logs', NotificationLogViewSet, basename='notification-logs')
router.register(r'health', HealthMonitoringViewSet, basename='health')
router.register(r'ovf-exports', OVFExportJobViewSet, basename='ovf-exports')
router.register(r'vm-backups', VMBackupJobViewSet, basename='vm-backups')
router.register(r'storage-paths', StoragePathViewSet, basename='storage-paths')
router.register(r'vm-replications', VMReplicationViewSet, basename='vm-replications')
router.register(r'failover-events', FailoverEventViewSet, basename='failover-events')
router.register(r'backup-verifications', BackupVerificationViewSet, basename='backup-verifications')
router.register(r'verification-schedules', BackupVerificationScheduleViewSet, basename='verification-schedules')
router.register(r'email-settings', EmailSettingsViewSet, basename='email-settings')

urlpatterns = [
    # Authentication endpoints
    path('auth/login/', login_view, name='auth-login'),
    path('auth/logout/', logout_view, name='auth-logout'),
    path('auth/user/', current_user_view, name='auth-user'),

    # Prometheus metrics for Grafana
    path('metrics', prometheus_metrics, name='prometheus-metrics'),

    # Router URLs (all other endpoints)
    path('', include(router.urls)),
]
