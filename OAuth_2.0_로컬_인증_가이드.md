# OAuth 2.0 로컬 인증 가이드

## ✅ 1단계: credentials.json 파일 준비 완료

`credentials.json` 파일이 프로젝트 루트에 생성되었습니다.

## 🔐 2단계: 로컬에서 인증 받기

### 방법 1: Flask 서버 실행 후 자동 인증

1. **Flask 서버 실행**
   ```bash
   python app.py
   ```

2. **엑셀 업로드 테스트 페이지 접속**
   - 브라우저에서: `http://localhost:5000/test-excel-upload.html`
   - 엑셀 파일 선택 후 업로드 시도
   - **첫 업로드 시 자동으로 브라우저가 열리고 Google 로그인 화면이 표시됩니다**

3. **Google 로그인 및 권한 승인**
   - 본인 Google 계정으로 로그인
   - "Google Drive에 대한 액세스 권한 부여" 화면에서 "허용" 클릭

4. **토큰 자동 저장**
   - 인증 완료 후 `token.pickle` 파일이 자동 생성됩니다
   - 위치: 프로젝트 루트 폴더 (`C:\3plsolution\token.pickle`)

### 방법 2: 직접 인증 API 호출 (선택사항)

인증만 먼저 받고 싶다면:

1. **Flask 서버 실행**
   ```bash
   python app.py
   ```

2. **인증 API 호출** (아직 구현되지 않았을 수 있음)
   - 브라우저에서: `http://localhost:5000/api/uploads/test/oauth-auth`
   - 또는 엑셀 업로드를 시도하면 자동으로 인증 플로우가 시작됩니다

## ✅ 3단계: 인증 확인

인증이 완료되면:
- `token.pickle` 파일이 생성되었는지 확인
- 다음 업로드부터는 자동으로 토큰을 사용합니다

## 🔄 토큰 갱신

토큰이 만료되면 자동으로 갱신됩니다. 갱신에 실패하면:
1. `token.pickle` 파일 삭제
2. 다시 인증 받기

## ⚠️ 주의사항

1. **파일 보안**
   - `credentials.json`과 `token.pickle`은 Git에 커밋하지 마세요
   - `.gitignore`에 이미 추가되어 있습니다

2. **토큰 만료**
   - OAuth 2.0 토큰은 일정 시간 후 만료됩니다
   - Refresh token을 사용하여 자동 갱신됩니다
   - 갱신 실패 시 다시 인증이 필요합니다

## 🚀 다음 단계

로컬 인증이 완료되면:
1. 로컬에서 엑셀 업로드 테스트
2. Vercel 환경 변수 설정 (서버리스 환경용)
3. 배포 및 테스트

## 📝 Vercel 환경 변수 설정 (나중에)

로컬 인증이 완료되면, Vercel에서도 사용할 수 있도록 환경 변수를 설정해야 합니다:

1. **credentials.json 내용 복사**
   - 전체 내용을 복사

2. **Vercel 환경 변수 설정**
   - Key: `GOOGLE_OAUTH_CREDENTIALS_JSON`
   - Value: credentials.json 전체 내용

3. **토큰 정보 추출** (추후 필요)
   - `token.pickle`에서 토큰 정보 추출
   - Key: `GOOGLE_OAUTH_TOKEN_JSON`
   - Value: 토큰 JSON

자세한 내용은 `OAuth_2.0_설정_가이드.md`를 참고하세요.

