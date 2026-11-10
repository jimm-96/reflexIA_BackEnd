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
git switch -c recurso-<nombre>
# ... commits de la etapa ...
git push -u origin recurso-<nombre>
```

Luego se abre el Pull Request hacia `main` en GitHub y se integra con **Merge pull request**. Abrir el PR no basta: sus commits llegan a `main` solo después del merge. Recién entonces se vuelve a `main` con `git switch main` y `git pull`, y se crea la rama de la etapa siguiente. Así cada etapa parte con la anterior ya integrada y las migraciones quedan en orden (`0001`, `0002`, …).

| Etapa | Rama |
|---|---|
| 0 | `main` (directo) |
| 1 | `recurso-usuarios` (PR #1, integrado) |
| 2 | `recurso-talleres` (PR #2, integrado) |
| 3 | `recurso-preguntas` (PR #3, integrado) |
| 4 | `recurso-intentos-cuestionario` (PR #4, integrado) |
| 5 | `recurso-reflexiones` |
| 6 | `recurso-retroalimentaciones` (PR #6, integrado) |
| 7 | `recurso-evaluaciones` (PR #7, integrado) |
| 8 | `recurso-innovaciones` |
| 9 | `config-mysql` |

## Etapa 0: estructura inicial ✅

Entorno virtual, proyecto `reflexIA_Proyect`, aplicación `reflexIA_App`, configuración y documentación.

| # | Archivos | Mensaje sugerido |
|---|---|---|
| 1 | `.gitignore`, `requirements.txt` | `chore: agrega gitignore y dependencias (Django 6.1 y DRF)` |
| 2 | `manage.py`, `reflexIA_Proyect/`, `reflexIA_App/` | `feat: crea proyecto reflexIA_Proyect y app reflexIA_App` |
| 3 | `README.md`, `docs/` | `docs: documenta instalación y plan incremental` |

## Etapa 1: usuarios autorizados (HU-01) ✅

Rama: `recurso-usuarios`.

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

## Etapa 2: talleres (HU-03, HU-06, HU-09) ✅

Rama: `recurso-talleres`.

Modelo `Taller`: la definición de cada uno de los cuatro talleres, con su plazo y sus intentos. Equivale a `Workshop` del frontend (`src/models/criticalIncident.ts`) más la configuración de plazos e intentos de `src/models/workPacing.ts`.

| Campo | Tipo | Detalle |
|---|---|---|
| `numero` | `PositiveSmallIntegerField` | Único, de 1 a 4 (RF-03: son cuatro talleres). Define el orden. |
| `titulo` | `CharField` | Título oficial del taller. |
| `objetivo` | `TextField` | Bloque "Objetivo" (RF-03). |
| `actividad` | `TextField` | Bloque "Actividad" (RF-03). |
| `producto` | `TextField` | Bloque "Producto" (RF-03). |
| `fecha_limite` | `DateField` | Opcional. Plazo que fija el profesor guía (DEC-13). Formato `AAAA-MM-DD`. |
| `intentos_maximos` | `PositiveSmallIntegerField` | De 1 a 3; por defecto 3 (DEC-11). |

Decisiones:

- `Taller` guarda solo la **definición** del taller, que es la misma para todos los estudiantes. El estado de cada estudiante (bloqueado, en curso, completado), sus intentos usados y su nota van en `Reflexion` y `Evaluacion` (etapas 5 y 7), que apuntarán a `Taller` con una llave foránea.
- No se agregó un campo `codigo` (`workshop-1`, …): se deduce de `numero`, y así no hay dos datos que puedan contradecirse.
- Los límites (4 talleres, 1 a 3 intentos) son constantes de la clase (`NUMERO_MAXIMO`, `INTENTOS_MAXIMOS_PERMITIDOS`), para cambiarlos en un solo lugar si el equipo los modifica.
- Los campos con tilde tienen etiqueta en español (`'número'`, `'título'`, `'fecha límite'`, `'intentos máximos'`) para que el admin y los mensajes de error se lean bien.

| # | Archivos | Mensaje sugerido |
|---|---|---|
| 1 | `reflexIA_App/models.py`, `reflexIA_App/migrations/0002_taller.py` | `feat: agrega modelo Taller con plazo e intentos máximos` |
| 2 | `reflexIA_App/admin.py` | `feat: registra Taller en el admin` |
| 3 | `reflexIA_App/serializers.py` | `feat: agrega TallerSerializer` |
| 4 | `reflexIA_App/views.py` | `feat: agrega TallerViewSet` |
| 5 | `reflexIA_App/urls.py` | `feat: expone /api/talleres/ en el router` |
| 6 | `README.md`, `docs/plan-incremental.md` | `docs: documenta etapa 2 (talleres)` |

Cómo probarla:

1. `python manage.py migrate`.
2. En `/admin/` → **Talleres**: cargar los cuatro talleres. Títulos oficiales (RF-03):
   1. Identificación del incidente
   2. Del aula a la transformación profesional
   3. Confrontación teórica
   4. Transformación e innovación
3. Comprobar que se rechazan un número repetido, el número 5 y 4 intentos.
4. En `/api/talleres/`: listar, crear, y en `/api/talleres/<id>/` editar el plazo o los intentos (PATCH) y eliminar.

## Etapa 3: preguntas teóricas (HU-04) ✅

Rama: `recurso-preguntas`.

Modelos `PreguntaTeorica` y `Alternativa`: el banco de preguntas del cuestionario del marco teórico. Equivalen a `QuizQuestion` y `QuizOption` del frontend (`src/models/theoryQuiz.ts`).

`PreguntaTeorica`:

| Campo | Tipo | Detalle |
|---|---|---|
| `enunciado` | `TextField` | Texto de la pregunta. Obligatorio. |
| `activa` | `BooleanField` | Por defecto `True`. Permite sacar una pregunta del cuestionario sin borrarla. |

`Alternativa`:

| Campo | Tipo | Detalle |
|---|---|---|
| `pregunta` | `ForeignKey` a `PreguntaTeorica` | `on_delete=CASCADE`: al borrar la pregunta se borran sus alternativas. `related_name='alternativas'`. |
| `texto` | `CharField` | Texto de la opción, hasta 300 caracteres. |
| `es_correcta` | `BooleanField` | Por defecto `False`. Marca la respuesta correcta. |

Decisiones:

- En el frontend la respuesta correcta se guarda en la pregunta (`correctOptionId`); aquí cada alternativa indica si es correcta con `es_correcta`, como propone el plan.
- En el admin, las alternativas se cargan en la misma pantalla de la pregunta (`TabularInline` con 4 filas), y `Alternativa` no se registra por separado para que no queden alternativas sin pregunta.
- En la API, cada pregunta trae sus alternativas anidadas (`AlternativaSerializer` dentro de `PreguntaTeoricaSerializer`). Son de solo lectura: se crean desde el admin.
- El ViewSet usa `prefetch_related('alternativas')`, que trae las alternativas de todas las preguntas en una sola consulta en vez de una por pregunta.

Pendientes para el ajuste final:

- La API muestra `es_correcta`. Cuando haya autenticación (etapa 10), el estudiante no debería ver cuál es la respuesta correcta.
- Las alternativas no se pueden crear ni editar por la API. Si el frontend necesita cargar preguntas, el serializer tendrá que aceptar alternativas anidadas.
- No se valida que cada pregunta tenga exactamente una alternativa correcta (etapa 11).

| # | Archivos | Mensaje sugerido |
|---|---|---|
| 1 | `reflexIA_App/models.py`, `reflexIA_App/migrations/0003_preguntateorica_alternativa.py` | `feat: agrega modelos PreguntaTeorica y Alternativa` |
| 2 | `reflexIA_App/admin.py` | `feat: registra PreguntaTeorica en el admin con sus alternativas` |
| 3 | `reflexIA_App/serializers.py` | `feat: agrega PreguntaTeoricaSerializer` |
| 4 | `reflexIA_App/views.py` | `feat: agrega PreguntaTeoricaViewSet` |
| 5 | `reflexIA_App/urls.py` | `feat: expone /api/preguntas/ en el router` |
| 6 | `README.md`, `docs/plan-incremental.md` | `docs: documenta etapa 3 (preguntas teóricas)` |

Cómo probarla:

1. `python manage.py migrate`.
2. En `/admin/` → **Preguntas teóricas**: crear una pregunta con cuatro alternativas y marcar una como correcta.
3. En `/api/preguntas/`: comprobar que la pregunta aparece con sus alternativas anidadas, crear otra (POST), y comprobar que un enunciado vacío se rechaza.
4. En `/api/preguntas/<id>/`: desactivarla (PATCH con `"activa": false`) y eliminarla (DELETE). Al eliminar una pregunta también se eliminan sus alternativas.

## Etapa 4: intentos de cuestionario (HU-04) ✅

Rama: `recurso-intentos-cuestionario`.

Modelo `IntentoCuestionario`: cada vez que un estudiante rinde el cuestionario del marco teórico, con su resultado. Equivale a `QuizAttempt` del frontend (`src/models/theoryQuiz.ts`).

| Campo | Tipo | Detalle |
|---|---|---|
| `estudiante` | `ForeignKey` a `UsuarioAutorizado` | Solo usuarios con rol `student` (`limit_choices_to`). `on_delete=CASCADE`: al eliminar al estudiante se eliminan sus intentos (RN-03). `related_name='intentos_cuestionario'`. |
| `respuestas_correctas` | `PositiveSmallIntegerField` | De 0 a 10: cada intento tiene 10 preguntas (RF-04). |
| `nota` | `DecimalField` | De 1.0 a 7.0, con un decimal (`max_digits=2`, `decimal_places=1`). |
| `aprobado` | `BooleanField` | Por defecto `False`. |
| `fecha` | `DateTimeField` | Se llena sola al crear; solo lectura. |

Decisiones:

- Solo los estudiantes pueden tener intentos (`limit_choices_to={'rol': 'student'}`). Se adelantó a esta etapa porque es parte del modelo, igual que el dominio `@ucen.cl` en la etapa 1: el admin solo ofrece estudiantes y la API rechaza a un profesor.
- La nota es `DecimalField` y no `FloatField`, para que `6.6` se guarde exacto. La API la entrega como número (`6.6`) y no como texto (`"6.6"`), igual que la usa el frontend (`coerce_to_string=False`).
- Los límites (10 preguntas, notas de 1.0 a 7.0) son constantes de la clase (`PREGUNTAS_POR_INTENTO`, `NOTA_MINIMA`, `NOTA_MAXIMA`).
- El estudiante se envía por su id; la respuesta agrega `correo_estudiante` (solo lectura) para leer quién rindió sin buscar el id.
- El ViewSet y el admin usan `select_related('estudiante')`, que trae el estudiante de cada intento en la misma consulta.
- No se agregó un campo con el número de intento: se obtiene contando los intentos del estudiante, y así no hay dos datos que puedan contradecirse.

Pendientes para el ajuste final:

- La nota y `aprobado` los envía quien registra el intento. Las reglas (aprobar con 8 de 10, máximo 9 intentos en bloques con nota máxima 7.0, 5.0 y 4.0, DEC-15) se aplican en la etapa 11.
- No hay filtro por estudiante (`?estudiante=<id>`): la lista trae los intentos de todos.

| # | Archivos | Mensaje sugerido |
|---|---|---|
| 1 | `reflexIA_App/models.py`, `reflexIA_App/migrations/0004_intentocuestionario.py` | `feat: agrega modelo IntentoCuestionario` |
| 2 | `reflexIA_App/admin.py` | `feat: registra IntentoCuestionario en el admin` |
| 3 | `reflexIA_App/serializers.py` | `feat: agrega IntentoCuestionarioSerializer` |
| 4 | `reflexIA_App/views.py` | `feat: agrega IntentoCuestionarioViewSet` |
| 5 | `reflexIA_App/urls.py` | `feat: expone /api/intentos-cuestionario/ en el router` |
| 6 | `README.md`, `docs/plan-incremental.md` | `docs: documenta etapa 4 (intentos de cuestionario)` |

Cómo probarla:

1. `python manage.py migrate`.
2. En `/admin/` → **Usuarios autorizados**: tener al menos un estudiante y un profesor.
3. En `/admin/` → **Intentos de cuestionario**: comprobar que la lista de estudiantes no incluye al profesor, crear un intento (por ejemplo, 9 correctas y nota 6.6) y comprobar que se rechazan 11 correctas y la nota 8.
4. En `/api/intentos-cuestionario/`: listar, crear (POST) y comprobar que el id de un profesor se rechaza. En `/api/intentos-cuestionario/<id>/`: editar (PATCH) y eliminar (DELETE).

## Etapa 5: reflexiones (HU-03) ✅

Rama: `recurso-reflexiones`.

Modelo `Reflexion`: el análisis de un incidente crítico que un estudiante escribe en un taller. Equivale a `IncidentDraft` y `WorkshopAttempt` del frontend (`src/models/criticalIncident.ts`). Es el primer modelo con dos llaves foráneas.

| Campo | Tipo | Detalle |
|---|---|---|
| `estudiante` | `ForeignKey` a `UsuarioAutorizado` | Solo usuarios con rol `student` (`limit_choices_to`). `on_delete=CASCADE`. `related_name='reflexiones'`. |
| `taller` | `ForeignKey` a `Taller` | `on_delete=CASCADE`: al eliminar el taller se eliminan sus reflexiones. `related_name='reflexiones'`. |
| `contexto`, `descripcion`, `actores`, `relevancia` | `TextField` | Los cuatro pasos del formulario del frontend (`context`, `description`, `actors`, `relevance`). Pueden quedar vacíos (`blank=True`) mientras la reflexión es un borrador. |
| `estado` | `CharField` con opciones | `draft` (Borrador, por defecto), `submitted` (Enviada) o `reviewed` (Revisada). |
| `intentos_usados` | `PositiveSmallIntegerField` | De 0 a 3, por defecto 0. |
| `fecha_creacion` | `DateTimeField` | Se llena sola al crear (`auto_now_add`); solo lectura. |
| `fecha_actualizacion` | `DateTimeField` | Se actualiza sola cada vez que se guarda (`auto_now`); solo lectura. Equivale a `savedAt` del borrador en el frontend. |

Decisiones:

- Un estudiante tiene una sola reflexión por taller (`UniqueConstraint` sobre `estudiante` y `taller`). Los reintentos se cuentan en `intentos_usados`, no como filas nuevas. La regla está en el modelo, así que el admin y la API la aplican con el mismo mensaje: "Este estudiante ya tiene una reflexión en este taller."
- Los valores guardados de `estado` son los del frontend, en inglés, igual que `rol` en la etapa 1; las etiquetas se muestran en español.
- El tope de `intentos_usados` reutiliza la constante `Taller.INTENTOS_MAXIMOS_PERMITIDOS` (3), en vez de repetir el número.
- El estudiante y el taller se envían por id; la respuesta agrega `correo_estudiante` y `numero_taller` (solo lectura).
- El ViewSet y el admin usan `select_related('estudiante', 'taller')`. Con 9 reflexiones, la lista se obtiene en 1 consulta en vez de 19.
- El formulario del admin se separa en secciones (`fieldsets`): datos, análisis del incidente y fechas.

Pendientes para el ajuste final:

- `intentos_usados` y `estado` los envía el cliente. Las reglas (no superar los `intentos_maximos` de cada taller, que pueden ser 1 o 2; cambios de estado en orden; mínimo de 50 caracteres por texto para enviar; cierre al vencer `fecha_limite`) se aplican en la etapa 11.
- Solo se guarda el contenido más reciente. El frontend guarda el texto de cada intento (`WorkshopAttempt.content`) y las respuestas a pasos configurados por el docente (`answers`, C-05); falta decidir si van en un modelo aparte.
- No hay filtros por estudiante ni por taller (`?estudiante=<id>`, `?taller=<id>`).

| # | Archivos | Mensaje sugerido |
|---|---|---|
| 1 | `reflexIA_App/models.py`, `reflexIA_App/migrations/0005_reflexion.py` | `feat: agrega modelo Reflexion` |
| 2 | `reflexIA_App/admin.py` | `feat: registra Reflexion en el admin` |
| 3 | `reflexIA_App/serializers.py` | `feat: agrega ReflexionSerializer` |
| 4 | `reflexIA_App/views.py` | `feat: agrega ReflexionViewSet` |
| 5 | `reflexIA_App/urls.py` | `feat: expone /api/reflexiones/ en el router` |
| 6 | `README.md`, `docs/plan-incremental.md` | `docs: documenta etapa 5 (reflexiones)` |

Cómo probarla:

1. `python manage.py migrate`.
2. Tener al menos un estudiante, un profesor y dos talleres.
3. En `/admin/` → **Reflexiones**: crear una reflexión con solo el contexto (se acepta como borrador), comprobar que la lista de estudiantes no incluye al profesor, y que se rechazan una segunda reflexión del mismo estudiante en el mismo taller y 4 intentos usados.
4. En `/api/reflexiones/`: crear una reflexión en el otro taller (POST) y comprobar que el duplicado se rechaza. En `/api/reflexiones/<id>/`: enviarla (PATCH con `"estado": "submitted"` e `"intentos_usados": 1`), comprobar que cambia `fecha_actualizacion`, y eliminarla (DELETE).

## Etapa 6: retroalimentaciones (HU-02) ✅

Rama: `recurso-retroalimentaciones`.

Modelo `Retroalimentacion`: conserva la propuesta de la IA y el comentario del profesor guía asociado a una reflexión.

| Campo | Tipo | Detalle |
|---|---|---|
| `reflexion` | `ForeignKey` a `Reflexion` | `on_delete=CASCADE`: al eliminar la reflexión se elimina su retroalimentación. `related_name='retroalimentaciones'`. |
| `propuesta_ia` | `TextField` | Orientación propuesta por la IA. Obligatoria. |
| `comentario_docente` | `TextField` | Comentario del profesor guía. Puede quedar vacío mientras está pendiente. |
| `estado` | `CharField` con opciones | `pending` (Pendiente), `edited` (Editada) o `validated` (Validada). |

Decisiones:

- Los valores de estado coinciden con el frontend (`ReviewStatus`); el admin y los mensajes los muestran en español.
- La retroalimentación está asociada a la reflexión y su respuesta agrega el correo del estudiante y el número de taller para hacer legible la relación.
- El flujo de transición entre estados y la validación obligatoria antes de entregar al estudiante se implementarán junto con las reglas de negocio posteriores.

| # | Archivos | Mensaje sugerido |
|---|---|---|
| 1 | `reflexIA_App/models.py`, `reflexIA_App/migrations/0006_retroalimentacion.py` | `feat: agrega modelo Retroalimentacion` |
| 2 | `reflexIA_App/admin.py` | `feat: registra Retroalimentacion en el admin` |
| 3 | `reflexIA_App/serializers.py` | `feat: agrega RetroalimentacionSerializer` |
| 4 | `reflexIA_App/views.py` | `feat: agrega RetroalimentacionViewSet` |
| 5 | `reflexIA_App/urls.py` | `feat: expone /api/retroalimentaciones/ en el router` |
| 6 | `README.md`, `docs/plan-incremental.md` | `docs: documenta etapa 6 (retroalimentaciones)` |

Cómo probarla:

1. `python manage.py migrate`.
2. En `/admin/` → **Retroalimentaciones**: asociar una propuesta a una reflexión y comprobar los filtros por estado.
3. En `/api/retroalimentaciones/`: listar y crear (POST) una retroalimentación vinculada a una reflexión existente.
4. En `/api/retroalimentaciones/<id>/`: cambiar el comentario o estado (PATCH) y eliminar (DELETE). Comprobar que una reflexión inexistente se rechaza.

## Etapa 7: evaluaciones (HU-02, panel docente) ✅

Rama: `recurso-evaluaciones`.

Modelo `Evaluacion`: registra la nota y el resultado que el profesor guía asigna a un estudiante en cada taller.

| Campo | Tipo | Detalle |
|---|---|---|
| `estudiante` | `ForeignKey` a `UsuarioAutorizado` | Solo usuarios con rol `student` (`limit_choices_to`). `on_delete=CASCADE`. `related_name='evaluaciones'`. |
| `taller` | `ForeignKey` a `Taller` | `on_delete=CASCADE`: al eliminar el taller se eliminan sus evaluaciones. `related_name='evaluaciones'`. |
| `nota` | `DecimalField` | De 1.0 a 7.0, con un decimal. |
| `resultado` | `CharField` con opciones | `approved` (Aprobado) o `failed` (Reprobado), igual que `WorkshopOutcome` del frontend. |
| `fecha` | `DateTimeField` | Se llena sola al crear; solo lectura. |

Decisiones:

- Se guarda una sola evaluación por estudiante y taller (`UniqueConstraint`): al modificar la nota se actualiza la evaluación del taller sin duplicarla.
- El estudiante y el taller se envían por id; la respuesta agrega `correo_estudiante` y `numero_taller` (solo lectura).
- Los valores de `resultado` coinciden con el frontend; las etiquetas se muestran en español.
- La regla de negocio que determina `approved` desde una nota de 4.0 o superior se aplicará en la etapa 11.

| # | Archivos | Mensaje sugerido |
|---|---|---|
| 1 | `reflexIA_App/models.py`, `reflexIA_App/migrations/0007_evaluacion.py` | `feat: agrega modelo Evaluacion` |
| 2 | `reflexIA_App/admin.py` | `feat: registra Evaluacion en el admin` |
| 3 | `reflexIA_App/serializers.py` | `feat: agrega EvaluacionSerializer` |
| 4 | `reflexIA_App/views.py` | `feat: agrega EvaluacionViewSet` |
| 5 | `reflexIA_App/urls.py` | `feat: expone /api/evaluaciones/ en el router` |
| 6 | `README.md`, `docs/plan-incremental.md` | `docs: documenta etapa 7 (evaluaciones)` |

Cómo probarla:

1. `python manage.py migrate`.
2. En `/admin/` → **Evaluaciones**: registrar una nota para un estudiante y un taller; comprobar que no se ofrecen usuarios con otro rol y que la fecha es de solo lectura.
3. En `/api/evaluaciones/`: listar y crear (POST) una evaluación, comprobando la respuesta con correo y número de taller.
4. Probar notas fuera del rango, ids inválidos y una segunda evaluación para el mismo estudiante y taller; deben rechazarse. En `/api/evaluaciones/<id>/`: editar (PATCH) y eliminar (DELETE).

## Recursos previstos

Cada recurso sale de un modelo del frontend (`reflexIA/src/models/`). Los nombres y campos son una propuesta; se confirman al empezar cada etapa.

| Etapa | Modelo | HU | Campos principales | Ruta |
|---|---|---|---|---|
| 1 ✅ | `UsuarioAutorizado` | HU-01 Whitelist | `correo` (`@ucen.cl`, único), `nombre`, `rol`, `estado`, `fecha_registro`, `fecha_revocacion` | `/api/usuarios/` |
| 2 ✅ | `Taller` | HU-03, HU-06, HU-09 | `numero`, `titulo`, `objetivo`, `actividad`, `producto`, `fecha_limite`, `intentos_maximos` (3 por defecto) | `/api/talleres/` |
| 3 ✅ | `PreguntaTeorica` y `Alternativa` | HU-04 Marco teórico | Pregunta: `enunciado`, `activa`. Alternativa: `pregunta` (FK), `texto`, `es_correcta` | `/api/preguntas/` |
| 4 ✅ | `IntentoCuestionario` | HU-04 | `estudiante` (FK), `respuestas_correctas`, `nota`, `aprobado`, `fecha` | `/api/intentos-cuestionario/` |
| 5 ✅ | `Reflexion` | HU-03 Incidentes críticos | `estudiante` (FK), `taller` (FK), `contexto`, `descripcion`, `actores`, `relevancia`, `estado` (borrador, enviada, revisada), `intentos_usados`, `fecha_creacion`, `fecha_actualizacion` | `/api/reflexiones/` |
| 6 | `Retroalimentacion` | HU-02 El Impulso | `reflexion` (FK), `propuesta_ia`, `comentario_docente`, `estado` (pendiente, editada, validada) | `/api/retroalimentaciones/` |
| 7 | `Evaluacion` | HU-02, panel docente | `estudiante` (FK), `taller` (FK), `nota` (1,0 a 7,0), `resultado` (aprobado, reprobado), `fecha` | `/api/evaluaciones/` |
| 8 | `Innovacion` | HU-07 Biblioteca | `titulo`, `categoria`, `descripcion`, `autor` (FK), `publicada` | `/api/innovaciones/` |

El orden importa: los modelos con llaves foráneas (FK) van después de los modelos a los que apuntan.

## Etapas posteriores ⏳

| Etapa | Contenido |
|---|---|
| 9 | Cambio de SQLite a **MySQL** (`mysqlclient`, credenciales en `.env`). |
| 10 | Preparación para integrar con el frontend React: CORS (`django-cors-headers`) y autenticación. |
| 11 | Reglas de negocio en el servidor: aprobación 8/10 del cuestionario, nota 7,0 para avanzar, cierre automático del taller al vencer su plazo (DEC-13, GAP-05). (El dominio `@ucen.cl` se valida desde la etapa 1 y el rango de 1 a 3 intentos, desde la etapa 2.) |
