from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

# Cada ViewSet de views.py se registra aquí, por ejemplo:
# router.register(r'usuarios', views.UsuarioAutorizadoViewSet)
router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
]
