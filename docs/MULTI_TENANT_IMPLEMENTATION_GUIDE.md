# Guide d'Implémentation Multi-Tenant SaaS

Ce guide explique comment intégrer l'architecture multi-tenant dans l'application ESXi Backup Manager existante.

## Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Installation et Configuration](#installation-et-configuration)
3. [Migration des Modèles Existants](#migration-des-modèles-existants)
4. [Configuration des Paiements](#configuration-des-paiements)
5. [Tests](#tests)
6. [Déploiement](#déploiement)

---

## Vue d'ensemble

L'architecture multi-tenant utilise le modèle **Single Database + Row-Level Security (RLS)** :

- **Une seule base de données** pour tous les tenants
- **Isolation au niveau des lignes** via des filtres automatiques
- **Middleware** pour détecter le tenant courant
- **Managers personnalisés** pour filtrage automatique des queries
- **Provisionnement automatique** après paiement confirmé

### Structure des Dossiers

```
backend/
├── tenants/                    # Application multi-tenant
│   ├── models.py              # Plan, Organization, Order, Payment, etc.
│   ├── serializers.py         # Serializers REST API
│   ├── views.py               # ViewSets pour API
│   ├── urls.py                # Routes API tenants
│   ├── admin.py               # Interface admin Django
│   ├── middleware.py          # TenantMiddleware, TenantAccessMiddleware
│   ├── managers.py            # TenantManager pour filtrage auto
│   └── services/
│       ├── payment_service.py     # PayPal, MTN MoMo, Bank Transfer
│       └── provisioning_service.py # Provisionnement automatique
└── esxi/
    ├── models.py              # Modèles ESXi existants (à modifier)
    └── ...
```

---

## Installation et Configuration

### Étape 1: Ajouter l'application tenants

Modifier `backend/backend/settings.py` :

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'esxi',
    'tenants',  # ← Ajouter ici
]
```

### Étape 2: Configurer les Middlewares

Ajouter les middlewares dans `settings.py` :

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'tenants.middleware.TenantMiddleware',        # ← Ajouter après auth
    'tenants.middleware.TenantAccessMiddleware',  # ← Ajouter après tenant
]
```

### Étape 3: Configurer les URLs

Modifier `backend/backend/urls.py` :

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('api/tenants/', include('tenants.urls')),  # ← Ajouter ici
]
```

### Étape 4: Configuration des Paiements

Ajouter dans `settings.py` :

```python
# PayPal Configuration
PAYPAL_MODE = 'sandbox'  # 'sandbox' ou 'live'
PAYPAL_CLIENT_ID = 'your-paypal-client-id'
PAYPAL_CLIENT_SECRET = 'your-paypal-client-secret'

# MTN Mobile Money Configuration
MTN_MOMO_ENVIRONMENT = 'sandbox'  # 'sandbox' ou 'production'
MTN_MOMO_SUBSCRIPTION_KEY = 'your-mtn-subscription-key'
MTN_MOMO_USER_ID = 'your-mtn-user-id'
MTN_MOMO_API_KEY = 'your-mtn-api-key'

# Bank Transfer Configuration
BANK_NAME = 'Votre Banque'
BANK_ACCOUNT_NAME = 'ESXi Backup Manager SAS'
BANK_ACCOUNT_NUMBER = 'XXXXXXXXXXXX'
BANK_SWIFT_CODE = 'XXXXXXXX'
BANK_IBAN = 'XX XX XXXX XXXX XXXX XXXX XXXX XXX'
BANK_BRANCH = 'Agence Principale'

# Application URL (for emails)
APP_BASE_URL = 'http://localhost:5173'  # Frontend URL
```

### Étape 5: Créer les Migrations

```bash
cd backend
python manage.py makemigrations tenants
python manage.py migrate tenants
```

### Étape 6: Créer les Plans de Subscription

Créer un fichier `backend/tenants/management/commands/create_plans.py` :

```python
from django.core.management.base import BaseCommand
from tenants.models import Plan, PaymentMethod


class Command(BaseCommand):
    help = 'Create default subscription plans and payment methods'

    def handle(self, *args, **kwargs):
        # Create Plans
        bronze, _ = Plan.objects.get_or_create(
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

        silver, _ = Plan.objects.get_or_create(
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

        gold, _ = Plan.objects.get_or_create(
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

        # Create Payment Methods
        PaymentMethod.objects.get_or_create(
            name='paypal',
            defaults={
                'display_name': 'PayPal',
                'is_active': True,
                'is_automatic': True,
                'description': 'Paiement sécurisé via PayPal'
            }
        )

        PaymentMethod.objects.get_or_create(
            name='mtn_momo',
            defaults={
                'display_name': 'MTN Mobile Money',
                'is_active': True,
                'is_automatic': True,
                'description': 'Paiement via MTN Mobile Money'
            }
        )

        PaymentMethod.objects.get_or_create(
            name='bank_transfer',
            defaults={
                'display_name': 'Virement Bancaire',
                'is_active': True,
                'is_automatic': False,
                'description': 'Virement bancaire (vérification manuelle)'
            }
        )

        self.stdout.write(self.style.SUCCESS('Plans and payment methods created successfully'))
```

Exécuter la commande :

```bash
python manage.py create_plans
```

---

## Migration des Modèles Existants

Pour isoler les données par tenant, il faut ajouter un champ `organization` aux modèles existants.

### Étape 1: Modifier les Modèles ESXi

Modifier `backend/esxi/models.py` :

```python
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from tenants.managers import TenantManager  # ← Importer

class ESXiServer(models.Model):
    # ← Ajouter ce champ
    organization = models.ForeignKey(
        'tenants.Organization',
        on_delete=models.CASCADE,
        related_name='esxi_servers',
        null=True,  # Temporaire pour migration
        blank=True
    )

    hostname = models.CharField(max_length=255)
    username = models.CharField(max_length=100)
    password = models.CharField(max_length=100)
    port = models.PositiveIntegerField(default=443)
    connection_status = models.CharField(max_length=50, default='disconnected')
    last_connection = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='servers')
    created_at = models.DateTimeField(auto_now_add=True)

    # ← Ajouter les managers
    objects = TenantManager()  # Manager avec filtrage auto
    all_objects = models.Manager()  # Manager sans filtrage (pour admins)

    def __str__(self):
        return self.hostname

    class Meta:
        # ← Ajouter index pour performance
        indexes = [
            models.Index(fields=['organization']),
        ]
```

**Répéter pour tous les modèles** :
- `VirtualMachine`
- `DatastoreInfo`
- `BackupConfiguration`
- `BackupJob`
- `BackupSchedule`
- `SnapshotSchedule`
- `Snapshot`
- `RemoteStorageConfig`
- `BackupChain`
- `NotificationConfig`
- `NotificationLog`
- `OVFExportJob`
- `VMBackupJob`
- `StoragePath`
- `VMReplication`
- `FailoverEvent`
- `BackupVerification`
- `BackupVerificationSchedule`

### Étape 2: Créer les Migrations

```bash
python manage.py makemigrations esxi
```

### Étape 3: Migration de Données

Créer un script de migration pour assigner les objets existants à une organisation par défaut :

```bash
python manage.py shell
```

```python
from tenants.models import Organization, Plan
from django.contrib.auth.models import User
from esxi.models import ESXiServer, VirtualMachine  # etc.

# Créer une organisation par défaut pour les données existantes
admin_user = User.objects.filter(is_superuser=True).first()
default_plan = Plan.objects.get(name='gold')

default_org, created = Organization.objects.get_or_create(
    slug='default-organization',
    defaults={
        'name': 'Organisation par Défaut',
        'plan': default_plan,
        'owner': admin_user,
        'email': admin_user.email,
        'status': 'active',
        'billing_cycle': 'yearly'
    }
)

# Assigner tous les objets existants à cette organisation
ESXiServer.all_objects.filter(organization__isnull=True).update(organization=default_org)
VirtualMachine.all_objects.filter(organization__isnull=True).update(organization=default_org)
# Répéter pour tous les modèles...

print(f"Migration completed. {ESXiServer.all_objects.count()} servers assigned to default organization")
```

### Étape 4: Rendre organization Obligatoire

Après la migration, modifier les modèles pour rendre `organization` obligatoire :

```python
organization = models.ForeignKey(
    'tenants.Organization',
    on_delete=models.CASCADE,
    related_name='esxi_servers',
    null=False,  # ← Changer de True à False
    blank=False  # ← Changer de True à False
)
```

Créer et exécuter une nouvelle migration :

```bash
python manage.py makemigrations esxi
python manage.py migrate esxi
```

---

## Modification des ViewSets Existants

Modifier les ViewSets pour utiliser le tenant courant.

### Exemple: ESXiServerViewSet

Modifier `backend/api/views.py` :

```python
from rest_framework import viewsets
from tenants.managers import set_current_tenant

class ESXiServerViewSet(viewsets.ModelViewSet):
    queryset = ESXiServer.objects.all()  # Filtré automatiquement par TenantManager
    serializer_class = ESXiServerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        """Assigner automatiquement l'organisation courante"""
        if hasattr(self.request, 'organization') and self.request.organization:
            serializer.save(
                created_by=self.request.user,
                organization=self.request.organization
            )
        else:
            raise ValidationError("Aucune organisation active")

    def get_queryset(self):
        """Optionnel: Filtrage explicite supplémentaire"""
        queryset = super().get_queryset()

        # Le TenantManager filtre déjà, mais on peut ajouter d'autres filtres
        # Par exemple, vérifier les quotas
        if hasattr(self.request, 'organization'):
            org = self.request.organization
            plan = org.plan

            # Si on approche de la limite, logger un warning
            count = queryset.count()
            if count >= plan.max_esxi_servers * 0.9:
                logger.warning(f"Organization {org.name} approaching ESXi server quota")

        return queryset
```

---

## Configuration des Paiements

### PayPal

1. Créer un compte développeur : https://developer.paypal.com
2. Créer une application REST API
3. Copier Client ID et Secret dans `settings.py`

### MTN Mobile Money

1. S'inscrire sur MTN MoMo Developer Portal : https://momodeveloper.mtn.com
2. Créer un produit Collections
3. Obtenir les clés API et les ajouter dans `settings.py`

### Virement Bancaire

1. Configurer les coordonnées bancaires dans `settings.py`
2. Les paiements nécessitent une vérification manuelle par un admin dans Django Admin

---

## Flux de Paiement Complet

### 1. Création de Commande

**Frontend:**
```javascript
// Créer une commande
const response = await fetch('/api/tenants/orders/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    plan_id: 2,  // Silver
    billing_cycle: 'monthly',
    customer_name: 'Entreprise XYZ',
    customer_email: 'contact@xyz.com',
    customer_phone: '237XXXXXXXXX',
    coupon_code: 'PROMO2024'  // Optionnel
  })
})

const order = await response.json()
console.log('Order created:', order.order_number)
```

### 2. Initier le Paiement

**PayPal:**
```javascript
const payment = await fetch(`/api/tenants/orders/${order.id}/initiate_payment/`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    order_id: order.id,
    payment_method_id: 1,  // PayPal
    return_url: 'https://myapp.com/payment/success',
    cancel_url: 'https://myapp.com/payment/cancel'
  })
})

