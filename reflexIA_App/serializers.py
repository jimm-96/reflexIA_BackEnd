from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import (
    Alternativa,
    Evaluacion,
    Innovacion,
    IntentoCuestionario,
    PasoInnovacion,
    PreguntaTeorica,
    Reflexion,
    Retroalimentacion,
    Taller,
    UsuarioAutorizado,
    validar_correo_institucional,
)


class UsuarioAutorizadoSerializer(serializers.ModelSerializer):
    # Se declara el campo para que la revisión de duplicados ignore
    # mayúsculas: "ANA@ucen.cl" y "ana@ucen.cl" son el mismo correo.
    correo = serializers.EmailField(
        validators=[
            UniqueValidator(
                queryset=UsuarioAutorizado.objects.all(),
                lookup='iexact',
                message='Este correo ya está autorizado.',
            ),
            validar_correo_institucional,
        ]
    )

    class Meta:
        model = UsuarioAutorizado
        fields = '__all__'
        read_only_fields = ('fecha_registro',)


class TallerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Taller
        fields = '__all__'


class AlternativaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alternativa
        fields = ('id', 'texto', 'es_correcta')


class PreguntaTeoricaSerializer(serializers.ModelSerializer):
    # Cada pregunta trae sus alternativas dentro del mismo JSON.
    # Son de solo lectura: por ahora se cargan desde el admin.
    alternativas = AlternativaSerializer(many=True, read_only=True)

    class Meta:
        model = PreguntaTeorica
        fields = ('id', 'enunciado', 'activa', 'alternativas')


class IntentoCuestionarioSerializer(serializers.ModelSerializer):
    # El estudiante se recibe por su id; el correo se agrega en la
    # respuesta para que se lea quién rindió sin buscar el id.
    correo_estudiante = serializers.EmailField(source='estudiante.correo', read_only=True)

    class Meta:
        model = IntentoCuestionario
        fields = (
            'id',
            'estudiante',
            'correo_estudiante',
            'respuestas_correctas',
            'nota',
            'aprobado',
            'fecha',
        )
        read_only_fields = ('fecha',)
        extra_kwargs = {
            # La nota sale como número (6.6) y no como texto ("6.6"),
            # igual que la usa el frontend.
            'nota': {'coerce_to_string': False},
            # Un profesor existe, pero no puede tener intentos: el mensaje
            # por defecto ("objeto no existe") confundiría.
            'estudiante': {
                'error_messages': {
                    'does_not_exist': 'No existe un estudiante con id {pk_value}.',
                },
            },
        }


class ReflexionSerializer(serializers.ModelSerializer):
    # El estudiante y el taller se reciben por su id; la respuesta agrega
    # el correo y el número para leerla sin buscar los ids.
    correo_estudiante = serializers.EmailField(source='estudiante.correo', read_only=True)
    numero_taller = serializers.IntegerField(source='taller.numero', read_only=True)

    class Meta:
        model = Reflexion
        fields = (
            'id',
            'estudiante',
            'correo_estudiante',
            'taller',
            'numero_taller',
            'contexto',
            'descripcion',
            'actores',
            'relevancia',
            'estado',
            'intentos_usados',
            'fecha_creacion',
            'fecha_actualizacion',
        )
        read_only_fields = ('fecha_creacion', 'fecha_actualizacion')
        extra_kwargs = {
            # Igual que en los intentos: un profesor existe, pero no puede
            # tener reflexiones.
            'estudiante': {
                'error_messages': {
                    'does_not_exist': 'No existe un estudiante con id {pk_value}.',
                },
            },
            'taller': {
                'error_messages': {
                    'does_not_exist': 'No existe un taller con id {pk_value}.',
                },
            },
        }


class RetroalimentacionSerializer(serializers.ModelSerializer):
    correo_estudiante = serializers.EmailField(
        source='reflexion.estudiante.correo',
        read_only=True,
    )
    numero_taller = serializers.IntegerField(
        source='reflexion.taller.numero',
        read_only=True,
    )

    class Meta:
        model = Retroalimentacion
        fields = (
            'id',
            'reflexion',
            'correo_estudiante',
            'numero_taller',
            'propuesta_ia',
            'comentario_docente',
            'estado',
        )
        extra_kwargs = {
            'reflexion': {
                'error_messages': {
                    'does_not_exist': 'No existe una reflexión con id {pk_value}.',
                },
            },
        }


class EvaluacionSerializer(serializers.ModelSerializer):
    correo_estudiante = serializers.EmailField(source='estudiante.correo', read_only=True)
    numero_taller = serializers.IntegerField(source='taller.numero', read_only=True)

    class Meta:
        model = Evaluacion
        fields = (
            'id',
            'estudiante',
            'correo_estudiante',
            'taller',
            'numero_taller',
            'nota',
            'resultado',
            'fecha',
        )
        read_only_fields = ('fecha',)
        extra_kwargs = {
            'estudiante': {
                'error_messages': {
                    'does_not_exist': 'No existe un estudiante con id {pk_value}.',
                },
            },
            'taller': {
                'error_messages': {
                    'does_not_exist': 'No existe un taller con id {pk_value}.',
                },
            },
            'nota': {'coerce_to_string': False},
        }


class EtiquetasField(serializers.Field):
    """
    Las etiquetas se guardan separadas por coma, pero la API las entrega
    y las recibe como lista, igual que `tags` en el frontend.
    """

    def to_representation(self, value):
        return [etiqueta.strip() for etiqueta in value.split(',') if etiqueta.strip()]

    def to_internal_value(self, data):
        if not isinstance(data, list) or not all(isinstance(etiqueta, str) for etiqueta in data):
            raise serializers.ValidationError('Debe ser una lista de textos.')
        if any(',' in etiqueta for etiqueta in data):
            raise serializers.ValidationError('Una etiqueta no puede contener comas.')
        texto = ', '.join(etiqueta.strip() for etiqueta in data if etiqueta.strip())
        if len(texto) > Innovacion._meta.get_field('etiquetas').max_length:
            raise serializers.ValidationError('Las etiquetas superan el largo permitido.')
        return texto


class PasoInnovacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PasoInnovacion
        fields = ('id', 'orden', 'texto')


class InnovacionSerializer(serializers.ModelSerializer):
    # Los pasos van dentro del mismo JSON. Son de solo lectura: por ahora
    # se cargan desde el admin, igual que las alternativas.
    pasos = PasoInnovacionSerializer(many=True, read_only=True)
    etiquetas = EtiquetasField(required=False)
    # default=None: el caso puede no tener autor (SET_NULL).
    correo_autor = serializers.EmailField(source='autor.correo', read_only=True, default=None)

    class Meta:
        model = Innovacion
        fields = (
            'id',
            'titulo',
            'categoria',
            'resumen',
            'contexto',
            'desafio',
            'actuacion',
            'pasos',
            'impacto_esperado',
            'etiquetas',
            'autor',
            'correo_autor',
            'publicada',
            'fecha_creacion',
            'fecha_actualizacion',
        )
        read_only_fields = ('fecha_creacion', 'fecha_actualizacion')
        extra_kwargs = {
            # Un estudiante existe, pero no puede ser autor de un caso.
            'autor': {
                'error_messages': {
                    'does_not_exist': 'No existe un profesor guía o administrador con id {pk_value}.',
                },
            },
        }
