from rest_framework import filters, viewsets
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

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
from .permissions import (
    EstaEnWhitelist,
    PermisoPorRol,
    es_superusuario,
    obtener_usuario_reflexia,
)
from .serializers import (
    EvaluacionSerializer,
    InnovacionSerializer,
    IntentoCuestionarioSerializer,
    PreguntaTeoricaEstudianteSerializer,
    PreguntaTeoricaSerializer,
    ReflexionSerializer,
    RetroalimentacionSerializer,
    TallerSerializer,
    UsuarioAutorizadoSerializer,
)

# Roles de la whitelist (UsuarioAutorizado.ROL_CHOICES).
ESTUDIANTE = 'student'
PROFESOR = 'teacher'
ADMINISTRADOR = 'admin'


# ─────────────────────────────────────────────
# Bases con permisos
# ─────────────────────────────────────────────


class ViewSetConRoles(viewsets.ModelViewSet):
    """
    ModelViewSet que exige whitelist activa y un rol permitido (RN-01, RN-02).

    Cada ViewSet hijo declara qué roles pueden leer, crear y editar. Los
    roles siguen la matriz de permisos del frontend
    (docs/especificacion/03-actores-y-permisos.md). Los superusuarios de
    Django pueden hacer todo, igual que en el panel de administración.
    """

    permission_classes = [EstaEnWhitelist, PermisoPorRol]
    roles_lectura = frozenset()
    roles_creacion = frozenset()
    roles_edicion = frozenset()

    @property
    def usuario_reflexia(self):
        return obtener_usuario_reflexia(self.request)

    def es_estudiante(self):
        if es_superusuario(self.request):
            return False
        usuario = self.usuario_reflexia
        return usuario is not None and usuario.rol == ESTUDIANTE


class RegistrosPropiosMixin:
    """
    Un estudiante solo ve y modifica sus propios registros.

    - Al listar o ver el detalle, solo recibe los suyos; los de otro
      estudiante responden 404, como si no existieran.
    - Al crear o modificar, no puede asignar el registro a otro estudiante.

    `campo_estudiante` es el camino desde el modelo hasta el estudiante
    dueño del registro (por ejemplo, 'reflexion__estudiante').
    """

    campo_estudiante = 'estudiante'
    mensaje_ajeno = 'Solo puedes registrar datos a tu nombre.'

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.es_estudiante():
            queryset = queryset.filter(**{self.campo_estudiante: self.usuario_reflexia})
        return queryset

    def validar_dueno(self, serializer):
        if not self.es_estudiante():
            return
        estudiante = serializer.validated_data.get('estudiante')
        if estudiante is not None and estudiante != self.usuario_reflexia:
            raise PermissionDenied(self.mensaje_ajeno)

    def perform_create(self, serializer):
        self.validar_dueno(serializer)
        serializer.save()

    def perform_update(self, serializer):
        self.validar_dueno(serializer)
        serializer.save()


# ─────────────────────────────────────────────
# Sesión
# ─────────────────────────────────────────────


class UsuarioActualView(APIView):
    """
    GET /api/auth/yo/: quién soy y con qué rol (HU-08).

    Equivale a `verifyUserAccess` del frontend: confirma que el correo de
    la sesión está activo en la whitelist y devuelve su rol, para que el
    frontend sepa a qué panel redirigir.
    """

    permission_classes = [EstaEnWhitelist]

    def get(self, request):
        usuario = obtener_usuario_reflexia(request)
        return Response({
            'correo': usuario.correo if usuario else request.user.email,
            'nombre': usuario.nombre if usuario else request.user.get_full_name(),
            'rol': usuario.rol if usuario else None,
            'es_superusuario': es_superusuario(request),
        })


class RutaNoEncontradaView(APIView):
    """
    Responde 404 en JSON a cualquier ruta de /api/ que no existe.

    Sin esta vista, Django devolvería su página HTML de error, y el
    frontend esperaría JSON. No exige sesión: una ruta inexistente responde
    lo mismo a todos.
    """

    authentication_classes = []
    permission_classes = []

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        raise NotFound(f'La ruta {request.path} no existe en la API.')


# ─────────────────────────────────────────────
# Recursos
# ─────────────────────────────────────────────


class UsuarioAutorizadoViewSet(ViewSetConRoles):
    # Gestión de la whitelist: solo el administrador (HU-01).
    queryset = UsuarioAutorizado.objects.all()
    serializer_class = UsuarioAutorizadoSerializer
    roles_lectura = {ADMINISTRADOR}
    roles_creacion = {ADMINISTRADOR}
    roles_edicion = {ADMINISTRADOR}


class TallerViewSet(ViewSetConRoles):
    # El estudiante consulta los talleres; el profesor guía define su
    # estructura, plazo e intentos (HU-06, HU-09).
    queryset = Taller.objects.all()
    serializer_class = TallerSerializer
    roles_lectura = {ESTUDIANTE, PROFESOR}
    roles_creacion = {PROFESOR}
    roles_edicion = {PROFESOR}


