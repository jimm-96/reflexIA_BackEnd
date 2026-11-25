# Integración y despliegue de ReflexIA

Guía interna del equipo para conectar el frontend (`reflexIA`, React) con el backend (`reflexIA_BackEnd`, Django), probarlos, desplegarlos y medir su carga.

Está ordenada por prioridad. Primero lo que hay que **decidir o resolver antes de escribir código** (sección 1); luego el [tablero de avance](#tablero-de-avance), que cada integrante actualiza a medida que avanza; y después, los pasos en el orden en que dependen unos de otros.

> Las plataformas gratuitas cambian seguido. Lo que dice esta guía sobre planes gratuitos se verificó el **24-11-2026** (fuentes al final). Revísenlo de nuevo al crear las cuentas.

---

## 1. Antes de empezar: problemas y decisiones

Resuelvan estos puntos en este orden. Los primeros bloquean a todos los demás. Su estado se lleva en el [tablero de avance](#tablero-de-avance).

| # | Tema | Qué hay que hacer | Bloquea a | En el tablero |
|---|---|---|---|---|
| 1.1 | Base de datos MySQL en producción | Elegir dónde alojarla y probar que Django funcione con ella. | Todo el backend en producción | D-1 |
| 1.2 | Ajustes del backend para integrar | Agregar dos endpoints que el frontend necesita: corregir el cuestionario e impulsos. | Cuestionario y talleres en el frontend | D-2 |
| 1.3 | `SECRET_KEY` expuesta | Generar una nueva para producción, fuera del código. | Despliegue del backend | D-3 |
| 1.4 | Herramienta de pruebas del frontend | Elegir entre Jest y Vitest, ambos con React Testing Library. | Pruebas del frontend | D-4 |
| 1.5 | Alcance de la integración | Acordar qué pasa a la API y qué se queda en Firebase. | Reparto del frontend | D-5 |
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
- Si falla, anoten el error y pasen a las alternativas, en este orden:
  1. Si **algún integrante tiene una cuenta de PythonAnywhere creada antes del 15-01-2026**, esa cuenta trae MySQL gratuito. En ese caso el backend se despliega allí (sin despliegue automático: `git pull` y "Reload") y Render se descarta.
  2. Bajar el backend a **Django 5.2 LTS** (soportado hasta abril de 2028) y usar `django-tidb` de la versión correspondiente.
  3. Pagar MySQL administrado (el plan Developer de Aiven cuesta unos USD 5 al mes) o usar PostgreSQL gratuito (por ejemplo, Neon). Esta última opción deja de ser MySQL, así que tendrían que decidirlo como equipo.

> **No usen XAMPP para el MySQL local.** Trae MariaDB 10.4, más antiguo que la versión mínima que exige Django 6.1. Instalen **MySQL Community Server 8.4 LTS** (incluye MySQL Workbench) o usen Docker.

### 1.2 Ajustes del backend que la integración necesita

Al cruzar los servicios del frontend con los permisos del backend aparecen dos conflictos. Sin resolverlos, el frontend no puede funcionar contra la API:

| Conflicto | Por qué pasa | Solución | Detalle |
|---|---|---|---|
| **El frontend no puede corregir el cuestionario** | Desde la etapa 9, el estudiante no recibe `es_correcta`, para no ver las respuestas antes de rendir. Sin ellas, el navegador no puede calcular la nota. | El servidor corrige: `POST /api/intentos-cuestionario/rendir/`. Además, la nota deja de ser manipulable desde el navegador. | B-Q1 |
| **El estudiante no puede guardar sus impulsos** | "El Impulso" se genera en el frontend, pero en el backend solo el profesor puede crear retroalimentaciones. | Endpoint `POST /api/reflexiones/<id>/impulsos/`: guarda el impulso y descuenta el intento en el servidor. | B-I2 |

### 1.3 `SECRET_KEY` expuesta

La clave actual está escrita en `reflexIA_Proyect/settings.py`. Como el repositorio es público, ya quedó en el historial de GitHub y no sirve para producción. Hay que generar una clave nueva y leerla desde una variable de entorno (B-1):

```bash
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

### 1.4 Herramienta de pruebas del frontend

El frontend ya usa **Vitest** (`npm test` → `vitest run`), con 3 archivos de prueba de lógica. La alternativa es **Jest**. Las dos se usan junto con **React Testing Library** para probar componentes, y su API es casi igual (`describe`, `it`, `expect`, `vi.fn()` ≈ `jest.fn()`).

| | Vitest | Jest |
|---|---|---|
| Configuración en un proyecto Vite | Mínima: lee `vite.config.ts`. | Más trabajo: no entiende `import.meta.env` y necesita `ts-jest`. |
| Pruebas actuales | Ya funcionan. | Hay que cambiar `vi.fn()` por `jest.fn()`. |
| Cuándo elegirla | Si no hay un motivo para usar Jest. | Si el equipo necesita Jest en particular. |

Las dos configuraciones están en la sección 8.2. Decídanlo antes de escribir pruebas de componentes, para no tener que migrarlas después.

### 1.5 Alcance de la integración

Un sistema acotado pero bien conectado vale más que uno grande a medio integrar. Propuesta de qué queda **fuera** de la API:

| Funcionalidad | Dónde queda | Motivo |
|---|---|---|
| Inicio de sesión (correo y contraseña) | Firebase Authentication | Ya funciona; el backend verifica el token (B-4). |
| Detección de datos sensibles (HU-05) | Frontend → OpenRouter | No hay recurso de backend; queda como evolución (GAP-06). |
| Estructura configurable de talleres (HU-09, `workshopConfigurations`) | Firestore | `Taller` no guarda el esquema de formularios. Si sobra tiempo, se agrega un campo JSON. |
| Generación de "El Impulso" | Frontend (`impulseGenerator`, simulado) | La IA real es evolución (GAP-07). El impulso **sí se guarda** en el backend (B-I2). |

Todo lo demás pasa a la API (sección 6).

### 1.6 Cuentas, accesos y reparto

1. **Cuentas.** Que cada servicio tenga un dueño y que el resto quede invitado:
   - GitHub: los 4 integrantes con acceso de escritura a **ambos** repos.
   - [TiDB Cloud](https://tidbcloud.com) (dueño: Estudiante 1). Crear un cluster **Starter** en la región AWS más cercana.
   - [Render](https://render.com) (dueño: Estudiante 1) y [Vercel](https://vercel.com) (dueño: Estudiante 2), ambos con login de GitHub.
   - Consola de Firebase del proyecto actual: todos con acceso, para ver usuarios y el *Project ID*.
2. **Reparto:** sección 3.

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
| D-2 | Acordar los dos endpoints nuevos del backend (1.2). | Todos | — | ⏳ | | |
| D-3 | Generar la `SECRET_KEY` de producción (1.3). | Estudiante 1 | — | ⏳ | | |
| D-4 | Elegir Vitest o Jest para el frontend (1.4). | Todos | — | ⏳ | | |
| D-5 | Acordar el alcance: qué queda fuera de la API (1.5). | Todos | — | ⏳ | | |
| D-6 | Crear cuentas (TiDB, Render, Vercel), dar accesos y confirmar el reparto (1.6). | Todos | — | ⏳ | | |

### Backend (sección 5)

| ID | Tarea | Responsable | Depende de | Estado | Rama / PR | Notas |
|---|---|---|---|---|---|---|
| B-1 | Configuración por variables de entorno y `.env.example`. | Estudiante 1 | D-3 | ⏳ | | |
| B-2 | MySQL local y configuración para TiDB. | Estudiante 1 | D-1 | ⏳ | | |
| B-3 | CORS, WhiteNoise, gunicorn y `/api/salud/`. | Estudiante 1 | B-1 | ⏳ | | |
| B-4 | `FirebaseAuthentication` y sus pruebas (`tests_firebase.py`). | Estudiante 1 | B-1 | ⏳ | | |
| B-5 | Fixtures de talleres y preguntas; whitelist cargada. | Estudiante 1 | B-2 | ⏳ | | |
| B-Q1 | Endpoint `rendir`: el servidor corrige el cuestionario, con pruebas. | Estudiante 3 | D-2 | ⏳ | | |
| B-I2 | Endpoint `impulsos`, con pruebas (incluida la invariante del borrador). | Estudiante 4 | D-2 | ⏳ | | |
| B-6 | Despliegue en Render (`build.sh`, variables, superusuario, datos). | Estudiante 1 | B-1 a B-5 | ⏳ | | |
| B-7 | README del backend con URL pública y variables. | Estudiante 1 | B-6 | ⏳ | | |

### Frontend (sección 6)

| ID | Tarea | Responsable | Depende de | Estado | Rama / PR | Notas |
|---|---|---|---|---|---|---|
| F-1 | `api.ts`, `VITE_API_URL` y pruebas de `api.ts`. | Estudiante 2 | B-3, B-4 | ⏳ | | |
| F-2 | Sesión: `verifyUserAccess` y `checkAccess` contra `/auth/yo/`. | Estudiante 2 | F-1 | ⏳ | | |
| F-3 | Whitelist (`whitelistService`) contra `/usuarios/`. | Estudiante 2 | F-1 | ⏳ | | |
| F-4 | Talleres y plazos contra `/talleres/`. | Estudiante 2 | F-1, B-5 | ⏳ | | |
| F-5 | Cuestionario (`theoryQuizService`) contra la API. | Estudiante 3 | F-1, B-Q1 | ⏳ | | |
| F-6 | Reflexiones e impulsos (`criticalIncidentService`). | Estudiante 4 | F-1, B-I2 | ⏳ | | |
| F-7 | Revisión docente y notas (`reflectionService`, `studentEvaluationService`). | Estudiante 4 | F-6 | ⏳ | | |
| F-8 | Innovaciones y panel de seguimiento; quitar `studentProgressService.sync()`. | Estudiante 4 | F-1 | ⏳ | | |
| F-9 | Despliegue en Vercel (`vercel.json`, variables, dominio en Firebase) y CORS de producción. | Estudiantes 2 y 1 | B-6, F-2 a F-8 | ⏳ | | |

### Pruebas (sección 8)

| ID | Tarea | Responsable | Depende de | Estado | Rama / PR | Notas |
|---|---|---|---|---|---|---|
| P-1 | Configurar React Testing Library con la herramienta elegida (8.2). | Estudiante 2 | D-4 | ⏳ | | |
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

## 2. Objetivos del sistema integrado

| Objetivo | Qué significa en la práctica | Sección |
|---|---|---|
| Sistema conectado | El frontend muestra datos reales del backend, obtenidos con `fetch`, en vez de datos fijos o de `localStorage`. | 6 |
| Conexión bien configurada | CORS autoriza solo al frontend, y la URL de la API vive en una variable de entorno, nunca escrita en el código. | 5 (B-3), 6 (F-1) |
| Pruebas automatizadas | Un conjunto documentado en el backend (`TestCase`) y en el frontend (React Testing Library), que cualquiera del equipo puede ejecutar en cualquier momento, completo o una prueba suelta. | 8 |
| Despliegue | Backend y frontend en servicios gratuitos, con URL pública, funcionando igual que en local. | 5 (B-6), 6 (F-9), 7 |
| Pruebas de carga | Varios escenarios documentados con Locust, con sus resultados guardados (usuarios, tiempo de respuesta, tasa de error). | 9 |
| Trabajo en GitHub | Ambas ramas `main` siempre funcionales, y cada integrante con al menos 6 commits propios e incrementales en esta etapa. | 10 |
| Dominio del proyecto | Cada integrante puede explicar cualquier parte: frontend, backend y su conexión. | 12 |

---

## 3. Arquitectura y reparto

### Arquitectura final

```
 Navegador
    │  https://reflexia.vercel.app  (React compilado)
    ▼
 ┌──────────────┐  1. login (correo + contraseña)  ┌───────────────────────┐
 │   Vercel     │ ───────────────────────────────▶ │ Firebase Authentication│
 │  (frontend)  │ ◀─────── ID token (JWT) ──────── └───────────────────────┘
 └──────┬───────┘
        │ 2. fetch(`${VITE_API_URL}/talleres/`, { Authorization: Bearer <ID token> })
        ▼
 ┌──────────────┐  3. verifica el token con las claves públicas de Google
 │   Render     │  4. busca el correo en la whitelist → rol → permisos
 │ Django + DRF │
 │  (gunicorn)  │  5. ORM ─────────────────▶ ┌─────────────────────────┐
 └──────────────┘                             │ TiDB Cloud Starter      │
                                              │ (compatible con MySQL)  │
                                              └─────────────────────────┘
```

| Tema | Decisión | Por qué |
|---|---|---|
| **Login** | Se mantiene **Firebase Authentication** en el frontend. El backend verifica el ID token y saca el rol de su propia whitelist. | Ya funciona y no hay que migrar contraseñas. Es lo decidido en la etapa 9 (`docs/autenticacion-y-permisos.md`): los permisos no cambian, solo se agrega una forma más de autenticarse. |
| **Datos** | Pasan de Firestore y `localStorage` a la **API de Django**. | El profesor guía ve los datos de todos los estudiantes, y la nota deja de calcularse en el navegador. |
| **Base de datos** | MySQL 8.4 local y TiDB Cloud Starter en producción. | Sección 1.1. |
| **Backend** | **Render** (plan gratuito), con despliegue automático desde `main`. | Se conecta a GitHub y maneja las variables de entorno desde el panel. |
| **Frontend** | **Vercel** (plan gratuito), con despliegue automático desde `main`. | Detecta Vite solo y maneja las variables de entorno desde el panel. |
| **Peticiones** | `fetch` nativo, con un único cliente (`src/services/api.ts`). | Sin dependencias extra. El paquete `axios` queda sin uso y se puede quitar. |
| **Carga** | **Locust**, en una carpeta `carga/` del backend con su propio entorno virtual. | Así Render no instala Locust. |

### Reparto propuesto

Cada integrante trabaja en ambos lados y escribe pruebas de lo suyo, así todos pueden explicar el sistema completo. Ajústenlo como quieran.

| Integrante | Backend | Frontend | Pruebas y entrega |
|---|---|---|---|
| **Estudiante 1** (backend) | B-1 a B-7: configuración de producción, MySQL/TiDB, CORS, autenticación con Firebase, datos iniciales, despliegue en Render. | — | Pruebas de `FirebaseAuthentication` · `docs/pruebas.md` del backend. |
| **Estudiante 2** (frontend base) | — | F-1 a F-4: cliente `api.ts`, `VITE_API_URL`, sesión (`/auth/yo/`), whitelist, talleres. Despliegue en Vercel. | Configuración de React Testing Library · pruebas de `api.ts` y del login · `docs/pruebas.md` del frontend. |
| **Estudiante 3** (cuestionario) | B-Q1: el servidor corrige el cuestionario. | F-5: `theoryQuizService` contra la API. | Pruebas del endpoint y de la vista del cuestionario · **pruebas de carga (Locust)**. |
| **Estudiante 4** (talleres y docente) | B-I2: endpoint para registrar impulsos. | F-6 a F-8: reflexiones, revisión docente (retroalimentaciones y evaluaciones), innovaciones y panel de seguimiento. | Pruebas del endpoint y de los componentes de revisión. |

Dependencias, es decir, qué tiene que estar listo antes:

```
Sección 1 (todos) ─▶ B-1..B-4 (Est. 1) ─▶ B-6 Render ─────────────────────▶ F-9 Vercel + CORS prod
                          │                                                     ▲
                          └─▶ F-1 api.ts (Est. 2) ─▶ F-2..F-8 (en paralelo) ────┘
                   B-Q1 (Est. 3) ─▶ F-5        B-I2 (Est. 4) ─▶ F-6
```

Mientras B-6 no esté listo, todos desarrollan contra el backend **local** (`http://localhost:8000/api`).

---

## 4. Orden de trabajo

| Fase | Qué | Quién |
|---|---|---|
| 0 | Sección 1: decisiones, prueba de viabilidad de TiDB y cuentas. | Todos |
| 1 | B-1 a B-4: backend listo para producción, con MySQL local. | Estudiante 1 |
| 2 | F-1: cliente de la API. B-Q1 y B-I2: endpoints nuevos. | Estudiantes 2, 3 y 4 |
| 3 | F-2 a F-8: cada servicio contra la API local. | Estudiantes 2, 3 y 4 |
| 4 | B-5 y B-6: datos iniciales y despliegue en Render. | Estudiante 1 |
| 5 | F-9: despliegue en Vercel y CORS de producción. | Estudiantes 2 y 1 |
| 6 | Sección 8: pruebas de ambos lados, documentadas. | Todos |
| 7 | Sección 9: pruebas de carga. | Estudiante 3 |
| 8 | Secciones 7 y 11: verificación final y ensayo. | Todos |

---

## 5. Backend: preparar para producción e integrar

Ramas sugeridas, todas desde `main` actualizado y con un Pull Request por rama: `config-produccion` (B-1 a B-4), `datos-iniciales` (B-5), `cuestionario-servidor` (B-Q1), `impulsos` (B-I2) y `despliegue-render` (B-6, B-7).

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
FIREBASE_PROJECT_ID=el-project-id-de-firebase
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

if config('DB_ENGINE', default='sqlite') == 'mysql':
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
    # Sin MySQL instalado (o para correr las pruebas rápido), se usa SQLite.
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
```

El interruptor `DB_ENGINE` sirve para que un integrante sin MySQL pueda correr las pruebas (`DB_ENGINE=sqlite`). Las pruebas no dependen del motor.

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

### B-4. Autenticación con el token de Firebase

El frontend enviará `Authorization: Bearer <ID token de Firebase>`. El backend comprueba la firma con las claves públicas de Google, que no necesitan credenciales secretas, y obtiene el correo del token.

```bash
pip install google-auth requests CacheControl
pip freeze > requirements.txt
```

Nuevo `reflexIA_App/authentication.py`:

```python
"""
Autenticación con el ID token de Firebase (Authorization: Bearer <token>).

El frontend inicia sesión con Firebase y envía el token en cada petición.
Aquí se verifica la firma con las claves públicas de Google y se toma el
correo. El rol y los permisos los siguen decidiendo permissions.py y la
whitelist.
"""
import cachecontrol
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

# Guarda en caché las claves públicas de Google: sin esto, cada petición las
# descargaría de nuevo (se nota en las pruebas de carga).
_peticion_google = google_requests.Request(session=cachecontrol.CacheControl(requests.session()))


class FirebaseAuthentication(BaseAuthentication):
    palabra_clave = 'Bearer'

    def authenticate(self, request):
        partes = get_authorization_header(request).split()
        if not partes or partes[0].decode().lower() != self.palabra_clave.lower():
            return None  # No es un token de Firebase: que lo intente otra clase.
        if len(partes) != 2:
            raise AuthenticationFailed('El encabezado Authorization no tiene el formato "Bearer <token>".')

        proyecto = settings.FIREBASE_PROJECT_ID
        try:
            datos = id_token.verify_firebase_token(partes[1].decode(), _peticion_google, audience=proyecto)
        except ValueError:
            raise AuthenticationFailed('El token de Firebase no es válido o expiró.')
        if datos.get('iss') != f'https://securetoken.google.com/{proyecto}':
            raise AuthenticationFailed('El token no pertenece a este proyecto de Firebase.')

        correo = (datos.get('email') or '').strip().lower()
        if not correo:
            raise AuthenticationFailed('El token no trae un correo.')

        # Una cuenta de Django "sombra" por correo, sin contraseña. Los permisos
        # la enlazan con la whitelist por el correo (permissions.py).
        usuario, creado = get_user_model().objects.get_or_create(username=correo, defaults={'email': correo})
        if creado:
            usuario.set_unusable_password()
            usuario.save()
        return usuario, datos

    def authenticate_header(self, request):
        return self.palabra_clave
```

`settings.py`:

```python
FIREBASE_PROJECT_ID = config('FIREBASE_PROJECT_ID')

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'reflexIA_App.authentication.FirebaseAuthentication',  # frontend
        'rest_framework.authentication.TokenAuthentication',   # Locust y pruebas manuales
        'rest_framework.authentication.SessionAuthentication', # admin y API navegable
    ],
    # ... (permisos y EXCEPTION_HANDLER igual que hoy)
}
```

Pruebas en `reflexIA_App/tests_firebase.py`: simular la verificación con `unittest.mock.patch('reflexIA_App.authentication.id_token.verify_firebase_token', return_value={...})` y comprobar cuatro casos:
- un token válido con correo de la whitelist responde 200;
- un correo fuera de la whitelist responde 403;
- un token inválido (el mock lanza `ValueError`) responde 401;
- un emisor (`iss`) de otro proyecto responde 401.

### B-5. Datos iniciales (fixtures)

La base nueva parte vacía. Para tener datos reales desde el primer día:

| Fixture | Contenido | De dónde sale |
|---|---|---|
| `fixtures/talleres.json` | Los 4 talleres con sus títulos oficiales (RF-03), objetivo, actividad, producto e intentos. | `docs/plan-incremental.md` (etapa 2) y el texto de los talleres del frontend. |
| `fixtures/preguntas.json` | Las 30 preguntas del marco teórico con sus alternativas y la correcta. | `QUESTION_BANK` en `reflexIA/src/services/theoryQuizService.ts`. Conviene un script de un solo uso que lo convierta a JSON. |
| `fixtures/innovaciones.json` | Ya existe. | — |

La **whitelist** no va en un fixture: los correos reales no deben quedar en un repositorio público. Se carga a mano en `/admin/` → **Usuarios autorizados**: los integrantes y las cuentas de prueba de cada rol. Los correos deben ser los mismos que usan para entrar en Firebase.

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

1. Si el estudiante ya aprobó, rechaza con 400 y el mensaje "Ya aprobaste la evaluación." (equivale a `already-approved`).
2. Si ya usó 9 intentos, rechaza con 400 y el mensaje "Usaste los 9 intentos…" (equivale a `blocked`).
3. `numero_intento` = cantidad de intentos previos + 1, calculado por el servidor.
4. `respuestas_correctas` = respuestas cuya alternativa tiene `es_correcta=True`.
5. Nota por aciertos con exigencia del 60% (6 de 10 = 4,0), redondeada a un decimal y limitada por `nota_maxima` del bloque (7,0 / 5,0 / 4,0).
6. `aprobado` si tiene 8 o más correctas. `estado='timed-out'` si `tiempo_agotado` es verdadero.

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
   | `FIREBASE_PROJECT_ID` | El *Project ID* de Firebase |
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

Ramas sugeridas: `cliente-api` (F-1), `api-sesion-whitelist` (F-2, F-3), `api-talleres` (F-4), `api-cuestionario` (F-5), `api-reflexiones` (F-6, F-7), `api-innovaciones-panel` (F-8) y `despliegue-vercel` (F-9).

**Regla del frontend que hay que mantener (R4):** vistas y componentes no llaman a los servicios; solo los hooks lo hacen. Por eso basta con **cambiar el interior de cada servicio** y mantener sus firmas: hooks y componentes no se tocan, o casi no se tocan.

### F-1. Cliente de la API y variable de entorno (Estudiante 2)

`.env` y `.env.example`:

```ini
VITE_API_URL=http://localhost:8000/api
```

Nuevo `src/services/api.ts`:

```ts
/**
 * Cliente único de la API de ReflexIA.
 *
 * - Toma la URL base de VITE_API_URL (nunca escrita en el código).
 * - Agrega el ID token de Firebase de la sesión actual.
 * - Convierte las respuestas de error del backend ({error, mensaje, campos})
 *   en un ApiError que los hooks pueden mostrar.
 */