const result = await payment.json()
// Rediriger vers PayPal
window.location.href = result.redirect_url
```

**MTN Mobile Money:**
```javascript
const payment = await fetch(`/api/tenants/orders/${order.id}/initiate_payment/`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    order_id: order.id,
    payment_method_id: 2,  // MTN MoMo
    phone_number: '237XXXXXXXXX'
  })
})

const result = await payment.json()
// Afficher message: "Vérifiez votre téléphone pour confirmer"
// Puis poll le statut
```

**Virement Bancaire:**
```javascript
const payment = await fetch(`/api/tenants/orders/${order.id}/initiate_payment/`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    order_id: order.id,
    payment_method_id: 3  // Bank Transfer
  })
})

const result = await payment.json()
// Afficher les coordonnées bancaires
console.log(result.bank_details)
// Permettre l'upload du reçu
```

### 3. Vérifier le Paiement

**Polling (pour MTN MoMo, Bank Transfer):**
```javascript
async function checkPaymentStatus(orderId) {
  const response = await fetch(`/api/tenants/orders/${orderId}/verify_payment/`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  })

  const result = await response.json()

  if (result.success && result.organization) {
    // Paiement confirmé et organisation créée
    console.log('Organization provisioned:', result.organization)
    return true
  }

  return false
}