class PreguntaTeoricaViewSet(ViewSetConRoles):
    # prefetch_related trae todas las alternativas en una sola consulta,
    # en vez de hacer una consulta por cada pregunta.
    queryset = PreguntaTeorica.objects.prefetch_related('alternativas')
    serializer_class = PreguntaTeoricaSerializer
    roles_lectura = {ESTUDIANTE, PROFESOR}
    roles_creacion = {PROFESOR}
    roles_edicion = {PROFESOR}

    def get_queryset(self):
        queryset = super().get_queryset()
        # El estudiante solo recibe las preguntas que están en uso.
        if self.es_estudiante():
            queryset = queryset.filter(activa=True)
        return queryset

    def get_serializer_class(self):
        # El estudiante no debe ver qué alternativa es la correcta.
        if self.es_estudiante():
            return PreguntaTeoricaEstudianteSerializer
        return super().get_serializer_class()


class IntentoCuestionarioViewSet(RegistrosPropiosMixin, ViewSetConRoles):
    # select_related trae el estudiante de cada intento en la misma
    # consulta, porque la respuesta incluye su correo.
    queryset = IntentoCuestionario.objects.select_related('estudiante')
    serializer_class = IntentoCuestionarioSerializer
    # El estudiante registra y ve sus intentos; el profesor guía los ve
    # todos para el seguimiento. Un intento rendido no se modifica: queda
    # como registro (solo un superusuario puede corregirlo).
    roles_lectura = {ESTUDIANTE, PROFESOR}
    roles_creacion = {ESTUDIANTE}
    roles_edicion = frozenset()
    mensaje_ajeno = 'Solo puedes registrar tus propios intentos.'


class ReflexionViewSet(RegistrosPropiosMixin, ViewSetConRoles):
    # select_related trae el estudiante y el taller de cada reflexión en
    # la misma consulta, porque la respuesta incluye el correo y el número.
    queryset = Reflexion.objects.select_related('estudiante', 'taller')
    serializer_class = ReflexionSerializer
    # El estudiante escribe sus reflexiones; el profesor guía las lee
    # para revisarlas (HU-02, HU-03).
    roles_lectura = {ESTUDIANTE, PROFESOR}
    roles_creacion = {ESTUDIANTE}
    roles_edicion = {ESTUDIANTE}
    mensaje_ajeno = 'Solo puedes escribir tus propias reflexiones.'


class RetroalimentacionViewSet(RegistrosPropiosMixin, ViewSetConRoles):
    queryset = Retroalimentacion.objects.select_related(
        'reflexion',
        'reflexion__estudiante',
        'reflexion__taller',
    )
    serializer_class = RetroalimentacionSerializer
    # El profesor guía revisa y valida la retroalimentación; el estudiante
    # solo lee la de sus propias reflexiones (HU-02).
    roles_lectura = {ESTUDIANTE, PROFESOR}
    roles_creacion = {PROFESOR}
    roles_edicion = {PROFESOR}
    campo_estudiante = 'reflexion__estudiante'


class EvaluacionViewSet(RegistrosPropiosMixin, ViewSetConRoles):
    queryset = Evaluacion.objects.select_related('estudiante', 'taller')
    serializer_class = EvaluacionSerializer
    # Solo el profesor guía escribe notas oficiales; el estudiante ve
    # las suyas.
    roles_lectura = {ESTUDIANTE, PROFESOR}
    roles_creacion = {PROFESOR}
    roles_edicion = {PROFESOR}


class InnovacionViewSet(ViewSetConRoles):
    # select_related trae el autor en la misma consulta y prefetch_related
    # trae los pasos de todas las innovaciones en una sola consulta.
    queryset = Innovacion.objects.select_related('autor').prefetch_related('pasos')
    serializer_class = InnovacionSerializer
    # ?search=<texto> busca en los mismos campos que el buscador del
    # frontend; la categoría se filtra aparte con ?categoria=.
    filter_backends = [filters.SearchFilter]
    search_fields = ['titulo', 'resumen', 'contexto', 'etiquetas']
    # El estudiante consulta la biblioteca; el profesor guía revisa,
    # anonimiza y publica (HU-07, DEC-14).
    roles_lectura = {ESTUDIANTE, PROFESOR}
    roles_creacion = {PROFESOR}
    roles_edicion = {PROFESOR}

    def get_queryset(self):
        queryset = super().get_queryset()
        parametros = self.request.query_params

        # El estudiante solo ve los casos publicados.
        if self.es_estudiante():
            queryset = queryset.filter(publicada=True)

        # ?categoria=<valor> deja solo los casos de esa categoría (HU-07).
        categoria = parametros.get('categoria')
        if categoria:
            categorias = dict(Innovacion.CATEGORIA_CHOICES)
            if categoria not in categorias:
                opciones = ', '.join(categorias)
                raise ValidationError({
                    'categoria': [f'"{categoria}" no es una categoría válida. Usa una de estas: {opciones}.'],
                })
            queryset = queryset.filter(categoria=categoria)

        # ?publicada=true|false separa los casos publicados de los borradores.
        publicada = parametros.get('publicada')
        if publicada:
            if publicada.lower() not in ('true', 'false'):
                raise ValidationError({'publicada': ['Debe ser "true" o "false".']})
            queryset = queryset.filter(publicada=publicada.lower() == 'true')

        return queryset