import { firebaseAuth } from './firebase'

const API_URL = import.meta.env.VITE_API_URL

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly codigo: string,
    message: string,
    readonly campos: Record<string, string[]> = {},
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export async function apiFetch<T>(ruta: string, opciones: RequestInit = {}): Promise<T> {
  const token = await firebaseAuth?.currentUser?.getIdToken()

  let respuesta: Response
  try {
    respuesta = await fetch(`${API_URL}${ruta}`, {
      ...opciones,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...opciones.headers,
      },
    })
  } catch {
    throw new ApiError(0, 'sin_conexion', 'No se pudo conectar con el servidor. Revisa tu conexión.')
  }

  if (respuesta.status === 204) return undefined as T
  const datos = await respuesta.json().catch(() => null)
  if (!respuesta.ok) {
    throw new ApiError(
      respuesta.status,
      datos?.error ?? 'error',
      datos?.mensaje ?? 'Ocurrió un error inesperado.',
      datos?.campos ?? {},
    )
  }
  return datos as T
}
```

El backend usa nombres en español y snake_case (`fecha_registro`); el frontend, en inglés y camelCase (`addedAt`). Cada servicio convierte en un solo lugar, con funciones `desdeApi()` y `haciaApi()`. Así los modelos del frontend no cambian.

### F-2 a F-8. Servicio por servicio

| # | Servicio del frontend | Endpoint(s) | Campos que cambian de nombre (frontend → backend) | Responsable |
|---|---|---|---|---|
| F-2 | `authService.verifyUserAccess`, `whitelistService.checkAccess` | `GET /auth/yo/` (401/403 = no autorizado) | `role` → `rol` | Estudiante 2 |
| F-3 | `whitelistService` (`fetchEntries`, `addEntry`, `importEntries`, `revokeAccess`, `restoreAccess`) | `GET/POST /usuarios/`, `PATCH /usuarios/<id>/` | `email`→`correo`, `role`→`rol`, `status`→`estado`, `addedAt`→`fecha_registro`, `revokedAt`→`fecha_revocacion` | Estudiante 2 |
| F-4 | `workPacingService`, lista de talleres de `criticalIncidentService.fetchWorkshops` | `GET /talleres/`, `PATCH /talleres/<id>/` | `number`→`numero`, `title`→`titulo`, `deadline`→`fecha_limite`, `maxAttempts`→`intentos_maximos` | Estudiante 2 |
| F-5 | `theoryQuizService` (`fetchQuestions`, `submitAttempt`, `getApprovalStatus`, `getAttemptHistory`) | `GET /preguntas/`, `POST /intentos-cuestionario/rendir/`, `GET /intentos-cuestionario/` | `attemptNumber`→`numero_intento`, `score`→`respuestas_correctas`, `grade`→`nota`, `maxGrade`→`nota_maxima`, `status`→`estado` | Estudiante 3 |
| F-6 | `criticalIncidentService` (`getDraft`, `saveDraft`, `requestImpulse`, `getAttempts`) | `GET/POST /reflexiones/`, `PATCH /reflexiones/<id>/`, `POST /reflexiones/<id>/impulsos/` | `context`→`contexto`, `description`→`descripcion`, `actors`→`actores`, `relevance`→`relevancia` | Estudiante 4 |
| F-7 | `reflectionService`, `studentEvaluationService` (revisión docente y notas) | `GET/PATCH /retroalimentaciones/`, `GET/POST/PATCH /evaluaciones/` | `aiFeedback`→`propuesta_ia`, `grade`→`nota`, `outcome`→`resultado` | Estudiante 4 |
| F-8 | `innovationService`, `teacherDashboardService`, `studentProfileService` | `GET/POST/PATCH /innovaciones/`; el panel se arma con `GET` de `/usuarios/`, `/intentos-cuestionario/`, `/reflexiones/` y `/evaluaciones/` | Según `InnovacionSerializer` | Estudiante 4 |

Notas:
- **`studentProgressService.sync()`** (Firestore `progress`) deja de ser necesario: el panel docente lee los datos directo de la API. Se elimina al terminar F-8.
- **Bloqueo de talleres (HU-03 → HU-04):** `useTheoryGate` sigue leyendo `getApprovalStatus()`, que ahora sale de los intentos guardados en el backend.
- **Simuladores de desarrollo** (`DevTheoryToggle`, `DevWorkshopResultToggle`): se eliminan cuando su dato llegue desde la API.
- **Revocación en tiempo real:** `whitelistService.watchAccess` usaba `onSnapshot` de Firestore. Con la API, basta con que la respuesta 403 de cualquier petición cierre la sesión.
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
4. Variables de entorno en Vercel: `VITE_API_URL=https://reflexia-backend.onrender.com/api`, las 6 `VITE_FIREBASE_*` y `VITE_OPENROUTER_API_KEY`.
   - Vite **incrusta** estas variables al compilar, así que cambiarlas exige volver a desplegar (**Redeploy**).
   - Todo lo que empieza con `VITE_` queda visible en el navegador: nunca pongan ahí una clave del backend.