// Poll toutes les 5 secondes
const interval = setInterval(async () => {
  const completed = await checkPaymentStatus(order.id)
  if (completed) {
    clearInterval(interval)
    // Rediriger vers l'application
    window.location.href = '/dashboard'
  }
}, 5000)
```

---

## Tests

### Tests Unitaires

Créer `backend/tenants/tests.py` :

```python
from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
from .models import Plan, Organization, Order
from .services.provisioning_service import ProvisioningService


class ProvisioningTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )

        self.plan = Plan.objects.create(
            name='bronze',
            display_name='Bronze',
            monthly_price=Decimal('25000'),
            yearly_price=Decimal('250000'),
            max_esxi_servers=2,
            max_vms=10,
            max_backups_per_month=100,
            max_storage_gb=100,
            max_users=2
        )

    def test_provision_organization(self):
        """Test organization provisioning"""
        order = Order.objects.create(
            user=self.user,
            plan=self.plan,
            billing_cycle='monthly',
            customer_name='Test Company',
            customer_email='test@company.com',
            subtotal=Decimal('25000'),
            total_amount=Decimal('25000'),
            status='paid',
            payment_status='paid'
        )

        service = ProvisioningService()
        org = service.provision_organization(order)

        self.assertIsNotNone(org)
        self.assertEqual(org.name, 'Test Company')
        self.assertEqual(org.plan, self.plan)
        self.assertEqual(org.status, 'active')
        self.assertTrue(org.members.filter(user=self.user, role='owner').exists())

    def test_usage_metrics_created(self):
        """Test that usage metrics are created on provisioning"""
        order = Order.objects.create(
            user=self.user,
            plan=self.plan,
            billing_cycle='monthly',
            customer_name='Test Company 2',
            customer_email='test2@company.com',
            subtotal=Decimal('25000'),
            total_amount=Decimal('25000'),
            status='paid',
            payment_status='paid'
        )

        service = ProvisioningService()
        org = service.provision_organization(order)

        self.assertTrue(org.usage_metrics.exists())
        metrics = org.usage_metrics.first()
        self.assertEqual(metrics.users_count, 1)
