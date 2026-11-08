# Plan incremental

El backend se construye por etapas. Cada etapa agrega **un recurso** de ReflexIA siguiendo el mismo patrón del Laboratorio 6, y cada paso del patrón es un commit:

1. `models.py`: el modelo y su migración (`makemigrations` + `migrate`).
2. `admin.py`: registro en el panel de administración y prueba cargando datos desde `/admin/`.
3. `serializers.py`: `ModelSerializer` del modelo.
4. `views.py`: `ModelViewSet` del modelo.
5. `urls.py`: registro en el `DefaultRouter` y prueba en la interfaz navegable de DRF (`/api/...`).

Al terminar cada etapa, `python manage.py check` no debe mostrar errores.

Estados: ✅ hecha · ⏳ pendiente.

## Flujo de ramas

Solo la etapa 0 (configuración inicial) se hizo directamente en `main`. Desde la etapa 1, cada etapa se trabaja en su propia rama y se integra a `main` con un Pull Request, como en el Laboratorio 6:

```bash
git switch main
git pull
git switch -c feature/recurso-<nombre>
# ... commits de la etapa ...
git push -u origin feature/recurso-<nombre>
```

Luego se abre el Pull Request hacia `main` en GitHub. Después del merge se vuelve a `main` con `git switch main` y `git pull`, y recién ahí se crea la rama de la etapa siguiente. Así cada etapa parte con la anterior ya integrada.

| Etapa | Rama |
|---|---|
| 0 | `main` (directo) |
| 1 | `feature/recurso-usuarios` |
| 2 | `feature/recurso-talleres` |
| 3 | `feature/recurso-preguntas` |
| 4 | `feature/recurso-intentos-cuestionario` |
| 5 | `feature/recurso-reflexiones` |
| 6 | `feature/recurso-retroalimentaciones` |
| 7 | `feature/recurso-evaluaciones` |
| 8 | `feature/recurso-innovaciones` |
| 9 | `feature/config-mysql` |

## Etapa 0: estructura inicial ✅

Entorno virtual, proyecto `reflexIA_Proyect`, aplicación `reflexIA_App`, configuración y documentación.

| # | Archivos | Mensaje sugerido |
|---|---|---|
| 1 | `.gitignore`, `requirements.txt` | `chore: agrega gitignore y dependencias (Django 6.1 y DRF)` |
| 2 | `manage.py`, `reflexIA_Proyect/`, `reflexIA_App/` | `feat: crea proyecto reflexIA_Proyect y app reflexIA_App` |
| 3 | `README.md`, `docs/` | `docs: documenta instalación y plan incremental` |

## Etapa 1: usuarios autorizados (HU-01) ✅

Rama: `feature/recurso-usuarios`.

Modelo `UsuarioAutorizado`: la whitelist de correos que pueden ingresar a ReflexIA. Equivale a `WhitelistEntry` del frontend (`src/models/whitelist.ts`).

| Campo | Tipo | Detalle |
|---|---|---|
| `correo` | `EmailField` | Único. Solo `@ucen.cl` (RN-01). Se guarda en minúsculas. |
| `nombre` | `CharField` | Opcional. |
| `rol` | `CharField` con `choices` | `student` (Estudiante), `teacher` (Profesor guía), `admin` (Administrador). Por defecto `student`. |
| `estado` | `CharField` con `choices` | `active` (Activo), `revoked` (Revocado). Por defecto `active`. |
| `fecha_registro` | `DateTimeField` | Se llena sola al crear; solo lectura. |
| `fecha_revocacion` | `DateTimeField` | Opcional; vacía mientras el usuario esté activo. |

Decisiones:

- Los valores guardados de `rol` y `estado` son los mismos del frontend (`student`, `active`…), para que la integración no necesite traducirlos. El panel de administración y los mensajes muestran las etiquetas en español.
- La validación del dominio `@ucen.cl` se adelantó a esta etapa porque es parte del modelo: la aplican tanto el admin como la API.
- Los duplicados se detectan sin importar mayúsculas (`ANA@ucen.cl` = `ana@ucen.cl`): en el admin con `clean()` del modelo y en la API con un `UniqueValidator(lookup='iexact')` en el serializer.