5. **CORS en producción (Estudiante 1):** en Render, cambiar `CORS_ALLOWED_ORIGINS` a `http://localhost:5173,https://reflexia.vercel.app`. La URL va exacta, con `https://` y sin `/` al final.
6. **Firebase:** en *Authentication → Settings → Authorized domains*, agregar el dominio de Vercel (`reflexia.vercel.app`). Si falta, Firebase puede rechazar el login con `auth/unauthorized-domain`.
7. Probar el sitio completo **desde la URL de Vercel**:
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
- [ ] El login con Firebase funciona y `/auth/yo/` devuelve el rol correcto.
- [ ] El estudiante rinde el cuestionario, su nota la calcula el servidor y desbloquea el Taller 1.
- [ ] El estudiante guarda un borrador (no descuenta intentos) y pide un impulso (sí descuenta).
- [ ] El profesor ve la reflexión y el impulso, valida y pone la nota; el estudiante la ve.
- [ ] El administrador agrega y revoca correos; el revocado deja de entrar.
- [ ] Las innovaciones publicadas se ven para el estudiante.

---

## 8. Pruebas automatizadas

El objetivo es un conjunto **documentado** en ambos lados, que cualquiera del equipo pueda ejecutar completo o **de a una prueba**. Practiquen ejecutar pruebas sueltas, no solo la suite completa.

