# Vercel 로그 확인 가이드

## 🔍 배포 환경 403 오류 디버깅

환경 변수는 설정되어 있지만 여전히 403 오류가 발생하는 경우, Vercel 로그를 확인해야 합니다.

## 📋 Vercel 로그 확인 방법

### 1단계: Vercel 대시보드 접속

1. https://vercel.com/ 접속
2. 프로젝트 선택

### 2단계: Deployments 탭

1. 상단 메뉴에서 **"Deployments"** 탭 클릭
2. 최신 배포 항목 클릭 (가장 위에 있는 것)

### 3단계: Functions 탭

1. 배포 상세 페이지에서 **"Functions"** 탭 클릭
2. 또는 **"Logs"** 탭 클릭

### 4단계: 로그 확인

엑셀 업로드 시도 후 로그에서 다음 메시지를 확인하세요:

#### ✅ 정상 작동 시 보이는 메시지:
```
📄 엑셀 파일 업로드 시작: [파일명]
🔍 OAuth 2.0 인증 정보 확인 중...
   Vercel 환경: True
   GOOGLE_OAUTH_TOKEN_JSON 존재: True
   GOOGLE_OAUTH_CREDENTIALS_JSON 존재: True
   GOOGLE_OAUTH_TOKEN_JSON 길이: [숫자] 문자
   GOOGLE_OAUTH_CREDENTIALS_JSON 길이: [숫자] 문자
✅ 환경 변수에서 OAuth 토큰 로드 성공 (Vercel 배포 환경)
✅ Google Drive API 서비스 생성 완료 (OAuth 2.0)
✅ 메인 폴더 ID 사용: 제이제이솔루션 (ID: ...)
✅ 대상 폴더 찾기 성공: 정산파일 (ID: ...)
✅ 파일 업로드 성공: [파일명]
```

#### ❌ 문제 발생 시 보이는 메시지:

**환경 변수가 없는 경우:**
```
🔍 OAuth 2.0 인증 정보 확인 중...
   Vercel 환경: True
   GOOGLE_OAUTH_TOKEN_JSON 존재: False
   GOOGLE_OAUTH_CREDENTIALS_JSON 존재: False
⚠️ 환경 변수에서 토큰 로드 실패: ...
Vercel 배포 환경에서 OAuth 2.0 환경 변수가 설정되지 않았습니다.
```

**JSON 파싱 실패:**
```
⚠️ 환경 변수에서 토큰 로드 실패: JSON 파싱 오류: ...
```

**토큰 만료:**
```
✅ 환경 변수에서 OAuth 토큰 로드 성공
🔄 토큰 갱신 중...
❌ 토큰 갱신 실패: ...
```

## 🔧 문제 해결

### 환경 변수가 없다고 나오는 경우

1. **Vercel 환경 변수 재확인**
   - Settings → Environment Variables
   - 두 환경 변수가 모두 있는지 확인
   - 각각 클릭하여 내용 확인

2. **재배포**
   - 환경 변수를 추가한 후 반드시 재배포 필요
   - Deployments → 최신 배포 → "..." → Redeploy

### JSON 파싱 오류인 경우

1. **환경 변수 내용 확인**
   - JSON 형식이 올바른지 확인
   - 따옴표가 올바르게 이스케이프되었는지 확인

2. **환경 변수 재설정**
   - 로컬 파일에서 다시 복사
   - Vercel에 다시 붙여넣기
   - 재배포

### 토큰 만료인 경우

1. **로컬에서 다시 인증 받기**
   - `token.pickle` 파일 삭제
   - 다시 업로드 시도하여 인증 받기

2. **토큰 추출 및 환경 변수 업데이트**
   - `python extract_oauth_token.py` 실행
   - 출력된 JSON을 Vercel 환경 변수에 업데이트
   - 재배포

## 📝 체크리스트

로그 확인:
- [ ] Vercel Deployments → 최신 배포 → Functions/Logs
- [ ] 엑셀 업로드 시도
- [ ] 로그에서 디버깅 메시지 확인:
  - [ ] "Vercel 환경: True" 확인
  - [ ] "GOOGLE_OAUTH_TOKEN_JSON 존재: True" 확인
  - [ ] "GOOGLE_OAUTH_CREDENTIALS_JSON 존재: True" 확인
  - [ ] "✅ 환경 변수에서 OAuth 토큰 로드 성공" 확인
  - [ ] "✅ Google Drive API 서비스 생성 완료 (OAuth 2.0)" 확인

## 💡 중요 사항

1. **로그는 실시간으로 업데이트됩니다**
   - 엑셀 업로드를 시도하면 로그에 메시지가 나타납니다

2. **로그를 복사하여 공유**
   - 문제가 지속되면 로그를 복사하여 공유하면 더 정확한 진단이 가능합니다

3. **환경 변수는 재배포 후에만 적용됩니다**
   - 환경 변수를 추가/수정한 후 반드시 재배포해야 합니다

