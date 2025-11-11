@echo off
chcp 65001 >nul
echo ========================================
echo Flask 서버 및 ngrok 시작 스크립트
echo ========================================
echo.

echo [1/3] Flask 서버 시작 중...
start "Flask Server" cmd /k "python app.py"
echo 서버가 시작되었습니다. 잠시만 기다려주세요...
timeout /t 5 /nobreak >nul

echo.
echo [2/3] ngrok 시작 중...
echo ngrok이 실행되면 HTTPS URL이 표시됩니다.
echo 모바일에서 해당 URL로 접속하세요.
echo.
echo 예: https://xxxx-xx-xx-xx-xx.ngrok.io/admin
echo.
echo 서버를 종료하려면 이 창을 닫으세요.
echo ========================================
echo.

ngrok http 5000

pause



