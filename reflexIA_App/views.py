from rest_framework import viewsets

from .models import Taller, UsuarioAutorizado
from .serializers import TallerSerializer, UsuarioAutorizadoSerializer


class UsuarioAutorizadoViewSet(viewsets.ModelViewSet):
    queryset = UsuarioAutorizado.objects.all()
    serializer_class = UsuarioAutorizadoSerializer


class TallerViewSet(viewsets.ModelViewSet):
    queryset = Taller.objects.all()
    serializer_class = TallerSerializer
