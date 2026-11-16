from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'usuarios', views.UsuarioAutorizadoViewSet)
router.register(r'talleres', views.TallerViewSet)
router.register(r'preguntas', views.PreguntaTeoricaViewSet)
router.register(r'intentos-cuestionario', views.IntentoCuestionarioViewSet)
router.register(r'reflexiones', views.ReflexionViewSet)
router.register(r'retroalimentaciones', views.RetroalimentacionViewSet)
router.register(r'evaluaciones', views.EvaluacionViewSet)
router.register(r'innovaciones', views.InnovacionViewSet)

urlpatterns = [
    # Autenticación (HU-08): obtener un token y consultar la sesión actual.
    path('auth/token/', obtain_auth_token, name='auth-token'),
    path('auth/yo/', views.UsuarioActualView.as_view(), name='auth-yo'),
    path('', include(router.urls)),
]
