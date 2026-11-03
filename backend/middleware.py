import jwt
from functools import wraps
from flask import request, jsonify, g
from config import JWTConfig
from models import TokenBlacklist


def token_requerido(f):
    """Protege una ruta: exige 'Authorization: Bearer <token>' válido y no revocado."""
    @wraps(f)
    def decorado(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        partes = auth.split()
        if len(partes) != 2 or partes[0].lower() != 'bearer':
            return jsonify({'error': 'Token de autenticación requerido'}), 401
        token = partes[1]
        try:
            payload = jwt.decode(token, JWTConfig.SECRET_KEY, algorithms=[JWTConfig.ALGORITHM])
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expirado, inicia sesión nuevamente'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token inválido'}), 401
        try:
            if TokenBlacklist.esta_revocado(payload.get('jti')):
                return jsonify({'error': 'Token revocado, inicia sesión nuevamente'}), 401
        except ConnectionError:
            return jsonify({'error': 'Error de conexión con la base de datos'}), 500
        g.usuario = payload
        g.token = token
        return f(*args, **kwargs)
    return decorado


def admin_requerido(f):
    """Exige token válido y rol admin."""
    @wraps(f)
    @token_requerido
    def decorado(*args, **kwargs):
        if g.usuario.get('rol') != 'admin':
            return jsonify({'error': 'Acceso denegado: se requiere rol de administrador'}), 403
        return f(*args, **kwargs)
    return decorado
