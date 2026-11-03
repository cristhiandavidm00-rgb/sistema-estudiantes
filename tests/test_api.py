"""Pruebas sin MySQL: se sustituye la capa de BD por un doble en memoria.
Ejecutar:  cd proyecto-crud && python -m unittest discover -s tests -v
(en un entorno con bcrypt instalado se usa el real; si no, un sustituto simple)"""
import os, sys, unittest, types
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
try:
    import bcrypt  # noqa
except ImportError:  # solo para poder probar sin la dependencia
    fake = types.ModuleType('bcrypt')
    fake.gensalt = lambda: b'salt'
    fake.hashpw = lambda p, s: b'h:' + p
    fake.checkpw = lambda p, h: h == b'h:' + p
    sys.modules['bcrypt'] = fake

import models
import app as appmod

SQL = []
USUARIOS = {'admin': dict(id=1, username='admin', email='a@x.co', rol='admin',
                          password_hash='h:admin123', fecha_creacion=datetime.now(), ultimo_acceso=None),
            'ana': dict(id=2, username='ana', email='ana@x.co', rol='usuario',
                        password_hash=models.hash_password('ana123'), fecha_creacion=datetime.now(), ultimo_acceso=None)}
USUARIOS['admin']['password_hash'] = models.hash_password('admin123')
REVOCADOS = set()


def fake_ejecutar(sql, params=(), fetch=None, commit=False):
    s = ' '.join(sql.split())
    SQL.append((s, list(params)))
    if s.startswith('DELETE FROM token_blacklist'):
        return None, None, 0
    if s.startswith('INSERT IGNORE INTO token_blacklist'):
        REVOCADOS.add(params[0]); return None, None, 1
    if 'FROM token_blacklist' in s:
        return ({'jti': params[0]} if params[0] in REVOCADOS else None), None, 0
    if 'FROM usuarios WHERE username=%s OR email' in s:
        return [u for u in USUARIOS.values() if u['username'] == params[0] or u['email'] == params[1]], None, 0
    if 'FROM usuarios WHERE username' in s:
        return USUARIOS.get(params[0]), None, 0
    if 'FROM usuarios WHERE id' in s:
        return next((u for u in USUARIOS.values() if u['id'] == params[0]), None), None, 0
    if s.startswith('UPDATE usuarios'):
        return None, None, 1
    if s.startswith('INSERT INTO usuarios'):
        return None, 3, 1
    if 'COUNT(*) AS total FROM estudiantes' in s and 'AVG' not in s:
        return {'total': 12}, None, 0
    if 'AVG(edad)' in s:
        return {'total': 3, 'promedio': 21.0, 'minima': 20, 'maxima': 22}, None, 0
    if 'GROUP BY carrera' in s:
        return [{'carrera': 'Sistemas', 'cantidad': 2}], None, 0
    if s.startswith('SELECT id, nombre') and 'LIMIT' in s:
        return [{'id': 1, 'nombre': 'Juan', 'fecha_creacion': datetime(2024, 1, 1)}], None, 0
    if s.startswith('SELECT id FROM estudiantes WHERE email'):
        return ({'id': 99} if params[0] == 'dup@x.co' else None), None, 0
    if s.startswith('SELECT id FROM estudiantes WHERE id'):
        return ({'id': params[0]} if params[0] != 404 else None), None, 0
    if s.startswith('SELECT id, nombre'):
        return ({'id': params[0], 'nombre': 'Juan', 'fecha_creacion': None} if params[0] != 404 else None), None, 0
    if s.startswith('INSERT INTO estudiantes'):
        return None, 15, 1
    if s.startswith('UPDATE estudiantes'):
        return None, None, 1
    if s.startswith('DELETE FROM estudiantes'):
        return None, None, (0 if params[0] == 404 else 1)
    raise AssertionError('SQL no previsto: ' + s)


models.ejecutar = fake_ejecutar
import routes.estudiantes as rest
rest.ejecutar = fake_ejecutar

VALIDO = {'nombre': 'María', 'apellido': 'González', 'edad': 22, 'carrera': 'Ingeniería Financiera',
          'email': 'maria@unilibre.edu.co', 'telefono': '+57 311 2345678'}


