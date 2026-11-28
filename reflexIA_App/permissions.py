"""
Autorización del backend: whitelist activa y permisos por rol.

Replica en el servidor las mismas reglas que aplica el frontend
(`authService.signInUser` y la guarda de rutas `RequireAuth`):

1. El usuario debe haber iniciado sesión (autenticación).
2. Su correo debe estar en la whitelist (`UsuarioAutorizado`) con estado
   `active` (RN-01). Si no está o fue revocado, se le niega el acceso.
3. Su rol (`student`, `teacher`, `admin`) debe estar entre los roles que
   la vista permite para esa acción (RN-02, matriz de permisos del documento
   03-actores-y-permisos del frontend).

El usuario inicia sesión con una cuenta de Django (token o sesión) cuyo
correo coincide con la whitelist. El frontend usa este mismo login
(POST /api/auth/token/); el proyecto no usa Firebase.
"""

from rest_framework.permissions import BasePermission

from .models import UsuarioAutorizado

# Acciones de un ModelViewSet agrupadas como se definen los permisos.
ACCIONES_LECTURA = {'list', 'retrieve'}
ACCIONES_CREACION = {'create'}
ACCIONES_EDICION = {'update', 'partial_update', 'destroy'}


def es_superusuario(request):
    """Los superusuarios de Django administran todo, igual que en /admin/."""
    return bool(request.user and request.user.is_authenticated and request.user.is_superuser)


def obtener_usuario_reflexia(request):
    """
    Devuelve el `UsuarioAutorizado` activo de quien hace la petición, o None.

    El correo se toma del campo email de la cuenta de Django; si está vacío,
    del nombre de usuario (así se puede crear la cuenta con el correo como
    nombre de usuario). El resultado se guarda en la petición para no
    repetir la consulta.
    """
    if hasattr(request, '_usuario_reflexia'):
        return request._usuario_reflexia

    usuario = None
    if request.user and request.user.is_authenticated:
        correo = (request.user.email or request.user.username or '').strip().lower()
        if correo:
            usuario = UsuarioAutorizado.objects.filter(
                correo=correo,
                estado='active',
            ).first()

    request._usuario_reflexia = usuario
    return usuario


class EstaEnWhitelist(BasePermission):
    """Exige sesión iniciada y correo activo en la whitelist (RN-01)."""

    message = 'Tu correo no está autorizado en ReflexIA o su acceso fue revocado.'

    def has_permission(self, request, view):
        if es_superusuario(request):
            return True
        return obtener_usuario_reflexia(request) is not None


class PermisoPorRol(BasePermission):
    """
    Permite cada acción solo a los roles que declara la vista (RN-02).

    Cada ViewSet define tres conjuntos de roles:

    - `roles_lectura`: listar y ver el detalle (GET).
    - `roles_creacion`: crear (POST).
    - `roles_edicion`: modificar y eliminar (PUT, PATCH, DELETE).

    Una acción que la vista no declara queda prohibida: si se agrega un
    endpoint y se olvidan sus roles, nadie lo puede usar por error.
    """

    message = 'Tu rol no tiene permiso para realizar esta acción.'

    def has_permission(self, request, view):
        if es_superusuario(request):
            return True

        usuario = obtener_usuario_reflexia(request)
        if usuario is None:
            return False

        accion = getattr(view, 'action', None)
        if accion in ACCIONES_LECTURA:
            roles = getattr(view, 'roles_lectura', set())
        elif accion in ACCIONES_CREACION:
            roles = getattr(view, 'roles_creacion', set())
        elif accion in ACCIONES_EDICION:
            roles = getattr(view, 'roles_edicion', set())
        else:
            # Acciones que no son de un ViewSet (por ejemplo OPTIONS): solo lectura.
            roles = getattr(view, 'roles_lectura', set())
        return usuario.rol in roles
