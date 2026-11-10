from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

# Único dominio institucional permitido (RN-01, DEC-03).
DOMINIO_INSTITUCIONAL = '@ucen.cl'


def validar_correo_institucional(correo):
    """Rechaza cualquier correo que no termine en @ucen.cl."""
    if not correo.lower().endswith(DOMINIO_INSTITUCIONAL):
        raise ValidationError(
            f'Solo se permiten correos institucionales {DOMINIO_INSTITUCIONAL}.'
        )


class UsuarioAutorizado(models.Model):
    """
    Correo autorizado para ingresar a ReflexIA (HU-01, whitelist).

    Equivale a `WhitelistEntry` del frontend (src/models/whitelist.ts).
    Los valores guardados de `rol` y `estado` son los mismos del frontend
    para facilitar la integración; las etiquetas se muestran en español.
    """

    ROL_CHOICES = [
        ('student', 'Estudiante'),
        ('teacher', 'Profesor guía'),
        ('admin', 'Administrador'),
    ]

    ESTADO_CHOICES = [
        ('active', 'Activo'),
        ('revoked', 'Revocado'),
    ]

    correo = models.EmailField(
        unique=True,
        validators=[validar_correo_institucional],
    )
    nombre = models.CharField(max_length=150, blank=True)
    rol = models.CharField(max_length=10, choices=ROL_CHOICES, default='student')
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='active')
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_revocacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'usuario autorizado'
        verbose_name_plural = 'usuarios autorizados'
        ordering = ['correo']

    def clean(self):
        # El admin llama a clean() antes de revisar duplicados: así
        # "ANA@ucen.cl" se detecta como repetido de "ana@ucen.cl".
        self.correo = self.correo.strip().lower()

    def save(self, *args, **kwargs):
        # El correo se guarda siempre en minúsculas, igual que en el frontend.
        self.correo = self.correo.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.correo} ({self.get_rol_display()})'


class Taller(models.Model):
    """
    Uno de los cuatro talleres de la práctica (HU-03, HU-06, HU-09).

    Equivale a `Workshop` del frontend (src/models/criticalIncident.ts) junto
    con el plazo y los intentos que configura el profesor guía
    (src/models/workPacing.ts). Guarda solo la definición del taller; el
    avance de cada estudiante va en modelos de etapas posteriores.
    """

    # La práctica tiene exactamente cuatro talleres (RF-03).
    NUMERO_MAXIMO = 4
    # Intentos de revisión: 3 por defecto, configurables de 1 a 3 (DEC-11).
    INTENTOS_POR_DEFECTO = 3
    INTENTOS_MAXIMOS_PERMITIDOS = 3

    numero = models.PositiveSmallIntegerField(
        'número',
        unique=True,
        validators=[MinValueValidator(1), MaxValueValidator(NUMERO_MAXIMO)],
    )
    titulo = models.CharField('título', max_length=150)
    objetivo = models.TextField()
    actividad = models.TextField()
    producto = models.TextField()
    fecha_limite = models.DateField('fecha límite', null=True, blank=True)
    intentos_maximos = models.PositiveSmallIntegerField(
        'intentos máximos',
        default=INTENTOS_POR_DEFECTO,
        validators=[MinValueValidator(1), MaxValueValidator(INTENTOS_MAXIMOS_PERMITIDOS)],
    )

    class Meta:
        verbose_name = 'taller'
        verbose_name_plural = 'talleres'
        ordering = ['numero']

    def __str__(self):
        return f'Taller {self.numero}: {self.titulo}'


class PreguntaTeorica(models.Model):
    """
    Pregunta del cuestionario del marco teórico (HU-04).

    Equivale a `QuizQuestion` del frontend (src/models/theoryQuiz.ts).
    Sus alternativas están en el modelo `Alternativa`.
    """

    enunciado = models.TextField()
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'pregunta teórica'
        verbose_name_plural = 'preguntas teóricas'
        ordering = ['id']

    def __str__(self):
        return self.enunciado


