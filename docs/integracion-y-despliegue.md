# Integración y despliegue de ReflexIA

Guía interna del equipo para conectar el frontend (`reflexIA`, React) con el backend (`reflexIA_BackEnd`, Django), probarlos, desplegarlos y medir su carga.

> **Actualización del 27-11-2026:** el proyecto deja **Firebase** (Authentication y Firestore): el login lo hace Django y todos los datos van a la API, con **MySQL** como base de datos. El despliegue es **Vercel** (frontend) y **Render** (backend), decidido por el equipo. La guía quedó alineada con la pauta de la EVA3 (sección 2) y suma los vacíos encontrados al revisar el código (cuentas, límite de intentos, panel docente y cuestionario).

Está ordenada por prioridad. Primero lo que hay que **decidir o resolver antes de escribir código** (sección 1); luego el [tablero de avance](#tablero-de-avance), que cada integrante actualiza a medida que avanza; y después, los pasos en el orden en que dependen unos de otros.

> Las plataformas gratuitas cambian seguido. Lo que dice esta guía sobre planes gratuitos se verificó el **24-11-2026** (fuentes al final). Revísenlo de nuevo al crear las cuentas.

---

## 1. Antes de empezar: problemas y decisiones

Resuelvan estos puntos en este orden. Los primeros bloquean a todos los demás. Su estado se lleva en el [tablero de avance](#tablero-de-avance).

| # | Tema | Qué hay que hacer | Bloquea a | En el tablero |
|---|---|---|---|---|
| 1.1 | Base de datos MySQL en producción | Elegir dónde alojarla y probar que Django funcione con ella. | Todo el backend en producción | D-1 |
| 1.2 | Ajustes del backend para integrar | Resolver lo que hoy impide que el frontend funcione contra la API (cuentas, cuestionario, impulsos, panel docente). | Casi todo el frontend | D-2 |
| 1.3 | `SECRET_KEY` expuesta | Generar una nueva para producción, fuera del código. | Despliegue del backend | D-3 |
| 1.4 | Herramienta de pruebas del frontend | **Decidido: Jest y React Testing Library**, como exige la pauta. Falta configurarlo y migrar las pruebas actuales, que están en Vitest. | Pruebas del frontend | D-4 ✅ |
| 1.5 | Alcance de la integración | Acordar qué pasa a la API y qué queda en el frontend. | Reparto del frontend | D-5 |
| 1.6 | Cuentas y reparto | Crear cuentas en las plataformas, darse accesos y repartir tareas. | Todo | D-6 |

### 1.1 Base de datos MySQL en producción

**El problema.** Hasta este año había MySQL gratuito en PythonAnywhere y en Aiven. Ya no sirve para cuentas nuevas:

| Opción | Situación al 24-11-2026 |
|---|---|
| PythonAnywhere (cuenta gratuita) | Las cuentas creadas **desde el 15-01-2026** ya no incluyen MySQL. Las anteriores lo conservan. |
| Aiven MySQL Free | **Retirado**: desde noviembre de 2026 no se pueden crear servicios MySQL gratuitos. |
| Render | Solo ofrece PostgreSQL gratuito, y la base gratuita expira a los pocos días o semanas. |
| **TiDB Cloud Starter** | **Gratis sin tarjeta**: 5 GiB y 50 millones de "Request Units" al mes. Habla el protocolo de MySQL, así que Django se conecta con el backend `mysql`. |

**Propuesta:** **MySQL 8.4** en local para desarrollar y **TiDB Cloud Starter** en producción.

**Riesgo:** TiDB no es MySQL al 100%, y no hay confirmación de que `django-tidb` (su backend especial) soporte Django 6.1. Por eso, antes de construir nada encima, hay una **prueba de viabilidad** (unos 30 minutos, en una rama de prueba que no se integra):

```bash
pip install mysqlclient certifi
# Configurar DATABASES con los datos de TiDB (ver B-2) y luego:
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver   # crear un taller desde /admin/ y leerlo en /api/talleres/
```

- Si `migrate` termina y el admin funciona, **se sigue con TiDB**.
- Si falla, anoten el error y pasen a las alternativas, en este orden. Todas mantienen el backend en **Render**; solo cambia dónde vive la base de datos:
  1. Bajar el backend a **Django 5.2 LTS** (soportado hasta abril de 2028) y usar `django-tidb` de la versión correspondiente.
  2. Pagar MySQL administrado (el plan Developer de Aiven cuesta unos USD 5 al mes) o usar PostgreSQL gratuito (por ejemplo, Neon). Esta última opción deja de ser MySQL, así que tendrían que decidirlo como equipo.

> **No usen XAMPP para el MySQL local.** Trae MariaDB 10.4, más antiguo que la versión mínima que exige Django 6.1. Instalen **MySQL Community Server 8.4 LTS** (incluye MySQL Workbench) o usen Docker.

### 1.2 Ajustes del backend que la integración necesita

Al cruzar los servicios del frontend con los permisos y modelos del backend aparecen estos conflictos:

| Conflicto | Por qué pasa | Solución | Detalle |
|---|---|---|---|
| **El frontend no puede corregir el cuestionario** | Desde la etapa 9, el estudiante no recibe `es_correcta`, para no ver las respuestas antes de rendir. Sin ellas, el navegador no puede calcular la nota. | El servidor corrige: `POST /api/intentos-cuestionario/rendir/`. Además, la nota deja de ser manipulable desde el navegador. | B-Q1 |
| **El estudiante no puede guardar sus impulsos** | "El Impulso" se genera en el frontend, pero en el backend solo el profesor puede crear retroalimentaciones. | Endpoint `POST /api/reflexiones/<id>/impulsos/`: guarda el impulso y descuenta el intento en el servidor. | B-I2 |
| **Autorizar un correo no crea su cuenta** | La whitelist (`UsuarioAutorizado`) y las cuentas de Django son cosas separadas. Quien se agregue desde la app no podrá entrar. | Crear y desactivar la cuenta junto con la whitelist. | B-4 |
| **El estudiante no conoce su `id`** | Para crear una reflexión hay que enviar `estudiante`, `/auth/yo/` no lo devuelve y el estudiante no puede leer `/usuarios/`. | `/auth/yo/` devuelve el `id` de la whitelist. | B-4 |
| **El límite de intentos de los talleres se puede saltar** | El estudiante puede editar `intentos_usados` y `estado`, o borrar su reflexión y crearla de nuevo (se borra también la retroalimentación). | Proteger esos campos y quitar el borrado al estudiante. | B-I2 |
| **El profesor guía no puede listar estudiantes** | `/usuarios/` es solo del administrador, y el panel necesita ver también a quienes no tienen actividad. | Lectura de estudiantes para el profesor guía. | B-8 |
| **Faltan datos en los modelos** | `PreguntaTeorica` no tiene explicación; no hay dónde guardar la estructura de talleres ni los trabajos que se envían a innovaciones. | Campo y modelos nuevos. | B-Q1, B-9 |

### 1.3 `SECRET_KEY` expuesta

La clave actual está escrita en `reflexIA_Proyect/settings.py`. Como el repositorio es público, ya quedó en el historial de GitHub y no sirve para producción. Hay que generar una clave nueva y leerla desde una variable de entorno (B-1):

```bash
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

### 1.4 Herramienta de pruebas del frontend

La pauta de la EVA3 pide pruebas del frontend con **Jest y React Testing Library**, dos veces y sin alternativa. El frontend hoy usa **Vitest** (`npm test` → `vitest run`), con pruebas de lógica en `src/utils/` y `src/services/`.

**Decidido (27-11-2026):** se usa **Jest**. Hay que migrar antes de escribir pruebas de componentes, para no presentar algo distinto de lo que pide la pauta. La migración es corta: la API es casi igual (`describe`, `it`, `expect`); cambian `vi.fn()` → `jest.fn()`, `vi.mock()` → `jest.mock()` y `vi.stubGlobal()` → asignar en `globalThis`. La configuración está en la sección 8.2.

### 1.5 Alcance de la integración

Un sistema acotado pero bien conectado vale más que uno grande a medio integrar. Propuesta de qué queda **fuera** de la API:

| Funcionalidad | Dónde queda | Motivo |
|---|---|---|
| Detección de datos sensibles (HU-05) | Frontend → OpenRouter | No hay recurso de backend; queda como evolución (GAP-06). |
| Generación de "El Impulso" | Frontend (`impulseGenerator`, simulado) | La IA real es evolución (GAP-07). El impulso **sí se guarda** en el backend (B-I2). |

Todo lo demás pasa a la API (sección 6), incluidos el **inicio de sesión** (cuentas de Django) y la **estructura configurable de talleres** (B-9).

### 1.6 Cuentas, accesos y reparto

1. **Cuentas.** Que cada servicio tenga un dueño y que el resto quede invitado:
   - GitHub: los 4 integrantes con acceso de escritura a **ambos** repos.
   - [TiDB Cloud](https://tidbcloud.com) (dueño: Estudiante 1). Crear un cluster **Starter** en la región AWS más cercana.
   - [Render](https://render.com) (dueño: Estudiante 1) y [Vercel](https://vercel.com) (dueño: Estudiante 2), ambos con login de GitHub.
2. **Reparto:** sección 3.

### 1.7 Cambios de la validación con la profesora que afectan al modelo

Salen de `reflexIA/docs/especificacion/11-cambios-validacion-prototipo.md`. Conviene resolverlos **antes** de conectar los talleres (F-6).

| Cambio | Choque con el backend actual | Estado |
|---|---|---|
| Cada taller tiene sus propios pasos; el Taller 1 es una "Ficha del incidente" de 5 preguntas (CAM-14) | `Reflexion` tiene cuatro textos fijos. Hace falta guardar las respuestas por pregunta (por ejemplo, un campo JSON). | Confirmado para el Taller 1 |
| Títulos oficiales de los talleres (CAM-12) | Difieren de los de la etapa 2. Usar los nuevos en B-5. | Confirmar con los documentos |
| El profesor guía habilita a un estudiante bloqueado (CAM-23) | No está modelado, y `numero_intento` llega como máximo a 9. | Falta decidir cómo (duda D-02) |
| Intentos por bloques también en los talleres (CAM-17) | `intentos_maximos` e `intentos_usados` llegan como máximo a 3. | Falta decidir (conflicto C-02) |

---

## Tablero de avance

Backlog de toda la etapa. Cada fila es una tarea con su ID, el mismo que usa el resto de la guía.

**Estados:** ⏳ Pendiente · 🔄 En curso · 👀 En revisión (PR abierto) · ✅ Hecho · ⛔ Bloqueado (anotar por qué en "Notas").

**Cómo actualizarlo:**
- Cada integrante cambia **solo sus filas**, en el mismo PR de la tarea. Así el tablero de `main` siempre refleja lo integrado, y los PR no chocan entre sí.
- El tablero vive en el repo del backend. Para las tareas del frontend (F, P-1 a P-5, P-7), actualicen la fila con un commit `docs:` en el backend después del merge en el frontend, y anoten el PR con el nombre del repo (`reflexIA#40`).
- Al empezar, pasa la fila a 🔄 y anota la rama. Al abrir el PR, a 👀 con el número (`#15`). Al hacer merge, a ✅.
- Si una tarea queda bloqueada, se marca ⛔ y se explica en "Notas" para que el equipo la vea.
- Las decisiones (D-1 a D-6) se marcan ✅ cuando el equipo las acuerda, anotando la decisión en "Notas".

### Decisiones (sección 1)

| ID | Tarea | Responsable | Depende de | Estado | Rama / PR | Notas |
|---|---|---|---|---|---|---|
| D-1 | Base de datos de producción: prueba de viabilidad de TiDB y elección final (1.1). | Estudiante 1 | — | ⏳ | | |
| D-2 | Acordar los cambios del backend para integrar (1.2). | Todos | — | ⏳ | | |
| D-3 | Generar la `SECRET_KEY` de producción (1.3). | Estudiante 1 | — | ⏳ | | |
| D-4 | Herramienta de pruebas del frontend (1.4). | Todos | — | ✅ | | Jest y React Testing Library, como exige la pauta (27-11-2026). |
| D-5 | Acordar el alcance: qué queda fuera de la API (1.5). | Todos | — | ⏳ | | Propuesta actualizada el 27-11: sin Firebase. |
| D-6 | Crear cuentas (TiDB, Render, Vercel), dar accesos y confirmar el reparto (1.6). | Todos | — | ⏳ | | Servicios de despliegue decididos: Vercel (frontend) y Render (backend). |

### Backend (sección 5)

| ID | Tarea | Responsable | Depende de | Estado | Rama / PR | Notas |
|---|---|---|---|---|---|---|
| B-1 | Configuración por variables de entorno y `.env.example`. | Estudiante 1 | D-3 | ⏳ | | |
| B-2 | MySQL local y configuración para TiDB. | Estudiante 1 | D-1 | ⏳ | | |
| B-3 | CORS, WhiteNoise, gunicorn y `/api/salud/`. | Estudiante 1 | B-1 | ⏳ | | |
| B-4 | Cuentas y sesiones: cuenta junto con la whitelist, cierre de sesión, vencimiento, límite de contraseñas e `id` en `/auth/yo/`. | Estudiante 1 | B-1 | ⏳ | | |
| B-5 | Fixtures de talleres y preguntas; whitelist y cuentas cargadas. | Estudiante 1 | B-2 | ⏳ | | |
| B-Q1 | Endpoint `rendir`: el servidor corrige el cuestionario, con pruebas. | Estudiante 3 | D-2 | ⏳ | | |
| B-I2 | Endpoint `impulsos` y protección de los intentos, con pruebas (incluida la invariante del borrador). | Estudiante 4 | D-2 | ⏳ | | |
| B-6 | Despliegue en Render (`build.sh`, variables, superusuario, datos). | Estudiante 1 | B-1 a B-5 | ⏳ | | |
| B-7 | README del backend con URL pública y variables. | Estudiante 1 | B-6 | ⏳ | | |
| B-8 | Lectura de estudiantes para el profesor guía y resultado de la evaluación derivado de la nota, con pruebas. | Estudiante 4 | D-2 | ⏳ | | |
| B-9 | Modelos para la estructura de talleres y los trabajos enviados a innovaciones. | Por asignar | D-2 | ⏳ | | |

### Frontend (sección 6)

| ID | Tarea | Responsable | Depende de | Estado | Rama / PR | Notas |
|---|---|---|---|---|---|---|
| F-1 | Cliente de la API (`apiClient.ts`) y sus pruebas. | Estudiante 2 | B-3 | 🔄 | `reflexIA`: `feature/cambios-validacion` | Cliente hecho, sin commit. Falta `apiClient.test.ts`. |
| F-2 | Login y sesión contra `/auth/token/` y `/auth/yo/`. | Estudiante 2 | F-1 | 🔄 | `reflexIA`: `feature/cambios-validacion` | Hecho y probado contra el backend local, sin commit. |
| F-3 | Whitelist (`whitelistService`) contra `/usuarios/`, con eliminación definitiva (CAM-24). | Estudiante 2 | F-1, B-4 | ⏳ | | |
| F-4 | Talleres y plazos contra `/talleres/`. | Estudiante 2 | F-1, B-5 | ⏳ | | |
| F-5 | Cuestionario (`theoryQuizService`) contra la API. | Estudiante 3 | F-1, B-Q1 | ⏳ | | |
| F-6 | Reflexiones e impulsos (`criticalIncidentService`). | Estudiante 4 | F-1, B-I2 | ⏳ | | |
| F-7 | Revisión docente y notas (`reflectionService`, `studentEvaluationService`). | Estudiante 4 | F-6, B-8 | ⏳ | | |
| F-8 | Innovaciones y panel de seguimiento; quitar `studentProgressService.sync()` y Firebase del proyecto. | Estudiante 4 | F-1, B-8, B-9 | ⏳ | | |
| F-9 | Despliegue en Vercel (`vercel.json`, variables) y CORS de producción. | Estudiantes 2 y 1 | B-6, F-2 a F-8 | ⏳ | | |

### Pruebas (sección 8)

| ID | Tarea | Responsable | Depende de | Estado | Rama / PR | Notas |
|---|---|---|---|---|---|---|
| P-1 | Configurar Jest y React Testing Library y migrar las pruebas de Vitest (8.2). | Estudiante 2 | D-4 | ⏳ | | |
| P-2 | Prueba de `LoginView`. | Estudiante 2 | P-1 | ⏳ | | |
| P-3 | Prueba de `TheoryQuizView`. | Estudiante 3 | P-1, F-5 | ⏳ | | |
| P-4 | Prueba de borrador e impulso en el asistente del taller. | Estudiante 4 | P-1, F-6 | ⏳ | | |
| P-5 | Prueba de `InnovationsView`. | Estudiante 4 | P-1, F-8 | ⏳ | | |
| P-6 | `docs/pruebas.md` del backend (catálogo completo). | Estudiante 1 (+ cada uno las suyas) | B-4, B-Q1, B-I2 | ⏳ | | |
| P-7 | `docs/pruebas.md` del frontend (catálogo completo). | Estudiante 2 (+ cada uno las suyas) | P-2 a P-5 | ⏳ | | |

### Carga (sección 9)

| ID | Tarea | Responsable | Depende de | Estado | Rama / PR | Notas |
|---|---|---|---|---|---|---|
| C-1 | Carpeta `carga/`, entorno virtual y cuentas de carga (local y producción). | Estudiante 3 | B-3, B-6 | ⏳ | | |
| C-2 | `locustfile.py` con los escenarios E0 a E4. | Estudiante 3 | C-1 | ⏳ | | |
| C-3 | Matriz de escenarios en **local**, con CSV y HTML guardados. | Estudiante 3 | C-2 | ⏳ | | |
| C-4 | Matriz de escenarios en **producción**, con cargas bajas. | Estudiante 3 | C-2, B-6 | ⏳ | | |
| C-5 | `docs/pruebas-de-carga.md` con resultados y análisis. | Estudiante 3 | C-3, C-4 | ⏳ | | |

### Cierre (secciones 7, 10 y 11)

| ID | Tarea | Responsable | Depende de | Estado | Rama / PR | Notas |
|---|---|---|---|---|---|---|
| X-1 | Checklist "funciona igual que en local" completo (sección 7). | Todos | F-9 | ⏳ | | |
| X-2 | READMEs de ambos repos con las URLs públicas. | Estudiantes 1 y 2 | F-9 | ⏳ | | |
| X-3 | Meta de 6 commits propios verificada (Estudiante 1). | Estudiante 1 | — | ⏳ | | |
| X-4 | Meta de 6 commits propios verificada (Estudiante 2). | Estudiante 2 | — | ⏳ | | |
| X-5 | Meta de 6 commits propios verificada (Estudiante 3). | Estudiante 3 | — | ⏳ | | |
| X-6 | Meta de 6 commits propios verificada (Estudiante 4). | Estudiante 4 | — | ⏳ | | |
| X-7 | Cada integrante ejecutó al menos una prueba de cada lado y un escenario de carga. | Todos | P-6, P-7, C-5 | ⏳ | | |
| X-8 | Recorrido de demostración ensayado desde las URLs públicas (sección 11). | Todos | X-1 | ⏳ | | |

---

## 2. Qué exige la pauta de la EVA3

Fuente: `EVA3_Instrucciones_y_Pauta.docx`. La EVA3 es la presentación final del Proyecto Integrador: el **mismo** frontend de la EVA1 y el **mismo** backend de la EVA2, ahora conectados, probados y desplegados. Los ajustes hechos para conectarlos, como dejar Firebase, son parte normal del proceso y no rompen la continuidad.

### Criterios y cómo los cubre esta guía

| Criterio | Peso | Qué se evalúa | Cómo lo cubrimos | Tareas |
|---|---|---|---|---|
| Funcionalidad y alcance | 15% | El sistema conectado funciona sin errores y mantiene lo comprometido en la EVA1 y la EVA2. | Las mismas HU, ahora contra la API. Alcance declarado en la sección 1.5. | F-2 a F-8, X-1 |
| Conexión frontend-backend | 15% | CORS configurado en el backend, URL de la API como variable de entorno (**nunca escrita en el código**) y datos reales obtenidos con `fetch`. | `django-cors-headers` (B-3), `VITE_API_URL` (F-1) y servicios sin datos fijos ni `localStorage` como fuente. | B-3, F-1 a F-8 |
| Testing en ambos lados | 15% | Conjunto completo y documentado: `TestCase` en el backend y **Jest + React Testing Library** en el frontend. El docente elige en el momento qué prueba ejecutar, de cualquiera de los dos lados. | `docs/pruebas.md` en ambos repos, con el comando de cada prueba. | P-1 a P-7 |
| Despliegue | 15% | Backend y frontend en servicios gratuitos, públicos y funcionando igual que en local. | Frontend en **Vercel**, backend en **Render** y base en TiDB (compatible con MySQL). | B-6, F-9, X-1 |
| Prueba de carga | 5% | Conjunto completo de escenarios, no uno suelto, con usuarios simulados, tiempo de respuesta y tasa de error de cada uno. El docente elige cuál ejecutar en vivo. | Locust con los escenarios E0 a E4, en local y en producción (sección 9). | C-1 a C-5 |
| Proceso en GitHub | 10% | Ambos `main` funcionales y **6 commits propios por integrante**, adicionales a los de la EVA1 y la EVA2, incrementales. | Una rama y un PR por tarea (sección 10). | X-3 a X-6 |
| Defensa oral | 25% | Cada integrante responde sobre **cualquier** parte: frontend, backend y su conexión. | Reparto cruzado (sección 3) y repaso en equipo (sección 12). | — |

**Testing y carga se califican distinto:** 100% si las pruebas están documentadas de forma completa **y** se ejecuta en vivo la que pide el docente; 50% si se cumple solo una de las dos; 0% si ninguna. En Testing, esto se aplica por separado al backend y al frontend. Los demás criterios usan Logrado (100%), Logrado parcialmente (50%) y No logrado (0%).

Nota = 1,0 + (puntaje total ÷ 100) × 6,0.

### Qué se entrega

- Los dos repositorios, accesibles para el docente **antes** de la fecha.
- Ambos `main` funcionales: son los únicos que se ejecutan ese día.
- Las URLs públicas del frontend y del backend.
- Pruebas automatizadas en ambos lados (mínimo una por lado; la pauta pide un conjunto completo y documentado).

### Cómo es la demostración (15 a 20 minutos)

| Momento | Duración | Qué ocurre |
|---|---|---|
| Alcance | 1 a 2 min | Qué se conectó, qué se probó, dónde se desplegó y qué se midió en la carga. |
| Demostración | 10 a 13 min | Se navega desde la **URL pública** (no `localhost`). Las pruebas automatizadas y de carga que elija el docente se ejecutan en vivo **desde el código de cada integrante** (`python manage.py test`, `npm test`, `locust …`). |
| Preguntas | 5 a 7 min | El docente pregunta a distintos integrantes sobre decisiones y código del proyecto completo. |

Participan todos los integrantes.

---

## 3. Arquitectura y reparto

### Arquitectura final

```
 Navegador
    │  https://reflexia.vercel.app  (React compilado)
    ▼
 ┌──────────────┐
 │   Vercel     │
 │  (frontend)  │
 └──────┬───────┘
        │ 1. POST /auth/token/  (correo + contraseña) → token
        │ 2. fetch(`${VITE_API_URL}/talleres/`, { Authorization: Token <token> })
        ▼
 ┌──────────────┐  3. valida el token y busca el correo en la whitelist → rol → permisos
 │   Render     │
 │ Django + DRF │
 │  (gunicorn)  │  4. ORM ─────────────────▶ ┌─────────────────────────┐
 └──────────────┘                             │ TiDB Cloud Starter      │
                                              │ (compatible con MySQL)  │
                                              └─────────────────────────┘
```

| Tema | Decisión | Por qué |
|---|---|---|
| **Login** | **Cuentas de Django** con token de DRF. El rol sale de la whitelist, enlazada por correo. | Es lo que ya hace la etapa 9, y evita depender de un segundo servicio. |
| **Datos** | Pasan de Firestore y `localStorage` a la **API de Django**. | El profesor guía ve los datos de todos los estudiantes, y la nota deja de calcularse en el navegador. |
| **Base de datos** | MySQL 8.4 local y TiDB Cloud Starter en producción. | Sección 1.1. |
| **Backend** | **Render** (plan gratuito), con despliegue automático desde `main`. **Decidido.** | Se conecta a GitHub y maneja las variables de entorno desde el panel. |
| **Frontend** | **Vercel** (plan gratuito), con despliegue automático desde `main`. **Decidido.** | Detecta Vite solo y maneja las variables de entorno desde el panel. |
| **Peticiones** | `fetch` nativo, con un único cliente (`src/services/apiClient.ts`). | Sin dependencias extra. El paquete `axios` queda sin uso y se puede quitar. |
| **Carga** | **Locust**, en una carpeta `carga/` del backend con su propio entorno virtual. | Así Render no instala Locust. |

### Reparto propuesto

Cada integrante trabaja en ambos lados y escribe pruebas de lo suyo, así todos pueden explicar el sistema completo. Ajústenlo como quieran.

| Integrante | Backend | Frontend | Pruebas y entrega |
|---|---|---|---|
| **Estudiante 1** (backend) | B-1 a B-7: configuración de producción, MySQL/TiDB, CORS, cuentas y sesiones, datos iniciales, despliegue en Render. | — | Pruebas de cuentas y sesiones · `docs/pruebas.md` del backend. |
| **Estudiante 2** (frontend base) | — | F-1 a F-4: cliente `apiClient.ts`, sesión, whitelist, talleres. Despliegue en Vercel. | Configuración de React Testing Library · pruebas de `apiClient.ts` y del login · `docs/pruebas.md` del frontend. |
| **Estudiante 3** (cuestionario) | B-Q1: el servidor corrige el cuestionario. | F-5: `theoryQuizService` contra la API. | Pruebas del endpoint y de la vista del cuestionario · **pruebas de carga (Locust)**. |
| **Estudiante 4** (talleres y docente) | B-I2 (impulsos e intentos) y B-8 (estudiantes para el profesor). | F-6 a F-8: reflexiones, revisión docente (retroalimentaciones y evaluaciones), innovaciones y panel de seguimiento. | Pruebas de los endpoints y de los componentes de revisión. |

Dependencias, es decir, qué tiene que estar listo antes:

```
Sección 1 (todos) ─▶ B-1..B-4 (Est. 1) ─▶ B-6 Render ─────────────────────▶ F-9 Vercel + CORS prod
                          │                                                     ▲
                          └─▶ F-1 apiClient (Est. 2) ─▶ F-2..F-8 (en paralelo) ────┘
                   B-Q1 (Est. 3) ─▶ F-5        B-I2 (Est. 4) ─▶ F-6
```

Mientras B-6 no esté listo, todos desarrollan contra el backend **local** (`http://localhost:8000/api`).

---

## 4. Orden de trabajo

| Fase | Qué | Quién |
|---|---|---|
| 0 | Sección 1: decisiones, prueba de viabilidad de TiDB y cuentas. | Todos |
| 1 | B-1 a B-4: backend listo para producción, con MySQL local. | Estudiante 1 |
| 2 | F-1: cliente de la API. B-Q1, B-I2, B-8 y B-9: cambios del backend. | Estudiantes 2, 3 y 4 |
| 3 | F-2 a F-8: cada servicio contra la API local. | Estudiantes 2, 3 y 4 |
| 4 | B-5 y B-6: datos iniciales y despliegue en Render. | Estudiante 1 |
| 5 | F-9: despliegue en Vercel y CORS de producción. | Estudiantes 2 y 1 |
| 6 | Sección 8: pruebas de ambos lados, documentadas. | Todos |
| 7 | Sección 9: pruebas de carga. | Estudiante 3 |
| 8 | Secciones 7 y 11: verificación final y ensayo. | Todos |

---

## 5. Backend: preparar para producción e integrar

Ramas sugeridas, todas desde `main` actualizado y con un Pull Request por rama: `config-produccion` (B-1 a B-4), `datos-iniciales` (B-5), `cuestionario-servidor` (B-Q1), `impulsos` (B-I2), `estudiantes-docente` (B-8), `modelos-faltantes` (B-9) y `despliegue-render` (B-6, B-7).

### B-1. Configuración por variables de entorno

```bash
pip install python-decouple
pip freeze > requirements.txt
```

`reflexIA_Proyect/settings.py`:

```python
from decouple import Csv, config

SECRET_KEY = config('DJANGO_SECRET_KEY')
DEBUG = config('DJANGO_DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('DJANGO_ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())
# Para que /admin/ funcione por HTTPS en Render (formularios con CSRF).
CSRF_TRUSTED_ORIGINS = config('DJANGO_CSRF_TRUSTED_ORIGINS', default='', cast=Csv())

# Render atiende HTTPS y reenvía a Django por HTTP: este encabezado indica el original.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
```

`.env` (no se sube) y `.env.example` (sí se sube):

```ini
DJANGO_SECRET_KEY=generar-una-con-get_random_secret_key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=
CORS_ALLOWED_ORIGINS=http://localhost:5173
DB_ENGINE=mysql
DB_NAME=reflexia
DB_USER=reflexia
DB_PASSWORD=cambiar
DB_HOST=127.0.0.1
DB_PORT=3306
DB_SSL=False
```

### B-2. MySQL (local) y TiDB (producción)

**Local, una vez por integrante.** Con MySQL 8.4 instalado, abrir MySQL Workbench o la consola `mysql -u root -p`:

```sql
CREATE DATABASE reflexia CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'reflexia'@'localhost' IDENTIFIED BY 'cambiar';
GRANT ALL PRIVILEGES ON reflexia.* TO 'reflexia'@'localhost';
-- Django crea una base "test_reflexia" para las pruebas:
GRANT ALL PRIVILEGES ON test_reflexia.* TO 'reflexia'@'localhost';
FLUSH PRIVILEGES;
```

```bash
pip install mysqlclient certifi
pip freeze > requirements.txt
```

`settings.py`:

```python
import certifi

if config('DB_ENGINE', default='mysql') == 'mysql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': config('DB_NAME'),
            'USER': config('DB_USER'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST': config('DB_HOST', default='127.0.0.1'),
            'PORT': config('DB_PORT', default='3306'),
            'OPTIONS': {'charset': 'utf8mb4'},
        }
    }
    # TiDB Cloud exige conexión cifrada (TLS).
    if config('DB_SSL', default=False, cast=bool):
        DATABASES['default']['OPTIONS']['ssl'] = {'ca': certifi.where()}
else:
    # Solo para correr las pruebas en un equipo sin MySQL (DB_ENGINE=sqlite).
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
```

La base del proyecto es **MySQL**: es el valor por defecto en local y en producción. `DB_ENGINE=sqlite` queda solo como salida para correr las pruebas en un equipo sin MySQL; la demostración y el despliegue usan MySQL. Las pruebas no dependen del motor.

**TiDB.** En el panel del cluster, botón **Connect**: copiar host, puerto (`4000`), usuario (`xxxx.root`) y contraseña. Crear la base `reflexia` desde el *SQL Editor* del panel (`CREATE DATABASE reflexia;`). Esos datos van solo en las variables de entorno de Render, con `DB_SSL=True`.

**Si `mysqlclient` no compila** (en Render aparece `mysql_config not found` o un error de `pkg-config`), cambiar al conector en Python puro:

```bash
pip uninstall mysqlclient && pip install PyMySQL && pip freeze > requirements.txt
```

```python
# reflexIA_Proyect/__init__.py
import pymysql

# Django 6.1 exige mysqlclient 2.2.1 o superior; PyMySQL se presenta como compatible.
pymysql.version_info = (2, 2, 1, 'final', 0)
pymysql.install_as_MySQLdb()
```

Después: `python manage.py migrate` y `python manage.py test`. Deben pasar las 81 pruebas actuales.

### B-3. CORS, archivos estáticos, servidor de producción y ruta de salud

```bash
pip install django-cors-headers whitenoise gunicorn
pip freeze > requirements.txt
```

`settings.py`:

```python
INSTALLED_APPS = [
    # ...
    'corsheaders',
    'rest_framework',
    # ...
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',      # justo después de Security
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',           # antes de CommonMiddleware
    'django.middleware.common.CommonMiddleware',
    # ... (el resto igual)
]

# Solo estos orígenes pueden llamar a la API desde el navegador.
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:5173', cast=Csv())

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    # Sin "Manifest" a propósito: las pruebas del admin no exigen collectstatic.
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}
```

WhiteNoise sirve el CSS del admin y de la API navegable cuando `DEBUG=False`.

**Ruta de salud pública** `GET /api/salud/`. Hoy `/api/` responde 401 sin sesión, y Render y Locust necesitan una ruta que responda 200. En `views.py`:

```python
from rest_framework.permissions import AllowAny

class SaludView(APIView):
    """GET /api/salud/: responde 200 si la API está en línea (para Render y Locust)."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'estado': 'ok'})
```

Y en `urls.py`, **antes** de la ruta comodín: `path('salud/', views.SaludView.as_view(), name='salud'),`.

### B-4. Cuentas y sesiones

El login ya existe (`POST /api/auth/token/`). Falta lo necesario para usarlo en producción.

1. **La cuenta se crea con la whitelist.** Al crear un `UsuarioAutorizado` (API o admin), crear la cuenta de Django con **nombre de usuario = correo en minúsculas** y sin contraseña utilizable. Al eliminarlo, borrar también la cuenta, para que no queden token ni contraseña antiguos si el correo se vuelve a autorizar. La revocación ya la cubre `EstaEnWhitelist`.
2. **Contraseña.** Mientras no exista la activación por correo, la define el administrador en `/admin/` → **Usuarios**. La activación (CAM-05) puede usar `default_token_generator` de Django y requiere configurar un servicio de correo.
3. **Cerrar sesión:** `POST /api/auth/salir/` borra el token. Como DRF entrega un token por usuario, cierra la sesión en todos sus equipos.
4. **Vencimiento:** el token de DRF no vence. Una subclase de `TokenAuthentication` puede rechazar los más antiguos que un plazo acordado y la vista de login debe entregar uno nuevo.
5. **Límite de intentos de contraseña:** la vista `obtain_auth_token` no tiene límite. Hay que usar una subclase de `ObtainAuthToken` con `throttle_classes`, y poder subir el límite por variable de entorno para las pruebas de carga.
6. **`GET /api/auth/yo/`** devuelve además `id` (el de `UsuarioAutorizado`).

Pruebas: crear en la whitelist crea la cuenta; eliminar la borra; después de salir el token responde 401; un token vencido responde 401; demasiados intentos responden 429; `yo` devuelve el `id`.

### B-5. Datos iniciales (fixtures)

La base nueva parte vacía. Para tener datos reales desde el primer día:

| Fixture | Contenido | De dónde sale |
|---|---|---|
| `fixtures/talleres.json` | Los 4 talleres, objetivo, actividad, producto e intentos. Títulos según CAM-12: "Identificación del incidente crítico", "Del aula a la transformación profesional", "Confrontación teórica" y "Transformación de la práctica e innovación pedagógica". | Documentos de la profesora; mientras tanto, el texto del frontend. |
| `fixtures/preguntas.json` | Las 30 preguntas con sus alternativas, la correcta y la explicación. Las actuales son de ejemplo: la profesora enviará las definitivas (CAM-08). | `QUESTION_BANK` en `reflexIA/src/services/theoryQuizService.ts`. |
| `fixtures/innovaciones.json` | Ya existe. | — |

La **whitelist** no va en un fixture: los correos reales no deben quedar en un repositorio público. Se carga a mano en `/admin/` → **Usuarios autorizados**: los integrantes y las cuentas de prueba de cada rol. Cada correo necesita además su cuenta de Django con contraseña (B-4).

```bash
python manage.py loaddata talleres preguntas innovaciones
```

### B-Q1. El servidor corrige el cuestionario (Estudiante 3)

Resuelve el primer conflicto de la sección 1.2.

Nuevo endpoint `POST /api/intentos-cuestionario/rendir/` (una `@action(detail=False, methods=['post'])` en `IntentoCuestionarioViewSet`, solo para el rol `student`):

```json
// Petición
{"respuestas": [{"pregunta": 3, "alternativa": 11}, ...], "tiempo_agotado": false}
// Respuesta 201: el intento guardado, con el mismo formato de IntentoCuestionarioSerializer
```

Reglas, idénticas a `reflexIA/src/utils/theoryQuizGrading.ts`:

0. Valida las respuestas: exactamente **10 preguntas distintas y activas**, y cada alternativa debe pertenecer a su pregunta. Sin esto, se podría enviar 10 veces la misma pregunta conocida. Si se acaba el tiempo, las preguntas sin responder se envían con `"alternativa": null` y cuentan como incorrectas.
1. Si el estudiante ya aprobó, rechaza con 400 y el mensaje "Ya aprobaste la evaluación." (equivale a `already-approved`).
2. Si ya usó 9 intentos, rechaza con 400 y el mensaje "Usaste los 9 intentos…" (equivale a `blocked`).
3. `numero_intento` = cantidad de intentos previos + 1, calculado por el servidor.
4. `respuestas_correctas` = respuestas cuya alternativa tiene `es_correcta=True`.
5. Nota por aciertos con exigencia del 60% (6 de 10 = 4,0), redondeada a un decimal y limitada por `nota_maxima` del bloque (7,0 / 5,0 / 4,0). La exigencia del 60% sigue **pendiente de confirmar** (PEND-01 de la especificación); dejarla en una constante.
6. `aprobado` si tiene 8 o más correctas. `estado='timed-out'` si `tiempo_agotado` es verdadero.

**Revisión de respuestas.** El frontend muestra, al terminar, la respuesta correcta y una explicación de cada pregunta. Agreguen el campo `explicacion` a `PreguntaTeorica` y devuelvan ese detalle en la respuesta de `rendir` (solo ahí). El equipo debe decidir si se muestra la respuesta correcta cuando aún quedan intentos.

El temporizador de 15 minutos lo controla solo el navegador. Controlarlo en el servidor exigiría registrar el inicio de cada intento; queda como evolución.

Dejen la regla en una función propia (por ejemplo, `reflexIA_App/calificacion.py`) para probarla con pruebas unitarias, igual que en el frontend. El POST normal de `/api/intentos-cuestionario/` queda solo para el superusuario: quiten `ESTUDIANTE` de `roles_creacion`.

### B-I2. Registrar los impulsos de "El Impulso" (Estudiante 4)

Resuelve el segundo conflicto de la sección 1.2.

Nuevo endpoint `POST /api/reflexiones/<id>/impulsos/` (una `@action(detail=True, methods=['post'])` en `ReflexionViewSet`, solo para el estudiante dueño):

```json
// Petición: el impulso que generó el frontend
{"propuesta_ia": "Profundiza en cómo reaccionaron los estudiantes..."}
// Respuesta 201: la retroalimentación creada (estado "pending") y los intentos usados
```

Reglas:
- Si `intentos_usados` ya es igual a `taller.intentos_maximos`, rechaza con 400 ("Ya usaste los N intentos de revisión de este taller.").
- Si no, suma 1 a `intentos_usados` y crea la `Retroalimentacion`, todo dentro de `transaction.atomic()`.
- Guardar un borrador (PATCH de la reflexión) **nunca** descuenta intentos. Es la invariante de HU-03: agréguenle una prueba.

**Sin lo siguiente, el límite no sirve:**
- `intentos_usados` pasa a ser de solo lectura en la API: solo lo cambia este endpoint.
- El estudiante no puede eliminar reflexiones (hoy `roles_edicion` incluye el borrado).
- El estudiante solo puede pasar `estado` de `draft` a `submitted`; `reviewed` queda para el profesor guía.
- Pruebas: un PATCH con `"intentos_usados": 0` no cambia el contador, y un DELETE del estudiante responde 403.

El texto del impulso lo envía el navegador, así que podría alterarse. Se acepta mientras "El Impulso" sea simulado.

### B-8. Profesor guía: estudiantes y resultado de la nota (Estudiante 4)

- `GET /api/estudiantes/`, de solo lectura y solo para el rol `teacher`: usuarios activos con rol `student`, con `id`, `correo` y `nombre`. La gestión de `/api/usuarios/` sigue siendo solo del administrador.
- `Evaluacion.resultado` se calcula a partir de la nota (`approved` desde 4,0) y deja de enviarse, para que no se contradigan. Pendiente de la etapa 7 del plan incremental.

### B-9. Datos que hoy no tienen modelo

| Dato del frontend | Hoy en | Propuesta |
|---|---|---|
| Estructura configurable de talleres (HU-09), con la pauta de respuestas privada | Firestore `workshopConfigurations` y su subcolección `private` | Campo JSON en `Taller` para el esquema y otro para la pauta, que el estudiante no recibe. |
| Trabajos enviados y su publicación en la biblioteca (`content`, `responses`, fecha, innovación publicada) | Firestore `workshopSubmissions` | Decidir si se integra en `Reflexion` o va en un modelo aparte. La nota debe saber a qué envío corresponde. |

### B-6. Despliegue en Render (Estudiante 1)

1. En el repo, crear `build.sh` en la raíz:
   ```bash
   #!/usr/bin/env bash
   set -o errexit
   pip install -r requirements.txt
   python manage.py collectstatic --no-input
   python manage.py migrate
   ```
   Si el commit se hace desde Windows, marcarlo como ejecutable con `git update-index --chmod=+x build.sh`.
2. Render → **New → Web Service** → conectar `reflexIA_BackEnd` → rama `main`.
   - Runtime: **Python 3**.
   - Build Command: `./build.sh`.
   - Start Command: `gunicorn reflexIA_Proyect.wsgi:application`.
   - Plan: **Free**.
   - Health Check Path: `/api/salud/`.
3. Variables de entorno (en **Environment**, nunca en el código):

   | Variable | Valor |
   |---|---|
   | `PYTHON_VERSION` | `3.13.1` (o la versión exacta de su `.venv`) |
   | `DJANGO_SECRET_KEY` | La clave **nueva** de la sección 1.3, distinta de la local |
   | `DJANGO_DEBUG` | `False` |
   | `DJANGO_ALLOWED_HOSTS` | `reflexia-backend.onrender.com` (el dominio que asigne Render) |
   | `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://reflexia-backend.onrender.com` |
   | `CORS_ALLOWED_ORIGINS` | `http://localhost:5173` por ahora; en F-9 se agrega la URL de Vercel |
   | `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Los de TiDB |
   | `DB_SSL` | `True` |
4. Después del primer despliegue, en **Shell** de Render: `python manage.py createsuperuser` y `python manage.py loaddata talleres preguntas innovaciones`. Si el plan gratuito no incluye Shell, corran esos comandos **desde su computador** con su `.env` apuntando a TiDB. La base es la misma.
5. Comprobar en el navegador:
   - `https://…onrender.com/api/salud/` responde `{"estado": "ok"}`;
   - `/admin/` se ve con estilos;
   - `/api/talleres/` responde 401 sin sesión.

**El plan gratuito se duerme tras 15 minutos sin tráfico** y tarda cerca de un minuto en despertar. Antes de mostrar el sistema, abran `/api/salud/` unos 2 minutos antes.

### B-7. Documentar el backend

- `README.md`: URL pública, variables de entorno y cómo correr con MySQL.
- `.env.example` actualizado.
- `docs/pruebas.md` con el catálogo de pruebas (sección 8.1).

---

## 6. Frontend: consumir la API

Ramas sugeridas: `cliente-api` (F-1), `api-sesion-whitelist` (F-2, F-3; F-1 y F-2 ya se avanzaron en `feature/cambios-validacion`), `api-talleres` (F-4), `api-cuestionario` (F-5), `api-reflexiones` (F-6, F-7), `api-innovaciones-panel` (F-8) y `despliegue-vercel` (F-9).

**Regla del frontend que hay que mantener (R4):** vistas y componentes no llaman a los servicios; solo los hooks lo hacen. Por eso basta con **cambiar el interior de cada servicio** y mantener sus firmas: hooks y componentes no se tocan, o casi no se tocan.

### F-1. Cliente de la API (Estudiante 2)

**Avanzado** en `reflexIA`, rama `feature/cambios-validacion` (sin commit):

- `src/services/apiClient.ts`: `apiRequest()` agrega `Authorization: Token <token>` y convierte `{error, mensaje, campos}` en `ApiError` (`status`, `code`, `message`, `fields`).
- `src/services/session.ts`: guarda el token y el usuario.
- `src/services/authService.ts` y `AuthContext.tsx`: login, sesión al recargar y cierre al revocar el acceso. Pruebas en `authService.test.ts`.

**Falta para cumplir la pauta** ("la URL de la API se maneja como variable de entorno, nunca escrita en el código"):

- Hoy `apiClient.ts` usa `/api` si falta la variable, y `vite.config.ts` redirige `/api` a `http://127.0.0.1:8000`. Hay que quitar ambos: que la URL salga **solo** de `VITE_API_URL` y que, si falta, la app muestre un error claro.
- Sin el proxy, el navegador llama directo al backend también en desarrollo, así que **CORS se usa y se prueba en local**, no solo en producción.
- `apiClient.test.ts`, y llamar a `/auth/salir/` al cerrar sesión cuando exista B-4.

`.env` (no se sube) y `.env.example` (sí se sube):

```ini
# Desarrollo
VITE_API_URL=http://localhost:8000/api
# Producción (en el panel de Vercel)
# VITE_API_URL=https://reflexia-backend.onrender.com/api
```

### F-2 a F-8. Servicio por servicio

| # | Servicio del frontend | Endpoint(s) | Campos que cambian de nombre (frontend → backend) | Responsable |
|---|---|---|---|---|
| F-2 | `authService` (`signInUser`, `restoreSession`) | `POST /auth/token/`, `GET /auth/yo/` (401/403 = no autorizado) | `role` → `rol` | Estudiante 2 |
| F-3 | `whitelistService` (`fetchEntries`, `addEntry`, `importEntries`, `revokeAccess`, `restoreAccess` y la eliminación nueva) | `GET/POST /usuarios/`, `PATCH/DELETE /usuarios/<id>/` | `email`→`correo`, `role`→`rol`, `status`→`estado`, `addedAt`→`fecha_registro`, `revokedAt`→`fecha_revocacion` | Estudiante 2 |
| F-4 | `workPacingService`, lista de talleres de `criticalIncidentService.fetchWorkshops` | `GET /talleres/`, `PATCH /talleres/<id>/` | `number`→`numero`, `title`→`titulo`, `deadline`→`fecha_limite`, `maxAttempts`→`intentos_maximos` | Estudiante 2 |
| F-5 | `theoryQuizService` (`fetchQuestions`, `submitAttempt`, `getApprovalStatus`, `getAttemptHistory`) | `GET /preguntas/`, `POST /intentos-cuestionario/rendir/`, `GET /intentos-cuestionario/` | `attemptNumber`→`numero_intento`, `score`→`respuestas_correctas`, `grade`→`nota`, `maxGrade`→`nota_maxima`, `status`→`estado` | Estudiante 3 |
| F-6 | `criticalIncidentService` (`getDraft`, `saveDraft`, `requestImpulse`, `getAttempts`) | `GET/POST /reflexiones/`, `PATCH /reflexiones/<id>/`, `POST /reflexiones/<id>/impulsos/` | `context`→`contexto`, `description`→`descripcion`, `actors`→`actores`, `relevance`→`relevancia` | Estudiante 4 |
| F-7 | `reflectionService`, `studentEvaluationService` (revisión docente y notas) | `GET/PATCH /retroalimentaciones/`, `GET/POST/PATCH /evaluaciones/` | `aiFeedback`→`propuesta_ia`, `grade`→`nota`, `outcome`→`resultado` | Estudiante 4 |
| F-8 | `innovationService`, `teacherDashboardService`, `studentProfileService` | `GET/POST/PATCH /innovaciones/`; el panel se arma con `GET` de `/estudiantes/` (B-8), `/intentos-cuestionario/`, `/reflexiones/` y `/evaluaciones/` | Según `InnovacionSerializer` | Estudiante 4 |

Notas:
- **`studentProgressService.sync()`** (Firestore `progress`) deja de ser necesario: el panel docente lee los datos directo de la API. Se elimina al terminar F-8.
- **Bloqueo de talleres (HU-03 → HU-04):** `useTheoryGate` sigue leyendo `getApprovalStatus()`, que ahora sale de los intentos guardados en el backend.
- **Simuladores de desarrollo** (`DevTheoryToggle`, `DevWorkshopResultToggle`): se eliminan cuando su dato llegue desde la API.
- **Revocación:** ya resuelta en F-2: la sesión se revisa cada minuto y al volver a la pestaña.
- **Eliminar definitivamente (CAM-24):** borra en cascada intentos, reflexiones y notas del estudiante. El aviso de confirmación debe decirlo.
- **Datos locales:** lo guardado en el navegador antes de dejar Firebase usaba otro identificador y ya no se muestra.
- **Firebase:** al terminar F-8, quitar `services/firebase.ts`, el paquete `firebase`, `firestore.rules` y las variables `VITE_FIREBASE_*`.
- Probar cada servicio con **la pestaña Network** del navegador: URL, código de estado y respuesta.

### F-9. Despliegue en Vercel (Estudiante 2)

1. En `reflexIA`, crear `vercel.json` para que las rutas de React Router (`/docente/plazos`, …) no respondan 404 al recargar la página:
   ```json
   { "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }] }
   ```
2. Probar el build en local antes de subir: `npm run build` y `npm run preview`.
3. Vercel → **Add New → Project** → importar `reflexIA` → Framework **Vite** (lo detecta solo):
   - Build Command: `npm run build`.
   - Output: `dist`.
4. Variables de entorno en Vercel: `VITE_API_URL=https://reflexia-backend.onrender.com/api`, y `VITE_OPENROUTER_API_KEY`.
   - Vite **incrusta** estas variables al compilar, así que cambiarlas exige volver a desplegar (**Redeploy**).
   - Todo lo que empieza con `VITE_` queda visible en el navegador: nunca pongan ahí una clave del backend.
5. **CORS en producción (Estudiante 1):** en Render, cambiar `CORS_ALLOWED_ORIGINS` a `http://localhost:5173,https://reflexia.vercel.app`. La URL va exacta, con `https://` y sin `/` al final.
6. Probar el sitio completo **desde la URL de Vercel**:
   - entrar con un usuario de cada rol;
   - comprobar que los datos cargan;
   - comprobar que los formularios guardan (POST y PATCH).

---

## 7. Checklist de "funciona igual que en local"

- [ ] `/api/salud/` responde 200 en Render.
- [ ] `/admin/` de Render tiene estilos y permite entrar con el superusuario.
- [ ] Vercel carga sin errores en la consola del navegador.
- [ ] Recargar una ruta interna (por ejemplo `/docente/plazos`) no da 404.
- [ ] No hay errores de CORS en la pestaña Network.
- [ ] El login funciona y `/auth/yo/` devuelve el rol correcto.
- [ ] Un usuario agregado desde la app puede entrar.
- [ ] El estudiante rinde el cuestionario, su nota la calcula el servidor y desbloquea el Taller 1.
- [ ] El estudiante guarda un borrador (no descuenta intentos) y pide un impulso (sí descuenta).
- [ ] El profesor ve la reflexión y el impulso, valida y pone la nota; el estudiante la ve.
- [ ] El administrador agrega y revoca correos; el revocado deja de entrar.
- [ ] Las innovaciones publicadas se ven para el estudiante.

---

## 8. Pruebas automatizadas

El objetivo es un conjunto **documentado** en ambos lados, que cualquiera del equipo pueda ejecutar completo o **de a una prueba**. Practiquen ejecutar pruebas sueltas, no solo la suite completa.

### 8.1 Backend (Django `TestCase`)

Ya hay 81 pruebas (`tests.py`, `tests_permisos.py`, `tests_errores.py`). Se suman las de B-4, B-Q1, B-I2 y B-8.

```bash
python manage.py test                                     # todas
python manage.py test reflexIA_App.tests_permisos         # un archivo
python manage.py test reflexIA_App.tests_permisos.IntentosPermisosTests                       # una clase
python manage.py test reflexIA_App.tests_permisos.IntentosPermisosTests.test_un_intento_rendido_no_se_modifica  # una prueba
python manage.py test -v 2                                # muestra el nombre de cada prueba
```

`docs/pruebas.md` del backend (responsable: Estudiante 1, y cada integrante agrega las suyas): una tabla por archivo con **prueba · tipo (unitaria o de integración) · qué verifica · comando**. Ejemplo:

| Prueba | Tipo | Qué verifica | Comando |
|---|---|---|---|
| `IntentosPermisosTests.test_estudiante_registra_sus_intentos_pero_no_los_de_otro` | Integración | Un estudiante no puede registrar intentos a nombre de otro (403). | `python manage.py test reflexIA_App.tests_permisos.IntentosPermisosTests.test_estudiante_registra_sus_intentos_pero_no_los_de_otro` |

### 8.2 Frontend (Jest + React Testing Library)

Es lo que pide la pauta (sección 1.4).

```bash
npm uninstall vitest
npm install -D jest jest-environment-jsdom ts-jest @types/jest @testing-library/react @testing-library/jest-dom @testing-library/user-event identity-obj-proxy
```

El frontend es un proyecto Vite con `"type": "module"`, y Jest no entiende `import.meta.env`. Para evitarlo:
- dejen todas las lecturas de variables en un solo archivo (`src/config/env.ts`) y reemplácenlo en las pruebas con `moduleNameMapper`;
- usen un `jest.config.cjs` (la extensión `.cjs`, por el `"type": "module"`), con `testEnvironment: 'jsdom'`, `ts-jest` y `setupFilesAfterEnv: ['<rootDir>/src/setupTests.ts']`;
- en `src/setupTests.ts`: `import '@testing-library/jest-dom'`;
- mapeen el CSS a `identity-obj-proxy`;
- cambien el script a `"test": "jest"`;
- migren las pruebas actuales: `vi.fn()` → `jest.fn()`, `vi.mock()` → `jest.mock()`, `vi.stubGlobal()` → asignar en `globalThis`.

Prueben la configuración con una prueba de componente sencilla antes de migrar todo.

Pruebas mínimas a escribir. Cada responsable escribe las de su módulo:

| Archivo | Qué prueba | Responsable |
|---|---|---|
| `src/services/apiClient.test.ts` | `apiRequest` agrega `Authorization` y convierte `{error, mensaje, campos}` en `ApiError` (con `fetch` simulado). | Estudiante 2 |
| `src/views/auth/LoginView.test.tsx` | Renderiza el formulario; un correo que no es `@ucen.cl` muestra el error (`fireEvent` o `userEvent`). | Estudiante 2 |
| `src/views/theory-verification/TheoryQuizView.test.tsx` | Con `fetch` simulado, muestra las preguntas (`findByText`) y, al enviar, la nota que devolvió la API. | Estudiante 3 |
| `src/views/critical-incidents/…test.tsx` | Guardar un borrador no cambia el contador de intentos; pedir un impulso sí lo baja. | Estudiante 4 |
| `src/views/innovations/InnovationsView.test.tsx` | Muestra las innovaciones que devuelve la API y filtra por categoría. | Estudiante 4 |

Comandos: `npm test` (todas), `npx jest src/services/apiClient.test.ts` (un archivo) y `npx jest -t "nombre de la prueba"` (una prueba). Documentar en `docs/pruebas.md` del frontend con la misma tabla que en el backend.

---

## 9. Pruebas de carga con Locust (Estudiante 3)

### Preparación

En `reflexIA_BackEnd/carga/`, con un entorno virtual propio para que Render no instale Locust:

```bash
cd carga
python -m venv .venv-carga
.\.venv-carga\Scripts\Activate.ps1
pip install locust
pip freeze > requirements-carga.txt
```

Cuentas de carga: crear en `/admin/` (local y producción) dos cuentas de Django con contraseña y su correo en la whitelist, `carga-estudiante@ucen.cl` (student) y `carga-profesor@ucen.cl` (teacher). Locust entra con `POST /api/auth/token/`, igual que el frontend. Para E4, subir el límite de intentos de contraseña (B-4) o se medirán respuestas 429. Las contraseñas van en variables de entorno (`LOCUST_PASSWORD`), nunca en el archivo.

`carga/locustfile.py`, una clase por escenario:

```python
import os
from locust import HttpUser, between, task

PASSWORD = os.environ['LOCUST_PASSWORD']


class ConToken(HttpUser):
    abstract = True
    correo = ''

    def on_start(self):
        r = self.client.post('/api/auth/token/', json={'username': self.correo, 'password': PASSWORD})
        self.client.headers['Authorization'] = f'Token {r.json()["token"]}'


class EstudianteConsulta(ConToken):
    """E1: lectura liviana, lo que más hace un estudiante."""
    wait_time = between(1, 3)
    correo = 'carga-estudiante@ucen.cl'

    @task(3)
    def talleres(self):
        self.client.get('/api/talleres/')

    @task(2)
    def preguntas(self):
        self.client.get('/api/preguntas/')

    @task(1)
    def innovaciones(self):
        self.client.get('/api/innovaciones/')


class EstudianteGuardaBorrador(ConToken):
    """E2: escritura repetida (PATCH de un borrador; no descuenta intentos)."""
    wait_time = between(2, 5)
    correo = 'carga-estudiante@ucen.cl'

    def on_start(self):
        super().on_start()
        self.reflexion = self.client.get('/api/reflexiones/').json()[0]['id']

    @task
    def guardar(self):
        self.client.patch(f'/api/reflexiones/{self.reflexion}/', json={'contexto': 'Borrador de carga'},
                          name='/api/reflexiones/[id]/')


class ProfesorRevisa(ConToken):
    """E3: listas con relaciones (select_related) que lee el panel docente."""
    wait_time = between(1, 3)
    correo = 'carga-profesor@ucen.cl'

    @task
    def revisar(self):
        self.client.get('/api/reflexiones/')
        self.client.get('/api/intentos-cuestionario/')
        self.client.get('/api/evaluaciones/')


class Login(HttpUser):
    """E4: login con contraseña (el hash de la contraseña es costoso en CPU)."""
    wait_time = between(1, 2)

    @task
    def login(self):
        self.client.post('/api/auth/token/', json={'username': 'carga-estudiante@ucen.cl', 'password': PASSWORD})


class Salud(HttpUser):
    """E0: línea base sin base de datos ni autenticación."""
    wait_time = between(1, 2)

    @task
    def salud(self):
        self.client.get('/api/salud/')
```

Antes de E2, la cuenta `carga-estudiante` debe tener al menos una reflexión creada.

### Matriz de escenarios

| Escenario | Local (`runserver`) | Producción (Render + TiDB) |
|---|---|---|
| E0 Salud | 10 · 50 · 100 usuarios | 5 · 10 · 20 |
| E1 Estudiante consulta | 10 · 50 · 100 | 5 · 10 · 20 |
| E2 Guarda borrador | 10 · 50 | 5 · 10 |
| E3 Profesor revisa | 10 · 50 | 5 · 10 |
| E4 Login | 10 · 25 | 5 |

Comando por fila (sin interfaz, guarda CSV y HTML como evidencia):

```bash
locust -f locustfile.py EstudianteConsulta --headless -u 50 -r 5 -t 1m \
       --host http://127.0.0.1:8000 \
       --csv resultados/e1_local_50 --html resultados/e1_local_50.html
```

Para mostrarlo en vivo, la interfaz web (`locust -f locustfile.py --host …`, en `http://localhost:8089`) se ve mejor.

`docs/pruebas-de-carga.md`: por cada fila, **usuarios · RPS · mediana (ms) · p95 (ms) · % de errores**, con el análisis:
- ¿Qué escenario degrada primero? Probablemente E4, por el hash de contraseñas en 0,1 CPU.
- Diferencia entre local y producción: latencia de red a TiDB y el plan gratuito.
- Cuellos de botella encontrados y qué se cambió. Por ejemplo, `select_related` ya evita consultas N+1, y la caché de claves en B-4 evita descargarlas en cada petición.

**Cuidado con la producción:**
- cargas bajas;
- despertar Render antes de medir;
- detener la prueba si el panel de Render o de TiDB marca el límite. TiDB rechaza conexiones si se agotan las *Request Units* del mes.

---

## 10. Trabajo en GitHub

- `main` de ambos repos **siempre funcional**: se despliega sola con cada merge. Antes de cada merge, corran `python manage.py test` o `npm test` y `npm run build`.
- Una rama por tarea y un PR revisado por otro integrante.
- Commits pequeños y con mensaje claro: cada avance real en su propio commit, nunca todo el trabajo de una persona en uno o dos.
- Meta de la pauta: **al menos 6 commits propios por integrante**, adicionales a los de la EVA1 y la EVA2, en ambos repos sumados. Cada uno revisa su conteo en ambos repos, contando desde el inicio de la etapa (ajusten la fecha):
  ```bash
  git shortlog -sn --since=2026-11-17 main
  ```
- Cada integrante hace sus commits con **su** cuenta. Los commits hechos desde la cuenta de otro no cuentan como propios.

---

## 11. Checklist antes de presentar el sistema

- [ ] Ambos repositorios accesibles para el docente **antes** de la fecha.
- [ ] Las URLs de Vercel y Render responden sin depender de `localhost`. Quedan en ambos README.
- [ ] Ambos `main` actualizados, con las pruebas pasando.
- [ ] Cada integrante practicó ejecutar **cualquier** prueba de backend y de frontend, y **cualquier** escenario de Locust, no solo las más fáciles.
- [ ] El alcance que se declarará al inicio está acordado (qué se conectó, qué se probó, dónde se desplegó y qué se midió).
- [ ] `docs/pruebas.md` (en ambos repos) y `docs/pruebas-de-carga.md`, con resultados guardados.
- [ ] Meta de commits por integrante, verificada.
- [ ] Cuentas de demostración de los 3 roles listas, con contraseñas a mano.
- [ ] Recorrido de demostración ensayado, siempre desde las URLs públicas:
  1. Alcance: qué se conectó, dónde se desplegó, qué se midió, y lo que queda fuera de la API (sección 1.5).
  2. Navegación:
     - estudiante: cuestionario → taller → impulso;
     - profesor: revisión → nota;
     - administrador: whitelist;
     - estudiante: ve su nota.
  3. Ejecución en vivo de pruebas y de un escenario de carga.
- [ ] Despertar Render **2 minutos antes**.

---

## 12. Preguntas para repasar en equipo

Todos deberían poder explicar **todo** el sistema. Repasen juntos:

- **Conexión:** ¿qué es CORS y por qué el error sale en el navegador y no en Django? ¿Dónde está configurado? ¿Por qué `VITE_API_URL` es una variable de entorno y cuándo se incrusta?
- **Autenticación:** ¿cómo sabe el backend quién es el usuario a partir del token? ¿Qué decide `EstaEnWhitelist` y qué `PermisoPorRol`? ¿Por qué un estudiante recibe 404 y no 403 al pedir el registro de otro?
- **Reglas en el servidor:** ¿por qué el estudiante no recibe `es_correcta`? ¿Dónde se calcula la nota del cuestionario y por qué ahí?
- **Despliegue:** ¿por qué `DEBUG=False` en producción? ¿Qué hacen `ALLOWED_HOSTS`, `SECRET_KEY`, gunicorn y WhiteNoise? ¿Por qué TiDB y no SQLite?
- **Testing:** diferencia entre prueba unitaria y de integración, con un ejemplo propio de cada lado. ¿Qué es un mock de `fetch`?
- **Carga:** ¿qué es RPS, la latencia p95 y la tasa de error? ¿Qué escenario degradó primero y por qué?
- **Frontend:** regla R4 (vistas → hooks → servicios). ¿Por qué cambiar los servicios no obligó a cambiar los componentes?

---

## 13. Riesgos y planes B

| Riesgo | Señal | Plan B |
|---|---|---|
| TiDB incompatible con Django 6.1 | Falla `migrate` en la prueba de viabilidad. | Sección 1.1: Django 5.2 + `django-tidb` → MySQL pagado o PostgreSQL. El backend sigue en Render. |
| `mysqlclient` no compila en Render | Build falla con `mysql_config` o `pkg-config`. | PyMySQL (B-2). |
| Render dormido al mostrar el sistema | La primera carga tarda unos 50 s. | Abrir `/api/salud/` 2 minutos antes. |
| Error de CORS en producción | "blocked by CORS policy" en la consola. | Revisar que `CORS_ALLOWED_ORIGINS` tenga la URL exacta de Vercel, sin `/` final. |
| Nadie puede entrar en producción | `/auth/token/` responde 400. | Comprobar que la cuenta de Django existe, que su nombre de usuario es el correo en minúsculas y que tiene contraseña. |
| Cuota de TiDB agotada | Conexiones rechazadas. | Cargas bajas contra producción; las pruebas grandes, en local. |
| Recarga de ruta da 404 en Vercel | 404 en `/docente/...`. | `vercel.json` con *rewrites* (F-9). |

---

## Fuentes (verificadas el 24-11-2026)

- PythonAnywhere, [funciones de las cuentas gratuitas](https://help.pythonanywhere.com/pages/FreeAccountsFeatures/) y [cambios en las cuentas gratuitas](https://blog.pythonanywhere.com/221/).
- Aiven, [el MySQL gratuito fue retirado](https://aiven.io/free-mysql-database).
- TiDB Cloud, [planes](https://docs.pingcap.com/tidbcloud/select-cluster-tier/) y [límites de Starter](https://docs.pingcap.com/tidbcloud/serverless-limitations/); [django-tidb](https://github.com/pingcap/django-tidb).
- Render, [plataformas con plan gratuito en 2026](https://render.com/articles/platforms-with-a-real-free-tier-for-developers-in-2026) (el plan gratuito se duerme a los 15 minutos).