### 8.1 Backend (Django `TestCase`)

Ya hay 81 pruebas (`tests.py`, `tests_permisos.py`, `tests_errores.py`). Se suman las de B-4, B-Q1 y B-I2.

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

### 8.2 Frontend (React Testing Library + Vitest o Jest)

Según lo que se decida en la sección 1.4.

**Opción A: Vitest + React Testing Library.**

```bash
npm install -D @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
```

`vite.config.ts`:

```ts
/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: { environment: 'jsdom', globals: true, setupFiles: './src/setupTests.ts' },
})
```

`src/setupTests.ts`: `import '@testing-library/jest-dom/vitest'`.

**Opción B: Jest + React Testing Library.**

```bash
npm install -D jest jest-environment-jsdom ts-jest @types/jest @testing-library/react @testing-library/jest-dom @testing-library/user-event identity-obj-proxy
```

Jest no entiende `import.meta.env` de Vite. Para evitarlo:
- dejen todas las lecturas de variables en un solo archivo (`src/config/env.ts`) y reemplácenlo en las pruebas con `moduleNameMapper`;
- mapeen el CSS a `identity-obj-proxy`;
- cambien el script a `"test": "jest"`;
- las 3 pruebas actuales pasan casi sin cambios, salvo cambiar `vi.fn()` por `jest.fn()`.

