@echo off
chcp 65001 >nul
echo ========================================
echo SQLite → PostgreSQL 데이터 마이그레이션
echo ========================================
echo.

REM Vercel DATABASE_URL 환경 변수 설정
REM ⚠️ 아래 DATABASE_URL 값을 Vercel 대시보드에서 복사하여 붙여넣으세요
REM Vercel → Settings → Environment Variables → DATABASE_URL

echo ⚠️  DATABASE_URL을 설정해야 합니다.
echo.
echo Vercel 대시보드에서 DATABASE_URL을 복사하세요:
echo 1. Vercel 대시보드 열기
echo 2. 프로젝트 선택
echo 3. Settings → Environment Variables
echo 4. DATABASE_URL 값 복사
echo.
echo 아래에 DATABASE_URL을 입력하세요 (또는 이 파일을 수정하세요):
echo.

set /p DATABASE_URL="DATABASE_URL 입력: "

if "%DATABASE_URL%"=="" (
    echo.
    echo ❌ DATABASE_URL이 입력되지 않았습니다.
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ DATABASE_URL 설정 완료
echo.
echo 마이그레이션 스크립트 실행 중...
echo.

python migrate_sqlite_to_postgresql.py

echo.
echo ========================================
echo 마이그레이션 완료!
echo ========================================
echo.
pause

