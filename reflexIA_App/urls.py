from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'usuarios', views.UsuarioAutorizadoViewSet)
router.register(r'talleres', views.TallerViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
