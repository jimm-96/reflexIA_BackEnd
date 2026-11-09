from rest_framework import viewsets

from .models import IntentoCuestionario, PreguntaTeorica, Taller, UsuarioAutorizado
from .serializers import (
    IntentoCuestionarioSerializer,
    PreguntaTeoricaSerializer,
    TallerSerializer,
    UsuarioAutorizadoSerializer,
)


class UsuarioAutorizadoViewSet(viewsets.ModelViewSet):
    queryset = UsuarioAutorizado.objects.all()
    serializer_class = UsuarioAutorizadoSerializer


class TallerViewSet(viewsets.ModelViewSet):
    queryset = Taller.objects.all()
    serializer_class = TallerSerializer


class PreguntaTeoricaViewSet(viewsets.ModelViewSet):
    # prefetch_related trae todas las alternativas en una sola consulta,
    # en vez de hacer una consulta por cada pregunta.
    queryset = PreguntaTeorica.objects.prefetch_related('alternativas')
    serializer_class = PreguntaTeoricaSerializer


class IntentoCuestionarioViewSet(viewsets.ModelViewSet):
    # select_related trae el estudiante de cada intento en la misma
    # consulta, porque la respuesta incluye su correo.
    queryset = IntentoCuestionario.objects.select_related('estudiante')
    serializer_class = IntentoCuestionarioSerializer
