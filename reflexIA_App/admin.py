from django.contrib import admin

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


@admin.register(Reflexion)
class ReflexionAdmin(admin.ModelAdmin):
    list_display = ('estudiante', 'taller', 'estado', 'intentos_usados', 'fecha_actualizacion')
    list_filter = ('estado', 'taller')
    search_fields = ('estudiante__correo', 'estudiante__nombre')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')
    # Trae el estudiante y el taller de cada reflexión en la misma consulta.
    list_select_related = ('estudiante', 'taller')
    # Agrupa el formulario en secciones, igual que los pasos del frontend.
    fieldsets = (
        (None, {'fields': ('estudiante', 'taller', 'estado', 'intentos_usados')}),
        ('Análisis del incidente', {'fields': ('contexto', 'descripcion', 'actores', 'relevancia')}),
        ('Fechas', {'fields': ('fecha_creacion', 'fecha_actualizacion')}),
    )


@admin.register(Retroalimentacion)
class RetroalimentacionAdmin(admin.ModelAdmin):
    list_display = ('reflexion', 'estado')
    list_filter = ('estado',)
    search_fields = ('reflexion__estudiante__correo', 'reflexion__taller__titulo')
    list_select_related = ('reflexion', 'reflexion__estudiante', 'reflexion__taller')


@admin.register(Evaluacion)
class EvaluacionAdmin(admin.ModelAdmin):
    list_display = ('estudiante', 'taller', 'nota', 'resultado', 'fecha')
    list_filter = ('resultado', 'taller')
    search_fields = ('estudiante__correo', 'estudiante__nombre', 'taller__titulo')
    readonly_fields = ('fecha',)
    list_select_related = ('estudiante', 'taller')


class PasoInnovacionInline(admin.TabularInline):
    model = PasoInnovacion
    extra = 3


@admin.register(Innovacion)
class InnovacionAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'categoria', 'autor', 'publicada', 'fecha_actualizacion')
    list_filter = ('categoria', 'publicada')
    search_fields = ('titulo', 'resumen', 'etiquetas')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')
    list_select_related = ('autor',)
    # Los pasos se cargan en la misma pantalla, igual que las alternativas.
    inlines = [PasoInnovacionInline]
    fieldsets = (
        (None, {'fields': ('titulo', 'categoria', 'autor', 'publicada', 'etiquetas')}),
        ('Caso pedagógico', {'fields': ('resumen', 'contexto', 'desafio', 'actuacion', 'impacto_esperado')}),
        ('Fechas', {'fields': ('fecha_creacion', 'fecha_actualizacion')}),
    )
