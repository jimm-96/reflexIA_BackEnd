from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import UsuarioAutorizado, validar_correo_institucional


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
