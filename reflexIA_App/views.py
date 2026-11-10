from rest_framework import viewsets

from .models import (
    Evaluacion,
    Innovacion,
    IntentoCuestionario,
    PreguntaTeorica,
    Reflexion,
    Retroalimentacion,
    Taller,
    UsuarioAutorizado,
)
from .serializers import (
    EvaluacionSerializer,
    InnovacionSerializer,
    IntentoCuestionarioSerializer,
    PreguntaTeoricaSerializer,
    ReflexionSerializer,
    RetroalimentacionSerializer,
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


class ReflexionViewSet(viewsets.ModelViewSet):
    # select_related trae el estudiante y el taller de cada reflexión en
    # la misma consulta, porque la respuesta incluye el correo y el número.
    queryset = Reflexion.objects.select_related('estudiante', 'taller')
    serializer_class = ReflexionSerializer


class RetroalimentacionViewSet(viewsets.ModelViewSet):
    queryset = Retroalimentacion.objects.select_related(
        'reflexion',
        'reflexion__estudiante',
        'reflexion__taller',
    )
    serializer_class = RetroalimentacionSerializer


class EvaluacionViewSet(viewsets.ModelViewSet):
    queryset = Evaluacion.objects.select_related('estudiante', 'taller')
    serializer_class = EvaluacionSerializer


class InnovacionViewSet(viewsets.ModelViewSet):
    # select_related trae el autor en la misma consulta y prefetch_related
    # trae los pasos de todas las innovaciones en una sola consulta.
    queryset = Innovacion.objects.select_related('autor').prefetch_related('pasos')
    serializer_class = InnovacionSerializer
