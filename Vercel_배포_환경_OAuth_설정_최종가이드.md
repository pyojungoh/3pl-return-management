# Vercel 배포 환경 OAuth 2.0 설정 최종 가이드

## 🎯 목표

**배포 환경(Vercel)에서 OAuth 2.0이 정상 작동하도록 설정**

로컬 테스트는 선택사항이며, 배포 환경에서 작동하는 것이 가장 중요합니다.

## 📋 사전 준비

✅ OAuth 클라이언트 ID 생성 완료 (데스크톱 앱 타입)
✅ credentials.json 파일 준비 완료

## 🔧 Vercel 배포 환경 설정 (필수)

### 1단계: 로컬에서 한 번만 인증 받기 (토큰 생성용)

**목적**: Vercel 환경 변수에 설정할 토큰을 생성하기 위함

1. **로컬에서 Flask 서버 실행**
   ```bash
   python app.py
   ```

2. **엑셀 업로드 테스트**
   - 브라우저: `http://localhost:5000/test-excel-upload.html`
   - 엑셀 파일 업로드 시도
   - Google 로그인 및 권한 승인
   - `token.pickle` 파일 생성 확인

3. **토큰 정보 추출**
   ```bash
   python extract_oauth_token.py
   ```
   - 출력된 JSON 전체를 복사 (나중에 사용)

### 2단계: Vercel 환경 변수 설정

1. **Vercel 대시보드 접속**
   - https://vercel.com/
   - 프로젝트 선택

2. **Settings → Environment Variables**

3. **첫 번째 환경 변수: credentials.json**
   - Key: `GOOGLE_OAUTH_CREDENTIALS_JSON`
   - Value: `credentials.json` 파일 전체 내용
     ```json
     {"installed":{"client_id":"...","project_id":"...","auth_uri":"...","token_uri":"...","client_secret":"...","redirect_uris":["http://localhost"]}}
     ```
   - Environment: ✅ Production, ✅ Preview, ✅ Development (모두 선택)
   - Save

4. **두 번째 환경 변수: 토큰 정보**
   - Key: `GOOGLE_OAUTH_TOKEN_JSON`
   - Value: `extract_oauth_token.py`에서 출력된 JSON 전체
     ```json
     {
       "token": "...",
       "refresh_token": "...",
       "token_uri": "https://oauth2.googleapis.com/token",
       "client_id": "...",
       "client_secret": "...",
       "scopes": ["https://www.googleapis.com/auth/drive"]
     }
     ```
   - Environment: ✅ Production, ✅ Preview, ✅ Development (모두 선택)
   - Save

### 3단계: 코드 확인

코드는 이미 환경 변수를 지원하도록 수정되어 있습니다:
- `api/uploads/oauth_drive.py`의 `get_credentials()` 함수
- 환경 변수에서 토큰을 읽도록 구현됨

### 4단계: 배포 및 테스트

1. **코드 푸시**
   ```bash
   git add .
   git commit -m "OAuth 2.0 설정 완료"
   git push
   ```

2. **Vercel 자동 배포 확인**
   - Vercel 대시보드에서 배포 상태 확인
   - 배포 완료 대기

3. **배포 환경에서 테스트**
   - `https://jjaysolution.com/test-excel-upload.html`
   - 엑셀 파일 업로드 시도
   - ✅ 성공하면 완료!

## 🔍 문제 해결

### 환경 변수가 로드되지 않는 경우

1. **환경 변수 확인**
   - Vercel 대시보드 → Settings → Environment Variables
   - 두 환경 변수가 모두 설정되어 있는지 확인
   - Production, Preview, Development 모두 선택되었는지 확인

2. **재배포**
   - 환경 변수 추가 후 자동 재배포가 안 될 수 있음
   - Deployments → 최신 배포 → "..." → Redeploy

3. **로그 확인**
   - Vercel 대시보드 → Deployments → Functions
   - 오류 로그 확인

### 토큰 만료 오류

토큰이 만료되면:

1. **로컬에서 다시 인증 받기**
   - `token.pickle` 파일 삭제
   - 다시 업로드 시도하여 인증 받기

2. **토큰 추출 및 환경 변수 업데이트**
   ```bash
   python extract_oauth_token.py
   ```
   - 출력된 JSON을 Vercel 환경 변수 `GOOGLE_OAUTH_TOKEN_JSON`에 업데이트
   - 재배포

## ✅ 체크리스트

배포 환경 설정:
- [ ] 로컬에서 OAuth 인증 완료 (`token.pickle` 생성)
- [ ] `extract_oauth_token.py` 실행하여 토큰 JSON 추출
- [ ] Vercel 환경 변수 설정:
  - [ ] `GOOGLE_OAUTH_CREDENTIALS_JSON` (credentials.json 전체)
  - [ ] `GOOGLE_OAUTH_TOKEN_JSON` (토큰 JSON)
- [ ] 환경 변수 Environment 모두 선택 (Production, Preview, Development)
- [ ] 코드 푸시 및 배포
- [ ] 배포 환경에서 엑셀 업로드 테스트 성공

## 🚀 빠른 시작 (요약)

```bash
# 1. 로컬에서 인증 받기 (한 번만)
python app.py
# 브라우저에서 http://localhost:5000/test-excel-upload.html 접속하여 인증

# 2. 토큰 추출
python extract_oauth_token.py

# 3. Vercel 환경 변수 설정
# - GOOGLE_OAUTH_CREDENTIALS_JSON: credentials.json 전체
# - GOOGLE_OAUTH_TOKEN_JSON: 추출한 토큰 JSON

# 4. 배포
git push

# 5. 배포 환경에서 테스트
# https://jjaysolution.com/test-excel-upload.html
```

## 💡 중요 사항

1. **로컬 인증은 토큰 생성용**
   - 로컬에서 인증 받는 것은 Vercel 환경 변수에 설정할 토큰을 생성하기 위함
   - 로컬에서 잘 작동하는 것은 중요하지 않음
   - **배포 환경에서 작동하는 것이 핵심**

2. **환경 변수 설정 필수**
   - Vercel 서버리스 환경에서는 파일 시스템을 사용할 수 없음
   - 환경 변수에 토큰을 저장해야 함

3. **토큰 자동 갱신**
   - 코드가 refresh token을 사용하여 자동으로 토큰을 갱신합니다
   - 갱신 실패 시에만 다시 인증이 필요합니다

## 📝 다음 단계

배포 환경에서 테스트가 성공하면:
1. 실제 사용자에게 배포
2. 모니터링 및 로그 확인
3. 토큰 만료 시 재인증 프로세스 준비

