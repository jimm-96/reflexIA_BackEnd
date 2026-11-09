from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import (
    Alternativa,
    PreguntaTeorica,
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
