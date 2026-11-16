"""
Pruebas del formato uniforme de errores (reflexIA_App/exceptions.py).

Todas las respuestas de error deben tener la forma
{"error": "<código>", "mensaje": "<texto>", "campos": {...}}, con mensajes
claros en español en vez de los mensajes por defecto de DRF.
"""

from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import Taller, UsuarioAutorizado


class ErroresTestCase(TestCase):
    def setUp(self):
        superusuario = get_user_model().objects.create_superuser(
            username='superusuario-errores', email='errores@ejemplo.cl', password=None,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=superusuario)
        self.estudiante = UsuarioAutorizado.objects.create(correo='estudiante@ucen.cl')
        self.taller = Taller.objects.create(
            numero=1, titulo='Taller', objetivo='o', actividad='a', producto='p',
        )

    def assertError(self, response, status, codigo):
        """Comprueba el código HTTP y la forma {error, mensaje, campos}."""
        self.assertEqual(response.status_code, status, response.data)
        self.assertEqual(set(response.data), {'error', 'mensaje', 'campos'})
        self.assertEqual(response.data['error'], codigo)
        self.assertTrue(response.data['mensaje'])
        return response.data


class ValidacionTests(ErroresTestCase):
    def test_campos_obligatorios_y_vacios(self):
        data = self.assertError(
            self.client.post('/api/talleres/', {'titulo': ''}, format='json'), 400, 'validacion',
        )

        self.assertEqual(data['mensaje'], 'Revisa los datos enviados: hay campos con errores.')
        self.assertEqual(data['campos']['titulo'], ['Este campo no puede quedar vacío.'])
        self.assertEqual(data['campos']['objetivo'], ['Este campo es obligatorio.'])

    def test_opcion_invalida_lista_las_opciones_validas(self):
        data = self.assertError(
            self.client.post('/api/usuarios/', {'correo': 'ana@ucen.cl', 'rol': 'jefe'}, format='json'),
            400, 'validacion',
        )

        self.assertEqual(
            data['campos']['rol'],
            ['"jefe" no es una opción válida. Usa una de estas: student, teacher, admin.'],
        )

    def test_nota_fuera_de_formato_explica_el_rango(self):
        payload = {
            'estudiante': self.estudiante.pk,
            'taller': self.taller.pk,
            'resultado': 'approved',
        }
        for nota in (70, 6.66, 'siete'):
            with self.subTest(nota=nota):
                data = self.assertError(
                    self.client.post('/api/evaluaciones/', {**payload, 'nota': nota}, format='json'),
                    400, 'validacion',
                )
                self.assertEqual(
                    data['campos']['nota'],
                    ['Debe ser un número entre 1.0 y 7.0, con un decimal como máximo.'],
                )

    def test_tipos_invalidos(self):
        data = self.assertError(
            self.client.post(
                '/api/talleres/',
                {'numero': 'uno', 'fecha_limite': '31-12-2026', 'intentos_maximos': 9},
                format='json',
            ),
            400, 'validacion',
        )

        self.assertEqual(data['campos']['numero'], ['Debe ser un número entero.'])
        self.assertEqual(
            data['campos']['fecha_limite'],
            ['Debe ser una fecha real con formato AAAA-MM-DD (por ejemplo, 2026-12-04).'],
        )
        self.assertEqual(data['campos']['intentos_maximos'], ['Debe ser menor o igual a 3.'])

    def test_llave_foranea_inexistente_o_de_otro_tipo(self):
        data = self.assertError(
            self.client.post('/api/reflexiones/', {'estudiante': 'abc', 'taller': 999}, format='json'),
            400, 'validacion',
        )

        self.assertEqual(data['campos']['estudiante'], ['Debe ser el id (número) de un registro.'])
        self.assertEqual(data['campos']['taller'], ['No existe un taller con id 999.'])

    def test_conserva_los_mensajes_propios_del_proyecto(self):
        data = self.assertError(
            self.client.post(
                '/api/intentos-cuestionario/',
                {'estudiante': 999, 'numero_intento': 1, 'respuestas_correctas': 5, 'nota': 4.0},
                format='json',
            ),
            400, 'validacion',
        )

        # Mensaje definido en IntentoCuestionarioSerializer, no el de DRF.
        self.assertEqual(data['campos']['estudiante'], ['No existe un estudiante con id 999.'])

    def test_correo_mal_escrito_recibe_un_solo_mensaje(self):
        mal_escrito = self.client.post('/api/usuarios/', {'correo': 'no-es-correo'}, format='json')
        otro_dominio = self.client.post('/api/usuarios/', {'correo': 'ana@gmail.com'}, format='json')

        self.assertEqual(
            self.assertError(mal_escrito, 400, 'validacion')['campos']['correo'],
            ['Debe ser un correo electrónico válido.'],
        )
        self.assertEqual(
            self.assertError(otro_dominio, 400, 'validacion')['campos']['correo'],
            ['Solo se permiten correos institucionales @ucen.cl.'],
        )

    def test_error_general_va_en_el_mensaje(self):
        datos = {'estudiante': self.estudiante.pk, 'taller': self.taller.pk}
        self.client.post('/api/reflexiones/', datos, format='json')

        data = self.assertError(
            self.client.post('/api/reflexiones/', datos, format='json'), 400, 'validacion',
        )

        self.assertEqual(data['mensaje'], 'Este estudiante ya tiene una reflexión en este taller.')
        self.assertEqual(data['campos'], {})

    def test_filtro_invalido_usa_el_mismo_formato(self):
        data = self.assertError(
            self.client.get('/api/innovaciones/?categoria=otra'), 400, 'validacion',
        )

        self.assertIn('Usa una de estas: teaching', data['campos']['categoria'][0])