class Alternativa(models.Model):
    """
    Opción de respuesta de una pregunta teórica (HU-04).

    Equivale a `QuizOption` del frontend. En el frontend la respuesta
    correcta se marca en la pregunta (`correctOptionId`); aquí cada
    alternativa indica si es correcta.
    """

    pregunta = models.ForeignKey(
        PreguntaTeorica,
        on_delete=models.CASCADE,
        related_name='alternativas',
    )
    texto = models.CharField(max_length=300)
    es_correcta = models.BooleanField('es correcta', default=False)

    class Meta:
        verbose_name = 'alternativa'
        verbose_name_plural = 'alternativas'
        ordering = ['id']

    def __str__(self):
        return self.texto


class IntentoCuestionario(models.Model):
    """
    Un intento de un estudiante en el cuestionario del marco teórico (HU-04).

    Equivale a `QuizAttempt` del frontend (src/models/theoryQuiz.ts).
    Por ahora solo guarda el resultado; las reglas de aprobación y de
    intentos por bloques se aplican en una etapa posterior.
    """

    # Cada intento tiene 10 preguntas sacadas del banco (RF-04).
    PREGUNTAS_POR_INTENTO = 10
    # Escala de notas chilena.
    NOTA_MINIMA = Decimal('1.0')
    NOTA_MAXIMA = Decimal('7.0')

    estudiante = models.ForeignKey(
        UsuarioAutorizado,
        on_delete=models.CASCADE,
        related_name='intentos_cuestionario',
        # Solo los estudiantes rinden el cuestionario.
        limit_choices_to={'rol': 'student'},
    )
    respuestas_correctas = models.PositiveSmallIntegerField(
        'respuestas correctas',
        validators=[MaxValueValidator(PREGUNTAS_POR_INTENTO)],
    )
    nota = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        validators=[MinValueValidator(NOTA_MINIMA), MaxValueValidator(NOTA_MAXIMA)],
    )
    aprobado = models.BooleanField(default=False)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'intento de cuestionario'
        verbose_name_plural = 'intentos de cuestionario'
        ordering = ['-fecha']

    def __str__(self):
        return (
            f'{self.estudiante.correo}: '
            f'{self.respuestas_correctas}/{self.PREGUNTAS_POR_INTENTO}, nota {self.nota}'
        )


class Reflexion(models.Model):
    """
    Análisis de un incidente crítico que un estudiante escribe en un taller (HU-03).

    Equivale a `IncidentDraft` y `WorkshopAttempt` del frontend
    (src/models/criticalIncident.ts). Los cuatro textos son los cuatro
    pasos del formulario. Los valores guardados de `estado` siguen el
    frontend; las etiquetas se muestran en español.
    """

    ESTADO_CHOICES = [
        ('draft', 'Borrador'),
        ('submitted', 'Enviada'),
        ('reviewed', 'Revisada'),
    ]

    estudiante = models.ForeignKey(
        UsuarioAutorizado,
        on_delete=models.CASCADE,
        related_name='reflexiones',
        # Solo los estudiantes escriben reflexiones.
        limit_choices_to={'rol': 'student'},
    )
    taller = models.ForeignKey(
        Taller,
        on_delete=models.CASCADE,
        related_name='reflexiones',
    )
    # Los textos pueden quedar vacíos mientras la reflexión es un borrador.
    contexto = models.TextField(blank=True)
    descripcion = models.TextField('descripción del hecho', blank=True)
    actores = models.TextField('actores e influencia', blank=True)
    relevancia = models.TextField('relevancia pedagógica', blank=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='draft')
    intentos_usados = models.PositiveSmallIntegerField(
        'intentos usados',
        default=0,
        validators=[MaxValueValidator(Taller.INTENTOS_MAXIMOS_PERMITIDOS)],
    )
    fecha_creacion = models.DateTimeField('fecha de creación', auto_now_add=True)
    fecha_actualizacion = models.DateTimeField('última actualización', auto_now=True)

    class Meta:
        verbose_name = 'reflexión'
        verbose_name_plural = 'reflexiones'
        ordering = ['estudiante__correo', 'taller__numero']
        constraints = [
            # Un estudiante tiene una sola reflexión por taller; sus
            # reintentos se cuentan en `intentos_usados`.
            models.UniqueConstraint(
                fields=['estudiante', 'taller'],
                name='reflexion_unica_por_taller',
                violation_error_message='Este estudiante ya tiene una reflexión en este taller.',
            ),
        ]

    def __str__(self):
        return (
            f'{self.estudiante.correo}: Taller {self.taller.numero} '
            f'({self.get_estado_display()})'
        )


