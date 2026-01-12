# OAuth 2.0 Vercel 설정 가이드

## 📋 개요

Vercel 서버리스 환경에서 OAuth 2.0을 사용하려면 환경 변수에 토큰을 설정해야 합니다.

## 🔧 설정 방법

### 1단계: 로컬에서 인증 받기 (한 번만)

1. **로컬에서 Flask 서버 실행**
   ```bash
   python app.py
   ```

2. **엑셀 업로드 테스트**
   - 브라우저: `http://localhost:5000/test-excel-upload.html`
   - 엑셀 파일 업로드 시도
   - Google 로그인 및 권한 승인
   - `token.pickle` 파일 생성 확인

### 2단계: 토큰 정보 추출

1. **토큰 추출 스크립트 실행**
   ```bash
   python extract_oauth_token.py
   ```

2. **출력된 JSON 복사**
   - 스크립트가 토큰 정보를 JSON 형식으로 출력합니다
   - 전체 JSON을 복사하세요

### 3단계: Vercel 환경 변수 설정

1. **Vercel 대시보드 접속**
   - https://vercel.com/
   - 프로젝트 선택

2. **Settings → Environment Variables**

3. **환경 변수 추가**

   **첫 번째: credentials.json**
   - Key: `GOOGLE_OAUTH_CREDENTIALS_JSON`
   - Value: `credentials.json` 파일 전체 내용
   - Environment: Production, Preview, Development 모두 선택
   - Save

   **두 번째: 토큰 정보**
   - Key: `GOOGLE_OAUTH_TOKEN_JSON`
   - Value: `extract_oauth_token.py`에서 출력된 JSON 전체
   - Environment: Production, Preview, Development 모두 선택
   - Save

4. **재배포**
   - Deployments → 최신 배포 → "..." → Redeploy
   - 또는 코드를 약간 수정하고 푸시

### 4단계: 테스트

1. **배포 완료 후 테스트**
   - `https://jjaysolution.com/test-excel-upload.html`
   - 엑셀 파일 업로드 시도

2. **성공 확인**
   - 파일이 Google Drive에 업로드되는지 확인
   - 파일 링크가 표시되는지 확인

## 🔄 토큰 갱신

토큰이 만료되면:

1. **로컬에서 다시 인증 받기**
   - `token.pickle` 파일 삭제
   - 다시 업로드 시도하여 인증 받기

2. **토큰 추출 및 환경 변수 업데이트**
   - `python extract_oauth_token.py` 실행
   - Vercel 환경 변수 `GOOGLE_OAUTH_TOKEN_JSON` 업데이트
   - 재배포

## ⚠️ 주의사항

1. **보안**
   - `credentials.json`과 토큰 정보는 절대 공유하지 마세요
   - Git에 커밋되지 않도록 `.gitignore`에 추가되어 있습니다

2. **토큰 만료**
   - OAuth 2.0 토큰은 일정 시간 후 만료됩니다
   - Refresh token을 사용하여 자동 갱신되지만, 실패 시 다시 인증이 필요합니다

3. **환경 변수 길이 제한**
   - Vercel 환경 변수는 길이 제한이 있을 수 있습니다
   - 토큰이 너무 길면 문제가 될 수 있습니다

## 📝 체크리스트

- [ ] 로컬에서 OAuth 2.0 인증 완료 (`token.pickle` 생성)
- [ ] `extract_oauth_token.py` 실행하여 토큰 정보 추출
- [ ] Vercel 환경 변수 설정:
  - [ ] `GOOGLE_OAUTH_CREDENTIALS_JSON` (credentials.json 내용)
  - [ ] `GOOGLE_OAUTH_TOKEN_JSON` (토큰 JSON)
- [ ] 재배포 완료
- [ ] 웹에서 엑셀 업로드 테스트 성공

## 🚀 빠른 시작

```bash
# 1. 로컬에서 인증 받기
python app.py
# 브라우저에서 http://localhost:5000/test-excel-upload.html 접속하여 인증

# 2. 토큰 추출
python extract_oauth_token.py

# 3. 출력된 JSON을 Vercel 환경 변수에 설정
# 4. 재배포
# 5. 웹에서 테스트
```

## 💡 팁

- 로컬에서 인증을 받으면 `token.pickle`이 생성됩니다
- 이 파일을 사용하여 토큰 정보를 추출할 수 있습니다
- Vercel에서는 환경 변수에서 토큰을 읽습니다
- 토큰이 만료되면 자동으로 갱신됩니다 (refresh token 사용)