class Base(unittest.TestCase):
    def setUp(self):
        self.c = appmod.app.test_client()
        SQL.clear(); REVOCADOS.clear()

    def login(self, u, p):
        r = self.c.post('/api/auth/login', json={'username': u, 'password': p})
        return r, ({'Authorization': 'Bearer ' + r.json['token']} if r.status_code == 200 else {})


class TestValidaciones(unittest.TestCase):
    def test_valido(self):
        self.assertEqual(models.validar_estudiante(VALIDO), {})

    def test_errores_por_campo(self):
        e = models.validar_estudiante({'nombre': 'J0', 'apellido': '', 'edad': 14, 'carrera': 'x',
                                       'email': 'malo', 'telefono': 'abc'})
        self.assertEqual(set(e), {'nombre', 'apellido', 'edad', 'carrera', 'email', 'telefono'})

    def test_edad_no_numerica_ni_bool(self):
        self.assertIn('edad', models.validar_estudiante({**VALIDO, 'edad': 'veinte'}))
        self.assertIn('edad', models.validar_estudiante({**VALIDO, 'edad': True}))

    def test_parcial(self):
        self.assertEqual(models.validar_estudiante({'edad': 23}, parcial=True), {})
        self.assertIn('edad', models.validar_estudiante({'edad': 101}, parcial=True))

    def test_registro(self):
        self.assertEqual(models.validar_registro({'username': 'nuevo_1', 'email': 'a@b.co', 'password': '123456'}), {})
        self.assertEqual(set(models.validar_registro({'username': 'a', 'email': 'x', 'password': '1'})),
                         {'username', 'email', 'password'})


class TestAuth(Base):
    def test_login_ok_y_payload(self):
        import jwt
        r, _ = self.login('admin', 'admin123')
        self.assertEqual(r.status_code, 200)
        p = jwt.decode(r.json['token'], appmod.app.config.get('X', None) or __import__('config').JWTConfig.SECRET_KEY,
                       algorithms=['HS256'])
        self.assertEqual((p['username'], p['rol']), ('admin', 'admin'))
        self.assertEqual(p['exp'] - p['iat'], 3600)
        self.assertTrue(p['jti'])

    def test_login_mal(self):
        self.assertEqual(self.login('admin', 'x')[0].status_code, 401)
        self.assertEqual(self.login('noexiste', 'x')[0].status_code, 401)
        self.assertEqual(self.c.post('/api/auth/login', json={}).status_code, 400)

    def test_registro(self):
        r = self.c.post('/api/auth/registro', json={'username': 'nuevo', 'email': 'n@x.co', 'password': 'abc123'})
        self.assertEqual(r.status_code, 201)
        r = self.c.post('/api/auth/registro', json={'username': 'ana', 'email': 'otro@x.co', 'password': 'abc123'})
        self.assertEqual(r.status_code, 409); self.assertIn('username', r.json['errores'])
        r = self.c.post('/api/auth/registro', json={'username': 'a', 'email': 'x', 'password': '1'})
        self.assertEqual(r.status_code, 400)

    def test_sin_token_token_malo_y_logout(self):
        self.assertEqual(self.c.get('/api/estudiantes').status_code, 401)
        self.assertEqual(self.c.get('/api/estudiantes', headers={'Authorization': 'Bearer xx'}).status_code, 401)
        _, h = self.login('ana', 'ana123')
        self.assertEqual(self.c.get('/api/auth/perfil', headers=h).status_code, 200)
        self.assertEqual(self.c.post('/api/auth/logout', headers=h).status_code, 200)
        r = self.c.get('/api/estudiantes', headers=h)  # blacklist
        self.assertEqual(r.status_code, 401); self.assertIn('revocado', r.json['error'])

    def test_token_expirado(self):
        import jwt, config
        from datetime import timedelta, timezone
        t = jwt.encode({'usuario_id': 1, 'username': 'a', 'rol': 'admin', 'jti': 'z',
                        'exp': datetime.now(timezone.utc) - timedelta(seconds=5)},
                       config.JWTConfig.SECRET_KEY, algorithm='HS256')
        r = self.c.get('/api/estudiantes', headers={'Authorization': 'Bearer ' + t})
        self.assertEqual(r.status_code, 401); self.assertIn('expirado', r.json['error'])


