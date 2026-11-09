from django.contrib import admin

from .models import (
    Alternativa,
    IntentoCuestionario,
    PreguntaTeorica,
    Taller,
    UsuarioAutorizado,
)


@admin.register(UsuarioAutorizado)
class UsuarioAutorizadoAdmin(admin.ModelAdmin):
    list_display = ('correo', 'nombre', 'rol', 'estado', 'fecha_registro')
    list_filter = ('rol', 'estado')
    search_fields = ('correo', 'nombre')
    readonly_fields = ('fecha_registro',)


@admin.register(Taller)
class TallerAdmin(admin.ModelAdmin):
    list_display = ('numero', 'titulo', 'fecha_limite', 'intentos_maximos')
    search_fields = ('titulo',)


class AlternativaInline(admin.TabularInline):
    model = Alternativa
    extra = 4


@admin.register(PreguntaTeorica)
class PreguntaTeoricaAdmin(admin.ModelAdmin):
    list_display = ('id', 'enunciado', 'activa')
    list_filter = ('activa',)
    search_fields = ('enunciado',)
    inlines = [AlternativaInline]


@admin.register(IntentoCuestionario)
class IntentoCuestionarioAdmin(admin.ModelAdmin):
    list_display = ('estudiante', 'respuestas_correctas', 'nota', 'aprobado', 'fecha')
    list_filter = ('aprobado',)
    search_fields = ('estudiante__correo', 'estudiante__nombre')
    readonly_fields = ('fecha',)
    # Trae el estudiante de cada intento en la misma consulta.
    list_select_related = ('estudiante',)
