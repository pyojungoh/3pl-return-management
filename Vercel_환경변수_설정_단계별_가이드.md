# Vercel 환경 변수 설정 단계별 가이드

## 📋 목표

`GOOGLE_OAUTH_TOKEN_JSON` 환경 변수를 Vercel에 설정하기

## 🔧 단계별 가이드

### 1단계: 로컬에서 토큰 생성 (아직 안 했다면)

1. **Flask 서버 실행**
   ```bash
   python app.py
   ```

2. **브라우저에서 엑셀 업로드 테스트**
   - `http://localhost:5000/test-excel-upload.html` 접속
   - 엑셀 파일 선택 후 "업로드 시작" 클릭
   - Google 로그인 화면에서 로그인 및 권한 승인
   - `token.pickle` 파일이 생성되었는지 확인

### 2단계: 토큰 정보 추출

1. **터미널에서 스크립트 실행**
   ```bash
   python extract_oauth_token.py
   ```

2. **출력 결과 확인**
   - 터미널에 다음과 같은 출력이 나타납니다:
   ```
   ✅ 토큰 정보 추출 완료!
   
   ============================================================
   Vercel 환경 변수 설정:
   ============================================================
   
   Key: GOOGLE_OAUTH_TOKEN_JSON
   Value: (아래 JSON 전체를 복사하세요)
   
   {
     "token": "ya29.a0AfH6SMC...",
     "refresh_token": "1//0g...",
     "token_uri": "https://oauth2.googleapis.com/token",
     "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
     "client_secret": "YOUR_CLIENT_SECRET",
     "scopes": ["https://www.googleapis.com/auth/drive"]
   }
   
   ============================================================
   ```

3. **JSON 전체 복사**
   - 위 출력에서 `{` 부터 `}` 까지 **전체를 복사**하세요
   - 마우스로 드래그하여 선택 후 `Ctrl+C` (또는 `Cmd+C`)

### 3단계: Vercel 대시보드에서 환경 변수 설정

1. **Vercel 대시보드 접속**
   - https://vercel.com/ 접속
   - 로그인

2. **프로젝트 선택**
   - 대시보드에서 프로젝트 클릭 (예: `jjaysolution.com` 또는 `3pl-return-management`)

3. **Settings 메뉴 클릭**
   - 상단 메뉴에서 **"Settings"** 탭 클릭

4. **Environment Variables 메뉴 클릭**
   - 왼쪽 사이드바에서 **"Environment Variables"** 클릭

5. **새 환경 변수 추가**
   - 오른쪽 상단의 **"Add New"** 버튼 클릭

6. **Key 입력**
   - **Key** 필드에 입력: `GOOGLE_OAUTH_TOKEN_JSON`
   - 정확히 입력하세요 (대소문자 구분)

7. **Value 입력**
   - **Value** 필드에 2단계에서 복사한 JSON 전체를 붙여넣기
   - `Ctrl+V` (또는 `Cmd+V`)
   - 예시:
     ```json
     {
       "token": "ya29.a0AfH6SMC...",
       "refresh_token": "1//0g...",
       "token_uri": "https://oauth2.googleapis.com/token",
       "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
       "client_secret": "YOUR_CLIENT_SECRET",
       "scopes": ["https://www.googleapis.com/auth/drive"]
     }
     ```

8. **Environment 선택**
   - 아래 체크박스에서 모두 선택:
     - ✅ **Production**
     - ✅ **Preview**
     - ✅ **Development**
   - (모두 선택하는 것이 중요합니다!)

9. **저장**
   - **"Save"** 버튼 클릭

### 4단계: credentials.json도 환경 변수로 설정

같은 방식으로 `GOOGLE_OAUTH_CREDENTIALS_JSON`도 설정하세요:

1. **다시 "Add New" 클릭**

2. **Key 입력**
   - `GOOGLE_OAUTH_CREDENTIALS_JSON`

3. **Value 입력**
   - 프로젝트 루트의 `credentials.json` 파일을 열기
   - 전체 내용 복사 (한 줄 JSON)
   - 예시:
     ```json
     {"installed":{"client_id":"YOUR_CLIENT_ID.apps.googleusercontent.com","project_id":"YOUR_PROJECT_ID","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_secret":"YOUR_CLIENT_SECRET","redirect_uris":["http://localhost"]}}
     ```

4. **Environment 선택**
   - ✅ Production
   - ✅ Preview
   - ✅ Development

5. **저장**

### 5단계: 재배포

1. **Deployments 탭으로 이동**
   - 상단 메뉴에서 **"Deployments"** 클릭

2. **최신 배포 찾기**
   - 가장 위에 있는 배포 항목 확인

3. **재배포**
   - 배포 항목 오른쪽의 **"..."** (점 3개) 메뉴 클릭
   - **"Redeploy"** 선택
   - 또는 코드를 약간 수정하고 `git push`하여 자동 재배포

### 6단계: 테스트

1. **배포 완료 대기**
   - 배포 상태가 "Ready"가 될 때까지 대기

2. **웹에서 테스트**
   - `https://jjaysolution.com/test-excel-upload.html` 접속
   - 엑셀 파일 업로드 시도
   - ✅ 성공하면 완료!

## ⚠️ 주의사항

1. **JSON 형식**
   - JSON 전체를 복사해야 합니다 (`{` 부터 `}` 까지)
   - 중간에 잘리면 안 됩니다
   - 따옴표가 올바르게 이스케이프되어 있어야 합니다

2. **Environment 선택**
   - Production, Preview, Development 모두 선택해야 합니다
   - 하나라도 빠지면 해당 환경에서 작동하지 않습니다

3. **재배포 필수**
   - 환경 변수를 추가한 후 반드시 재배포해야 합니다
   - 자동으로 재배포되지 않을 수 있습니다

## 🔍 확인 방법

환경 변수가 제대로 설정되었는지 확인:

1. **Vercel 대시보드 → Settings → Environment Variables**
2. 다음 두 개가 모두 보여야 합니다:
   - `GOOGLE_OAUTH_CREDENTIALS_JSON`
   - `GOOGLE_OAUTH_TOKEN_JSON`
3. 각각의 Environment가 모두 선택되어 있는지 확인

## 💡 팁

- JSON을 복사할 때 전체를 선택하는 것이 중요합니다
- Value 필드가 길어서 스크롤이 필요할 수 있습니다
- JSON 형식이 올바른지 확인하려면 온라인 JSON 검증 도구 사용 가능

