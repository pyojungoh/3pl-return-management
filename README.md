# 3PL 반품 관리 시스템

화주사별 반품 내역 조회 및 관리 시스템

## 🚀 빠른 시작

### GitHub에 푸시
```bash
cd C:\3pl반품관리및화주사관리
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/pyojungoh/3pl-return-management.git
git branch -M main
git push -u origin main
```

### Vercel 배포
1. https://vercel.com 접속
2. GitHub로 로그인
3. 저장소 선택
4. 환경 변수 설정:
   - `GOOGLE_SERVICE_ACCOUNT_JSON`: 서비스 계정 JSON
   - `SECRET_KEY`: 랜덤 문자열
5. 배포 완료!

## 📚 문서

- [단계별 가이드](STEP_BY_STEP_GUIDE.md)
- [GitHub 푸시 가이드](GITHUB_PUSH_GUIDE.md)
- [배포 가이드](DEPLOYMENT_GUIDE.md)

## 🔧 기술 스택

- **Backend**: Flask (Python)
- **Frontend**: HTML, CSS, JavaScript
- **Database**: Google Sheets
- **Deployment**: Vercel

## 📝 라이선스

Private

