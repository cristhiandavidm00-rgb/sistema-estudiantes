import uuid
from datetime import datetime, timedelta, timezone
import jwt
from flask import Blueprint, request, jsonify, g
from config import JWTConfig
from middleware import token_requerido
from models import (Usuario, TokenBlacklist, validar_registro, verificar_password)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


def _generar_token(usuario):
    ahora = datetime.now(timezone.utc)
    payload = {
        'usuario_id': usuario['id'],
        'username': usuario['username'],
        'rol': usuario['rol'],
        'iat': ahora,
        'exp': ahora + timedelta(hours=JWTConfig.EXPIRATION_HOURS),
        'jti': str(uuid.uuid4()),
    }
    return jwt.encode(payload, JWTConfig.SECRET_KEY, algorithm=JWTConfig.ALGORITHM)


@auth_bp.route('/registro', methods=['POST'])
def registro():
    data = request.get_json(silent=True)
    errores = validar_registro(data)
    if errores:
        return jsonify({'error': 'Datos inválidos', 'errores': errores}), 400
    username, email = data['username'].strip(), data['email'].strip()
    for fila in Usuario.existe(username, email):
        if fila['username'].lower() == username.lower():
            errores['username'] = 'El nombre de usuario ya está en uso'
        if fila['email'].lower() == email.lower():
            errores['email'] = 'El email ya está registrado'
    if errores:
        return jsonify({'error': 'Datos inválidos', 'errores': errores}), 409
    uid = Usuario.crear(username, email, data['password'])
    return jsonify({'mensaje': 'Usuario registrado exitosamente',
                    'usuario': {'id': uid, 'username': username, 'email': email}}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    username = str(data.get('username') or '').strip()
    password = str(data.get('password') or '')
    if not username or not password:
        return jsonify({'error': 'Usuario y contraseña son obligatorios'}), 400
    usuario = Usuario.por_username(username)
    # Mismo mensaje para usuario inexistente o clave errónea (no revela cuál falló)
    if not usuario or not verificar_password(password, usuario['password_hash']):
        return jsonify({'error': 'Credenciales incorrectas'}), 401
    Usuario.registrar_acceso(usuario['id'])
    return jsonify({
        'mensaje': 'Login exitoso',
        'token': _generar_token(usuario),
        'usuario': {'id': usuario['id'], 'username': usuario['username'],
                    'email': usuario['email'], 'rol': usuario['rol']},
    }), 200


@auth_bp.route('/logout', methods=['POST'])
@token_requerido
def logout():
    expira = datetime.fromtimestamp(g.usuario['exp'], tz=timezone.utc).replace(tzinfo=None)
    TokenBlacklist.revocar(g.usuario['jti'], expira)
    return jsonify({'mensaje': 'Logout exitoso'}), 200


@auth_bp.route('/perfil', methods=['GET'])
@token_requerido
def perfil():
    u = Usuario.por_id(g.usuario['usuario_id'])
    if not u:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    return jsonify({'usuario': {
        'id': u['id'], 'username': u['username'], 'email': u['email'], 'rol': u['rol'],
        'fecha_creacion': u['fecha_creacion'].isoformat() if u['fecha_creacion'] else None,
        'ultimo_acceso': u['ultimo_acceso'].isoformat() if u['ultimo_acceso'] else None,
    }}), 200