Pruebas mínimas a escribir. Cada responsable escribe las de su módulo:

| Archivo | Qué prueba | Responsable |
|---|---|---|
| `src/services/api.test.ts` | `apiFetch` usa `VITE_API_URL`, agrega `Authorization` y convierte `{error, mensaje, campos}` en `ApiError` (con `fetch` simulado). | Estudiante 2 |
| `src/views/auth/LoginView.test.tsx` | Renderiza el formulario; un correo que no es `@ucen.cl` muestra el error (`fireEvent` o `userEvent`). | Estudiante 2 |
| `src/views/theory-verification/TheoryQuizView.test.tsx` | Con `fetch` simulado, muestra las preguntas (`findByText`) y, al enviar, la nota que devolvió la API. | Estudiante 3 |
| `src/views/critical-incidents/…test.tsx` | Guardar un borrador no cambia el contador de intentos; pedir un impulso sí lo baja. | Estudiante 4 |
| `src/views/innovations/InnovationsView.test.tsx` | Muestra las innovaciones que devuelve la API y filtra por categoría. | Estudiante 4 |

Comandos: `npm test` (todas) y `npx vitest run src/services/api.test.ts` (con Jest: `npx jest src/services/api.test.ts`). Documentar en `docs/pruebas.md` del frontend con la misma tabla que en el backend.

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

