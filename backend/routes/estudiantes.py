from math import ceil
from flask import Blueprint, request, jsonify, g
from middleware import token_requerido, admin_requerido
from models import ejecutar, validar_estudiante

estudiantes_bp = Blueprint('estudiantes', __name__, url_prefix='/api/estudiantes')

CAMPOS_ORDEN = {'id', 'nombre', 'apellido', 'edad', 'carrera'}   # lista blanca (evita SQL injection)
COLUMNAS = 'id, nombre, apellido, edad, carrera, email, telefono, fecha_creacion'


def _limpio(data, campo):
    v = data.get(campo)
    if v is None:
        return None
    v = str(v).strip()
    return v or None


def _serializar(fila):
    if fila.get('fecha_creacion'):
        fila['fecha_creacion'] = fila['fecha_creacion'].isoformat()
    return fila


def _email_duplicado(email, excluir_id=None):
    if not email:
        return False
    fila = ejecutar("SELECT id FROM estudiantes WHERE email=%s AND id<>%s",
                    (email, excluir_id or 0), fetch='one')[0]
    return fila is not None


@estudiantes_bp.route('', methods=['GET'])
@token_requerido
def listar():
    try:
        page = max(int(request.args.get('page', 1)), 1)
        per_page = min(max(int(request.args.get('per_page', 5)), 1), 50)
    except ValueError:
        return jsonify({'error': 'page y per_page deben ser enteros'}), 400
    search = request.args.get('search', '').strip()
    orden = request.args.get('orden', 'id')
    direccion = request.args.get('direccion', 'asc').lower()
    if orden not in CAMPOS_ORDEN:
        orden = 'id'
    direccion = 'DESC' if direccion == 'desc' else 'ASC'

    where, params = '', []
    if search:
        where = 'WHERE nombre LIKE %s OR apellido LIKE %s OR carrera LIKE %s'
        params = [f'%{search}%'] * 3

    total = ejecutar(f'SELECT COUNT(*) AS total FROM estudiantes {where}', params, fetch='one')[0]['total']
    offset = (page - 1) * per_page
    filas = ejecutar(
        f'SELECT {COLUMNAS} FROM estudiantes {where} ORDER BY {orden} {direccion} LIMIT %s OFFSET %s',
        params + [per_page, offset], fetch='all')[0]
    total_pages = max(ceil(total / per_page), 1)
    return jsonify({
        'estudiantes': [_serializar(f) for f in filas],
        'paginacion': {'page': page, 'per_page': per_page, 'total_items': total,
                       'total_pages': total_pages, 'has_prev': page > 1, 'has_next': page < total_pages},
    }), 200


@estudiantes_bp.route('/stats/general', methods=['GET'])
@token_requerido
def estadisticas():
    r = ejecutar("""SELECT COUNT(*) AS total, ROUND(AVG(edad),1) AS promedio,
                    MIN(edad) AS minima, MAX(edad) AS maxima FROM estudiantes""", fetch='one')[0]
    carreras = ejecutar("""SELECT carrera, COUNT(*) AS cantidad FROM estudiantes
                           GROUP BY carrera ORDER BY cantidad DESC, carrera""", fetch='all')[0]
    return jsonify({
        'total_estudiantes': r['total'],
        'promedio_edad': float(r['promedio']) if r['promedio'] is not None else 0,
        'edad_minima': r['minima'], 'edad_maxima': r['maxima'],
        'estudiantes_por_carrera': carreras,
    }), 200


@estudiantes_bp.route('/<int:id>', methods=['GET'])
@token_requerido
def obtener(id):
    fila = ejecutar(f'SELECT {COLUMNAS} FROM estudiantes WHERE id=%s', (id,), fetch='one')[0]
    if not fila:
        return jsonify({'error': 'Estudiante no encontrado'}), 404
    return jsonify(_serializar(fila)), 200


@estudiantes_bp.route('', methods=['POST'])
@token_requerido
def crear():
    data = request.get_json(silent=True)
    errores = validar_estudiante(data)
    if errores:
        return jsonify({'error': 'Datos inválidos', 'errores': errores}), 400
    email = _limpio(data, 'email')
    if _email_duplicado(email):
        return jsonify({'error': 'Datos inválidos', 'errores': {'email': 'El email ya está registrado'}}), 409
    _, nuevo_id, _ = ejecutar(
        """INSERT INTO estudiantes (nombre, apellido, edad, carrera, email, telefono, creado_por)
           VALUES (%s,%s,%s,%s,%s,%s,%s)""",
        (data['nombre'].strip(), data['apellido'].strip(), int(data['edad']), data['carrera'].strip(),
         email, _limpio(data, 'telefono'), g.usuario['username']), commit=True)
    return jsonify({'mensaje': 'Estudiante creado exitosamente', 'id': nuevo_id,
                    'creado_por': g.usuario['username']}), 201


@estudiantes_bp.route('/<int:id>', methods=['PUT'])
@token_requerido
def actualizar(id):
    data = request.get_json(silent=True)
    errores = validar_estudiante(data, parcial=True)
    if errores:
        return jsonify({'error': 'Datos inválidos', 'errores': errores}), 400
    if not ejecutar('SELECT id FROM estudiantes WHERE id=%s', (id,), fetch='one')[0]:
        return jsonify({'error': 'Estudiante no encontrado'}), 404
    sets, params = [], []
    for campo in ('nombre', 'apellido', 'carrera', 'email', 'telefono'):
        if campo in data:
            if campo == 'email' and _email_duplicado(_limpio(data, 'email'), id):
                return jsonify({'error': 'Datos inválidos',
                                'errores': {'email': 'El email ya está registrado'}}), 409
            sets.append(f'{campo}=%s')
            params.append(_limpio(data, campo))
    if 'edad' in data:
        sets.append('edad=%s')
        params.append(int(data['edad']))
    if not sets:
        return jsonify({'error': 'No se enviaron campos para actualizar'}), 400
    ejecutar(f"UPDATE estudiantes SET {', '.join(sets)} WHERE id=%s", params + [id], commit=True)
    return jsonify({'mensaje': 'Estudiante actualizado exitosamente',
                    'actualizado_por': g.usuario['username']}), 200


@estudiantes_bp.route('/<int:id>', methods=['DELETE'])
@admin_requerido
def eliminar(id):
    _, _, filas = ejecutar('DELETE FROM estudiantes WHERE id=%s', (id,), commit=True)
    if filas == 0:
        return jsonify({'error': 'Estudiante no encontrado'}), 404
    return jsonify({'mensaje': 'Estudiante eliminado exitosamente',
                    'eliminado_por': g.usuario['username']}), 200
