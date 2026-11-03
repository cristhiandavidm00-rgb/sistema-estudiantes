-- Sistema de Gestión de Estudiantes v2 - Universidad Libre
-- Ejecutar desde phpMyAdmin (XAMPP) -> pestaña SQL, o: mysql -u root < universidad_db.sql
CREATE DATABASE IF NOT EXISTS universidad_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE universidad_db;

-- OJO: la v1 tenía la tabla estudiantes sin AUTO_INCREMENT ni email; se recrea.
DROP TRIGGER IF EXISTS trg_estudiantes_after_insert;
DROP TRIGGER IF EXISTS trg_estudiantes_after_update;
DROP TRIGGER IF EXISTS trg_estudiantes_after_delete;
DROP VIEW IF EXISTS vista_estadisticas_carrera;
DROP TABLE IF EXISTS auditoria_estudiantes;
DROP TABLE IF EXISTS estudiantes;

CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    rol ENUM('admin','usuario') NOT NULL DEFAULT 'usuario',
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ultimo_acceso DATETIME NULL
);

CREATE TABLE estudiantes (
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
);

CREATE TABLE IF NOT EXISTS token_blacklist (
    jti VARCHAR(64) PRIMARY KEY,
    expira DATETIME NOT NULL,
    INDEX idx_expira (expira)
);

-- Auditoría por triggers
CREATE TABLE auditoria_estudiantes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    estudiante_id INT NOT NULL,
    accion ENUM('INSERT','UPDATE','DELETE') NOT NULL,
    detalle VARCHAR(255),
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

DELIMITER //
CREATE TRIGGER trg_estudiantes_after_insert AFTER INSERT ON estudiantes FOR EACH ROW
BEGIN
    INSERT INTO auditoria_estudiantes (estudiante_id, accion, detalle)
    VALUES (NEW.id, 'INSERT', CONCAT(NEW.nombre, ' ', NEW.apellido));
END//
CREATE TRIGGER trg_estudiantes_after_update AFTER UPDATE ON estudiantes FOR EACH ROW
BEGIN
    INSERT INTO auditoria_estudiantes (estudiante_id, accion, detalle)
    VALUES (NEW.id, 'UPDATE', CONCAT(OLD.nombre, ' ', OLD.apellido, ' -> ', NEW.nombre, ' ', NEW.apellido));
END//
CREATE TRIGGER trg_estudiantes_after_delete AFTER DELETE ON estudiantes FOR EACH ROW
BEGIN
    INSERT INTO auditoria_estudiantes (estudiante_id, accion, detalle)
    VALUES (OLD.id, 'DELETE', CONCAT(OLD.nombre, ' ', OLD.apellido));
END//
DELIMITER ;

-- Vista para estadísticas
CREATE VIEW vista_estadisticas_carrera AS
SELECT carrera, COUNT(*) AS cantidad, ROUND(AVG(edad),1) AS promedio_edad
FROM estudiantes GROUP BY carrera;

-- Datos de ejemplo
INSERT INTO estudiantes (nombre, apellido, edad, carrera, email, telefono, creado_por) VALUES
('Juan', 'Pérez', 20, 'Ingeniería de Sistemas', 'juan@unilibre.edu.co', '+57 310 1234567', 'admin'),
('María', 'González', 22, 'Ingeniería Industrial', 'maria@unilibre.edu.co', '+57 311 2345678', 'admin'),
('Carlos', 'Rodríguez', 21, 'Ingeniería Electrónica', 'carlos@unilibre.edu.co', '+57 312 3456789', 'admin');

-- El usuario admin (admin / admin123) lo crea app.py al iniciar, con hash bcrypt.
