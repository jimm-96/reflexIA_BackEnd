# Respuestas de error

Ajuste posterior a la etapa 9 del [plan incremental](./plan-incremental.md). Rama: `errores-uniformes`.

## Por qué

DRF respondía los errores con formas distintas y con mensajes por defecto que a veces eran técnicos o estaban en inglés:

| Situación | Antes |
|---|---|
| Campo con error | `{"nota": ["Asegúrese de que no haya más de 1 dígitos en la parte entera."]}` |
| Registro inexistente | `{"detail": "No Taller matches the given query."}` |
| JSON mal escrito | `{"detail": "JSON parse error - Expecting property name enclosed in double quotes: line 1 column 14 (char 13)"}` |
| Combinación repetida | `{"non_field_errors": ["Este estudiante ya tiene una reflexión en este taller."]}` |
| Id de otro tipo | `{"estudiante": ["Tipo incorrecto. Se esperaba valor de clave primaria y se recibió str."]}` |
| Ruta inexistente | Página HTML de Django |

Además mezclaban "usted" (`Asegúrese`, `Introduzca`) con el "tú" de los mensajes propios del proyecto (`Tu correo…`), y un correo mal escrito recibía dos mensajes a la vez (formato y dominio).

## Formato

Todas las respuestas de error de `/api/` tienen la misma forma. El código de estado HTTP no cambia.

```json
{
  "error": "validacion",
  "mensaje": "Revisa los datos enviados: hay campos con errores.",
  "campos": {
    "nota": ["Debe ser un número entre 1.0 y 7.0, con un decimal como máximo."],
    "rol": ["\"jefe\" no es una opción válida. Usa una de estas: student, teacher, admin."]
  }
}
```

| Clave | Contenido |
|---|---|
| `error` | Código corto y estable, para que el frontend decida qué hacer sin leer el texto. |
| `mensaje` | Texto general, listo para mostrar al usuario. |
| `campos` | Errores de cada campo: `{"campo": ["mensaje", …]}`. Vacío (`{}`) si el error no es de un campo. |

### Códigos

| HTTP | `error` | Cuándo | Ejemplo de `mensaje` |
|---|---|---|---|
| 400 | `validacion` | Algún campo no es válido, o falla una regla entre campos. | "Revisa los datos enviados: hay campos con errores." |
| 400 | `json_invalido` | El cuerpo no es un JSON válido. | "El cuerpo de la petición no es un JSON válido. Revisa las comillas, comas y llaves." |
| 401 | `no_autenticado` | La petición no trae token ni sesión. | "Debes iniciar sesión para usar la API: envía el encabezado "Authorization: Token <token>"." |
| 401 | `credenciales_invalidas` | El token no existe o la cuenta está desactivada. | "El token no es válido o la cuenta está desactivada. Vuelve a iniciar sesión." |
| 403 | `sin_permiso` | Correo fuera de la whitelist, rol sin permiso o registro ajeno. | "Tu rol no tiene permiso para realizar esta acción." |
| 404 | `no_encontrado` | El registro o la ruta no existen. | "No existe un registro con id 999 en talleres." |
| 405 | `metodo_no_permitido` | El método no se acepta en esa ruta. | "El método DELETE no está permitido en esta ruta. Métodos permitidos: GET, POST, HEAD, OPTIONS." |
| 415 | `tipo_no_soportado` | El cuerpo no viene como JSON ni como formulario. | "El formato "text/plain" no es compatible. Envía los datos como JSON (Content-Type: application/json)." |
| 500 | `error_servidor` | Error no previsto (solo con `DEBUG=False`). | "Ocurrió un error inesperado en el servidor. Intenta de nuevo más tarde." |

## Mensajes de los campos

El manejador reemplaza **solo los mensajes por defecto de DRF** y usa los datos del campo para que el mensaje diga qué valor se espera:

| Error | Ahora |
|---|---|
| Campo faltante | "Este campo es obligatorio." |
| Texto vacío | "Este campo no puede quedar vacío." |
| Opción no válida | `"jefe" no es una opción válida. Usa una de estas: student, teacher, admin.` |
| Texto muy largo | "Puede tener como máximo 150 caracteres." |
| Número fuera de rango | "Debe ser menor o igual a 3." |
| Nota mal escrita (`70`, `6.66`, `"siete"`) | "Debe ser un número entre 1.0 y 7.0, con un decimal como máximo." |
| Entero, booleano o fecha mal escritos | "Debe ser un número entero." · "Debe ser true o false." · "Debe ser una fecha real con formato AAAA-MM-DD (por ejemplo, 2026-12-04)." |
| Llave foránea inexistente | "No existe un registro con id 999." |
| Llave foránea de otro tipo (`"abc"`) | "Debe ser el id (número) de un registro." |
| Login incorrecto (`/api/auth/token/`) | "Usuario o contraseña incorrectos." (en `mensaje`) |