```

Exécuter les tests :

```bash
python manage.py test tenants
```

---

## Déploiement

### 1. Variables d'Environnement

Créer un fichier `.env` :

```bash
# Django
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DB_NAME=esxi_backup
DB_USER=postgres
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432

# PayPal
PAYPAL_MODE=live
PAYPAL_CLIENT_ID=your-live-client-id
PAYPAL_CLIENT_SECRET=your-live-client-secret

# MTN Mobile Money
MTN_MOMO_ENVIRONMENT=production
MTN_MOMO_SUBSCRIPTION_KEY=your-production-key
MTN_MOMO_USER_ID=your-production-user-id
MTN_MOMO_API_KEY=your-production-api-key

# Bank
BANK_NAME=Your Bank Name
BANK_ACCOUNT_NUMBER=XXXXXXXXXXXX
# ... autres infos bancaires

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True

# Application
APP_BASE_URL=https://yourdomain.com
```

### 2. Collecte des Fichiers Statiques

```bash
python manage.py collectstatic --noinput
```

### 3. Migrations

```bash
python manage.py migrate
```

### 4. Créer un Superuser

```bash
python manage.py createsuperuser
```

### 5. Créer les Plans

```bash
python manage.py create_plans
```

### 6. Configuration Celery (pour tasks asynchrones)

Créer `backend/tenants/tasks.py` pour les tâches périodiques :

```python
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Organization, UsageMetrics


@shared_task
def check_subscription_expirations():
    """Check for expiring subscriptions and send notifications"""
    tomorrow = timezone.now().date() + timedelta(days=1)

    expiring_orgs = Organization.objects.filter(
        status='active',
        subscription_end__date=tomorrow
    )

    for org in expiring_orgs:
        # Send expiration warning email
        pass  # TODO: Implement


@shared_task
def update_usage_metrics():
    """Update usage metrics for all active organizations"""
    from esxi.models import ESXiServer, VirtualMachine, BackupJob

    active_orgs = Organization.objects.filter(status='active')

    for org in active_orgs:
        current_period = UsageMetrics.objects.filter(
            organization=org,
            period_start__lte=timezone.now().date(),
            period_end__gte=timezone.now().date()
        ).first()

        if current_period:
            current_period.esxi_servers_count = ESXiServer.objects.filter(
                organization=org
            ).count()
            current_period.vms_count = VirtualMachine.objects.filter(
                organization=org
            ).count()
            current_period.backups_count = BackupJob.objects.filter(
                organization=org,
                created_at__gte=current_period.period_start
            ).count()
            current_period.save()
