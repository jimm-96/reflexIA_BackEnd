# Autenticación y permisos por rol

Etapa 9 del [plan incremental](./plan-incremental.md). Rama: `autenticacion-permisos` (PR #13).

## Por qué

Hasta la etapa 8, la API respondía a cualquiera, sin iniciar sesión. Las reglas de acceso existían solo en el frontend:

- `authService.signInUser`: correo `@ucen.cl`, contraseña correcta y correo **activo** en la whitelist.
- La guarda de rutas `RequireAuth`: cada rol entra solo a su área (`/admin`, `/docente`, `/estudiante`).

Una regla que vive solo en el navegador se puede saltar llamando a la API directamente. Desde esta etapa el backend aplica las mismas reglas por su cuenta.

## Cómo funciona

Cada petición pasa por tres controles, en orden:

| # | Control | Si falla | Dónde |
|---|---|---|---|
| 1 | **Autenticación**: la petición trae un token válido o una sesión iniciada. | `401 Unauthorized` | `REST_FRAMEWORK` en `settings.py` |
| 2 | **Whitelist**: el correo de la cuenta está en `UsuarioAutorizado` con estado `active` (RN-01). | `403` "Tu correo no está autorizado en ReflexIA o su acceso fue revocado." | `EstaEnWhitelist` en `permissions.py` |
| 3 | **Rol**: el rol de la whitelist puede hacer esa acción en ese recurso (RN-02). | `403` "Tu rol no tiene permiso para realizar esta acción." | `PermisoPorRol` en `permissions.py` y los roles de cada ViewSet en `views.py` |

Además, un estudiante solo ve y modifica **sus propios** registros (ver más abajo).

Los mensajes de error llegan en el campo `mensaje` del [formato uniforme de errores](./errores.md), con `error` = `no_autenticado` (401) o `sin_permiso` (403).

### Enlace entre la cuenta y la whitelist

El login lo hace una cuenta de usuario de Django (`django.contrib.auth`), y el rol sale de la whitelist. Se enlazan **por correo**: el `email` de la cuenta (o su nombre de usuario, si el email está vacío) debe coincidir con el `correo` de `UsuarioAutorizado`, sin importar mayúsculas.

Así la whitelist sigue siendo la única fuente del rol, igual que en el frontend. Revocar a alguien en la whitelist le corta el acceso a la API en la siguiente petición, aunque su token siga vigente.

### Superusuarios

Un superusuario de Django (`createsuperuser`) puede hacer todo, aunque su correo no esté en la whitelist, igual que en `/admin/`. Sirve para administrar el sistema y para las pruebas de datos (`tests.py`). No tiene rol de ReflexIA: `/api/auth/yo/` devuelve `"rol": null`.

## Matriz de permisos

Sigue la matriz del frontend (`reflexIA/docs/especificacion/03-actores-y-permisos.md`). **L** leer (GET) · **C** crear (POST) · **E** editar y eliminar (PUT, PATCH, DELETE) · — sin acceso.

| Recurso | Estudiante (`student`) | Profesor guía (`teacher`) | Administrador (`admin`) |
|---|---|---|---|
| `/api/usuarios/` (whitelist) | — | — | L C E |
| `/api/talleres/` | L | L C E | — |
| `/api/preguntas/` | L (solo activas, **sin** `es_correcta`) | L C E | — |
| `/api/intentos-cuestionario/` | L C (solo los suyos) | L | — |
| `/api/reflexiones/` | L C E (solo las suyas) | L | — |
| `/api/retroalimentaciones/` | L (solo las de sus reflexiones) | L C E | — |
| `/api/evaluaciones/` | L (solo las suyas) | L C E | — |
| `/api/innovaciones/` | L (solo publicadas) | L C E | — |
| `/api/auth/yo/` | L | L | L |

Decisiones de la matriz:

- **El administrador solo gestiona la whitelist**, como en el frontend (`/admin/whitelist`). Si además debe ver talleres o notas, se le agrega el rol en el ViewSet correspondiente.
- **Un intento de cuestionario no se modifica ni se elimina** una vez registrado: es el respaldo de la nota. Solo un superusuario puede corregirlo.
- **El profesor guía no escribe reflexiones**: las lee para revisarlas. La retroalimentación y la nota las registra en sus propios recursos.
- **Solo el profesor guía escribe notas oficiales** (`/api/evaluaciones/`), igual que en el frontend.

## Registros propios del estudiante

`RegistrosPropiosMixin` (en `views.py`) aplica dos reglas a intentos, reflexiones, retroalimentaciones y evaluaciones:

- **Al leer**, el estudiante recibe solo sus registros. Pedir el de otro estudiante por id responde `404`, como si no existiera, para no revelar que existe.
- **Al crear o modificar**, no puede asignar el registro a otro estudiante: `403` "Solo puedes registrar tus propios intentos." (o el mensaje del recurso).

## Respuesta correcta oculta

Un estudiante que lista `/api/preguntas/` recibe las alternativas **sin** el campo `es_correcta`: si lo recibiera, vería las respuestas del cuestionario antes de rendirlo. Para eso `PreguntaTeoricaViewSet` usa `PreguntaTeoricaEstudianteSerializer`. El profesor guía sigue viendo el campo para editar el banco de preguntas. Es la misma regla que el frontend aplica a sus talleres (`answerKeyPrivate`).

## Endpoints de autenticación

| Método | Ruta | Qué hace | Requiere sesión |
| :--- | :--- | :--- | :--- |
| POST | `/api/auth/token/` | Recibe `username` y `password` y devuelve un token. | No |
| GET | `/api/auth/yo/` | Devuelve correo, nombre y rol de quien hace la petición. Equivale a `restoreSession` del frontend (`authService.ts`). | Sí |
| — | `/api-auth/login/` | Login de sesión para la API navegable de DRF (botón "Log in"). | No |

Ejemplo:

```bash
# 1. Obtener el token
curl -X POST http://127.0.0.1:8000/api/auth/token/ \
     -H "Content-Type: application/json" \
     -d '{"username": "profesor@ucen.cl", "password": "una-clave-segura"}'
# → {"token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"}

# 2. Usarlo en cada petición
curl http://127.0.0.1:8000/api/auth/yo/ \
     -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
# → {"correo": "profesor@ucen.cl", "nombre": "", "rol": "teacher", "es_superusuario": false}
```

## Cómo probarlo

1. `python manage.py migrate` (crea la tabla de tokens de `rest_framework.authtoken`).
2. En `/admin/` → **Usuarios autorizados**: crear `estudiante@ucen.cl` (Estudiante) y `profesor@ucen.cl` (Profesor guía).
3. En `/admin/` → **Usuarios** (de Django): crear dos cuentas con **nombre de usuario** igual a esos correos y una contraseña. No necesitan ser staff.
4. Ir a `/api/talleres/` sin sesión: responde `401`.
5. Con **Log in** (arriba a la derecha de la API navegable), entrar como el estudiante:
   - `/api/auth/yo/` muestra `"rol": "student"`.
   - `/api/talleres/` lista los talleres, pero el formulario para crear responde `403`.
   - `/api/preguntas/` no muestra `es_correcta`.
   - `/api/usuarios/` responde `403`.
6. Entrar como el profesor y comprobar que sí puede crear un taller.
7. En `/admin/` → **Usuarios autorizados**, revocar al estudiante y comprobar que su sesión ya no puede leer `/api/talleres/` (`403`).
8. `python manage.py test`: al cerrar esta etapa pasaban las 61 pruebas (30 de ellas en `tests_permisos.py`).

## Archivos y commits

| # | Archivos | Mensaje sugerido |
|---|---|---|
| 1 | `reflexIA_App/tests.py` | `test: autentica como superusuario las pruebas existentes de la API` |
| 2 | `reflexIA_App/permissions.py` | `feat: agrega permisos por whitelist activa y rol` |
| 3 | `reflexIA_App/serializers.py` | `feat: agrega serializer de preguntas sin la respuesta correcta para estudiantes` |
| 4 | `reflexIA_App/views.py` | `feat: aplica permisos por rol y registros propios en los ViewSets` |
| 5 | `reflexIA_Proyect/settings.py`, `reflexIA_Proyect/urls.py`, `reflexIA_App/urls.py` | `feat: agrega login por token y sesión y el endpoint /api/auth/yo/` |
| 6 | `reflexIA_App/tests_permisos.py` | `test: agrega pruebas de autenticación y permisos por rol` |
| 7 | `docs/autenticacion-y-permisos.md`, `docs/README.md`, `README.md` | `docs: documenta autenticación y permisos por rol` |
| 8 | `docs/plan-incremental.md` | `docs: restaura el plan incremental perdido en el PR #12 y agrega la etapa 9` |

Cada commit deja las pruebas en verde. El commit 1 va primero porque, desde el commit 4, la API exige sesión: las pruebas existentes se autentican antes como superusuario, ya que revisan datos y no permisos.

## Pendiente

El proyecto dejó Firebase (27-11-2026): el frontend inicia sesión con este mismo login de Django. Lo pendiente está en [integracion-y-despliegue.md](./integracion-y-despliegue.md):

- **Cuentas y sesiones (tarea B-4):** crear la cuenta de Django al autorizar un correo, cerrar sesión en el servidor, vencimiento del token, límite de intentos de contraseña e `id` en `/api/auth/yo/`.
- **CORS (tarea B-3):** el frontend en `localhost:5173` necesita `django-cors-headers` para llamar a la API.
- **Lectura de estudiantes para el profesor guía (tarea B-8):** hoy `/api/usuarios/` es solo del administrador.
- **Permisos por campo (tarea B-I2):** hoy el estudiante puede editar cualquier campo de su reflexión, incluido `estado`. Que solo pueda pasarla de `draft` a `submitted`, y que el profesor la marque como revisada, son reglas de negocio de esa tarea, junto con que `intentos_usados` sea de solo lectura y que el estudiante no pueda eliminar su reflexión.
- **Auditoría (RN-04, GAP-08):** no se registra quién hizo cada cambio.
