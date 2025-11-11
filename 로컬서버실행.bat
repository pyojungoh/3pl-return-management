@echo off
chcp 65001
cd /d "C:\3pl반품관리및화주사관리"
echo.
echo ========================================
echo 3PL 반품 관리 시스템 서버 실행
echo ========================================
echo.

REM 가상환경 확인 및 활성화
if exist "venv\Scripts\activate.bat" (
    echo [1/3] 가상환경 활성화 중...
    call venv\Scripts\activate.bat
) else (
    echo [정보] 가상환경이 없습니다. 전역 Python을 사용합니다.
)

REM 패키지 설치 확인
echo [2/3] 패키지 확인 중...
pip install -q -r requirements.txt

REM 서버 실행
echo [3/3] 서버 시작 중...
echo.
echo ========================================
echo 서버 주소: http://localhost:5000
echo 브라우저에서 접속하세요!
echo 서버 중지: Ctrl + C
echo ========================================
echo.
python app.py
pause

