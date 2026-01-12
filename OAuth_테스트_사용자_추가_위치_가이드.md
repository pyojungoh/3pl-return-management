# OAuth 테스트 사용자 추가 위치 가이드

## 📍 현재 위치

**OAuth Overview 페이지** - 여기서는 테스트 사용자를 추가할 수 없습니다.

## ✅ 올바른 위치로 이동하기

### 방법 1: 왼쪽 사이드바에서 이동 (권장)

1. **왼쪽 사이드바 확인**
   - 현재 "개요" (Overview)가 선택되어 있음
   - 아래 메뉴들을 확인:
     - 브랜딩 (Branding)
     - 대상 (Target)
     - 클라이언트 (Client)
     - 데이터 액세스 (Data Access)
     - 인증 센터 (Auth Center)
     - 설정 (Settings)

2. **"대상" (Target) 또는 "설정" (Settings) 클릭**
   - 테스트 사용자는 OAuth 동의 화면 설정에 있습니다
   - "대상" 또는 "설정" 메뉴에서 찾을 수 있습니다

### 방법 2: APIs & Services 메뉴로 이동 (기존 방식)

1. **왼쪽 상단 햄버거 메뉴 클릭** (☰)
2. **"APIs & Services" 찾기**
   - 메뉴에서 "APIs & Services" 또는 "API 및 서비스" 찾기
3. **"OAuth consent screen" 클릭**
   - "OAuth 동의 화면" 또는 "OAuth consent screen"
4. **페이지 하단으로 스크롤**
   - "Test users" 또는 "테스트 사용자" 섹션 찾기
   - "+ ADD USERS" 또는 "+ 사용자 추가" 버튼 클릭

### 방법 3: 직접 URL 접속

1. **브라우저 주소창에 입력**:
   ```
   https://console.cloud.google.com/apis/credentials/consent?project=composite-dream-477907-c5
   ```
2. **또는**:
   ```
   https://console.cloud.google.com/apis/credentials/consent
   ```
   (프로젝트가 자동으로 선택됨)

## 🔍 테스트 사용자 추가 위치

OAuth 동의 화면 페이지에서:

1. **페이지 하단으로 스크롤**
2. **"Test users" 또는 "테스트 사용자" 섹션 찾기**
   - "Testing" 상태일 때만 표시됩니다
3. **"+ ADD USERS" 또는 "+ 사용자 추가" 버튼 클릭**
4. **이메일 입력**: `jjay220304@gmail.com`
5. **"ADD" 또는 "추가" 클릭**
6. **저장**

## 💡 팁

- OAuth Overview 페이지가 아닌 **OAuth consent screen** 페이지로 이동해야 합니다
- 왼쪽 사이드바에서 다른 메뉴를 클릭하거나
- 상단 메뉴에서 "APIs & Services" → "OAuth consent screen"으로 이동하세요

## 📝 체크리스트

- [ ] OAuth Overview 페이지에서 나가기
- [ ] OAuth consent screen 페이지로 이동
- [ ] 페이지 하단 "Test users" 섹션 찾기
- [ ] "+ ADD USERS" 버튼 클릭
- [ ] 이메일 추가: `jjay220304@gmail.com`
- [ ] 저장