class CuerpoDeLaPeticionTests(ErroresTestCase):
    def test_json_mal_escrito(self):
        self.assertError(
            self.client.post('/api/talleres/', '{"numero": 1,', content_type='application/json'),
            400, 'json_invalido',
        )

    def test_cuerpo_que_no_es_un_objeto(self):
        data = self.assertError(
            self.client.post('/api/talleres/', [1, 2], format='json'), 400, 'validacion',
        )

        self.assertEqual(
            data['mensaje'],
            'El cuerpo de la petición debe ser un objeto JSON con los campos del recurso.',
        )

    def test_formato_no_compatible(self):
        self.assertError(
            self.client.post('/api/talleres/', 'numero=1', content_type='text/plain'),
            415, 'tipo_no_soportado',
        )


class OtrosErroresTests(ErroresTestCase):
    def test_registro_inexistente(self):
        data = self.assertError(self.client.get('/api/talleres/999/'), 404, 'no_encontrado')

        self.assertEqual(data['mensaje'], 'No existe un registro con id 999 en talleres.')

    def test_ruta_inexistente_responde_json(self):
        data = self.assertError(APIClient().get('/api/no-existe/'), 404, 'no_encontrado')

        self.assertEqual(data['mensaje'], 'La ruta /api/no-existe/ no existe en la API.')

    def test_ruta_sin_barra_final_sigue_redirigiendo(self):
        response = self.client.get('/api/talleres')

        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/api/talleres/')

    def test_metodo_no_permitido_lista_los_permitidos(self):
        data = self.assertError(self.client.delete('/api/talleres/'), 405, 'metodo_no_permitido')

        self.assertIn('GET, POST', data['mensaje'])

    def test_sin_sesion_y_token_invalido(self):
        self.assertError(APIClient().get('/api/talleres/'), 401, 'no_autenticado')
        self.assertError(
            APIClient(HTTP_AUTHORIZATION='Token no-existe').get('/api/talleres/'),
            401, 'credenciales_invalidas',
        )

    def test_login_con_credenciales_incorrectas(self):
        data = self.assertError(
            APIClient().post('/api/auth/token/', {'username': 'a', 'password': 'b'}, format='json'),
            400, 'validacion',
        )

        self.assertEqual(data['mensaje'], 'Usuario o contraseña incorrectos.')

    def test_sin_permiso_conserva_el_mensaje_del_rol(self):
        get_user_model().objects.create_user(username='estudiante@ucen.cl', password=None)
        cliente = APIClient()
        cliente.force_authenticate(user=get_user_model().objects.get(username='estudiante@ucen.cl'))

        data = self.assertError(cliente.get('/api/usuarios/'), 403, 'sin_permiso')

        self.assertEqual(data['mensaje'], 'Tu rol no tiene permiso para realizar esta acción.')

    @override_settings(DEBUG=False)
    def test_error_inesperado_responde_json_sin_detalles_internos(self):
        cliente = APIClient(raise_request_exception=False)
        cliente.force_authenticate(user=get_user_model().objects.get(username='superusuario-errores'))

        with mock.patch('reflexIA_App.views.TallerViewSet.list', side_effect=RuntimeError('detalle interno')), \
                self.assertLogs('reflexIA_App.exceptions', level='ERROR'):
            response = cliente.get('/api/talleres/')

        data = self.assertError(response, 500, 'error_servidor')
        self.assertNotIn('detalle interno', data['mensaje'])
