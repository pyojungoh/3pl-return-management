# OAuth 2.0 설정 가이드 - Google Drive 엑셀 업로드

## 📋 개요

Google Workspace 계정이 없어 서비스 계정 제한을 우회하기 위해 OAuth 2.0을 사용합니다.
사용자 계정으로 Google Drive에 파일을 업로드할 수 있습니다.

## 🔧 설정 방법

### 1. OAuth 2.0 클라이언트 ID 생성

1. **Google Cloud Console 접속**
   - https://console.cloud.google.com/

2. **프로젝트 선택**
   - 프로젝트: `composite-dream-477907-c5`

3. **APIs & Services → Credentials**
   - 왼쪽 메뉴: APIs & Services → Credentials

4. **OAuth 클라이언트 ID 생성**
   - 상단: "+ CREATE CREDENTIALS" 클릭
   - "OAuth client ID" 선택

5. **OAuth 동의 화면 설정** (처음 생성 시)
   - User Type: "External" 선택
   - 앱 정보 입력:
     - 앱 이름: `3PL 솔루션` (또는 원하는 이름)
     - 사용자 지원 이메일: `jjay220304@gmail.com` (또는 본인 이메일)
     - 개발자 연락처 정보: 이메일 입력
   - "SAVE AND CONTINUE" 클릭
   - Scopes: 기본값 사용 → "SAVE AND CONTINUE"
   - **Test users: 본인 이메일 추가** ⭐ (중요!)
     - `jjay220304@gmail.com` 추가
     - 이 단계를 건너뛰면 "403 access_denied" 오류 발생
   - "SAVE AND CONTINUE" 클릭
   - "BACK TO DASHBOARD" 클릭
   
   ⚠️ **만약 이미 생성했다면**:
   - APIs & Services → OAuth consent screen
   - 페이지 하단 "Test users" 섹션에서 "+ ADD USERS" 클릭
   - 본인 이메일 추가

6. **OAuth 클라이언트 ID 생성**
   - "자격 증명 만들기" → "OAuth 클라이언트 ID" 선택
   - 애플리케이션 유형: **"데스크톱 앱"** 선택 (로컬 테스트용, 권장!) ⭐
     - 한글판에서는 "데스크톱 앱" 또는 "데스크톱 애플리케이션"으로 표시됩니다
     - 로컬 서버 기반 인증(`run_local_server`)을 사용하므로 "데스크톱 앱"이 적합합니다
   - 이름: `3PL 솔루션 Desktop Client`
   - "만들기" 클릭
   - ⚠️ 참고: "웹 애플리케이션" 타입을 사용하면 redirect_uri_mismatch 오류가 발생할 수 있습니다

7. **JSON 다운로드**
   - 생성된 클라이언트 ID 옆의 다운로드 아이콘 클릭
   - JSON 파일 다운로드

### 2. 로컬 환경 설정

#### 2.1. credentials.json 파일 준비

1. **다운로드한 JSON 파일 확인**
   - 파일 구조 확인:
   ```json
   {
     "web": {
       "client_id": "...",
       "project_id": "composite-dream-477907-c5",
       "auth_uri": "https://accounts.google.com/o/oauth2/auth",
       "token_uri": "https://oauth2.googleapis.com/token",
       "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
       "client_secret": "...",
       "redirect_uris": ["http://localhost:5000"]
     }
   }
   ```

2. **프로젝트 루트 폴더에 저장**
   - 파일명: `credentials.json`
   - 위치: 프로젝트 루트 폴더 (`C:\3plsolution\credentials.json`)

#### 2.2. 로컬에서 인증 받기

1. **Flask 서버 실행**
   ```bash
   python app.py
   ```

2. **인증 URL 접속** (처음 한 번만)
   - 브라우저에서 접속: `http://localhost:5000/api/uploads/test/oauth-auth`
   - Google 로그인 화면에서 본인 계정으로 로그인
   - 권한 승인

3. **토큰 저장 확인**
   - `token.pickle` 파일이 생성되었는지 확인
   - 위치: 프로젝트 루트 폴더 (`C:\3plsolution\token.pickle`)

