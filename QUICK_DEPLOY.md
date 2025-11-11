# ⚡ 빠른 배포 가이드

## 🚀 Railway 배포 (3단계)

### 1단계: GitHub에 코드 업로드

#### 방법 A: GitHub 웹사이트 사용 (가장 쉬움)
1. GitHub.com에 로그인
2. 새 저장소 생성 (New repository)
3. 저장소 이름 입력 (예: `3pl-return-management`)
4. "Upload files" 클릭
5. 다음 파일들을 드래그 앤 드롭:
   - `app.py`
   - `requirements.txt`
   - `Procfile`
   - `railway.json`
   - `dashboard_server.html`
   - `dashboard.html`
   - `index.html`
   - `api/` 폴더 전체
   - `templates/` 폴더 전체 (있는 경우)
   - `.gitignore`
6. "Commit changes" 클릭

**제외할 파일들:**
- ❌ `venv/` 폴더
- ❌ `data.db` 파일
- ❌ `__pycache__/` 폴더
- ❌ `.env` 파일
- ❌ `service_account.json` 파일

#### 방법 B: Git 명령어 사용
```bash
# Git 초기화
git init

# 파일 추가
git add app.py requirements.txt Procfile railway.json dashboard_server.html dashboard.html index.html api/ templates/ .gitignore

# 커밋
git commit -m "배포 준비"

# GitHub 저장소 생성 후
git remote add origin https://github.com/your-username/your-repo.git
git branch -M main
git push -u origin main
```

### 2단계: Railway에서 배포

1. **Railway 웹사이트 접속**
   - https://railway.app 접속
   - "Login" 클릭
   - GitHub 계정으로 로그인

2. **새 프로젝트 생성**
   - "New Project" 버튼 클릭
   - "Deploy from GitHub repo" 선택
   - 방금 업로드한 저장소 선택
   - "Deploy Now" 클릭

3. **자동 배포 시작**
   - Railway가 자동으로 Python 프로젝트를 인식
   - `requirements.txt`에서 패키지 설치
   - `Procfile`에서 실행 명령어 실행
   - 배포가 완료될 때까지 대기 (약 2-3분)

### 3단계: 환경 변수 설정 (선택사항)

현재 코드에 기본값이 있어서 필수는 아니지만, 프로덕션에서는 설정하는 것을 권장합니다.

1. Railway 대시보드 → 프로젝트 클릭
2. "Variables" 탭 클릭
3. "New Variable" 클릭하여 추가:
   - `CLOUDINARY_CLOUD_NAME` = `dokk81rjh` (또는 본인의 값)
   - `CLOUDINARY_API_KEY` = `447577332396678` (또는 본인의 값)
   - `CLOUDINARY_API_SECRET` = `_fh-dOMoaFvOvCRkFk_AzqjOFA8` (또는 본인의 값)
   - `SECRET_KEY` = 임의의 긴 문자열 (예: `your-secret-key-12345`)

### 4단계: 배포 완료 확인

1. Railway 대시보드에서 배포 상태 확인
2. "Settings" → "Domains"에서 생성된 URL 확인
3. URL로 접속하여 애플리케이션 테스트

## 📋 배포 후 확인사항

- ✅ 메인 페이지 로드 확인
- ✅ 로그인 기능 테스트
- ✅ 대시보드 표시 확인
- ✅ 이미지 업로드 기능 테스트
- ✅ 데이터베이스 저장 확인

## 🔧 문제 해결

### 배포 실패
- Railway 대시보드 → "Logs" 탭에서 에러 메시지 확인
- `requirements.txt`의 패키지가 올바른지 확인

### 애플리케이션 오류
- 로그에서 Python 에러 확인
- 환경 변수 설정 확인
- 데이터베이스 파일 경로 확인

### 이미지 업로드 오류
- Cloudinary 환경 변수 확인
- API 키가 올바른지 확인

## 💡 팁

- Railway는 무료 플랜을 제공합니다 (월 500시간)
- GitHub에 푸시하면 자동으로 재배포됩니다
- Railway 대시보드에서 실시간 로그를 확인할 수 있습니다
- 커스텀 도메인을 설정할 수 있습니다 (Settings → Domains)

## 📞 지원

문제가 발생하면 Railway 대시보드의 로그를 확인하거나, GitHub Issues에 문의하세요.

