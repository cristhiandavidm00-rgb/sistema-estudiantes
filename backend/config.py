import importlib
import os


class DatabaseConfig:
    """Conexión a MySQL (XAMPP: usuario root sin contraseña por defecto)."""
    HOST = os.getenv('DB_HOST', 'localhost')
    PORT = int(os.getenv('DB_PORT', '3306'))
    USER = os.getenv('DB_USER', 'root')
    PASSWORD = os.getenv('DB_PASSWORD', '')
    DATABASE = os.getenv('DB_NAME', 'universidad_db')

    @staticmethod
    def get_connection():
        try:
            mysql_connector = importlib.import_module('mysql.connector')
            connection = mysql_connector.connect(
                host=DatabaseConfig.HOST,
                port=DatabaseConfig.PORT,
                user=DatabaseConfig.USER,
                password=DatabaseConfig.PASSWORD,
                database=DatabaseConfig.DATABASE,
            )
            if connection.is_connected():
                return connection
        except Exception as e:
            print(f"Error al conectar al Servidor de MySQL: {e}")
        return None


class JWTConfig:
    # En producción definir JWT_SECRET_KEY como variable de entorno.
    SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'cambia-esta-clave-en-produccion-unilibre-2024')
    ALGORITHM = 'HS256'
    EXPIRATION_HOURS = 1


class CorsConfig:
    # Orígenes del frontend permitidos (python -m http.server 8000 / Live Server de VSC)
    ORIGINS = [
        'http://localhost', 'http://127.0.0.1',   # Apache de XAMPP (puerto 80)
        'http://localhost:8000', 'http://127.0.0.1:8000',
        'http://localhost:5500', 'http://127.0.0.1:5500',
    ]
