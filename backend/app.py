from flask import Flask, jsonify, request
from config import CorsConfig
from models import crear_tablas, crear_admin_por_defecto
from routes.auth import auth_bp
from routes.estudiantes import estudiantes_bp

app = Flask(__name__)
app.json.ensure_ascii = False


@app.after_request
def cors(response):
    """CORS restringido a los orígenes del frontend (métodos y headers limitados)."""
    origen = request.headers.get('Origin')
    if origen in CorsConfig.ORIGINS:
        response.headers['Access-Control-Allow-Origin'] = origen
        response.headers['Vary'] = 'Origin'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


@app.before_request
def preflight():
    if request.method == 'OPTIONS':
        return '', 204


app.register_blueprint(auth_bp)
app.register_blueprint(estudiantes_bp)


@app.route('/')
def index():
    return {'mensaje': 'API de Estudiantes v2 - Universidad Libre'}, 200


@app.errorhandler(ConnectionError)
def sin_bd(e):
    return jsonify({'error': 'Error de conexión con la base de datos'}), 500


@app.errorhandler(404)
def no_encontrado(e):
    return jsonify({'error': 'Ruta no encontrada'}), 404


if __name__ == '__main__':
    print('Inicializando base de datos...')
    crear_tablas()
    crear_admin_por_defecto()
    print('Tablas creadas/verificadas')
    print('Servidor iniciado en http://localhost:5000')
    app.run(debug=True, port=5000)
