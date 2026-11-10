from decimal import Decimal

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .admin import EvaluacionAdmin, InnovacionAdmin, PasoInnovacionInline, RetroalimentacionAdmin
from .models import (
    Evaluacion,
    Innovacion,
    PasoInnovacion,
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


class EtapaOchoTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.profesor = UsuarioAutorizado.objects.create(
            correo='profesor@ucen.cl',
            nombre='Profesor de prueba',
            rol='teacher',
        )
        self.estudiante = UsuarioAutorizado.objects.create(
            correo='estudiante@ucen.cl',
            nombre='Estudiante de prueba',
        )
        self.innovacion = Innovacion.objects.create(
            titulo='Rutina de pensamiento',
            categoria='teaching',
            resumen='Hace visibles las ideas iniciales.',
            contexto='Clases con discusión.',
            desafio='Las ideas previas quedan implícitas.',
            actuacion='Registrar una idea inicial y una conclusión.',
            impacto_esperado='Fortalecer la metacognición.',
            etiquetas='metacognición, diálogo',
            autor=self.profesor,
        )
        PasoInnovacion.objects.create(innovacion=self.innovacion, orden=2, texto='Segundo paso')
        PasoInnovacion.objects.create(innovacion=self.innovacion, orden=1, texto='Primer paso')


class InnovacionModeloTests(EtapaOchoTestCase):
    def test_innovacion_nueva_queda_sin_publicar(self):
        self.assertFalse(self.innovacion.publicada)
        self.assertEqual(str(self.innovacion), 'Rutina de pensamiento (Estrategias de enseñanza)')

    def test_pasos_se_ordenan_y_no_repiten_orden(self):
        self.assertEqual(
            [paso.texto for paso in self.innovacion.pasos.all()],
            ['Primer paso', 'Segundo paso'],
        )

        repetido = PasoInnovacion(innovacion=self.innovacion, orden=1, texto='Repetido')
        with self.assertRaises(ValidationError):
            repetido.full_clean()

    def test_eliminar_innovacion_elimina_sus_pasos(self):
        self.innovacion.delete()

        self.assertFalse(PasoInnovacion.objects.exists())

    def test_eliminar_autor_conserva_la_innovacion(self):
        self.profesor.delete()

        self.innovacion.refresh_from_db()
        self.assertIsNone(self.innovacion.autor)


class InnovacionApiTests(EtapaOchoTestCase):
    endpoint = '/api/innovaciones/'

    def crear_payload(self, **overrides):
        payload = {
            'titulo': 'Retroalimentación entre pares',
            'categoria': 'formative',
            'resumen': 'Usa criterios explícitos.',
            'contexto': 'Procesos de escritura.',
            'desafio': 'La revisión llega tarde.',
            'actuacion': 'Incorporar una pausa de revisión por pares.',
            'impacto_esperado': 'Comprender mejor los criterios.',
            'etiquetas': [' coevaluación ', 'criterios', ''],
            'autor': self.profesor.pk,
        }
        payload.update(overrides)
        return payload

    def test_crud_entrega_pasos_etiquetas_y_autor(self):
        response = self.client.post(self.endpoint, self.crear_payload(), format='json')

        self.assertEqual(response.status_code, 201, response.data)
        innovacion_id = response.data['id']
        self.assertEqual(response.data['etiquetas'], ['coevaluación', 'criterios'])
        self.assertEqual(response.data['correo_autor'], self.profesor.correo)
        self.assertFalse(response.data['publicada'])
        self.assertEqual(response.data['pasos'], [])
        self.assertEqual(Innovacion.objects.get(pk=innovacion_id).etiquetas, 'coevaluación, criterios')

        listado = self.client.get(self.endpoint)
        self.assertEqual(listado.status_code, 200)
        self.assertEqual(len(listado.data), 2)

        detalle = self.client.get(f'{self.endpoint}{self.innovacion.pk}/')
        self.assertEqual(detalle.status_code, 200)
        self.assertEqual(
            [paso['orden'] for paso in detalle.data['pasos']],
            [1, 2],
        )

        actualizada = self.client.patch(
            f'{self.endpoint}{innovacion_id}/',
            {'publicada': True, 'etiquetas': ['escritura']},
            format='json',
        )
        self.assertEqual(actualizada.status_code, 200, actualizada.data)
        self.assertTrue(actualizada.data['publicada'])
        self.assertEqual(actualizada.data['etiquetas'], ['escritura'])

        eliminada = self.client.delete(f'{self.endpoint}{innovacion_id}/')
        self.assertEqual(eliminada.status_code, 204)
        self.assertFalse(Innovacion.objects.filter(pk=innovacion_id).exists())

    def test_acepta_innovacion_sin_autor_ni_etiquetas(self):
        payload = self.crear_payload()
        del payload['autor']
        del payload['etiquetas']

        response = self.client.post(self.endpoint, payload, format='json')

        self.assertEqual(response.status_code, 201, response.data)
        self.assertIsNone(response.data['correo_autor'])
        self.assertEqual(response.data['etiquetas'], [])

    def test_rechaza_autor_estudiante_o_inexistente_categoria_y_etiquetas_invalidas(self):
        casos_invalidos = (
            self.crear_payload(autor=self.estudiante.pk),
            self.crear_payload(autor=999999),
            self.crear_payload(categoria='otra'),
            self.crear_payload(etiquetas='coevaluación'),
            self.crear_payload(etiquetas=['coevaluación, criterios']),
            self.crear_payload(etiquetas=['x' * 301]),
            self.crear_payload(titulo=''),
        )
        for invalid_payload in casos_invalidos:
            with self.subTest(payload=invalid_payload):
                response = self.client.post(self.endpoint, invalid_payload, format='json')
                self.assertEqual(response.status_code, 400, response.data)


class InnovacionFiltrosTests(EtapaOchoTestCase):
    endpoint = '/api/innovaciones/'

    def setUp(self):
        super().setUp()
        Innovacion.objects.create(
            titulo='Desafío conectado con el entorno',
            categoria='community',
            resumen='Conecta el currículo con el entorno.',
            contexto='Unidades que permiten observar situaciones cercanas.',
            desafio='Contenidos lejanos.',
            actuacion='Plantear una pregunta investigable.',
            impacto_esperado='Facilitar la transferencia.',
            etiquetas='indagación, ciudadanía',
            publicada=True,
        )

    def titulos(self, response):
        self.assertEqual(response.status_code, 200, response.data)
        return [innovacion['titulo'] for innovacion in response.data]

    def test_filtra_por_categoria_y_publicacion(self):
        self.assertEqual(
            self.titulos(self.client.get(self.endpoint, {'categoria': 'community'})),
            ['Desafío conectado con el entorno'],
        )
        self.assertEqual(
            self.titulos(self.client.get(self.endpoint, {'publicada': 'false'})),
            ['Rutina de pensamiento'],
        )
        self.assertEqual(
            self.titulos(self.client.get(self.endpoint, {'publicada': 'true'})),
            ['Desafío conectado con el entorno'],
        )

    def test_busca_por_texto_y_combina_con_categoria(self):
        casos = (
            ({'search': 'rutina'}, ['Rutina de pensamiento']),
            ({'search': 'ciudadanía'}, ['Desafío conectado con el entorno']),
            ({'search': 'situaciones cercanas'}, ['Desafío conectado con el entorno']),
            ({'search': 'metacognición', 'categoria': 'community'}, []),
            ({'search': 'metacognición', 'categoria': 'teaching'}, ['Rutina de pensamiento']),
        )
        for parametros, esperados in casos:
            with self.subTest(parametros=parametros):
                self.assertEqual(self.titulos(self.client.get(self.endpoint, parametros)), esperados)

    def test_rechaza_parametros_de_filtro_invalidos(self):
        for parametros in ({'categoria': 'otra'}, {'publicada': 'si'}):
            with self.subTest(parametros=parametros):
                response = self.client.get(self.endpoint, parametros)
                self.assertEqual(response.status_code, 400, response.data)


class InnovacionFixtureTests(TestCase):
    fixtures = ['innovaciones']

    def test_carga_los_casos_de_ejemplo_del_frontend(self):
        self.assertEqual(Innovacion.objects.count(), 5)
        self.assertEqual(PasoInnovacion.objects.count(), 20)
        self.assertFalse(Innovacion.objects.filter(publicada=False).exists())
        for innovacion in Innovacion.objects.prefetch_related('pasos'):
            with self.subTest(innovacion=innovacion.titulo):
                self.assertEqual([paso.orden for paso in innovacion.pasos.all()], [1, 2, 3, 4])


class EtapaOchoAdminTests(TestCase):
    def test_innovacion_esta_registrada_con_sus_pasos_en_linea(self):
        innovacion_admin = admin.site._registry[Innovacion]

        self.assertIsInstance(innovacion_admin, InnovacionAdmin)
        self.assertIn(PasoInnovacionInline, innovacion_admin.inlines)
        self.assertIn('categoria', innovacion_admin.list_filter)
        self.assertNotIn(PasoInnovacion, admin.site._registry)

    def test_formulario_admin_solo_ofrece_autores_docentes_o_administradores(self):
        User = get_user_model()
        administrador = User.objects.create_superuser(
            username='admin-test',
            email='admin-test@example.com',
            password='test-password',
        )
        UsuarioAutorizado.objects.create(correo='admin-estudiante@ucen.cl')
        profesor = UsuarioAutorizado.objects.create(correo='admin-profesor@ucen.cl', rol='teacher')
        admin_reflexia = UsuarioAutorizado.objects.create(correo='admin-reflexia@ucen.cl', rol='admin')
        self.client.force_login(administrador)

        formulario = self.client.get(reverse('admin:reflexIA_App_innovacion_add'))

        self.assertEqual(formulario.status_code, 200)
        campos = formulario.context['adminform'].form.fields
        self.assertQuerySetEqual(
            campos['autor'].queryset.order_by('correo'),
            [profesor, admin_reflexia],
        )
        self.assertNotIn('fecha_creacion', campos)
