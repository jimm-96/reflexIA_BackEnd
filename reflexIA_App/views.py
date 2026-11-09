from rest_framework import viewsets

from .models import UsuarioAutorizado
from .serializers import UsuarioAutorizadoSerializer


class UsuarioAutorizadoViewSet(viewsets.ModelViewSet):
    queryset = UsuarioAutorizado.objects.all()
    serializer_class = UsuarioAutorizadoSerializer