class TestEstudiantes(Base):
    def test_listado_paginado_y_sql_seguro(self):
        _, h = self.login('ana', 'ana123')
        r = self.c.get("/api/estudiantes?page=2&per_page=5&search=ing&orden=nombre;DROP&direccion=desc", headers=h)
        self.assertEqual(r.status_code, 200)
        p = r.json['paginacion']
        self.assertEqual((p['page'], p['per_page'], p['total_items'], p['total_pages'], p['has_prev'], p['has_next']),
                         (2, 5, 12, 3, True, True))
        sql, params = [x for x in SQL if 'LIMIT' in x[0]][0]
        self.assertIn('ORDER BY id DESC', sql)          # orden inválido -> id (lista blanca)
        self.assertNotIn('DROP', sql)
        self.assertEqual(params, ['%ing%'] * 3 + [5, 5])  # búsqueda parametrizada, offset=(2-1)*5

    def test_per_page_maximo_50_y_params_invalidos(self):
        _, h = self.login('ana', 'ana123')
        self.assertEqual(self.c.get('/api/estudiantes?per_page=999', headers=h).json['paginacion']['per_page'], 50)
        self.assertEqual(self.c.get('/api/estudiantes?page=abc', headers=h).status_code, 400)

    def test_stats(self):
        _, h = self.login('ana', 'ana123')
        r = self.c.get('/api/estudiantes/stats/general', headers=h)
        self.assertEqual((r.status_code, r.json['promedio_edad'], r.json['edad_maxima']), (200, 21.0, 22))

    def test_crear(self):
        _, h = self.login('ana', 'ana123')
        r = self.c.post('/api/estudiantes', json=VALIDO, headers=h)
        self.assertEqual((r.status_code, r.json['id'], r.json['creado_por']), (201, 15, 'ana'))
        self.assertEqual(self.c.post('/api/estudiantes', json={**VALIDO, 'edad': 5}, headers=h).status_code, 400)
        r = self.c.post('/api/estudiantes', json={**VALIDO, 'email': 'dup@x.co'}, headers=h)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(self.c.post('/api/estudiantes', data='no json', headers=h).status_code, 400)

    def test_actualizar(self):
        _, h = self.login('ana', 'ana123')
        r = self.c.put('/api/estudiantes/1', json={'nombre': 'María Fernanda', 'edad': 23}, headers=h)
        self.assertEqual((r.status_code, r.json['actualizado_por']), (200, 'ana'))
        self.assertEqual(self.c.put('/api/estudiantes/404', json={'edad': 20}, headers=h).status_code, 404)
        self.assertEqual(self.c.put('/api/estudiantes/1', json={'edad': 200}, headers=h).status_code, 400)
        self.assertEqual(self.c.put('/api/estudiantes/1', json={}, headers=h).status_code, 400)

    def test_obtener(self):
        _, h = self.login('ana', 'ana123')
        self.assertEqual(self.c.get('/api/estudiantes/1', headers=h).status_code, 200)
        self.assertEqual(self.c.get('/api/estudiantes/404', headers=h).status_code, 404)

    def test_delete_solo_admin(self):
        _, ha = self.login('ana', 'ana123')
        self.assertEqual(self.c.delete('/api/estudiantes/1', headers=ha).status_code, 403)
        _, hd = self.login('admin', 'admin123')
        r = self.c.delete('/api/estudiantes/1', headers=hd)
        self.assertEqual((r.status_code, r.json['eliminado_por']), (200, 'admin'))
        self.assertEqual(self.c.delete('/api/estudiantes/404', headers=hd).status_code, 404)

    def test_cors(self):
        r = self.c.options('/api/estudiantes', headers={'Origin': 'http://localhost:8000'})
        self.assertEqual(r.status_code, 204)
        self.assertEqual(r.headers['Access-Control-Allow-Origin'], 'http://localhost:8000')
        r = self.c.options('/api/estudiantes', headers={'Origin': 'http://malo.com'})
        self.assertNotIn('Access-Control-Allow-Origin', r.headers)


if __name__ == '__main__':
    unittest.main()
