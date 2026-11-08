# Plan incremental

El backend se construye por etapas. Cada etapa agrega **un recurso** de ReflexIA siguiendo el mismo patrón del Laboratorio 6, y cada paso del patrón es un commit:

1. `models.py`: el modelo y su migración (`makemigrations` + `migrate`).
2. `admin.py`: registro en el panel de administración y prueba cargando datos desde `/admin/`.
3. `serializers.py`: `ModelSerializer` del modelo.
4. `views.py`: `ModelViewSet` del modelo.
5. `urls.py`: registro en el `DefaultRouter` y prueba en la interfaz navegable de DRF (`/api/...`).

Al terminar cada etapa, `python manage.py check` no debe mostrar errores.

Estados: ✅ hecha · ⏳ pendiente.

## Etapa 0: estructura inicial ✅

Entorno virtual, proyecto `reflexIA_Proyect`, aplicación `reflexIA_App`, configuración y documentación.

| # | Archivos | Mensaje sugerido |
|---|---|---|
| 1 | `.gitignore`, `requirements.txt` | `chore: agrega gitignore y dependencias (Django 6.1 y DRF)` |
| 2 | `manage.py`, `reflexIA_Proyect/` | `feat: crea proyecto reflexIA_Proyect` |
| 3 | `reflexIA_App/` | `feat: crea app reflexIA_App con rutas de la API` |
| 4 | `README.md`, `docs/` | `docs: documenta instalación y plan incremental` |

> El commit 2 deja en `settings.py` la línea `'reflexIA_App'` en `INSTALLED_APPS`, pero la app recién aparece en el commit 3. Para que cada commit funcione por sí solo, haz los commits 2 y 3 juntos, o agrega esa línea recién en el commit 3.

## Recursos previstos

Cada recurso sale de un modelo del frontend (`reflexIA/src/models/`). Los nombres y campos son una propuesta; se confirman al empezar cada etapa.

| Etapa | Modelo | HU | Campos principales | Ruta |
|---|---|---|---|---|
| 1 | `UsuarioAutorizado` | HU-01 Whitelist | `correo` (`@ucen.cl`, único), `nombre`, `rol` (estudiante, profesor, administrador), `estado` (activo, revocado), `fecha_registro` | `/api/usuarios/` |
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
| 11 | Reglas de negocio en el servidor: dominio `@ucen.cl`, aprobación 8/10 del cuestionario, 3 intentos por taller, nota 7,0 para avanzar. |
