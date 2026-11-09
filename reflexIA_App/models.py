from django.core.exceptions import ValidationError
from django.db import models

# Único dominio institucional permitido (RN-01, DEC-03).
DOMINIO_INSTITUCIONAL = '@ucen.cl'


def validar_correo_institucional(correo):
    """Rechaza cualquier correo que no termine en @ucen.cl."""
    if not correo.lower().endswith(DOMINIO_INSTITUCIONAL):
        raise ValidationError(
            f'Solo se permiten correos institucionales {DOMINIO_INSTITUCIONAL}.'
        )


class UsuarioAutorizado(models.Model):
    """
    Correo autorizado para ingresar a ReflexIA (HU-01, whitelist).

    Equivale a `WhitelistEntry` del frontend (src/models/whitelist.ts).
    Los valores guardados de `rol` y `estado` son los mismos del frontend
    para facilitar la integración; las etiquetas se muestran en español.
    """

    ROL_CHOICES = [
        ('student', 'Estudiante'),
        ('teacher', 'Profesor guía'),
        ('admin', 'Administrador'),
    ]

    ESTADO_CHOICES = [
        ('active', 'Activo'),
        ('revoked', 'Revocado'),
    ]

    correo = models.EmailField(
        unique=True,
        validators=[validar_correo_institucional],
    )
    nombre = models.CharField(max_length=150, blank=True)
    rol = models.CharField(max_length=10, choices=ROL_CHOICES, default='student')
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='active')
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_revocacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'usuario autorizado'
        verbose_name_plural = 'usuarios autorizados'
        ordering = ['correo']

    def clean(self):
        # El admin llama a clean() antes de revisar duplicados: así
        # "ANA@ucen.cl" se detecta como repetido de "ana@ucen.cl".
        self.correo = self.correo.strip().lower()

    def save(self, *args, **kwargs):
        # El correo se guarda siempre en minúsculas, igual que en el frontend.
        self.correo = self.correo.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.correo} ({self.get_rol_display()})'
