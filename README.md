# Proyecto: Sistema de Gestión de Estudiantes (v2)

Hecho con Python (Flask), MySQL (XAMPP) y HTML/CSS/JavaScript.

## PARTE 1 – Preparar la base de datos (XAMPP + MySQL)
1. Abre el **XAMPP Control Panel** y presiona **Start** en **MySQL** (y en **Apache**).
2. Abre en el navegador: http://localhost/phpmyadmin
3. Clic en la pestaña **SQL**.
4. Abre el archivo `backend/universidad_db.sql` con VS Code, copia TODO, pégalo en la caja y presiona **Continuar**.
   (Listo: se crea la base `universidad_db` con sus tablas.)

> Usuario de MySQL en XAMPP: `root` y **sin contraseña**. Ya viene así en `backend/config.py`,
> no tienes que cambiar nada. Si tu MySQL sí tiene contraseña, cámbiala en la línea `PASSWORD` de `config.py`.

## PARTE 2 – Encender el backend (Python)
Abre VS Code → **Terminal → New Terminal** dentro de la carpeta `proyecto` y escribe uno por uno:
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cd backend
python app.py
```
Debe aparecer: `Servidor iniciado en http://localhost:5000`. **No cierres esta terminal.**

(Atajo en Windows: doble clic en `iniciar.bat` hace todo lo anterior.)

## PARTE 3 – Ver la página (frontend)
Elige UNA opción:
- **Con Apache de XAMPP:** copia la carpeta `frontend` a `C:\xampp\htdocs\` y abre http://localhost/frontend/
- **Sin Apache:** en una terminal nueva: `cd frontend` y `python -m http.server 8000`, luego abre http://localhost:8000

Entra con **usuario: admin  /  contraseña: admin123**.
Con ese usuario puedes crear, editar y eliminar estudiantes. Un usuario nuevo (botón Registrarse) no puede eliminar.

## PARTE 4 – Subir a GitHub
1. Crea una cuenta en https://github.com y un repositorio nuevo (botón **New**), sin README. Copia su URL.
2. En la terminal, en la carpeta `proyecto`:
```
git init
git add .
git commit -m "Sistema de Gestion de Estudiantes v2"
git branch -M main
git remote add origin URL_DE_TU_REPOSITORIO
git push -u origin main
```
(Reemplaza `URL_DE_TU_REPOSITORIO` por la que copiaste, ej: `https://github.com/tuusuario/proyecto.git`.)
GitHub te pedirá iniciar sesión la primera vez.

## Si algo falla
| Error | Solución |
|---|---|
| `python` no se reconoce | Instala Python desde python.org marcando "Add to PATH" |
| Error al conectar a MySQL | MySQL debe estar en verde (Start) en XAMPP |
| La página no carga datos | El backend (Parte 2) debe estar corriendo |
| Token expirado | Cierra sesión y vuelve a entrar (dura 1 hora) |

## Estructura
```
backend/   app.py (arranque), config.py (conexión), models.py (validaciones y tablas),
           middleware.py (protege rutas), routes/ (auth.py y estudiantes.py), universidad_db.sql
frontend/  index.html, css/styles.css, js/app.js
tests/     pruebas automáticas (python -m unittest discover -s tests)
```
