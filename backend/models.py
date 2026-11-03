import re
import bcrypt
from config import DatabaseConfig

# ───────────────────────── Validaciones (regex) ─────────────────────────
RE_NOMBRE = re.compile(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]+$')
RE_CARRERA = re.compile(r'^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑüÜ\s.,&()-]+$')
RE_EMAIL = re.compile(r'^[\w.+-]+@[\w-]+(\.[\w-]+)+$')
RE_TELEFONO = re.compile(r'^\+?[0-9\s-]{7,20}$')
RE_USERNAME = re.compile(r'^[a-zA-Z0-9_]{3,50}$')


def validar_estudiante(data, parcial=False):
    """Devuelve dict {campo: mensaje}. Vacío = datos válidos.
    parcial=True (PUT) solo valida los campos enviados."""
    errores = {}
    if not isinstance(data, dict):
        return {'general': 'El cuerpo debe ser un objeto JSON'}

    def presente(c):
        return c in data and data[c] not in (None, '')

    for campo in ('nombre', 'apellido', 'edad', 'carrera'):
        if not presente(campo) and not parcial:
            errores[campo] = f'El campo {campo} es obligatorio'

    for campo in ('nombre', 'apellido'):
        if presente(campo):
            v = str(data[campo]).strip()
            if len(v) < 2 or len(v) > 100:
                errores[campo] = f'El {campo} debe tener entre 2 y 100 caracteres'
            elif not RE_NOMBRE.match(v):
                errores[campo] = f'El {campo} solo puede contener letras'

    if presente('edad'):
        try:
            if isinstance(data['edad'], bool):
                raise ValueError
            edad = int(data['edad'])
            if edad < 15 or edad > 100:
                errores['edad'] = 'La edad debe estar entre 15 y 100'
        except (ValueError, TypeError):
            errores['edad'] = 'La edad debe ser un número entero'

    if presente('carrera'):
        v = str(data['carrera']).strip()
        if len(v) < 3 or len(v) > 150:
            errores['carrera'] = 'La carrera debe tener entre 3 y 150 caracteres'
        elif not RE_CARRERA.match(v):
            errores['carrera'] = 'La carrera contiene caracteres no permitidos'

    if presente('email'):
        v = str(data['email']).strip()
        if len(v) > 150 or not RE_EMAIL.match(v):
            errores['email'] = 'El email no tiene un formato válido'

    if presente('telefono'):
        if not RE_TELEFONO.match(str(data['telefono']).strip()):
            errores['telefono'] = 'El teléfono debe tener entre 7 y 20 dígitos (puede iniciar con +)'
    return errores


def validar_registro(data):
    errores = {}
    if not isinstance(data, dict):
        return {'general': 'El cuerpo debe ser un objeto JSON'}
    username = str(data.get('username') or '').strip()
    email = str(data.get('email') or '').strip()
    password = str(data.get('password') or '')
    if not RE_USERNAME.match(username):
        errores['username'] = 'El usuario debe tener 3-50 caracteres (letras, números o _)'
    if len(email) > 100 or not RE_EMAIL.match(email):
        errores['email'] = 'El email no tiene un formato válido'
    if len(password) < 6:
        errores['password'] = 'La contraseña debe tener mínimo 6 caracteres'
    elif len(password.encode('utf-8')) > 72:
        errores['password'] = 'La contraseña es demasiado larga (máx. 72 bytes)'
    return errores


# ───────────────────────── Helper de ejecución ─────────────────────────
def ejecutar(sql, params=(), fetch=None, commit=False):
    """Ejecuta una consulta parametrizada. fetch: None | 'one' | 'all'.
    Devuelve (resultado, lastrowid, rowcount). Lanza ConnectionError si no hay BD."""
    conn = DatabaseConfig.get_connection()
    if not conn:
        raise ConnectionError('No se pudo conectar a la base de datos')
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        resultado = None
        if fetch == 'one':
            resultado = cur.fetchone()
        elif fetch == 'all':
            resultado = cur.fetchall()
        if commit:
            conn.commit()
        last, count = cur.lastrowid, cur.rowcount
        cur.close()
        return resultado, last, count
    finally:
        conn.close()


# ───────────────────────── Tablas ─────────────────────────
def crear_tablas():
    ejecutar("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            email VARCHAR(100) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            rol ENUM('admin','usuario') NOT NULL DEFAULT 'usuario',
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ultimo_acceso DATETIME NULL
        )""", commit=True)
    ejecutar("""
        CREATE TABLE IF NOT EXISTS estudiantes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nombre VARCHAR(100) NOT NULL,
            apellido VARCHAR(100) NOT NULL,
            edad INT NOT NULL,
            carrera VARCHAR(150) NOT NULL,
            email VARCHAR(150) NULL UNIQUE,
            telefono VARCHAR(20) NULL,
            creado_por VARCHAR(50) NULL,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_apellido (apellido),
            INDEX idx_carrera (carrera)
        )""", commit=True)
    ejecutar("""
        CREATE TABLE IF NOT EXISTS token_blacklist (
            jti VARCHAR(64) PRIMARY KEY,
            expira DATETIME NOT NULL,
            INDEX idx_expira (expira)
        )""", commit=True)


def crear_admin_por_defecto():
    existe, _, _ = ejecutar("SELECT id FROM usuarios WHERE username=%s", ('admin',), fetch='one')
    if not existe:
        ejecutar(
            "INSERT INTO usuarios (username, email, password_hash, rol) VALUES (%s,%s,%s,'admin')",
            ('admin', 'admin@unilibre.edu.co', hash_password('admin123')), commit=True)
        print('Usuario admin creado (admin / admin123) - cambiar en producción')


# ───────────────────────── Seguridad ─────────────────────────
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verificar_password(password, hashed):
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except ValueError:
        return False


class Usuario:
    @staticmethod
    def por_username(username):
        return ejecutar("SELECT * FROM usuarios WHERE username=%s", (username,), fetch='one')[0]

    @staticmethod
    def por_id(uid):
        return ejecutar("SELECT * FROM usuarios WHERE id=%s", (uid,), fetch='one')[0]

    @staticmethod
    def existe(username, email):
        return ejecutar("SELECT username, email FROM usuarios WHERE username=%s OR email=%s",
                        (username, email), fetch='all')[0]

    @staticmethod
    def crear(username, email, password):
        _, uid, _ = ejecutar(
            "INSERT INTO usuarios (username, email, password_hash, rol) VALUES (%s,%s,%s,'usuario')",
            (username, email, hash_password(password)), commit=True)
        return uid

    @staticmethod
    def registrar_acceso(uid):
        ejecutar("UPDATE usuarios SET ultimo_acceso=NOW() WHERE id=%s", (uid,), commit=True)


class TokenBlacklist:
    @staticmethod
    def revocar(jti, expira_dt):
        ejecutar("DELETE FROM token_blacklist WHERE expira < NOW()", commit=True)  # limpieza
        ejecutar("INSERT IGNORE INTO token_blacklist (jti, expira) VALUES (%s,%s)",
                 (jti, expira_dt), commit=True)

    @staticmethod
    def esta_revocado(jti):
        return ejecutar("SELECT jti FROM token_blacklist WHERE jti=%s", (jti,), fetch='one')[0] is not None
