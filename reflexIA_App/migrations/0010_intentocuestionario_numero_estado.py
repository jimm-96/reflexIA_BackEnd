import django.core.validators
from django.db import migrations, models


def numerar_intentos_existentes(apps, schema_editor):
    """Numera 1, 2, 3… los intentos que ya existían, por estudiante y por fecha."""
    IntentoCuestionario = apps.get_model('reflexIA_App', 'IntentoCuestionario')
    contador = {}
    for intento in IntentoCuestionario.objects.order_by('estudiante_id', 'fecha', 'id'):
        contador[intento.estudiante_id] = contador.get(intento.estudiante_id, 0) + 1
        intento.numero_intento = contador[intento.estudiante_id]
        intento.save(update_fields=['numero_intento'])


class Migration(migrations.Migration):

    dependencies = [
        ('reflexIA_App', '0009_pasoinnovacion'),
    ]

    operations = [
        # 1. Se agrega vacío para no fallar con los intentos que ya existen.
        migrations.AddField(
            model_name='intentocuestionario',
            name='numero_intento',
            field=models.PositiveSmallIntegerField(null=True, verbose_name='número de intento'),
        ),
        # 2. Se numeran los intentos existentes en el orden en que se rindieron.
        migrations.RunPython(numerar_intentos_existentes, migrations.RunPython.noop),
        # 3. Ya numerados, el campo pasa a ser obligatorio y con su rango.
        migrations.AlterField(
            model_name='intentocuestionario',
            name='numero_intento',
            field=models.PositiveSmallIntegerField(
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(9),
                ],
                verbose_name='número de intento',
            ),
        ),
        migrations.AddField(
            model_name='intentocuestionario',
            name='estado',
            field=models.CharField(
                choices=[('completed', 'Completado'), ('timed-out', 'Tiempo agotado')],
                default='completed',
                max_length=10,
            ),
        ),
        migrations.AddConstraint(
            model_name='intentocuestionario',
            constraint=models.UniqueConstraint(
                fields=('estudiante', 'numero_intento'),
                name='intento_unico_por_numero',
                violation_error_message='Este estudiante ya tiene un intento con ese número.',
            ),
        ),
    ]
