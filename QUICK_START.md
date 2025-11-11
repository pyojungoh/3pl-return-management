# ⚡ 빠른 시작 가이드

## 5분 안에 배포하기

### 1단계: GitHub 가입 (2분)
1. https://github.com 접속
2. "Sign up" 클릭
3. 가입 완료

### 2단계: Git 설치 (2분)
1. https://git-scm.com/download/win 접속
2. 다운로드 및 설치
3. 컴퓨터 재시작

### 3단계: 코드 푸시 (1분)
PowerShell에서 실행:

```bash
# 프로젝트 폴더로 이동
cd C:\3pl반품관리및화주사관리

# Git 초기화
git init

# Git 설정 (한 번만)
git config --global user.name "Your-Username"
git config --global user.email "your-email@example.com"

# 파일 추가
git add .

# 커밋
git commit -m "Initial commit"

# GitHub 저장소 연결 (저장소 URL은 GitHub에서 복사)
git remote add origin https://github.com/your-username/your-repo.git

# 푸시
git branch -M main
git push -u origin main
```

### 4단계: Vercel 배포 (2분)
1. https://vercel.com 접속
2. "Sign Up" → "Continue with GitHub" 클릭
3. "Add New Project" 클릭
4. 저장소 선택 → "Import" 클릭
5. 환경 변수 추가:
   - `GOOGLE_SERVICE_ACCOUNT_JSON`: 서비스 계정 JSON 전체 내용
   - `SECRET_KEY`: 랜덤 문자열
6. "Deploy" 클릭
7. 완료! 🎉

---

## 📝 다음에 코드 수정할 때

```bash
git add .
git commit -m "수정 내용"
git push
```

Vercel이 자동으로 재배포합니다!

---

## 🔗 자세한 설명

더 자세한 설명이 필요하면 `GITHUB_VERCEL_SETUP.md` 파일을 참조하세요.

