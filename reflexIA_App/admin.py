from django.contrib import admin

from .models import UsuarioAutorizado


@admin.register(UsuarioAutorizado)
class UsuarioAutorizadoAdmin(admin.ModelAdmin):
    list_display = ('correo', 'nombre', 'rol', 'estado', 'fecha_registro')
    list_filter = ('rol', 'estado')
    search_fields = ('correo', 'nombre')
    readonly_fields = ('fecha_registro',)
