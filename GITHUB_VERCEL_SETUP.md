# 🚀 GitHub + Vercel 초기 설정 가이드 (완전 초보자용)

## 📋 목차
1. [GitHub 가입 및 저장소 생성](#1-github-가입-및-저장소-생성)
2. [Git 설치 및 초기 설정](#2-git-설치-및-초기-설정)
3. [코드를 GitHub에 푸시](#3-코드를-github에-푸시)
4. [Vercel 가입 및 배포](#4-vercel-가입-및-배포)

---

## 1. GitHub 가입 및 저장소 생성

### 1-1. GitHub 가입
1. 브라우저에서 https://github.com 접속
2. 오른쪽 위 "Sign up" 버튼 클릭
3. 사용자 이름, 이메일, 비밀번호 입력
4. 이메일 인증 완료

### 1-2. 새 저장소(Repository) 생성
1. GitHub 로그인 후 오른쪽 위 "+" 버튼 클릭
2. "New repository" 선택
3. 저장소 정보 입력:
   - **Repository name**: `3pl-return-management` (원하는 이름)
   - **Description**: "3PL 반품 관리 시스템" (선택사항)
   - **Public** 또는 **Private** 선택 (Private 추천)
   - **"Add a README file" 체크 해제** (이미 파일이 있으므로)
4. "Create repository" 버튼 클릭
5. 저장소 URL 복사 (예: `https://github.com/your-username/3pl-return-management.git`)

---

## 2. Git 설치 및 초기 설정

### 2-1. Git 설치 확인
Windows에서 PowerShell 또는 명령 프롬프트(cmd) 열기

```bash
git --version
```

**만약 "git이 인식되지 않습니다" 오류가 나면:**

1. https://git-scm.com/download/win 접속
2. "Download for Windows" 클릭
3. 다운로드된 파일 실행
4. 설치 마법사에서 "Next" 클릭 (기본 설정 유지)
5. 설치 완료 후 **컴퓨터 재시작**
6. 다시 `git --version` 실행하여 확인

### 2-2. Git 초기 설정
처음 한 번만 설정하면 됩니다.

```bash
# 사용자 이름 설정 (GitHub 사용자 이름과 동일하게)
git config --global user.name "Your-Username"

# 이메일 설정 (GitHub 가입 시 사용한 이메일)
git config --global user.email "your-email@example.com"

# 설정 확인
git config --global user.name
git config --global user.email
```

---

## 3. 코드를 GitHub에 푸시

### 3-1. 프로젝트 폴더로 이동
PowerShell 또는 명령 프롬프트에서:

```bash
# 프로젝트 폴더로 이동 (현재 폴더가 이미 프로젝트 폴더라면 이 단계 생략)
cd C:\3pl반품관리및화주사관리
```

### 3-2. Git 저장소 초기화
```bash
git init
```

### 3-3. 모든 파일 추가
```bash
git add .
```

### 3-4. 첫 커밋(Commit) 생성
```bash
git commit -m "Initial commit: Flask server setup"
```

### 3-5. GitHub 저장소 연결
```bash
# 저장소 URL은 위에서 복사한 것을 사용
git remote add origin https://github.com/your-username/3pl-return-management.git

# 연결 확인
git remote -v
```

### 3-6. GitHub에 푸시
```bash
# 메인 브랜치로 푸시
git branch -M main
git push -u origin main
```

**만약 로그인 창이 뜨면:**
- GitHub 사용자 이름 입력
- 비밀번호 대신 **Personal Access Token** 사용 필요

### 3-7. Personal Access Token 생성 (필요한 경우)
1. GitHub 오른쪽 위 프로필 클릭
2. "Settings" 선택
3. 왼쪽 메뉴에서 "Developer settings" 클릭
4. "Personal access tokens" → "Tokens (classic)" 선택
5. "Generate new token" → "Generate new token (classic)" 클릭
6. 설정:
   - **Note**: "Vercel Deployment" (원하는 이름)
   - **Expiration**: "90 days" 또는 "No expiration"
   - **Scopes**: `repo` 체크 (모든 권한)
7. "Generate token" 클릭
8. **토큰 복사** (한 번만 보여줌!)
9. 푸시할 때 비밀번호 대신 이 토큰 사용

### 3-8. 푸시 재시도
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

### 3-9. GitHub에서 확인
1. 브라우저에서 GitHub 저장소 페이지 접속
2. 파일들이 업로드된 것을 확인

---

## 4. Vercel 가입 및 배포

### 4-1. Vercel 가입
1. https://vercel.com 접속
2. "Sign Up" 버튼 클릭
3. "Continue with GitHub" 클릭 (GitHub 계정으로 로그인)
4. GitHub 권한 승인

### 4-2. 새 프로젝트 생성
1. Vercel 대시보드에서 "Add New..." → "Project" 클릭
2. GitHub 저장소 목록에서 방금 만든 저장소 선택
3. "Import" 클릭

### 4-3. 프로젝트 설정
1. **Framework Preset**: "Other" 또는 "Flask" 선택
2. **Root Directory**: `./` (기본값 유지)
3. **Build Command**: 비워두기 (Python은 빌드 불필요)
4. **Output Directory**: 비워두기
5. **Install Command**: `pip install -r requirements.txt`

### 4-4. 환경 변수 설정
1. "Environment Variables" 섹션 클릭
2. 다음 환경 변수 추가:

#### 환경 변수 1: GOOGLE_SERVICE_ACCOUNT_JSON
- **Key**: `GOOGLE_SERVICE_ACCOUNT_JSON`
- **Value**: 서비스 계정 JSON 파일의 전체 내용 (아래 참조)
- **Environment**: Production, Preview, Development 모두 선택

#### 환경 변수 2: SECRET_KEY
- **Key**: `SECRET_KEY`
- **Value**: 랜덤 문자열 (예: `my-super-secret-key-12345`)
- **Environment**: Production, Preview, Development 모두 선택

**서비스 계정 JSON 파일 내용 복사 방법:**
1. `service_account.json` 파일 열기 (메모장 또는 텍스트 에디터)
2. 전체 내용 복사 (Ctrl+A → Ctrl+C)
3. Vercel 환경 변수 Value에 붙여넣기

### 4-5. 배포 시작
1. "Deploy" 버튼 클릭
2. 배포 진행 상황 확인 (1-2분 소요)

### 4-6. 배포 완료
1. 배포가 완료되면 "Congratulations!" 메시지 표시
2. **배포 URL 확인** (예: `https://3pl-return-management.vercel.app`)
3. URL 클릭하여 사이트 접속 테스트

### 4-7. 환경 변수 수정 (나중에)
환경 변수를 수정하려면:
1. Vercel 대시보드 → 프로젝트 선택
2. "Settings" → "Environment Variables" 선택
3. 환경 변수 수정 후 "Save" 클릭
4. "Deployments" → 최신 배포 → "Redeploy" 클릭

---

## 🔄 코드 수정 후 재배포

코드를 수정한 후 GitHub에 푸시하면 Vercel이 자동으로 재배포합니다.

```bash
# 1. 변경된 파일 추가
git add .

# 2. 커밋 생성
git commit -m "Update: 코드 수정 내용 설명"

# 3. GitHub에 푸시
git push

# 4. Vercel이 자동으로 재배포 시작 (1-2분 소요)
```

---

## ✅ 체크리스트

배포 전 확인 사항:

- [ ] GitHub 가입 완료
- [ ] Git 설치 완료
- [ ] Git 초기 설정 완료 (user.name, user.email)
- [ ] GitHub 저장소 생성 완료
- [ ] 코드를 GitHub에 푸시 완료
- [ ] Vercel 가입 완료
- [ ] Vercel에서 프로젝트 생성 완료
- [ ] 환경 변수 설정 완료 (GOOGLE_SERVICE_ACCOUNT_JSON, SECRET_KEY)
- [ ] 배포 완료
- [ ] 배포된 사이트 접속 테스트 완료

---

## 🆘 문제 해결

### Git 푸시 오류
**오류**: `fatal: unable to access 'https://github.com/...': Failed to connect to github.com`

**해결**:
1. 인터넷 연결 확인
2. 방화벽 설정 확인
3. VPN 사용 중이면 끄기

### Personal Access Token 오류
**오류**: `remote: Support for password authentication was removed`

**해결**:
1. Personal Access Token 생성 (위 3-7 참조)
2. 비밀번호 대신 토큰 사용

### Vercel 배포 오류
**오류**: `Module not found` 또는 `Import error`

**해결**:
1. `requirements.txt` 파일 확인
2. 모든 패키지가 포함되어 있는지 확인
3. Vercel 로그 확인 (Deployments → 최신 배포 → "View Function Logs")

### 환경 변수 오류
**오류**: `Google API 인증 실패`

**해결**:
1. `GOOGLE_SERVICE_ACCOUNT_JSON` 환경 변수 확인
2. JSON 전체 내용이 올바르게 복사되었는지 확인
3. Google Sheets에 서비스 계정 이메일 공유 확인

---

## 📞 도움이 필요하면

1. GitHub 문서: https://docs.github.com
2. Vercel 문서: https://vercel.com/docs
3. Git 문서: https://git-scm.com/doc

---

## 🎉 완료!

이제 다음 주소로 접속할 수 있습니다:
- **배포 URL**: `https://your-project.vercel.app`
- **고정 URL**: 변경되지 않음
- **무료**: 완전 무료
- **빠른 속도**: Google Apps Script보다 훨씬 빠름

