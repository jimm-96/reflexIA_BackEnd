from decimal import Decimal

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .admin import EvaluacionAdmin, RetroalimentacionAdmin
from .models import (
    Evaluacion,
    Reflexion,
    Retroalimentacion,
    Taller,
    UsuarioAutorizado,
)


class EtapasSeisYSieteTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.estudiante = UsuarioAutorizado.objects.create(
            correo='estudiante@ucen.cl',
            nombre='Estudiante de prueba',
        )
        self.profesor = UsuarioAutorizado.objects.create(
            correo='profesor@ucen.cl',
            nombre='Profesor de prueba',
            rol='teacher',
        )
        self.taller = Taller.objects.create(
            numero=1,
            titulo='Taller de prueba',
            objetivo='Objetivo',
            actividad='Actividad',
            producto='Producto',
        )
        self.reflexion = Reflexion.objects.create(
            estudiante=self.estudiante,
            taller=self.taller,
            contexto='Contexto de prueba',
        )


class RetroalimentacionApiTests(EtapasSeisYSieteTestCase):
    endpoint = '/api/retroalimentaciones/'

    def crear_payload(self, **overrides):
        payload = {
            'reflexion': self.reflexion.pk,
            'propuesta_ia': 'Profundiza en el análisis del incidente.',
        }
        payload.update(overrides)
        return payload

    def test_crud_y_relaciones_de_lectura(self):
        response = self.client.post(
            self.endpoint,
            self.crear_payload(comentario_docente='Buen trabajo.'),
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.data)
        retroalimentacion_id = response.data['id']
        self.assertEqual(response.data['estado'], 'pending')
        self.assertEqual(response.data['correo_estudiante'], self.estudiante.correo)
        self.assertEqual(response.data['numero_taller'], self.taller.numero)

        listado = self.client.get(self.endpoint)
        self.assertEqual(listado.status_code, 200)
        self.assertEqual(len(listado.data), 1)

        detalle = self.client.get(f'{self.endpoint}{retroalimentacion_id}/')
        self.assertEqual(detalle.status_code, 200)
        self.assertEqual(detalle.data['propuesta_ia'], 'Profundiza en el análisis del incidente.')

        actualizada = self.client.patch(
            f'{self.endpoint}{retroalimentacion_id}/',
            {'comentario_docente': 'Comentario actualizado.', 'estado': 'validated'},
            format='json',
        )
        self.assertEqual(actualizada.status_code, 200, actualizada.data)
        self.assertEqual(actualizada.data['comentario_docente'], 'Comentario actualizado.')
        self.assertEqual(actualizada.data['estado'], 'validated')

        eliminada = self.client.delete(f'{self.endpoint}{retroalimentacion_id}/')
        self.assertEqual(eliminada.status_code, 204)
        self.assertFalse(Retroalimentacion.objects.exists())

    def test_rechaza_reflexion_inexistente_estado_invalido_y_propuesta_ausente(self):
        respuestas = (
            self.client.post(
                self.endpoint,
                self.crear_payload(reflexion=999999),
                format='json',
            ),
            self.client.post(
                self.endpoint,
                self.crear_payload(estado='unknown'),
                format='json',
            ),
            self.client.post(
                self.endpoint,
                {'reflexion': self.reflexion.pk},
                format='json',
            ),
        )

        for response in respuestas:
            with self.subTest(data=response.data):
                self.assertEqual(response.status_code, 400)

    def test_eliminar_reflexion_elimina_su_retroalimentacion(self):
        retroalimentacion = Retroalimentacion.objects.create(
            reflexion=self.reflexion,
            propuesta_ia='Propuesta de prueba',
        )

        self.reflexion.delete()

        self.assertFalse(Retroalimentacion.objects.filter(pk=retroalimentacion.pk).exists())


