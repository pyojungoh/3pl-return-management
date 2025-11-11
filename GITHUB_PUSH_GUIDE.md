# 🚀 GitHub 푸시 가이드 (빠른 시작)

## 📍 현재 상황
- GitHub 저장소 생성 완료: https://github.com/pyojungoh/3pl-return-management.git
- 로컬 코드를 GitHub에 푸시해야 함

## ⚡ 빠른 시작 (5분)

### 1단계: 명령 프롬프트 열기
1. **Windows 키 + R** 누르기
2. `cmd` 입력 후 **Enter**
3. 명령 프롬프트 창이 열림

### 2단계: 프로젝트 폴더로 이동
명령 프롬프트에서 실행:

```bash
cd C:\3pl반품관리및화주사관리
```

### 3단계: Git 초기화 (처음 한 번만)
```bash
git init
```

### 4단계: Git 사용자 정보 설정 (처음 한 번만)
```bash
git config --global user.name "pyojungoh"
git config --global user.email "your-email@example.com"
```

**주의**: `your-email@example.com`을 GitHub 가입 시 사용한 이메일로 변경하세요!

### 5단계: 파일 추가
```bash
git add .
```

### 6단계: 첫 커밋 생성
```bash
git commit -m "Initial commit: Flask server setup"
```

### 7단계: GitHub 저장소 연결
```bash
git remote add origin https://github.com/pyojungoh/3pl-return-management.git
```

### 8단계: 메인 브랜치 설정
```bash
git branch -M main
```

### 9단계: GitHub에 푸시
```bash
git push -u origin main
```

**로그인 창이 뜨면:**
- **사용자 이름**: `pyojungoh`
- **비밀번호**: GitHub 비밀번호 또는 **Personal Access Token**

### 10단계: Personal Access Token 생성 (비밀번호가 안 될 때)

1. **GitHub 웹사이트 접속**
2. 오른쪽 위 프로필 클릭 → **"Settings"** 선택
3. 왼쪽 메뉴에서 **"Developer settings"** 클릭
4. **"Personal access tokens"** → **"Tokens (classic)"** 선택
5. **"Generate new token"** → **"Generate new token (classic)"** 클릭
6. 설정:
   - **Note**: "Vercel Deployment"
   - **Expiration**: "90 days" 또는 "No expiration"
   - **Scopes**: `repo` 체크 (모든 권한)
7. **"Generate token"** 클릭
8. **토큰 복사** (한 번만 보여줌! 메모장에 저장)
9. 푸시할 때 비밀번호 대신 이 토큰 사용

### 11단계: 푸시 재시도
```bash
git push -u origin main
```

## ✅ 성공 메시지

다음과 같은 메시지가 나오면 성공입니다:

```
Enumerating objects: XX, done.
Counting objects: 100% (XX/XX), done.
Writing objects: 100% (XX/XX), done.
To https://github.com/pyojungoh/3pl-return-management.git
 * [new branch]      main -> main
Branch 'main' set up to track 'remote branch 'main' from 'origin'.
```

## 🔍 확인 방법

1. 브라우저에서 https://github.com/pyojungoh/3pl-return-management 접속
2. 파일들이 업로드된 것을 확인
3. ✅ **완료!**

## 🆘 문제 해결

### Git이 설치되지 않았을 때
1. https://git-scm.com/download/win 접속
2. Git 다운로드 및 설치
3. 컴퓨터 재시작
4. 다시 시도

### "git이 인식되지 않습니다" 오류
1. 컴퓨터 재시작
2. Git 재설치
3. 환경 변수 확인

### "remote origin already exists" 오류
```bash
git remote remove origin
git remote add origin https://github.com/pyojungoh/3pl-return-management.git
```

### "Support for password authentication was removed" 오류
- Personal Access Token 사용 (위 10단계 참조)

### 푸시가 안 될 때
1. 인터넷 연결 확인
2. 저장소 URL 확인
3. Personal Access Token 사용

## 🎯 다음 단계

GitHub에 푸시가 완료되면:
1. Vercel 가입 및 배포 (STEP_BY_STEP_GUIDE.md 참조)
2. 환경 변수 설정
3. 배포 완료!

## 📝 전체 명령어 한번에 복사

```bash
cd C:\3pl반품관리및화주사관리
git init
git config --global user.name "pyojungoh"
git config --global user.email "your-email@example.com"
git add .
git commit -m "Initial commit: Flask server setup"
git remote add origin https://github.com/pyojungoh/3pl-return-management.git
git branch -M main
git push -u origin main
```

**주의**: `your-email@example.com`을 실제 이메일로 변경하세요!

