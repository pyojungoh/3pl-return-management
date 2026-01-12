# OAuth 2.0 테스트 사용자 추가 가이드

## ❌ 오류 메시지

```
403 오류: access_denied
3pl-return-service은(는) Google 인증 절차를 완료하지 않았습니다
앱은 현재 테스트 중이며 개발자가 승인한 테스터만 앱에 액세스할 수 있습니다
```

## 🔍 원인

OAuth 동의 화면이 "Testing" 상태이고, 사용자 이메일이 테스트 사용자 목록에 없습니다.

## ✅ 해결 방법

### 방법 1: 테스트 사용자 추가 (빠른 해결)

1. **Google Cloud Console 접속**
   - https://console.cloud.google.com/
   - 프로젝트 선택: `composite-dream-477907-c5`

2. **APIs & Services → OAuth consent screen**
   - 왼쪽 메뉴: APIs & Services → OAuth consent screen

3. **테스트 사용자 추가**
   - 페이지 하단의 **"Test users"** 섹션 찾기
   - **"+ ADD USERS"** 버튼 클릭

4. **이메일 추가**
   - 본인 이메일 입력: `jjay220304@gmail.com`
   - **"ADD"** 클릭

5. **저장**
   - 페이지 하단의 **"SAVE AND CONTINUE"** 또는 **"BACK TO DASHBOARD"** 클릭

6. **다시 인증 시도**
   - 로컬에서 다시 엑셀 업로드 시도
   - 이제 정상적으로 로그인 가능합니다

### 방법 2: 앱을 Published 상태로 변경 (모든 사용자 사용 가능)

**주의**: 앱을 Published로 변경하면 모든 사용자가 사용할 수 있습니다. 테스트 단계에서는 방법 1을 권장합니다.

1. **OAuth consent screen 페이지 접속**
   - APIs & Services → OAuth consent screen

2. **"PUBLISH APP" 버튼 클릭**
   - 페이지 상단에 있는 버튼

3. **확인**
   - 경고 메시지 확인 후 "CONFIRM" 클릭

4. **다시 인증 시도**

## 📋 체크리스트

- [ ] Google Cloud Console 접속
- [ ] 프로젝트 선택: `composite-dream-477907-c5`
- [ ] APIs & Services → OAuth consent screen
- [ ] Test users 섹션에서 "+ ADD USERS" 클릭
- [ ] 이메일 추가: `jjay220304@gmail.com`
- [ ] 저장
- [ ] 다시 인증 시도

## 💡 참고

- **Testing 상태**: 개발 중인 앱, 테스트 사용자만 사용 가능
- **Published 상태**: 모든 사용자가 사용 가능 (Google 검토 필요할 수 있음)
- 테스트 단계에서는 **Testing 상태 + 테스트 사용자 추가**가 가장 간단합니다

## 🚀 다음 단계

테스트 사용자를 추가한 후:
1. 로컬에서 다시 엑셀 업로드 시도
2. Google 로그인 정상 작동 확인
3. 토큰 생성 확인 (`token.pickle` 파일 생성)
4. `python extract_oauth_token.py` 실행하여 토큰 추출
5. Vercel 환경 변수 설정