```

Ajouter dans `backend/backend/celery.py` :

```python
from celery.schedules import crontab

app.conf.beat_schedule = {
    'check-subscription-expirations': {
        'task': 'tenants.tasks.check_subscription_expirations',
        'schedule': crontab(hour=0, minute=0),  # Tous les jours à minuit
    },
    'update-usage-metrics': {
        'task': 'tenants.tasks.update_usage_metrics',
        'schedule': crontab(hour='*/6'),  # Toutes les 6 heures
    },
}
```

---

## Endpoints API Disponibles

### Plans
- `GET /api/tenants/plans/` - Liste des plans
- `GET /api/tenants/plans/{id}/` - Détails d'un plan
- `GET /api/tenants/plans/{id}/features/` - Fonctionnalités du plan

### Organizations
- `GET /api/tenants/organizations/` - Mes organisations
- `GET /api/tenants/organizations/{id}/` - Détails organisation
- `GET /api/tenants/organizations/{id}/members/` - Membres
- `POST /api/tenants/organizations/{id}/invite_member/` - Inviter un membre
- `GET /api/tenants/organizations/{id}/usage/` - Métriques d'utilisation

### Orders
- `GET /api/tenants/orders/` - Mes commandes
- `POST /api/tenants/orders/` - Créer une commande
- `POST /api/tenants/orders/{id}/initiate_payment/` - Initier paiement
- `POST /api/tenants/orders/{id}/verify_payment/` - Vérifier paiement

### Payments
- `GET /api/tenants/payments/` - Mes paiements
- `GET /api/tenants/payments/{id}/` - Détails paiement
- `POST /api/tenants/payments/{id}/verify_bank_transfer/` - Vérifier virement (admin)

### Invoices
- `GET /api/tenants/invoices/` - Mes factures
- `GET /api/tenants/invoices/{id}/download/` - Télécharger PDF

### Coupons
- `POST /api/tenants/coupons/validate/` - Valider un code promo

---

## Sécurité

### Isolation des Tenants

- Le `TenantMiddleware` détecte automatiquement le tenant courant
- Le `TenantManager` filtre toutes les queries par `organization`
- Les ViewSets vérifient les permissions et l'appartenance

### Vérifications des Quotas

Ajouter un décorateur pour vérifier les quotas avant création :

```python
from functools import wraps
from rest_framework.exceptions import ValidationError


def check_quota(resource_type):
    """Decorator to check quota before creating resource"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            if hasattr(request, 'organization'):
                org = request.organization
                plan = org.plan

                # Get current count
                if resource_type == 'esxi_server':
                    count = org.esxi_servers.count()
                    max_count = plan.max_esxi_servers
                elif resource_type == 'vm':
                    count = org.vms.count()
                    max_count = plan.max_vms
                # etc.

                if count >= max_count:
                    raise ValidationError(
                        f"Limite de {max_count} {resource_type}(s) atteinte. "
                        f"Veuillez mettre à niveau votre plan."
                    )

            return func(self, request, *args, **kwargs)
        return wrapper
    return decorator


# Utilisation
class ESXiServerViewSet(viewsets.ModelViewSet):
    @check_quota('esxi_server')
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
```

---

## Prochaines Étapes

1. **Admin Back-Office** : Interface web pour gérer les commandes, paiements, organisations
2. **Landing Page** : Page marketing avec pricing, features, inscription
3. **Frontend Multi-Tenant** : Composants Vue.js pour gestion d'organisation, paiements
4. **Webhooks** : Réception automatique des notifications PayPal/MTN MoMo
5. **Factures PDF** : Génération automatique de factures
6. **Emails Transactionnels** : Templates d'emails pour tous les événements
7. **Monitoring** : Dashboards de monitoring par organisation et global

---

## Support

Pour toute question sur l'implémentation, consulter :
- Documentation Django : https://docs.djangoproject.com
- Documentation DRF : https://www.django-rest-framework.org
- PayPal API : https://developer.paypal.com/docs/api/overview/
- MTN MoMo API : https://momodeveloper.mtn.com/api-documentation/