Cuentas de carga: crear en `/admin/` (local y producción) dos cuentas de Django con contraseña y su correo en la whitelist, `carga-estudiante@ucen.cl` (student) y `carga-profesor@ucen.cl` (teacher). Locust entra con `POST /api/auth/token/` (token de DRF) y no con Firebase. Las contraseñas van en variables de entorno (`LOCUST_PASSWORD`), nunca en el archivo.

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
- Meta del equipo: **al menos 6 commits propios por integrante** en esta etapa. Cada uno revisa su conteo en ambos repos, contando desde el inicio de la etapa (ajusten la fecha):
  ```bash
  git shortlog -sn --since=2026-11-17 main
  ```
- Cada integrante hace sus commits con **su** cuenta. Los commits hechos desde la cuenta de otro no cuentan como propios.

---

## 11. Checklist antes de presentar el sistema

- [ ] Las URLs de Vercel y Render responden sin depender de `localhost`. Quedan en ambos README.
- [ ] Ambos `main` actualizados, con las pruebas pasando.
- [ ] Cada integrante practicó ejecutar **cualquier** prueba de backend y de frontend, y **cualquier** escenario de Locust.
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
- **Autenticación:** ¿cómo sabe el backend quién es el usuario si el login lo hace Firebase? ¿Qué verifica `FirebaseAuthentication` y qué decide `PermisoPorRol`? ¿Por qué un estudiante recibe 404 y no 403 al pedir el registro de otro?
- **Reglas en el servidor:** ¿por qué el estudiante no recibe `es_correcta`? ¿Dónde se calcula la nota del cuestionario y por qué ahí?
- **Despliegue:** ¿por qué `DEBUG=False` en producción? ¿Qué hacen `ALLOWED_HOSTS`, `SECRET_KEY`, gunicorn y WhiteNoise? ¿Por qué TiDB y no SQLite?
- **Testing:** diferencia entre prueba unitaria y de integración, con un ejemplo propio de cada lado. ¿Qué es un mock de `fetch`?
- **Carga:** ¿qué es RPS, la latencia p95 y la tasa de error? ¿Qué escenario degradó primero y por qué?
- **Frontend:** regla R4 (vistas → hooks → servicios). ¿Por qué cambiar los servicios no obligó a cambiar los componentes?

