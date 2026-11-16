"""
Pruebas de autenticación y permisos por rol.

Revisan que el backend repita las reglas del frontend: sesión iniciada,
correo activo en la whitelist y rol permitido para cada acción. Las
pruebas de datos y validaciones de cada recurso están en tests.py.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import (
    Alternativa,
    Evaluacion,
    Innovacion,
    IntentoCuestionario,
    PreguntaTeorica,
    Reflexion,
    Retroalimentacion,
    Taller,
    UsuarioAutorizado,
)


def crear_cuenta(correo, password=None, **extra):
    """Cuenta de Django cuyo correo enlaza con la whitelist."""
    return get_user_model().objects.create_user(
        username=correo,
        email=correo,
        password=password,
        **extra,
    )


class PermisosTestCase(TestCase):
    """Whitelist con un usuario de cada rol, cada uno con su cuenta de Django."""

    def setUp(self):
        self.estudiante = UsuarioAutorizado.objects.create(correo='estudiante@ucen.cl')
        self.otro_estudiante = UsuarioAutorizado.objects.create(correo='otro@ucen.cl')
        self.profesor = UsuarioAutorizado.objects.create(correo='profesor@ucen.cl', rol='teacher')
        self.administrador = UsuarioAutorizado.objects.create(correo='admin@ucen.cl', rol='admin')

        self.cuentas = {
            usuario.correo: crear_cuenta(usuario.correo)
            for usuario in (self.estudiante, self.otro_estudiante, self.profesor, self.administrador)
        }
        self.taller = Taller.objects.create(
            numero=1,
            titulo='Identificación del incidente',
            objetivo='Objetivo',
            actividad='Actividad',
            producto='Producto',
        )

    def cliente(self, usuario):
        """Cliente de la API con la sesión iniciada como `usuario`."""
        cliente = APIClient()
        cliente.force_authenticate(user=self.cuentas[usuario.correo])
        return cliente


# ─────────────────────────────────────────────
# Autenticación
# ─────────────────────────────────────────────


class AutenticacionTests(PermisosTestCase):
    def test_sin_credenciales_responde_401(self):
        response = APIClient().get('/api/talleres/')

        self.assertEqual(response.status_code, 401)

    def test_token_permite_usar_la_api(self):
        crear_cuenta('token@ucen.cl', password='clave-segura-123')
        UsuarioAutorizado.objects.create(correo='token@ucen.cl', rol='teacher')

        response = APIClient().post(
            '/api/auth/token/',
            {'username': 'token@ucen.cl', 'password': 'clave-segura-123'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        cliente = APIClient()
        cliente.credentials(HTTP_AUTHORIZATION=f'Token {response.data["token"]}')

        self.assertEqual(cliente.get('/api/talleres/').status_code, 200)

    def test_token_rechaza_credenciales_incorrectas(self):
        crear_cuenta('token@ucen.cl', password='clave-segura-123')

        response = APIClient().post(
            '/api/auth/token/',
            {'username': 'token@ucen.cl', 'password': 'otra-clave'},
            format='json',
        )

        self.assertEqual(response.status_code, 400)

    def test_cuenta_fuera_de_la_whitelist_responde_403(self):
        cliente = APIClient()
        cliente.force_authenticate(user=crear_cuenta('intruso@ucen.cl'))

        response = cliente.get('/api/talleres/')

        self.assertEqual(response.status_code, 403)
        self.assertIn('no está autorizado', str(response.data['detail']))

    def test_acceso_revocado_responde_403(self):
        self.estudiante.estado = 'revoked'
        self.estudiante.save()

        response = self.cliente(self.estudiante).get('/api/talleres/')

        self.assertEqual(response.status_code, 403)

    def test_el_correo_se_compara_sin_mayusculas(self):
        cliente = APIClient()
        cliente.force_authenticate(user=crear_cuenta('Profesor@UCEN.cl'))

        response = cliente.get('/api/auth/yo/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['rol'], 'teacher')


class UsuarioActualTests(PermisosTestCase):
    def test_devuelve_correo_y_rol_de_la_whitelist(self):
        response = self.cliente(self.profesor).get('/api/auth/yo/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['correo'], 'profesor@ucen.cl')
        self.assertEqual(response.data['rol'], 'teacher')
        self.assertFalse(response.data['es_superusuario'])

    def test_superusuario_sin_whitelist_no_tiene_rol(self):
        superusuario = get_user_model().objects.create_superuser(
            username='root', email='root@ejemplo.cl', password=None,
        )
        cliente = APIClient()
        cliente.force_authenticate(user=superusuario)

        response = cliente.get('/api/auth/yo/')

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data['rol'])
        self.assertTrue(response.data['es_superusuario'])

    def test_sin_sesion_responde_401(self):
        self.assertEqual(APIClient().get('/api/auth/yo/').status_code, 401)


# ─────────────────────────────────────────────
# Roles por recurso
# ─────────────────────────────────────────────


class UsuariosPermisosTests(PermisosTestCase):
    endpoint = '/api/usuarios/'

    def test_solo_el_administrador_gestiona_la_whitelist(self):
        self.assertEqual(self.cliente(self.administrador).get(self.endpoint).status_code, 200)
        for usuario in (self.estudiante, self.profesor):
            with self.subTest(rol=usuario.rol):
                self.assertEqual(self.cliente(usuario).get(self.endpoint).status_code, 403)

        response = self.cliente(self.administrador).post(
            self.endpoint, {'correo': 'nuevo@ucen.cl'}, format='json',
        )
        self.assertEqual(response.status_code, 201)


class TalleresPermisosTests(PermisosTestCase):
    endpoint = '/api/talleres/'
    payload = {
        'numero': 2,
        'titulo': 'Del aula a la transformación profesional',
        'objetivo': 'o',
        'actividad': 'a',
        'producto': 'p',
    }

    def test_estudiante_lee_pero_no_crea(self):
        cliente = self.cliente(self.estudiante)

        self.assertEqual(cliente.get(self.endpoint).status_code, 200)
        self.assertEqual(cliente.post(self.endpoint, self.payload, format='json').status_code, 403)

    def test_profesor_crea_y_edita(self):
        cliente = self.cliente(self.profesor)

        self.assertEqual(cliente.post(self.endpoint, self.payload, format='json').status_code, 201)
        response = cliente.patch(f'{self.endpoint}{self.taller.pk}/', {'intentos_maximos': 2}, format='json')
        self.assertEqual(response.status_code, 200)

    def test_administrador_no_accede_a_los_talleres(self):
        self.assertEqual(self.cliente(self.administrador).get(self.endpoint).status_code, 403)


class PreguntasPermisosTests(PermisosTestCase):
    endpoint = '/api/preguntas/'

    def setUp(self):
        super().setUp()
        self.pregunta = PreguntaTeorica.objects.create(enunciado='¿Qué es un incidente crítico?')
        Alternativa.objects.create(pregunta=self.pregunta, texto='Un hecho significativo', es_correcta=True)
        Alternativa.objects.create(pregunta=self.pregunta, texto='Una evaluación')
        PreguntaTeorica.objects.create(enunciado='Pregunta retirada', activa=False)

    def test_estudiante_no_ve_la_respuesta_correcta_ni_preguntas_inactivas(self):
        response = self.cliente(self.estudiante).get(self.endpoint)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        for alternativa in response.data[0]['alternativas']:
            self.assertNotIn('es_correcta', alternativa)

    def test_profesor_ve_la_respuesta_correcta_y_todas_las_preguntas(self):
        response = self.cliente(self.profesor).get(self.endpoint)

        self.assertEqual(len(response.data), 2)
        pregunta = next(p for p in response.data if p['id'] == self.pregunta.pk)
        self.assertIn('es_correcta', pregunta['alternativas'][0])

    def test_estudiante_no_crea_preguntas(self):
        response = self.cliente(self.estudiante).post(
            self.endpoint, {'enunciado': 'Nueva'}, format='json',
        )

        self.assertEqual(response.status_code, 403)


class IntentosPermisosTests(PermisosTestCase):
    endpoint = '/api/intentos-cuestionario/'

    def payload(self, estudiante, numero_intento=1):
        return {
            'estudiante': estudiante.pk,
            'numero_intento': numero_intento,
            'respuestas_correctas': 8,
            'nota': 5.6,
            'aprobado': True,
        }

    def test_estudiante_registra_sus_intentos_pero_no_los_de_otro(self):
        cliente = self.cliente(self.estudiante)

        propio = cliente.post(self.endpoint, self.payload(self.estudiante), format='json')
        ajeno = cliente.post(self.endpoint, self.payload(self.otro_estudiante), format='json')

        self.assertEqual(propio.status_code, 201)
        self.assertEqual(ajeno.status_code, 403)
        self.assertFalse(IntentoCuestionario.objects.filter(estudiante=self.otro_estudiante).exists())

    def test_estudiante_solo_ve_sus_intentos(self):
        IntentoCuestionario.objects.create(
            estudiante=self.estudiante, numero_intento=1, respuestas_correctas=8, nota=Decimal('5.6'),
        )
        ajeno = IntentoCuestionario.objects.create(
            estudiante=self.otro_estudiante, numero_intento=1, respuestas_correctas=5, nota=Decimal('3.5'),
        )
        cliente = self.cliente(self.estudiante)

        lista = cliente.get(self.endpoint)

        self.assertEqual([i['estudiante'] for i in lista.data], [self.estudiante.pk])
        self.assertEqual(cliente.get(f'{self.endpoint}{ajeno.pk}/').status_code, 404)

    def test_un_intento_rendido_no_se_modifica(self):
        intento = IntentoCuestionario.objects.create(
            estudiante=self.estudiante, numero_intento=1, respuestas_correctas=5, nota=Decimal('3.5'),
        )

        response = self.cliente(self.estudiante).patch(
            f'{self.endpoint}{intento.pk}/', {'nota': 7.0}, format='json',
        )

        self.assertEqual(response.status_code, 403)

    def test_profesor_ve_todos_pero_no_registra(self):
        IntentoCuestionario.objects.create(
            estudiante=self.estudiante, numero_intento=1, respuestas_correctas=8, nota=Decimal('5.6'),
        )
        IntentoCuestionario.objects.create(
            estudiante=self.otro_estudiante, numero_intento=1, respuestas_correctas=5, nota=Decimal('3.5'),
        )
        cliente = self.cliente(self.profesor)

        self.assertEqual(len(cliente.get(self.endpoint).data), 2)
        response = cliente.post(self.endpoint, self.payload(self.estudiante, 2), format='json')
        self.assertEqual(response.status_code, 403)


class ReflexionesPermisosTests(PermisosTestCase):
    endpoint = '/api/reflexiones/'

    def test_estudiante_no_puede_pasar_su_reflexion_a_otro(self):
        reflexion = Reflexion.objects.create(estudiante=self.estudiante, taller=self.taller)

        response = self.cliente(self.estudiante).patch(
            f'{self.endpoint}{reflexion.pk}/', {'estudiante': self.otro_estudiante.pk}, format='json',
        )

        self.assertEqual(response.status_code, 403)
        reflexion.refresh_from_db()
        self.assertEqual(reflexion.estudiante, self.estudiante)

    def test_estudiante_no_ve_ni_edita_reflexiones_ajenas(self):
        ajena = Reflexion.objects.create(estudiante=self.otro_estudiante, taller=self.taller)
        cliente = self.cliente(self.estudiante)

        self.assertEqual(cliente.get(f'{self.endpoint}{ajena.pk}/').status_code, 404)
        response = cliente.patch(f'{self.endpoint}{ajena.pk}/', {'contexto': 'x'}, format='json')
        self.assertEqual(response.status_code, 404)

    def test_profesor_lee_pero_no_escribe_reflexiones(self):
        Reflexion.objects.create(estudiante=self.estudiante, taller=self.taller)
        cliente = self.cliente(self.profesor)

        self.assertEqual(len(cliente.get(self.endpoint).data), 1)
        response = cliente.post(
            self.endpoint,
            {'estudiante': self.estudiante.pk, 'taller': self.taller.pk},
            format='json',
        )
        self.assertEqual(response.status_code, 403)


class RetroalimentacionesPermisosTests(PermisosTestCase):
    endpoint = '/api/retroalimentaciones/'

    def setUp(self):
        super().setUp()
        self.propia = Retroalimentacion.objects.create(
            reflexion=Reflexion.objects.create(estudiante=self.estudiante, taller=self.taller),
            propuesta_ia='Profundiza en los actores.',
        )
        Retroalimentacion.objects.create(
            reflexion=Reflexion.objects.create(estudiante=self.otro_estudiante, taller=self.taller),
            propuesta_ia='Describe el contexto.',
        )

    def test_estudiante_solo_lee_la_de_sus_reflexiones(self):
        cliente = self.cliente(self.estudiante)

        lista = cliente.get(self.endpoint)

        self.assertEqual([r['id'] for r in lista.data], [self.propia.pk])
        response = cliente.patch(
            f'{self.endpoint}{self.propia.pk}/', {'estado': 'validated'}, format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_profesor_valida_la_retroalimentacion(self):
        response = self.cliente(self.profesor).patch(
            f'{self.endpoint}{self.propia.pk}/', {'estado': 'validated'}, format='json',
        )

        self.assertEqual(response.status_code, 200)


class EvaluacionesPermisosTests(PermisosTestCase):
    endpoint = '/api/evaluaciones/'

    def payload(self):
        return {
            'estudiante': self.estudiante.pk,
            'taller': self.taller.pk,
            'nota': 7.0,
            'resultado': 'approved',
        }

    def test_solo_el_profesor_pone_notas(self):
        respuesta_estudiante = self.cliente(self.estudiante).post(self.endpoint, self.payload(), format='json')
        respuesta_profesor = self.cliente(self.profesor).post(self.endpoint, self.payload(), format='json')

        self.assertEqual(respuesta_estudiante.status_code, 403)
        self.assertEqual(respuesta_profesor.status_code, 201)

    def test_estudiante_solo_ve_sus_notas(self):
        Evaluacion.objects.create(
            estudiante=self.estudiante, taller=self.taller, nota=Decimal('6.0'), resultado='approved',
        )
        Evaluacion.objects.create(
            estudiante=self.otro_estudiante, taller=self.taller, nota=Decimal('3.0'), resultado='failed',
        )

        lista = self.cliente(self.estudiante).get(self.endpoint)

        self.assertEqual([e['estudiante'] for e in lista.data], [self.estudiante.pk])


class InnovacionesPermisosTests(PermisosTestCase):
    endpoint = '/api/innovaciones/'

    def setUp(self):
        super().setUp()
        datos = {
            'categoria': 'teaching',
            'resumen': 'r',
            'contexto': 'c',
            'desafio': 'd',
            'actuacion': 'a',
            'impacto_esperado': 'i',
        }
        self.publicada = Innovacion.objects.create(titulo='Publicada', publicada=True, **datos)
        Innovacion.objects.create(titulo='Borrador', **datos)

    def test_estudiante_solo_ve_las_publicadas(self):
        cliente = self.cliente(self.estudiante)

        self.assertEqual([i['id'] for i in cliente.get(self.endpoint).data], [self.publicada.pk])
        # Pedir los borradores explícitamente tampoco los muestra.
        self.assertEqual(cliente.get(f'{self.endpoint}?publicada=false').data, [])

    def test_profesor_ve_borradores_y_publica(self):
        cliente = self.cliente(self.profesor)

        self.assertEqual(len(cliente.get(self.endpoint).data), 2)
        borrador = Innovacion.objects.get(titulo='Borrador')
        response = cliente.patch(f'{self.endpoint}{borrador.pk}/', {'publicada': True}, format='json')
        self.assertEqual(response.status_code, 200)

    def test_estudiante_no_publica(self):
        response = self.cliente(self.estudiante).patch(
            f'{self.endpoint}{self.publicada.pk}/', {'publicada': False}, format='json',
        )

        self.assertEqual(response.status_code, 403)
