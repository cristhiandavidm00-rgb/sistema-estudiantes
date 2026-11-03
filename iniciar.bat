@echo off
REM Antes: iniciar MySQL en XAMPP e importar backend\universidad_db.sql
if not exist venv python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt
cd backend
python app.py
pause
