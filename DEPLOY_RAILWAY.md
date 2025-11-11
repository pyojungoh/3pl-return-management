# Railway 배포 가이드

## 📋 배포 전 체크리스트

### 1. 필수 파일 확인
- ✅ `app.py` - 메인 Flask 앱
- ✅ `requirements.txt` - Python 패키지 의존성
- ✅ `Procfile` - Railway 실행 명령어
- ✅ `railway.json` - Railway 설정
- ✅ `dashboard_server.html` - 대시보드 파일
- ✅ `data.db` - SQLite 데이터베이스 (선택사항, 없으면 자동 생성)

### 2. 환경 변수 설정 (선택사항)
현재 코드에 기본값이 설정되어 있어서 필수는 아니지만, 프로덕션에서는 환경 변수로 설정하는 것을 권장합니다.

#### Railway 환경 변수 설정:
```
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
SECRET_KEY=your-secret-key-change-this
```

## 🚀 Railway 배포 단계

### 방법 1: Railway CLI 사용 (권장)

1. **Railway CLI 설치**
```bash
# Windows (PowerShell)
iwr https://railway.app/install.ps1 | iex

# 또는 npm으로 설치
npm i -g @railway/cli
```

2. **Railway 로그인**
```bash
railway login
```

3. **프로젝트 초기화**
```bash
railway init
```

4. **환경 변수 설정 (선택사항)**
```bash
railway variables set CLOUDINARY_CLOUD_NAME=your_cloud_name
railway variables set CLOUDINARY_API_KEY=your_api_key
railway variables set CLOUDINARY_API_SECRET=your_api_secret
railway variables set SECRET_KEY=your-secret-key
```

5. **배포**
```bash
railway up
```

### 방법 2: Railway 웹 대시보드 사용

1. **Railway 웹사이트 접속**
   - https://railway.app 접속
   - GitHub 계정으로 로그인

2. **새 프로젝트 생성**
   - "New Project" 클릭
   - "Deploy from GitHub repo" 선택
   - GitHub 저장소 연결

3. **서비스 설정**
   - 자동으로 `railway.json`과 `Procfile`을 인식
   - Python 런타임 자동 감지

4. **환경 변수 설정**
   - 프로젝트 설정 → Variables 탭
   - 다음 환경 변수 추가 (선택사항):
     - `CLOUDINARY_CLOUD_NAME`
     - `CLOUDINARY_API_KEY`
     - `CLOUDINARY_API_SECRET`
     - `SECRET_KEY`

5. **배포 확인**
   - 배포가 완료되면 자동으로 URL이 생성됨
   - "Settings" → "Domains"에서 커스텀 도메인 설정 가능

## 📝 중요 사항

### 데이터베이스 관리
- SQLite 데이터베이스는 Railway의 영구 저장소에 저장됩니다
- 초기 배포 시 `data.db` 파일이 없으면 자동으로 생성됩니다
- 기존 데이터베이스를 사용하려면 프로젝트에 포함시켜야 합니다

### 서비스 계정 파일 (선택사항)
- `service_account.json` 파일이 필요한 경우:
  - Railway 환경 변수로 변환하거나
  - Railway의 볼륨(Volume) 기능 사용

### 포트 설정
- Railway는 자동으로 `$PORT` 환경 변수를 제공합니다
- `Procfile`에서 이미 올바르게 설정되어 있습니다

## 🔍 배포 후 확인

1. **애플리케이션 로그 확인**
```bash
railway logs
```

2. **서비스 상태 확인**
- Railway 대시보드에서 서비스 상태 확인
- 배포된 URL로 접속 테스트

3. **에러 해결**
- 로그에서 에러 메시지 확인
- 필요시 환경 변수 재설정
- 데이터베이스 파일 확인

## 🌐 커스텀 도메인 설정

1. Railway 대시보드 → 프로젝트 → Settings → Domains
2. "Generate Domain" 클릭하거나 커스텀 도메인 추가
3. DNS 설정 (커스텀 도메인 사용 시)

## 💡 트러블슈팅

### 배포 실패 시
- `requirements.txt`의 패키지 버전 확인
- Python 버전 확인 (Railway는 자동 감지)
- 로그에서 에러 메시지 확인

### 데이터베이스 오류
- `data.db` 파일이 올바른 위치에 있는지 확인
- Railway의 영구 저장소 사용 확인

### 이미지 업로드 오류
- Cloudinary 환경 변수 확인
- API 키가 올바른지 확인

