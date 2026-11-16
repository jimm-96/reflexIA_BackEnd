"""
Respuestas de error uniformes para toda la API.

DRF entrega cada error con una forma distinta ({"campo": [...]},
{"detail": "..."}, {"non_field_errors": [...]}) y con mensajes por defecto
que a veces son técnicos o están en inglés. Este manejador (configurado en
REST_FRAMEWORK['EXCEPTION_HANDLER']) los convierte todos a la misma forma:

    {
        "error": "validacion",                 # código corto y estable
        "mensaje": "Revisa los datos enviados: hay campos con errores.",
        "campos": {"nota": ["Debe ser un número entre 1.0 y 7.0, con un decimal como máximo."]}
    }

- `error`: código para que el frontend decida qué hacer (igual que los
  códigos de `StudentAuthError` del frontend).
- `mensaje`: texto general, listo para mostrar.
- `campos`: errores de cada campo (vacío si el error no es de un campo).

El código de estado HTTP (400, 401, 403, 404…) no cambia.

Los mensajes **por defecto** de DRF se reemplazan por mensajes en español,
en "tú" y con los datos del campo (rango, opciones válidas, largo máximo).
Los mensajes propios del proyecto (por ejemplo, "No existe un estudiante con
id 999.") se dejan tal cual.
"""

import logging
import re

from django.conf import settings
from django.core.exceptions import PermissionDenied as PermisoDenegadoDjango
from django.http import Http404
from rest_framework import exceptions, serializers
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)

# Código corto de cada tipo de error. El orden importa: se usa el primero
# que coincide.
CODIGOS_DE_ERROR = [
    (exceptions.ValidationError, 'validacion'),
    (exceptions.ParseError, 'json_invalido'),
    (exceptions.NotAuthenticated, 'no_autenticado'),
    (exceptions.AuthenticationFailed, 'credenciales_invalidas'),
    (exceptions.PermissionDenied, 'sin_permiso'),
    (exceptions.NotFound, 'no_encontrado'),
    (exceptions.MethodNotAllowed, 'metodo_no_permitido'),
    (exceptions.NotAcceptable, 'formato_no_aceptado'),
    (exceptions.UnsupportedMediaType, 'tipo_no_soportado'),
    (exceptions.Throttled, 'demasiadas_peticiones'),
]

MENSAJE_VALIDACION = 'Revisa los datos enviados: hay campos con errores.'
MENSAJE_ERROR_SERVIDOR = 'Ocurrió un error inesperado en el servidor. Intenta de nuevo más tarde.'


def cuerpo_error(codigo, mensaje, campos=None):
    return {'error': codigo, 'mensaje': mensaje, 'campos': campos or {}}


def manejar_errores(exc, context):
    """Manejador de errores de la API (REST_FRAMEWORK['EXCEPTION_HANDLER'])."""
    # Django lanza Http404 (get_object_or_404) y PermissionDenied propios;
    # se convierten a los de DRF para darles el mismo formato.
    if isinstance(exc, Http404):
        exc = exceptions.NotFound(mensaje_no_encontrado(context))
    elif isinstance(exc, PermisoDenegadoDjango):
        exc = exceptions.PermissionDenied()

    # El manejador de DRF arma la respuesta con el código de estado y los
    # encabezados correctos (WWW-Authenticate, Allow); aquí solo se cambia
    # su contenido.
    response = exception_handler(exc, context)

    if response is None:
        # Error no previsto (500). En desarrollo se deja la página de Django
        # con el detalle del error; en producción se responde en JSON sin
        # mostrar detalles internos y se registra en el log.
        if settings.DEBUG:
            return None
        logger.exception('Error no controlado en la API', exc_info=exc)
        return Response(cuerpo_error('error_servidor', MENSAJE_ERROR_SERVIDOR), status=500)

    codigo = next((c for clase, c in CODIGOS_DE_ERROR if isinstance(exc, clase)), 'error')
    if isinstance(exc, exceptions.ValidationError):
        mensaje, campos = traducir_validacion(exc.detail, context)
    else:
        mensaje, campos = mensaje_general(exc, context), {}

    response.data = cuerpo_error(codigo, mensaje, campos)
    return response


