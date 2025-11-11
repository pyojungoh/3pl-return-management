@echo off
chcp 65001
cd /d "C:\3pl반품관리및화주사관리"
echo.
echo ========================================
echo GitHub에 푸시하기
echo ========================================
echo.

echo [1/4] 변경사항 확인 중...
git status
echo.

echo [2/4] 모든 파일 추가 중...
git add .
echo.

echo [3/4] 커밋 중...
git commit -m "데이터베이스 마이그레이션 완료"
echo.

echo [4/4] GitHub에 푸시 중...
git push origin main
echo.

echo ========================================
echo 완료! Vercel에서 자동 재배포됩니다.
echo ========================================
echo.
pause

