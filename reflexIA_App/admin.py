from django.contrib import admin

from .models import Taller, UsuarioAutorizado


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
