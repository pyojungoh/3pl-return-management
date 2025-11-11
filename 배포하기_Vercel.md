# 🚀 Vercel 배포 가이드 (GitHub 연동)

## 이미 배포했던 방법대로 다시 배포하기

### 1단계: GitHub에 코드 푸시

#### 방법 A: Git 명령어 사용
```bash
# 프로젝트 폴더에서 실행
git add .
git commit -m "업데이트"
git push origin main
```

#### 방법 B: GitHub Desktop 사용
1. GitHub Desktop 열기
2. 변경사항 확인
3. "Commit to main" 클릭
4. "Push origin" 클릭

### 2단계: Vercel에서 자동 배포

1. **Vercel 대시보드 접속**
   - https://vercel.com 접속
   - 로그인 (GitHub 계정)

2. **프로젝트 확인**
   - 기존 프로젝트가 있으면 자동으로 재배포됨
   - 새로 만들려면 "Add New Project" 클릭

3. **배포 확인**
   - 배포가 완료되면 URL 확인
   - 자동으로 최신 코드가 배포됨

### 3단계: 환경 변수 설정 (필요한 경우)

Vercel 대시보드 → 프로젝트 → Settings → Environment Variables

추가할 변수 (필요한 경우):
```
CLOUDINARY_CLOUD_NAME=dokk81rjh
CLOUDINARY_API_KEY=447577332396678
CLOUDINARY_API_SECRET=_fh-dOMoaFvOvCRkFk_AzqjOFA8
SECRET_KEY=your-secret-key
```

## 중요 파일 확인

배포에 필요한 파일:
- ✅ `app.py` - Flask 서버
- ✅ `requirements.txt` - Python 패키지
- ✅ `vercel.json` - Vercel 설정 (이미 있음)
- ✅ `dashboard_server.html` - 대시보드
- ✅ `api/` 폴더 - API 라우트

## 배포 후 확인

1. Vercel 대시보드에서 배포 상태 확인
2. 배포된 URL로 접속 테스트
3. 로그인 기능 테스트
4. 이미지 업로드 기능 테스트

## 문제 해결

### 배포 실패
- Vercel 대시보드 → Deployments → 로그 확인
- `requirements.txt` 패키지 확인
- `vercel.json` 설정 확인

### 환경 변수 오류
- Settings → Environment Variables 확인
- 변수 이름과 값이 올바른지 확인

## 자동 배포

- GitHub에 푸시하면 자동으로 Vercel에서 재배포됩니다
- 수동으로 재배포할 필요 없습니다!

