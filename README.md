# ReflexIA: Backend

API REST en Django y Django REST Framework para **ReflexIA**, la plataforma de práctica profesional pedagógica de la Universidad Central.

El proyecto completo tiene tres partes:

1. **Frontend** en React + TypeScript: listo, en el repo [`reflexIA`](https://github.com/gvbr-iel/reflexIA).
2. **Backend** en Django: este repositorio.
3. **Integración** entre ambos mediante la API: en iteraciones futuras.

> **Estado:** etapa 5 de 8, reflexiones. Los demás modelos se agregan por etapas. Ver [docs/plan-incremental.md](./docs/plan-incremental.md).

---

## Tecnologías

* **Python:** 3.13
* **Django:** 6.1
* **Django REST Framework:** 3.18
* **Base de datos:** SQLite en desarrollo; MySQL en una etapa posterior.

---

## Estructura

```
reflexIA_BackEnd/
├── reflexIA_Proyect/     # Proyecto Django
│   ├── settings.py       # Configuración (apps instaladas, idioma, base de datos)
│   └── urls.py           # Rutas raíz: /admin/ y /api/
├── reflexIA_App/         # Aplicación principal
│   ├── models.py         # Modelos (tablas)
│   ├── serializers.py    # Conversión de modelos a JSON
│   ├── views.py          # ViewSets de la API
│   ├── urls.py           # Router de DRF con los recursos
│   └── admin.py          # Registro de modelos en el panel de administración
├── docs/                 # Documentación
├── manage.py
└── requirements.txt
```

---

## Instalación y ejecución local

### 1. Clonar el repositorio
```bash
git clone https://github.com/jimm-96/reflexIA_BackEnd.git
cd reflexIA_BackEnd
```

### 2. Crear y activar el entorno virtual

* **En Windows (PowerShell):**
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  ```
  Si PowerShell bloquea el script: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
* **En Linux / macOS:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

### 3. Instalar las dependencias
```bash
pip install -r requirements.txt
```

### 4. Aplicar las migraciones
```bash
python manage.py migrate
```

### 5. Crear un superusuario para el panel de administración
```bash
python manage.py createsuperuser
```

### 6. Ejecutar el servidor de desarrollo
```bash
python manage.py runserver
```

| Dirección | Qué hay |
|---|---|
| `http://127.0.0.1:8000/admin/` | Panel de administración de Django |
| `http://127.0.0.1:8000/api/` | Raíz de la API (interfaz navegable de DRF) |

---

## Endpoints

Esta sección se completa en cada etapa.

### 1. Recurso: Usuarios autorizados (`/api/usuarios/`)

Whitelist de correos que pueden ingresar a ReflexIA (HU-01).

| Método | Ruta | Acción |
| :--- | :--- | :--- |
| GET | `/api/usuarios/` | Lista todos los usuarios autorizados |
| POST | `/api/usuarios/` | Autoriza un correo nuevo |
| GET | `/api/usuarios/<id>/` | Muestra un usuario |
| PUT / PATCH | `/api/usuarios/<id>/` | Modifica un usuario (por ejemplo, revoca su acceso) |
| DELETE | `/api/usuarios/<id>/` | Elimina un usuario definitivamente |

* **Payload esperado (JSON):**
  ```json
  {
    "correo": "ana.perez@ucen.cl",
    "nombre": "Ana Pérez",
    "rol": "student"
  }
  ```
* **Valores permitidos:** `rol` = `student`, `teacher` o `admin`; `estado` = `active` o `revoked`.
* **Validaciones:** el correo debe terminar en `@ucen.cl` y no puede repetirse (sin importar mayúsculas). Si no se cumple, la API responde `400 Bad Request` con el motivo.

### 2. Recurso: Talleres (`/api/talleres/`)

Los cuatro talleres de la práctica, con su plazo y su límite de intentos (HU-03, HU-06, HU-09).

| Método | Ruta | Acción |
| :--- | :--- | :--- |
| GET | `/api/talleres/` | Lista los talleres, ordenados por número |
| POST | `/api/talleres/` | Crea un taller |
| GET | `/api/talleres/<id>/` | Muestra un taller |
| PUT / PATCH | `/api/talleres/<id>/` | Modifica un taller (por ejemplo, su plazo o sus intentos) |
| DELETE | `/api/talleres/<id>/` | Elimina un taller |

* **Payload esperado (JSON):**
  ```json
  {
    "numero": 1,
    "titulo": "Identificación del incidente",
    "objetivo": "Reconocer un incidente crítico ocurrido en el aula.",
    "actividad": "Describir el contexto, el hecho, los actores y su relevancia.",
    "producto": "Relato del incidente crítico.",
    "fecha_limite": "2026-12-04",
    "intentos_maximos": 3
  }
  ```
* **Opcionales:** `fecha_limite` (por defecto sin plazo) e `intentos_maximos` (por defecto 3).
* **Validaciones:** `numero` es único y va de 1 a 4; `intentos_maximos` va de 1 a 3; `fecha_limite` debe ser una fecha real en formato `AAAA-MM-DD`. Si no se cumple, la API responde `400 Bad Request` con el motivo.

### 3. Recurso: Preguntas teóricas (`/api/preguntas/`)

Banco de preguntas del cuestionario del marco teórico, cada una con sus alternativas (HU-04).

| Método | Ruta | Acción |
| :--- | :--- | :--- |
| GET | `/api/preguntas/` | Lista las preguntas, cada una con sus alternativas |
| POST | `/api/preguntas/` | Crea una pregunta |
| GET | `/api/preguntas/<id>/` | Muestra una pregunta con sus alternativas |
| PUT / PATCH | `/api/preguntas/<id>/` | Modifica una pregunta (por ejemplo, la desactiva) |
| DELETE | `/api/preguntas/<id>/` | Elimina una pregunta junto con sus alternativas |

* **Payload esperado (JSON):**
  ```json
  {
    "enunciado": "¿Qué es un incidente crítico en el contexto de la práctica docente?",
    "activa": true
  }
  ```
* **Respuesta (GET):** cada pregunta incluye la lista `alternativas`, con `id`, `texto` y `es_correcta`.
* **Opcionales:** `activa` (por defecto `true`).
* **Validaciones:** `enunciado` no puede estar vacío. Si no se cumple, la API responde `400 Bad Request` con el motivo.
* **Alternativas:** por ahora se cargan desde el panel de administración, en la misma pantalla de la pregunta. En la API son de solo lectura.

### 4. Recurso: Intentos de cuestionario (`/api/intentos-cuestionario/`)

Cada vez que un estudiante rinde el cuestionario del marco teórico, con su resultado (HU-04).

| Método | Ruta | Acción |
| :--- | :--- | :--- |
| GET | `/api/intentos-cuestionario/` | Lista los intentos, del más reciente al más antiguo |
| POST | `/api/intentos-cuestionario/` | Registra un intento |
| GET | `/api/intentos-cuestionario/<id>/` | Muestra un intento |
| PUT / PATCH | `/api/intentos-cuestionario/<id>/` | Modifica un intento |
| DELETE | `/api/intentos-cuestionario/<id>/` | Elimina un intento |

* **Payload esperado (JSON):**
  ```json
  {
    "estudiante": 1,
    "respuestas_correctas": 9,
    "nota": 6.6,
    "aprobado": true
  }
  ```
* **Respuesta:** incluye además `correo_estudiante` y `fecha`, que son de solo lectura. La fecha se llena sola al crear el intento.
* **Opcionales:** `aprobado` (por defecto `false`).
* **Validaciones:** `estudiante` es el id de un usuario autorizado con rol `student`; `respuestas_correctas` va de 0 a 10; `nota` va de 1.0 a 7.0, con un decimal. Si no se cumple, la API responde `400 Bad Request` con el motivo.

### 5. Recurso: Reflexiones (`/api/reflexiones/`)

El análisis de un incidente crítico que cada estudiante escribe en un taller, en cuatro partes (HU-03).

| Método | Ruta | Acción |
| :--- | :--- | :--- |
| GET | `/api/reflexiones/` | Lista las reflexiones, por estudiante y número de taller |
| POST | `/api/reflexiones/` | Crea una reflexión (por ejemplo, un borrador) |
| GET | `/api/reflexiones/<id>/` | Muestra una reflexión |
| PUT / PATCH | `/api/reflexiones/<id>/` | Modifica una reflexión (por ejemplo, la envía) |
| DELETE | `/api/reflexiones/<id>/` | Elimina una reflexión |

* **Payload esperado (JSON):**
  ```json
  {
    "estudiante": 1,
    "taller": 1,
    "contexto": "Curso de 30 estudiantes de segundo básico, sala con proyector.",
    "descripcion": "Durante una actividad grupal, un estudiante se negó a participar.",
    "actores": "La docente en formación, el estudiante y su grupo.",
    "relevancia": "Muestra la importancia de anticipar la dinámica de los grupos."
  }
  ```
* **Respuesta:** incluye además `correo_estudiante`, `numero_taller`, `fecha_creacion` y `fecha_actualizacion`, que son de solo lectura. `fecha_actualizacion` cambia cada vez que se guarda.
* **Valores permitidos:** `estado` = `draft` (borrador), `submitted` (enviada) o `reviewed` (revisada).
* **Opcionales:** los cuatro textos (por defecto vacíos, para guardar borradores incompletos), `estado` (por defecto `draft`) e `intentos_usados` (por defecto 0).
* **Validaciones:** `estudiante` es el id de un usuario autorizado con rol `student`; `taller` es el id de un taller existente; `intentos_usados` va de 0 a 3; un estudiante tiene una sola reflexión por taller. Si no se cumple, la API responde `400 Bad Request` con el motivo.

---

## Flujo de trabajo incremental

La configuración inicial (etapa 0) está en `main`. Cada etapa siguiente se desarrolla en su propia rama y se integra a `main` mediante un Pull Request:

```bash
git switch main
git pull
git switch -c recurso-<nombre>     # por ejemplo, recurso-talleres
# ... commits de la etapa ...
git push -u origin recurso-<nombre>
```

Dentro de cada rama, el recurso se agrega en commits pequeños, con este orden:

1. Modelo en `models.py` y su migración.
2. Registro en `admin.py` y prueba desde el panel.
3. Serializer en `serializers.py`.
4. ViewSet en `views.py`.
5. Ruta en `urls.py` y prueba en `/api/`.

El detalle de cada etapa y los mensajes de commit sugeridos están en [docs/plan-incremental.md](./docs/plan-incremental.md).