Los **mensajes propios del proyecto se conservan** tal cual, por ejemplo:

- "No existe un estudiante con id 999." (`IntentoCuestionarioSerializer`)
- "Solo se permiten correos institucionales @ucen.cl."
- "Este correo ya está autorizado."
- "Este estudiante ya tiene una reflexión en este taller."
- "Tu rol no tiene permiso para realizar esta acción."

Los errores que no son de un campo (combinaciones únicas, login incorrecto) van en `mensaje`, y `campos` queda vacío.

## Decisiones

- **Un solo manejador** (`reflexIA_App/exceptions.py`, configurado en `REST_FRAMEWORK['EXCEPTION_HANDLER']`). Así ningún ViewSet tiene que formatear sus errores, y los recursos nuevos quedan cubiertos solos.
- **Cómo se distingue un mensaje por defecto de uno propio:** cada error de DRF trae un código (`required`, `invalid_choice`, `max_digits`…). El manejador compara el texto con la plantilla por defecto de DRF para ese código. Si coincide, lo reemplaza; si no, es un mensaje propio y lo deja.
- **El dominio del correo se valida en `validate_correo`** del serializer y no en `validators`: DRF llama a ese método solo si el formato ya es válido, así un correo mal escrito recibe un único mensaje. El modelo mantiene su validador para el admin.
- **Rutas inexistentes:** `RutaNoEncontradaView` responde `404` en JSON a cualquier ruta de `/api/` que termine en `/`. Las rutas sin `/` final siguen redirigiendo (`/api/talleres` → `/api/talleres/`).
- **Errores 500:** con `DEBUG=True` se mantiene la página de Django con el detalle, que sirve para programar. Con `DEBUG=False` se responde en JSON sin detalles internos y el error se registra en el log.
- **El código HTTP no cambia:** el frontend puede seguir usando el estado (`401`, `403`, `404`) y, además, el código `error`.

## Cómo probarlo

1. `python manage.py runserver` e iniciar sesión como superusuario en la API navegable.
2. En `/api/talleres/`, enviar `{"numero": "uno", "titulo": ""}` y revisar `campos`.
3. En `/api/evaluaciones/`, enviar una nota `70` o `6.66`: el mensaje explica el rango.
4. Abrir `/api/talleres/999/` y `/api/no-existe/`: ambas responden `404` en JSON.
5. `python manage.py test`: deben pasar las 81 pruebas (20 de ellas en `tests_errores.py`).

## Archivos y commits

| # | Archivos | Mensaje sugerido |
|---|---|---|
| 1 | `reflexIA_App/exceptions.py` | `feat: agrega manejador de errores con formato uniforme y mensajes en español` |
| 2 | `reflexIA_App/serializers.py` | `fix: evita el doble mensaje de error en correos mal escritos` |
| 3 | `reflexIA_App/views.py` | `feat: agrega respuesta JSON para rutas inexistentes y opciones válidas en los filtros` |
| 4 | `reflexIA_Proyect/settings.py`, `reflexIA_App/tests.py`, `reflexIA_App/tests_permisos.py` | `feat: activa el formato uniforme de errores en toda la API` |
| 5 | `reflexIA_App/urls.py` | `feat: responde 404 en JSON a las rutas inexistentes de /api/` |
| 6 | `reflexIA_App/tests_errores.py` | `test: agrega pruebas del formato uniforme de errores` |
| 7 | `docs/errores.md`, `docs/README.md`, `docs/autenticacion-y-permisos.md`, `docs/plan-incremental.md`, `README.md` | `docs: documenta el formato uniforme de errores` |

Cada commit deja las pruebas en verde. El commit 4 incluye `tests.py` y `tests_permisos.py` porque al activar el formato cambian las 3 pruebas que leían la forma anterior (`non_field_errors`, `detail` y los campos en la raíz).

## Pendiente

- **Integración:** el cliente del frontend (`apiClient.ts`, tarea F-1 de [integracion-y-despliegue.md](./integracion-y-despliegue.md)) ya convierte `error`, `mensaje` y `campos` en un `ApiError`. Falta que cada formulario muestre los mensajes de `campos` junto a su campo.
