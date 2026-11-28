# Documentación del backend

| Documento | Contenido |
|---|---|
| [plan-incremental.md](./plan-incremental.md) | Etapas de construcción del backend para la EVA2 (0 a 9 y ajustes), con sus commits, y cómo continúan en la EVA3. |
| [autenticacion-y-permisos.md](./autenticacion-y-permisos.md) | Etapa 9: login, whitelist, matriz de permisos por rol y registros propios del estudiante. |
| [integracion-y-despliegue.md](./integracion-y-despliegue.md) | EVA3: qué exige la pauta, decisiones pendientes y tablero de tareas para integrar con el frontend (sin Firebase), pasar a MySQL, desplegar (backend en Render y frontend en Vercel), probar (TestCase, Jest) y medir carga (Locust). |
| [errores.md](./errores.md) | Formato uniforme de las respuestas de error (`error`, `mensaje`, `campos`), códigos y mensajes. |

La especificación funcional (requisitos, reglas de negocio, casos de uso) está en el repo del frontend, en `reflexIA/docs/especificacion/`, y vale para ambos proyectos.