---

## 13. Riesgos y planes B

| Riesgo | Señal | Plan B |
|---|---|---|
| TiDB incompatible con Django 6.1 | Falla `migrate` en la prueba de viabilidad. | Sección 1.1: PythonAnywhere antiguo → Django 5.2 + `django-tidb` → MySQL pagado o PostgreSQL. |
| `mysqlclient` no compila en Render | Build falla con `mysql_config` o `pkg-config`. | PyMySQL (B-2). |
| Render dormido al mostrar el sistema | La primera carga tarda unos 50 s. | Abrir `/api/salud/` 2 minutos antes. |
| Error de CORS en producción | "blocked by CORS policy" en la consola. | Revisar que `CORS_ALLOWED_ORIGINS` tenga la URL exacta de Vercel, sin `/` final. |
| Login rechazado en Vercel | `auth/unauthorized-domain`. | Agregar el dominio en *Firebase → Authorized domains*. |
| Se decide usar Jest | — | Opción B de la sección 8.2. |
| Cuota de TiDB agotada | Conexiones rechazadas. | Cargas bajas contra producción; las pruebas grandes, en local. |
| Recarga de ruta da 404 en Vercel | 404 en `/docente/...`. | `vercel.json` con *rewrites* (F-9). |

---

## Fuentes (verificadas el 24-11-2026)

- PythonAnywhere, [funciones de las cuentas gratuitas](https://help.pythonanywhere.com/pages/FreeAccountsFeatures/) y [cambios en las cuentas gratuitas](https://blog.pythonanywhere.com/221/).
- Aiven, [el MySQL gratuito fue retirado](https://aiven.io/free-mysql-database).
- TiDB Cloud, [planes](https://docs.pingcap.com/tidbcloud/select-cluster-tier/) y [límites de Starter](https://docs.pingcap.com/tidbcloud/serverless-limitations/); [django-tidb](https://github.com/pingcap/django-tidb).
- Render, [plataformas con plan gratuito en 2026](https://render.com/articles/platforms-with-a-real-free-tier-for-developers-in-2026) (el plan gratuito se duerme a los 15 minutos).
