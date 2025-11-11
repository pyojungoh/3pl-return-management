@echo off
chcp 65001 >nul
echo ========================================
echo 3PL 반품 관리 시스템 로컬 실행
echo ========================================
echo.

REM 가상환경 활성화
if exist venv\Scripts\activate.bat (
    echo [1/3] 가상환경 활성화 중...
    call venv\Scripts\activate.bat
) else (
    echo [1/3] 가상환경이 없습니다. 생성 중...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo [2/3] 패키지 설치 중...
    pip install -r requirements.txt
)

REM 패키지 설치 확인
echo [2/3] 패키지 확인 중...
pip install -q -r requirements.txt

REM 서버 실행
echo [3/3] 서버 시작 중...
echo.
echo ========================================
echo 서버가 http://localhost:5000 에서 실행됩니다
echo 브라우저에서 접속하세요!
echo ========================================
echo.
python app.py

pause