class Retroalimentacion(models.Model):
    """Revisión docente de la propuesta de IA asociada a una reflexión (HU-02)."""

    ESTADO_CHOICES = [
        ('pending', 'Pendiente'),
        ('edited', 'Editada'),
        ('validated', 'Validada'),
    ]

    reflexion = models.ForeignKey(
        Reflexion,
        on_delete=models.CASCADE,
        related_name='retroalimentaciones',
    )
    propuesta_ia = models.TextField('propuesta de la IA')
    comentario_docente = models.TextField('comentario docente', blank=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='pending')

    class Meta:
        verbose_name = 'retroalimentación'
        verbose_name_plural = 'retroalimentaciones'
        ordering = ['reflexion__id']

    def __str__(self):
        return f'Reflexión {self.reflexion_id}: {self.get_estado_display()}'


class Evaluacion(models.Model):
    """Nota oficial de un estudiante en un taller (HU-02, panel docente)."""

    RESULTADO_CHOICES = [
        ('approved', 'Aprobado'),
        ('failed', 'Reprobado'),
    ]

    NOTA_MINIMA = Decimal('1.0')
    NOTA_MAXIMA = Decimal('7.0')

    estudiante = models.ForeignKey(
        UsuarioAutorizado,
        on_delete=models.CASCADE,
        related_name='evaluaciones',
        limit_choices_to={'rol': 'student'},
    )
    taller = models.ForeignKey(
        Taller,
        on_delete=models.CASCADE,
        related_name='evaluaciones',
    )
    nota = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        validators=[MinValueValidator(NOTA_MINIMA), MaxValueValidator(NOTA_MAXIMA)],
    )
    resultado = models.CharField(max_length=8, choices=RESULTADO_CHOICES)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'evaluación'
        verbose_name_plural = 'evaluaciones'
        ordering = ['estudiante__correo', 'taller__numero']
        constraints = [
            models.UniqueConstraint(
                fields=['estudiante', 'taller'],
                name='evaluacion_unica_por_taller',
                violation_error_message='Este estudiante ya tiene una evaluación en este taller.',
            ),
        ]

    def __str__(self):
        return (
            f'{self.estudiante.correo}: Taller {self.taller.numero}, '
            f'nota {self.nota} ({self.get_resultado_display()})'
        )


class Innovacion(models.Model):
    """
    Caso de la biblioteca de actuaciones mejoradas e innovaciones (HU-07).

    Equivale a `InnovationCase` del frontend
    (src/views/innovations/models/innovation.ts). Los valores guardados de
    `categoria` son claves cortas; las etiquetas se muestran en español.
    """

    CATEGORIA_CHOICES = [
        ('teaching', 'Estrategias de enseñanza'),
        ('formative', 'Evaluación formativa'),
        ('inclusion', 'Inclusión y participación'),
        ('community', 'Vinculación con el entorno'),
    ]

    titulo = models.CharField('título', max_length=150)
    categoria = models.CharField('categoría', max_length=10, choices=CATEGORIA_CHOICES)
    resumen = models.TextField()
    contexto = models.TextField()
    desafio = models.TextField('desafío pedagógico')
    actuacion = models.TextField('actuación mejorada')
    impacto_esperado = models.TextField('impacto esperado')
    # Palabras clave separadas por coma; la API las entrega como lista.
    etiquetas = models.CharField(max_length=300, blank=True)
    autor = models.ForeignKey(
        UsuarioAutorizado,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='innovaciones',
        # Solo el profesor guía o el administrador publican casos.
        limit_choices_to={'rol__in': ['teacher', 'admin']},
    )
    # Un caso nuevo queda sin publicar hasta su revisión editorial.
    publicada = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField('fecha de creación', auto_now_add=True)
    fecha_actualizacion = models.DateTimeField('última actualización', auto_now=True)

    class Meta:
        verbose_name = 'innovación'
        verbose_name_plural = 'innovaciones'
        ordering = ['categoria', 'titulo']

    def __str__(self):
        return f'{self.titulo} ({self.get_categoria_display()})'