| # | Archivos | Mensaje sugerido |
|---|---|---|
| 1 | `reflexIA_App/models.py`, `reflexIA_App/migrations/0001_initial.py` | `feat: agrega modelo UsuarioAutorizado con validación de dominio @ucen.cl` |
| 2 | `reflexIA_App/admin.py` | `feat: registra UsuarioAutorizado en el admin con filtros y búsqueda` |
| 3 | `reflexIA_App/serializers.py` | `feat: agrega UsuarioAutorizadoSerializer` |
| 4 | `reflexIA_App/views.py` | `feat: agrega UsuarioAutorizadoViewSet` |
| 5 | `reflexIA_App/urls.py` | `feat: expone /api/usuarios/ en el router` |
| 6 | `README.md`, `docs/plan-incremental.md` | `docs: documenta etapa 1 (usuarios autorizados)` |

Cómo probarla:

1. `python manage.py migrate` y `python manage.py createsuperuser`.
2. En `/admin/` → **Usuarios autorizados**: crear un correo `@ucen.cl` y comprobar que uno `@gmail.com` se rechaza.
3. En `/api/usuarios/`: listar, crear (POST), y en `/api/usuarios/<id>/` editar (PUT/PATCH) y eliminar (DELETE).

## Recursos previstos

Cada recurso sale de un modelo del frontend (`reflexIA/src/models/`). Los nombres y campos son una propuesta; se confirman al empezar cada etapa.

| Etapa | Modelo | HU | Campos principales | Ruta |
|---|---|---|---|---|
| 1 ✅ | `UsuarioAutorizado` | HU-01 Whitelist | `correo` (`@ucen.cl`, único), `nombre`, `rol`, `estado`, `fecha_registro`, `fecha_revocacion` | `/api/usuarios/` |
| 2 | `Taller` | HU-03, HU-06, HU-09 | `numero`, `titulo`, `objetivo`, `actividad`, `producto`, `fecha_limite`, `intentos_maximos` (3 por defecto) | `/api/talleres/` |
| 3 | `PreguntaTeorica` y `Alternativa` | HU-04 Marco teórico | Pregunta: `enunciado`, `activa`. Alternativa: `pregunta` (FK), `texto`, `es_correcta` | `/api/preguntas/` |
| 4 | `IntentoCuestionario` | HU-04 | `estudiante` (FK), `respuestas_correctas`, `nota`, `aprobado`, `fecha` | `/api/intentos-cuestionario/` |
| 5 | `Reflexion` | HU-03 Incidentes críticos | `estudiante` (FK), `taller` (FK), `contexto`, `descripcion`, `actores`, `relevancia`, `estado` (borrador, enviada, revisada), `intentos_usados` | `/api/reflexiones/` |
| 6 | `Retroalimentacion` | HU-02 El Impulso | `reflexion` (FK), `propuesta_ia`, `comentario_docente`, `estado` (pendiente, editada, validada) | `/api/retroalimentaciones/` |
| 7 | `Evaluacion` | HU-02, panel docente | `estudiante` (FK), `taller` (FK), `nota` (1,0 a 7,0), `resultado` (aprobado, reprobado), `fecha` | `/api/evaluaciones/` |
| 8 | `Innovacion` | HU-07 Biblioteca | `titulo`, `categoria`, `descripcion`, `autor` (FK), `publicada` | `/api/innovaciones/` |

El orden importa: los modelos con llaves foráneas (FK) van después de los modelos a los que apuntan.

## Etapas posteriores ⏳

| Etapa | Contenido |
|---|---|
| 9 | Cambio de SQLite a **MySQL** (`mysqlclient`, credenciales en `.env`). |
| 10 | Preparación para integrar con el frontend React: CORS (`django-cors-headers`) y autenticación. |
| 11 | Reglas de negocio en el servidor: aprobación 8/10 del cuestionario, 3 intentos por taller, nota 7,0 para avanzar. (El dominio `@ucen.cl` ya se valida desde la etapa 1.) |