class EvaluacionApiTests(EtapasSeisYSieteTestCase):
    endpoint = '/api/evaluaciones/'

    def crear_payload(self, **overrides):
        payload = {
            'estudiante': self.estudiante.pk,
            'taller': self.taller.pk,
            'nota': 6.0,
            'resultado': 'approved',
        }
        payload.update(overrides)
        return payload

    def test_crud_devuelve_nota_numerica_y_relaciones(self):
        response = self.client.post(self.endpoint, self.crear_payload(), format='json')

        self.assertEqual(response.status_code, 201, response.data)
        evaluacion_id = response.data['id']
        self.assertEqual(response.data['nota'], 6.0)
        self.assertEqual(response.data['correo_estudiante'], self.estudiante.correo)
        self.assertEqual(response.data['numero_taller'], self.taller.numero)
        self.assertTrue(response.data['fecha'])
        self.assertEqual(Evaluacion.objects.get(pk=evaluacion_id).nota, Decimal('6.0'))

        listado = self.client.get(self.endpoint)
        self.assertEqual(listado.status_code, 200)
        self.assertEqual(len(listado.data), 1)

        detalle = self.client.get(f'{self.endpoint}{evaluacion_id}/')
        self.assertEqual(detalle.status_code, 200)
        self.assertEqual(detalle.data['estudiante'], self.estudiante.pk)

        actualizada = self.client.patch(
            f'{self.endpoint}{evaluacion_id}/',
            {'nota': 3.5, 'resultado': 'failed'},
            format='json',
        )
        self.assertEqual(actualizada.status_code, 200, actualizada.data)
        self.assertEqual(actualizada.data['nota'], 3.5)
        self.assertEqual(actualizada.data['resultado'], 'failed')

        eliminada = self.client.delete(f'{self.endpoint}{evaluacion_id}/')
        self.assertEqual(eliminada.status_code, 204)
        self.assertFalse(Evaluacion.objects.exists())

    def test_acepta_limites_de_nota_y_rechaza_valores_fuera_de_rango_o_precision(self):
        for numero, nota in enumerate((1.0, 7.0), start=1):
            taller = Taller.objects.create(
                numero=numero + 1,
                titulo=f'Taller límite {numero}',
                objetivo='Objetivo',
                actividad='Actividad',
                producto='Producto',
            )
            response = self.client.post(
                self.endpoint,
                self.crear_payload(taller=taller.pk, nota=nota),
                format='json',
            )
            self.assertEqual(response.status_code, 201, response.data)

        for numero, nota in enumerate((0.9, 7.1, 6.66), start=4):
            taller = Taller.objects.create(
                numero=numero,
                titulo=f'Taller inválido {numero}',
                objetivo='Objetivo',
                actividad='Actividad',
                producto='Producto',
            )
            response = self.client.post(
                self.endpoint,
                self.crear_payload(taller=taller.pk, nota=nota),
                format='json',
            )
            with self.subTest(nota=nota):
                self.assertEqual(response.status_code, 400)

    def test_rechaza_profesor_relaciones_inexistentes_resultado_invalido_y_duplicado(self):
        payload = self.crear_payload()
        creada = self.client.post(self.endpoint, payload, format='json')
        self.assertEqual(creada.status_code, 201, creada.data)

        casos_invalidos = (
            self.crear_payload(estudiante=self.profesor.pk),
            self.crear_payload(estudiante=999999),
            self.crear_payload(taller=999999),
            self.crear_payload(resultado='pending'),
            payload,
        )
        for invalid_payload in casos_invalidos:
            with self.subTest(payload=invalid_payload):
                response = self.client.post(self.endpoint, invalid_payload, format='json')
                self.assertEqual(response.status_code, 400, response.data)

    def test_eliminar_estudiante_o_taller_elimina_evaluacion(self):
        evaluacion = Evaluacion.objects.create(
            estudiante=self.estudiante,
            taller=self.taller,
            nota=Decimal('6.0'),
            resultado='approved',
        )

        self.estudiante.delete()

        self.assertFalse(Evaluacion.objects.filter(pk=evaluacion.pk).exists())

        estudiante = UsuarioAutorizado.objects.create(correo='estudiante2@ucen.cl')
        taller = Taller.objects.create(
            numero=2,
            titulo='Taller de cascada',
            objetivo='Objetivo',
            actividad='Actividad',
            producto='Producto',
        )
        evaluacion = Evaluacion.objects.create(
            estudiante=estudiante,
            taller=taller,
            nota=Decimal('5.0'),
            resultado='approved',
        )

        taller.delete()

        self.assertFalse(Evaluacion.objects.filter(pk=evaluacion.pk).exists())


class EtapasSeisYSieteAdminTests(TestCase):
    def test_modelos_estan_registrados_con_configuracion_esperada(self):
        self.assertIsInstance(admin.site._registry[Retroalimentacion], RetroalimentacionAdmin)
        self.assertIsInstance(admin.site._registry[Evaluacion], EvaluacionAdmin)

        retroalimentacion_admin = admin.site._registry[Retroalimentacion]
        evaluacion_admin = admin.site._registry[Evaluacion]
        self.assertIn('estado', retroalimentacion_admin.list_filter)
        self.assertIn('resultado', evaluacion_admin.list_filter)
        self.assertIn('fecha', evaluacion_admin.readonly_fields)

    def test_formulario_admin_filtra_rol_y_exhibe_campos_de_fecha_solo_lectura(self):
        User = get_user_model()
        administrador = User.objects.create_superuser(
            username='admin-test',
            email='admin-test@example.com',
            password='test-password',
        )
        estudiante = UsuarioAutorizado.objects.create(correo='admin-estudiante@ucen.cl')
        profesor = UsuarioAutorizado.objects.create(
            correo='admin-profesor@ucen.cl',
            rol='teacher',
        )
        taller = Taller.objects.create(
            numero=1,
            titulo='Taller admin',
            objetivo='Objetivo',
            actividad='Actividad',
            producto='Producto',
        )
        client = self.client
        client.force_login(administrador)

        formulario = client.get(
            reverse('admin:reflexIA_App_evaluacion_add')
        )

        self.assertEqual(formulario.status_code, 200)
        campos = formulario.context['adminform'].form.fields
        estudiantes_disponibles = campos['estudiante'].queryset
        self.assertQuerySetEqual(
            estudiantes_disponibles,
            [estudiante],
            transform=lambda usuario: usuario,
        )
        self.assertNotIn('fecha', campos)