# ─────────────────────────────────────────────
# Errores que no son de validación
# ─────────────────────────────────────────────


def mensaje_no_encontrado(context):
    """'No existe un registro con id 999 en talleres.'"""
    vista = context.get('view')
    queryset = getattr(vista, 'queryset', None)
    pk = context.get('kwargs', {}).get('pk')
    if queryset is not None and pk is not None:
        return f'No existe un registro con id {pk} en {queryset.model._meta.verbose_name_plural}.'
    return 'No se encontró lo que buscas.'


def mensaje_general(exc, context):
    request = context.get('request')
    detalle = str(exc.detail)

    if isinstance(exc, exceptions.ParseError):
        return 'El cuerpo de la petición no es un JSON válido. Revisa las comillas, comas y llaves.'
    if isinstance(exc, exceptions.NotAuthenticated):
        return 'Debes iniciar sesión para usar la API: envía el encabezado "Authorization: Token <token>".'
    if isinstance(exc, exceptions.AuthenticationFailed):
        return 'El token no es válido o la cuenta está desactivada. Vuelve a iniciar sesión.'
    if isinstance(exc, exceptions.PermissionDenied):
        if detalle == str(exceptions.PermissionDenied.default_detail):
            return 'No tienes permiso para realizar esta acción.'
        return detalle  # Mensajes propios de permissions.py y views.py.
    if isinstance(exc, exceptions.NotFound):
        if detalle == str(exceptions.NotFound.default_detail):
            return 'No se encontró lo que buscas.'
        return detalle
    if isinstance(exc, exceptions.MethodNotAllowed):
        # El encabezado Allow lo agrega DRF después; se leen de la vista.
        vista = context.get('view')
        permitidos = ', '.join(getattr(vista, 'allowed_methods', []))
        return f'El método {request.method} no está permitido en esta ruta. Métodos permitidos: {permitidos}.'
    if isinstance(exc, exceptions.UnsupportedMediaType):
        return f'El formato "{request.content_type}" no es compatible. Envía los datos como JSON (Content-Type: application/json).'
    if isinstance(exc, exceptions.NotAcceptable):
        return 'No se puede responder en el formato pedido. Usa "Accept: application/json".'
    return detalle


# ─────────────────────────────────────────────
# Errores de validación (400)
# ─────────────────────────────────────────────


def traducir_validacion(detalle, context):
    """Separa los errores generales (mensaje) de los errores por campo (campos)."""
    if isinstance(detalle, list):
        generales = [traducir_error_general(error) for error in detalle]
        return ' '.join(generales) or MENSAJE_VALIDACION, {}

    generales = []
    campos = {}
    for nombre, errores in detalle.items():
        lista = errores if isinstance(errores, list) else [errores]

        if nombre == api_settings.NON_FIELD_ERRORS_KEY:
            generales.extend(traducir_error_general(error) for error in lista)
            continue

        campo = buscar_campo(context, nombre)
        textos = []
        for error in lista:
            # Los errores anidados (dict o list) se dejan con su estructura.
            texto = traducir_error_de_campo(error, campo, nombre, context) if isinstance(error, str) else error
            if texto not in textos:
                textos.append(texto)
        campos[nombre] = textos

    return ' '.join(generales) or MENSAJE_VALIDACION, campos


def traducir_error_general(error):
    """Errores que no son de un campo (por ejemplo, combinaciones únicas)."""
    codigo = getattr(error, 'code', None)
    if codigo == 'authorization':
        # POST /api/auth/token/ con usuario o contraseña incorrectos.
        return 'Usuario o contraseña incorrectos.'
    if codigo == 'invalid' and _coincide_con_plantilla(str(error), serializers.Serializer.default_error_messages['invalid']):
        return 'El cuerpo de la petición debe ser un objeto JSON con los campos del recurso.'
    return str(error)


def buscar_campo(context, nombre):
    """Campo del serializer de la vista, para conocer su tipo y sus límites."""
    vista = context.get('view')
    if not hasattr(vista, 'get_serializer'):
        return None
    try:
        return vista.get_serializer().fields.get(nombre)
    except Exception:  # Una vista sin serializer no debe romper el manejo del error.
        return None


