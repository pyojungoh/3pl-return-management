@echo off
cd /d "C:\3pl반품관리및화주사관리"
if exist "venv\Scripts\activate.bat" call venv\Scripts\activate.bat
pip install -q -r requirements.txt
echo 서버 실행: http://localhost:5000
python app.py

