# 🎯 단계별 완전 초보자 가이드

## ✅ 체크리스트

다음 단계를 순서대로 진행하세요:

- [ ] 1단계: GitHub 가입
- [ ] 2단계: Git 설치
- [ ] 3단계: GitHub 저장소 생성
- [ ] 4단계: 코드를 GitHub에 푸시
- [ ] 5단계: Vercel 가입 및 배포

---

## 1단계: GitHub 가입 (5분)

### 1-1. GitHub 웹사이트 접속
1. 브라우저에서 https://github.com 접속
2. 오른쪽 위 "Sign up" 버튼 클릭

### 1-2. 계정 생성
1. **Username**: 원하는 사용자 이름 입력 (예: `yourname`)
2. **Email**: 이메일 주소 입력
3. **Password**: 비밀번호 입력 (강한 비밀번호 권장)
4. "Verify your account" 퍼즐 풀기
5. "Create account" 버튼 클릭

### 1-3. 이메일 인증
1. 이메일 받은 편지함 확인
2. GitHub에서 보낸 인증 이메일 열기
3. "Verify email address" 버튼 클릭

### 1-4. 가입 완료
- GitHub 로그인 완료!
- 이제 코드를 올릴 수 있습니다.

---

## 2단계: Git 설치 (5분)

### 2-1. Git 다운로드
1. 브라우저에서 https://git-scm.com/download/win 접속
2. "Download for Windows" 버튼 클릭
3. 다운로드된 파일 실행

### 2-2. Git 설치
1. 설치 마법사에서 "Next" 버튼 클릭 (기본 설정 유지)
2. 모든 단계에서 "Next" 클릭
3. "Install" 버튼 클릭
4. 설치 완료 후 **컴퓨터 재시작** (중요!)

### 2-3. Git 설치 확인
1. **Windows 키 + R** 누르기
2. `cmd` 입력 후 Enter
3. 명령 프롬프트 창에서 다음 명령어 입력:

```bash
git --version
```

**성공 메시지:**
```
git version 2.xx.x
```

**실패 메시지 (git이 인식되지 않습니다):**
- 컴퓨터를 재시작했는지 확인
- Git이 제대로 설치되었는지 확인

### 2-4. Git 초기 설정 (한 번만)
명령 프롬프트에서 다음 명령어 실행:

```bash
git config --global user.name "Your-Username"
git config --global user.email "your-email@example.com"
```

**예시:**
```bash
git config --global user.name "pyo08"
git config --global user.email "pyo08@example.com"
```

**설정 확인:**
```bash
git config --global user.name
git config --global user.email
```

---

## 3단계: GitHub 저장소 생성 (3분)

### 3-1. 새 저장소 만들기
1. GitHub 로그인 상태에서 오른쪽 위 **"+"** 버튼 클릭
2. **"New repository"** 선택

### 3-2. 저장소 정보 입력
1. **Repository name**: `3pl-return-management` (원하는 이름)
2. **Description**: "3PL 반품 관리 시스템" (선택사항)
3. **Public** 또는 **Private** 선택
   - **Public**: 누구나 볼 수 있음 (무료)
   - **Private**: 나만 볼 수 있음 (무료, 추천)
4. **"Add a README file" 체크 해제** (이미 파일이 있으므로)
5. **"Create repository"** 버튼 클릭

### 3-3. 저장소 URL 복사
1. 저장소 페이지가 열리면
2. 녹색 **"Code"** 버튼 클릭
3. **HTTPS** 탭 선택
4. URL 복사 (예: `https://github.com/your-username/3pl-return-management.git`)
5. **이 URL을 메모장에 저장해두세요!**

---

## 4단계: 코드를 GitHub에 푸시 (10분)

### 4-1. 명령 프롬프트 열기
1. **Windows 키 + R** 누르기
2. `cmd` 입력 후 Enter
3. 명령 프롬프트 창이 열림

### 4-2. 프로젝트 폴더로 이동
명령 프롬프트에서 다음 명령어 실행:

```bash
cd C:\3pl반품관리및화주사관리
```

**만약 폴더 경로가 다르면:**
- 파일 탐색기에서 프로젝트 폴더 열기
- 주소 표시줄에서 경로 복사
- `cd ` 뒤에 경로 붙여넣기

### 4-3. Git 저장소 초기화
```bash
git init
```

**성공 메시지:**
```
Initialized empty Git repository in C:/3pl반품관리및화주사관리/.git/
```

### 4-4. 모든 파일 추가
```bash
git add .
```

**메시지가 없으면 정상입니다.**

### 4-5. 첫 커밋 생성
```bash
git commit -m "Initial commit: Flask server setup"
```

**성공 메시지:**
```
[main (root-commit) xxxxxxx] Initial commit: Flask server setup
 X files changed, X insertions(+)
```

### 4-6. GitHub 저장소 연결
```bash
git remote add origin https://github.com/your-username/3pl-return-management.git
```

**주의**: `your-username`과 `3pl-return-management`를 위에서 만든 저장소 이름으로 변경하세요!

**연결 확인:**
```bash
git remote -v
```

**성공 메시지:**
```
origin  https://github.com/your-username/3pl-return-management.git (fetch)
origin  https://github.com/your-username/3pl-return-management.git (push)
```

### 4-7. 메인 브랜치 설정
```bash
git branch -M main
```

### 4-8. GitHub에 푸시
```bash
git push -u origin main
```

**로그인 창이 뜨면:**
1. GitHub 사용자 이름 입력
2. 비밀번호 입력 (또는 Personal Access Token)