def valor_enviado(context, nombre):
    datos = getattr(context.get('request'), 'data', None)
    return datos.get(nombre) if isinstance(datos, dict) else None


def traducir_error_de_campo(error, campo, nombre, context):
    codigo = getattr(error, 'code', None)
    texto = str(error)
    if campo is None or not es_mensaje_por_defecto(texto, campo, codigo):
        return texto

    valor = valor_enviado(context, nombre)

    if codigo == 'required':
        return 'Este campo es obligatorio.'
    if codigo == 'null':
        return 'Este campo no puede ser nulo.'
    if codigo == 'blank':
        return 'Este campo no puede quedar vacío.'
    if codigo == 'max_length':
        return f'Puede tener como máximo {campo.max_length} caracteres.'
    if codigo == 'min_length':
        return f'Debe tener al menos {campo.min_length} caracteres.'
    if codigo == 'invalid_choice' and valor is not None:
        opciones = ', '.join(str(opcion) for opcion in campo.choices)
        return f'"{valor}" no es una opción válida. Usa una de estas: {opciones}.'
    if codigo == 'max_value':
        return f'Debe ser menor o igual a {campo.max_value}.'
    if codigo == 'min_value':
        return f'Debe ser mayor o igual a {campo.min_value}.'
    if codigo in ('max_digits', 'max_whole_digits', 'max_decimal_places'):
        return mensaje_decimal(campo)
    if codigo == 'does_not_exist':
        return f'No existe un registro con id {valor}.'
    if codigo == 'incorrect_type':
        return 'Debe ser el id (número) de un registro.'
    if codigo in ('invalid', 'date', 'datetime'):
        return mensaje_formato_invalido(campo, texto)
    return texto


def mensaje_decimal(campo):
    """'Debe ser un número entre 1.0 y 7.0, con un decimal como máximo.'"""
    if campo.min_value is not None and campo.max_value is not None:
        rango = f'Debe ser un número entre {campo.min_value} y {campo.max_value}'
    else:
        rango = 'Debe ser un número'
    decimales = 'un decimal' if campo.decimal_places == 1 else f'{campo.decimal_places} decimales'
    return f'{rango}, con {decimales} como máximo.'


def mensaje_formato_invalido(campo, texto):
    if isinstance(campo, serializers.BooleanField):
        return 'Debe ser true o false.'
    if isinstance(campo, serializers.IntegerField):
        return 'Debe ser un número entero.'
    if isinstance(campo, serializers.DecimalField):
        return mensaje_decimal(campo)
    if isinstance(campo, serializers.FloatField):
        return 'Debe ser un número.'
    if isinstance(campo, serializers.DateTimeField):
        return 'Debe ser una fecha y hora con formato AAAA-MM-DDThh:mm (por ejemplo, 2026-12-04T18:30).'
    if isinstance(campo, serializers.DateField):
        return 'Debe ser una fecha real con formato AAAA-MM-DD (por ejemplo, 2026-12-04).'
    if isinstance(campo, serializers.EmailField):
        return 'Debe ser un correo electrónico válido.'
    return texto


def es_mensaje_por_defecto(texto, campo, codigo):
    """
    True si `texto` es el mensaje por defecto de DRF para ese código.

    Busca la plantilla en `default_error_messages` de la clase del campo y
    de sus clases padre. Si el campo tiene un mensaje propio (error_messages
    o un validador del proyecto), el texto no coincide y no se reemplaza.
    """
    for clase in type(campo).__mro__:
        plantilla = vars(clase).get('default_error_messages', {}).get(codigo)
        if plantilla is not None:
            return _coincide_con_plantilla(texto, plantilla)
    return False


def _coincide_con_plantilla(texto, plantilla):
    # "Asegúrese de que este valor es menor o igual a {max_value}." se
    # convierte en una expresión regular donde {max_value} acepta cualquier texto.
    patron = re.sub(r'\\\{\w+\\\}', '.+?', re.escape(str(plantilla)))
    return re.fullmatch(patron, texto) is not None
