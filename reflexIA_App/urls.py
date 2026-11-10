from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'usuarios', views.UsuarioAutorizadoViewSet)
router.register(r'talleres', views.TallerViewSet)
router.register(r'preguntas', views.PreguntaTeoricaViewSet)
router.register(r'intentos-cuestionario', views.IntentoCuestionarioViewSet)
router.register(r'reflexiones', views.ReflexionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