### 4-9. Personal Access Token 생성 (비밀번호가 안 될 때)
1. GitHub 웹사이트 접속
2. 오른쪽 위 프로필 클릭 → **"Settings"** 선택
3. 왼쪽 메뉴에서 **"Developer settings"** 클릭
4. **"Personal access tokens"** → **"Tokens (classic)"** 선택
5. **"Generate new token"** → **"Generate new token (classic)"** 클릭
6. 설정:
   - **Note**: "Vercel Deployment" (원하는 이름)
   - **Expiration**: "90 days" 또는 "No expiration"
   - **Scopes**: `repo` 체크 (모든 권한)
7. **"Generate token"** 클릭
8. **토큰 복사** (한 번만 보여줌! 메모장에 저장)
9. 푸시할 때 비밀번호 대신 이 토큰 사용

### 4-10. 푸시 재시도
```bash
git push -u origin main
```

**성공 메시지:**
```
Enumerating objects: XX, done.
Counting objects: 100% (XX/XX), done.
Writing objects: 100% (XX/XX), done.
To https://github.com/your-username/3pl-return-management.git
 * [new branch]      main -> main
Branch 'main' set up to track 'remote branch 'main' from 'origin'.
```

### 4-11. GitHub에서 확인
1. 브라우저에서 GitHub 저장소 페이지 접속
2. 파일들이 업로드된 것을 확인
3. ✅ **4단계 완료!**

---

## 5단계: Vercel 가입 및 배포 (10분)

### 5-1. Vercel 가입
1. 브라우저에서 https://vercel.com 접속
2. **"Sign Up"** 버튼 클릭
3. **"Continue with GitHub"** 클릭 (GitHub 계정으로 로그인)
4. GitHub 권한 승인
5. Vercel 대시보드로 이동

### 5-2. 새 프로젝트 생성
1. Vercel 대시보드에서 **"Add New..."** → **"Project"** 클릭
2. GitHub 저장소 목록에서 방금 만든 저장소 선택
3. **"Import"** 버튼 클릭

### 5-3. 프로젝트 설정
1. **Framework Preset**: **"Other"** 선택
2. **Root Directory**: `./` (기본값 유지)
3. **Build Command**: **비워두기** (Python은 빌드 불필요)
4. **Output Directory**: **비워두기**
5. **Install Command**: `pip install -r requirements.txt`

### 5-4. 환경 변수 설정
1. **"Environment Variables"** 섹션 클릭
2. 다음 환경 변수 추가:

#### 환경 변수 1: GOOGLE_SERVICE_ACCOUNT_JSON
- **Key**: `GOOGLE_SERVICE_ACCOUNT_JSON`
- **Value**: 서비스 계정 JSON 파일의 전체 내용
- **Environment**: Production, Preview, Development 모두 선택

**서비스 계정 JSON 파일 내용 복사 방법:**
1. `service_account.json` 파일 열기 (메모장 또는 텍스트 에디터)
2. 전체 내용 선택 (Ctrl+A)
3. 복사 (Ctrl+C)
4. Vercel 환경 변수 Value에 붙여넣기 (Ctrl+V)

#### 환경 변수 2: SECRET_KEY
- **Key**: `SECRET_KEY`
- **Value**: 랜덤 문자열 (예: `my-super-secret-key-12345-abcdef`)
- **Environment**: Production, Preview, Development 모두 선택

### 5-5. 배포 시작
1. **"Deploy"** 버튼 클릭
2. 배포 진행 상황 확인 (1-2분 소요)
3. 배포가 완료되면 **"Congratulations!"** 메시지 표시

### 5-6. 배포 완료
1. **배포 URL 확인** (예: `https://3pl-return-management.vercel.app`)
2. URL 클릭하여 사이트 접속 테스트
3. ✅ **5단계 완료!**

---

## 🎉 완료!

이제 다음 주소로 접속할 수 있습니다:
- **배포 URL**: `https://your-project.vercel.app`
- **고정 URL**: 변경되지 않음
- **무료**: 완전 무료
- **빠른 속도**: Google Apps Script보다 훨씬 빠름

---

## 🔄 다음에 코드 수정할 때

코드를 수정한 후 다음 명령어만 실행하면 됩니다:

```bash
# 1. 변경된 파일 추가
git add .

# 2. 커밋 생성
git commit -m "수정 내용 설명"

# 3. GitHub에 푸시
git push

# 4. Vercel이 자동으로 재배포 (1-2분 소요)
```

---

## 🆘 문제 해결

### Git이 설치되지 않았을 때
1. 컴퓨터 재시작
2. Git 재설치
3. 환경 변수 확인

### GitHub 푸시가 안 될 때
1. Personal Access Token 사용
2. 인터넷 연결 확인
3. 저장소 URL 확인

### Vercel 배포가 안 될 때
1. 환경 변수 확인
2. `requirements.txt` 파일 확인
3. Vercel 로그 확인 (Deployments → 최신 배포 → "View Function Logs")

### 환경 변수 오류
1. JSON 전체 내용이 올바르게 복사되었는지 확인
2. 따옴표나 공백이 없는지 확인
3. Google Sheets에 서비스 계정 이메일 공유 확인

---

## 📞 도움이 필요하면

1. **GitHub 문서**: https://docs.github.com
2. **Vercel 문서**: https://vercel.com/docs
3. **Git 문서**: https://git-scm.com/doc

---

## ✅ 최종 체크리스트

- [ ] GitHub 가입 완료
- [ ] Git 설치 완료
- [ ] Git 초기 설정 완료
- [ ] GitHub 저장소 생성 완료
- [ ] 코드를 GitHub에 푸시 완료
- [ ] Vercel 가입 완료
- [ ] Vercel에서 프로젝트 생성 완료
- [ ] 환경 변수 설정 완료
- [ ] 배포 완료
- [ ] 배포된 사이트 접속 테스트 완료

---

**축하합니다! 🎉 이제 외부 서버로 빠르게 작동하는 시스템이 완성되었습니다!**

