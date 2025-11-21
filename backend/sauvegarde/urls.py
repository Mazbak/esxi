

from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),  # 👈 Toutes les routes REST
    path('api-token-auth/', views.obtain_auth_token),  # <-- ajoute ça
]