### 3. Vercel 배포 환경 설정

Vercel은 서버리스 환경이므로 로컬에서 인증 받은 토큰을 환경 변수로 저장해야 합니다.

#### 3.1. 토큰을 환경 변수로 변환

1. **로컬에서 token.pickle 읽기**
   ```python
   import pickle
   import json
   
   with open('token.pickle', 'rb') as f:
       token_data = pickle.load(f)
   
   # 토큰 정보 추출
   token_dict = {
       'token': token_data.token,
       'refresh_token': token_data.refresh_token,
       'token_uri': token_data.token_uri,
       'client_id': token_data.client_id,
       'client_secret': token_data.client_secret,
       'scopes': token_data.scopes
   }
   
   # JSON으로 변환
   print(json.dumps(token_dict))
   ```

2. **환경 변수로 설정**
   - Vercel 대시보드 → Settings → Environment Variables
   - Key: `GOOGLE_OAUTH_TOKEN_JSON`
   - Value: 위에서 출력한 JSON 문자열
   - Environment: Production, Preview, Development 모두 선택

#### 3.2. credentials.json 환경 변수 설정

1. **credentials.json 내용 복사**
   - 로컬의 `credentials.json` 파일 열기
   - 전체 내용 복사

2. **Vercel 환경 변수 설정**
   - Key: `GOOGLE_OAUTH_CREDENTIALS_JSON`
   - Value: credentials.json 전체 내용
   - Environment: Production, Preview, Development 모두 선택

### 4. 코드 수정 (선택사항)

서버리스 환경에서 토큰을 환경 변수에서 읽도록 `oauth_drive.py`를 수정할 수 있습니다:

```python
# 환경 변수에서 토큰 읽기 (Vercel용)
oauth_token_json = os.environ.get('GOOGLE_OAUTH_TOKEN_JSON')
if oauth_token_json:
    token_dict = json.loads(oauth_token_json)
    creds = Credentials.from_authorized_user_info(token_dict)
    # 토큰이 만료되었으면 갱신
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
```

## 🔍 문제 해결

### 토큰 만료 오류

토큰이 만료되면 자동으로 갱신됩니다. 하지만 갱신에 실패하면:
1. `token.pickle` 파일 삭제
2. 다시 인증 받기

### 로컬 서버 인증 문제

- `credentials.json`이 올바른 위치에 있는지 확인
- Redirect URI가 올바르게 설정되었는지 확인
- Google Cloud Console에서 OAuth 동의 화면이 올바르게 설정되었는지 확인

### Vercel 환경 변수 문제

- 환경 변수가 올바르게 설정되었는지 확인
- JSON 형식이 올바른지 확인
- 재배포 후 테스트

## ✅ 체크리스트

- [ ] OAuth 2.0 클라이언트 ID 생성 완료
- [ ] credentials.json 파일 준비 완료
- [ ] 로컬에서 인증 완료 (token.pickle 생성)
- [ ] Vercel 환경 변수 설정 완료:
  - [ ] `GOOGLE_OAUTH_CREDENTIALS_JSON`
  - [ ] `GOOGLE_OAUTH_TOKEN_JSON` (선택사항)
- [ ] 코드 수정 완료 (서버리스 환경 지원)
- [ ] 테스트 완료

## 📝 참고 사항

1. **토큰 보안**
   - `token.pickle` 파일은 Git에 커밋하지 마세요
   - `.gitignore`에 추가:
     ```
     token.pickle
     credentials.json
     ```

2. **토큰 만료**
   - OAuth 2.0 토큰은 일정 시간 후 만료됩니다
   - Refresh token을 사용하여 자동 갱신됩니다
   - 갱신 실패 시 다시 인증해야 합니다

3. **사용자 제한**
   - OAuth 동의 화면이 "Testing" 상태이면 테스트 사용자만 사용 가능
   - "Published"로 변경하면 모든 사용자 사용 가능

## 🚀 다음 단계

설정이 완료되면:
1. 로컬에서 테스트: `http://localhost:5000/test-excel-upload.html`
2. Vercel에 배포
3. 배포 환경에서 테스트

