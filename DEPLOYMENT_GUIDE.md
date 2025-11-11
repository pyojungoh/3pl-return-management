# 🚀 배포 가이드

## 📌 중요: Google Apps Script에 푸시 불필요!

**새로운 Flask 서버를 사용하므로 `clasp push`는 더 이상 필요하지 않습니다.**

## 🎯 배포 방법

### 방법 1: Vercel (추천 - 무료, 빠름)

1. **GitHub에 코드 푸시**
   ```bash
   git init
   git add .
   git commit -m "Add Flask server"
   git remote add origin https://github.com/your-username/your-repo.git
   git push -u origin main
   ```

2. **Vercel 배포**
   - [Vercel](https://vercel.com) 가입
   - "New Project" 클릭
   - GitHub 저장소 선택
   - 환경 변수 설정:
     - `GOOGLE_SERVICE_ACCOUNT_JSON`: 서비스 계정 JSON (전체 내용)
     - `SECRET_KEY`: 랜덤 문자열
   - "Deploy" 클릭

3. **배포 완료**
   - `https://your-project.vercel.app` 주소로 접근 가능
   - 고정 URL 제공

### 방법 2: Railway (추천 - 무료 크레딧)

1. **GitHub에 코드 푸시** (위와 동일)

2. **Railway 배포**
   - [Railway](https://railway.app) 가입
   - "New Project" → "Deploy from GitHub repo"
   - 저장소 선택
   - 환경 변수 설정:
     - `GOOGLE_SERVICE_ACCOUNT_JSON`: 서비스 계정 JSON
     - `SECRET_KEY`: 랜덤 문자열
   - 자동 배포 시작

3. **배포 완료**
   - `https://your-project.up.railway.app` 주소로 접근 가능
   - 고정 URL 제공

## 🔐 Google 서비스 계정 설정

1. **Google Cloud Console**
   - https://console.cloud.google.com 접속
   - 새 프로젝트 생성

2. **Google Sheets API 활성화**
   - "API 및 서비스" → "라이브러리"
   - "Google Sheets API" 검색 및 활성화

3. **서비스 계정 생성**
   - "API 및 서비스" → "사용자 인증 정보"
   - "사용자 인증 정보 만들기" → "서비스 계정"
   - 이름 입력 및 생성

4. **키 다운로드**
   - 서비스 계정 클릭
   - "키" 탭 → "키 추가" → "JSON" 선택
   - JSON 파일 다운로드

5. **Google Sheets 공유**
   - Google Sheets 열기
   - "공유" 버튼 클릭
   - 서비스 계정 이메일 추가 (편집 권한)
   - 예: `your-service-account@your-project.iam.gserviceaccount.com`

6. **환경 변수 설정**
   - 다운로드한 JSON 파일의 전체 내용을 환경 변수로 설정
   - Vercel/Railway에서 환경 변수 추가

## 📝 환경 변수 예시

```bash
# Vercel/Railway 환경 변수
GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account","project_id":"..."}'
SECRET_KEY='your-random-secret-key-here'
```

## 🔄 기존 Google Apps Script와의 관계

- **더 이상 사용하지 않음**: Google Apps Script (Code.js)는 백업으로만 보관
- **새 서버 사용**: Flask 서버가 모든 기능을 처리
- **데이터는 동일**: Google Sheets는 그대로 사용 (서비스 계정으로 접근)

## ⚡ 로컬 테스트

```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (Windows)
venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt

# 서비스 계정 JSON 파일을 프로젝트 루트에 저장
# 파일명: service_account.json

# 서버 실행
python server_new.py

# http://localhost:5000 접속
```

## 🎉 완료!

배포가 완료되면:
- ✅ 빠른 속도
- ✅ 안정적인 서비스
- ✅ 고정 URL
- ✅ 무료 호스팅

## 🆘 문제 해결

### 서비스 계정 인증 오류
- Google Sheets에 서비스 계정 이메일 공유 확인
- 환경 변수에 JSON 전체 내용이 올바르게 설정되었는지 확인

### 배포 오류
- `requirements.txt`의 패키지 버전 확인
- 환경 변수 설정 확인
- 로그 확인 (Vercel/Railway 대시보드)

### 데이터 조회 오류
- Google Sheets API 활성화 확인
- 서비스 계정 권한 확인
- 스프레드시트 ID 확인

