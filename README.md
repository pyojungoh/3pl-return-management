# 3PL 반품 관리 시스템

화주사별 반품 내역 조회 및 관리 시스템

## 🚀 빠른 시작

### 로컬 실행
```bash
# 1. 패키지 설치
pip install -r requirements.txt

# 2. 서버 실행
python app.py
```

### 서버 배포 (Vercel)
1. GitHub에 코드 푸시
2. https://vercel.com 접속 → GitHub 로그인
3. "New Project" → 저장소 선택
4. 환경 변수 추가: `SECRET_KEY` (랜덤 문자열)
5. "Deploy" 클릭
6. 배포 완료!

## 🔧 기술 스택

- **Backend**: Flask (Python)
- **Frontend**: HTML, CSS, JavaScript
- **Database**: SQLite
- **Image Storage**: Cloudinary
- **Deployment**: Railway / Render

## 📋 주요 기능

- 화주사별 반품 내역 조회
- QR 코드 스캔을 통한 반품 등록
- 이미지 업로드 (Cloudinary)
- 월별 반품 통계
- 관리자 페이지

## 📝 라이선스

Private

