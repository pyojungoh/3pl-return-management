# Vercel 환경 변수 설정 가이드 - Google Drive API

## ⚠️ 현재 문제

Vercel 배포 환경에서 Google Drive API 인증 오류가 발생하고 있습니다:
- 오류 메시지: "Google Drive API 인증 정보를 찾을 수 없습니다"
- 원인: 환경 변수 `GOOGLE_SERVICE_ACCOUNT_JSON`이 설정되지 않았거나 잘못 설정됨

## ✅ 해결 방법

### 1. Google Cloud Console에서 서비스 계정 JSON 다운로드

1. Google Cloud Console 접속: https://console.cloud.google.com/
2. 프로젝트 선택: `composite-dream-477907-c5`
3. 왼쪽 메뉴: **IAM & Admin** → **Service Accounts**
4. 서비스 계정 찾기: `id-pl-return-service@composite-dream-477907-c5.iam.gserviceaccount.com`
5. 서비스 계정 클릭 → **Keys** 탭
6. **Add Key** → **Create new key**
7. Key type: **JSON** 선택
8. **Create** 클릭 (JSON 파일이 자동 다운로드됨)

### 2. JSON 파일 내용 확인

다운로드한 JSON 파일을 열어서 다음 필드가 있는지 확인:
```json
{
  "type": "service_account",
  "project_id": "composite-dream-477907-c5",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "id-pl-return-service@composite-dream-477907-c5.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "..."
}
```

### 3. Vercel 환경 변수 설정

**방법 1: Vercel 대시보드에서 설정 (권장)**

1. Vercel 대시보드 접속: https://vercel.com/
2. 프로젝트 선택: `jjaysolution.com` 또는 `3pl-return-management`
3. **Settings** 탭 클릭
4. 왼쪽 메뉴: **Environment Variables** 클릭
5. **Add New** 버튼 클릭
6. 다음 정보 입력:
   - **Key**: `GOOGLE_SERVICE_ACCOUNT_JSON`
   - **Value**: JSON 파일 전체 내용을 복사하여 붙여넣기
     - ⚠️ **중요**: JSON 파일을 열어서 전체 내용을 복사 (한 줄로 되어 있어도 상관없음)
     - 줄바꿈(`\n`)이 포함되어 있어도 정상 작동
   - **Environment**: 
     - ✅ Production
     - ✅ Preview
     - ✅ Development
     - (모두 선택 권장)
7. **Save** 클릭

**방법 2: Vercel CLI 사용**

```bash
# JSON 파일 내용을 환경 변수로 설정
vercel env add GOOGLE_SERVICE_ACCOUNT_JSON

# 프롬프트가 나오면 JSON 파일 내용 붙여넣기 (Ctrl+V)
# Environment 선택: Production, Preview, Development 모두 선택
```

### 4. 재배포

환경 변수를 추가한 후 **자동으로 재배포되지 않을 수 있으므로**:

1. **Deployments** 탭으로 이동
2. 최신 배포 항목의 **"..."** 메뉴 클릭
3. **Redeploy** 선택
4. 또는 코드를 약간 수정하고 푸시하여 자동 재배포 유도

### 5. 확인

재배포 후 테스트:
1. 테스트 페이지 접속: `https://jjaysolution.com/test-excel-upload.html`
2. 엑셀 파일 업로드 시도
3. 오류가 발생하지 않으면 성공!

## 🔍 문제 해결

### 환경 변수가 설정되었는데도 오류가 발생하는 경우

1. **JSON 형식 확인**
   - JSON 파일이 올바른 형식인지 확인
   - 중괄호 `{}`로 시작하고 끝나는지 확인
   - 따옴표가 올바르게 이스케이프되었는지 확인

2. **Vercel 로그 확인**
   - Vercel 대시보드 → **Deployments** → 최신 배포 클릭
   - **Functions** 탭에서 로그 확인
   - 오류 메시지 확인

3. **서비스 계정 이메일 확인**
   - JSON 파일의 `client_email` 필드 확인
   - 올바른 서비스 계정: `id-pl-return-service@composite-dream-477907-c5.iam.gserviceaccount.com`

4. **Google Drive API 활성화 확인**
   - Google Cloud Console → **APIs & Services** → **Enabled APIs**
   - **Google Drive API**가 활성화되어 있는지 확인

## 📋 체크리스트

- [ ] Google Cloud Console에서 서비스 계정 JSON 파일 다운로드
- [ ] JSON 파일 내용 확인 (`client_email` 필드 확인)
- [ ] Vercel 대시보드에서 `GOOGLE_SERVICE_ACCOUNT_JSON` 환경 변수 추가
- [ ] JSON 파일 전체 내용을 Value에 붙여넣기
- [ ] Production, Preview, Development 모두 선택
- [ ] 재배포 실행
- [ ] 테스트 페이지에서 업로드 테스트
- [ ] 오류가 없는지 확인

## ⚠️ 주의사항

1. **JSON 파일 보안**
   - JSON 파일은 절대 Git에 커밋하지 마세요
   - `.gitignore`에 `service_account.json`이 포함되어 있는지 확인
   - Vercel 환경 변수에만 저장

2. **서비스 계정 권한**
   - Google Drive에서 폴더를 서비스 계정과 공유해야 함
   - 서비스 계정 이메일: `id-pl-return-service@composite-dream-477907-c5.iam.gserviceaccount.com`
   - 권한: **편집자** (중요!)

3. **환경 변수 형식**
   - JSON 파일 전체 내용을 그대로 붙여넣기
   - 줄바꿈이 포함되어 있어도 정상 작동
   - JSON 형식이 올바르게 유지되어야 함

## 📞 추가 도움

문제가 지속되면:
1. Vercel 로그 확인
2. Google Cloud Console에서 서비스 계정 상태 확인
3. Google Drive 폴더 공유 설정 확인

