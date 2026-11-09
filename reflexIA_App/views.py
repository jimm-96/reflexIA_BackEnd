from rest_framework import viewsets

from .models import PreguntaTeorica, Taller, UsuarioAutorizado
from .serializers import (
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
