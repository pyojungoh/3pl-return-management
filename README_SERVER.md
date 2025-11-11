# 3PL 반품 관리 시스템 - 외부 서버 버전

## 🚀 빠른 시작

### 1. Google 서비스 계정 설정

1. Google Cloud Console에서 프로젝트 생성
2. Google Sheets API 활성화
3. 서비스 계정 생성
4. 서비스 계정 키 JSON 파일 다운로드
5. `service_account.json` 파일을 프로젝트 루트에 저장
6. Google Sheets에 서비스 계정 이메일 공유 (편집 권한)

### 2. 로컬 개발 환경 설정

```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (Windows)
venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt

# 서버 실행
python server_new.py
```

서버가 `http://localhost:5000`에서 실행됩니다.

### 3. 환경 변수 설정 (배포 시)

배포 플랫폼에서 다음 환경 변수 설정:

- `GOOGLE_SERVICE_ACCOUNT_JSON`: 서비스 계정 JSON (전체 내용)
- `SECRET_KEY`: Flask 시크릿 키 (랜덤 문자열)
- `PORT`: 포트 번호 (일부 플랫폼은 자동 설정)

## 📦 배포 방법

### Vercel 배포

1. Vercel 계정 생성
2. GitHub에 코드 푸시
3. Vercel에서 프로젝트 임포트
4. 환경 변수 설정
5. 배포

### Railway 배포

1. Railway 계정 생성
2. GitHub 연동
3. 환경 변수 설정
4. 배포

## 🔧 API 엔드포인트

### 인증 API

- `POST /api/auth/login`: 로그인
- `GET /api/auth/health`: 상태 확인

### 반품 데이터 API

- `GET /api/returns/sheets`: 시트 목록 조회
- `GET /api/returns/data`: 반품 데이터 조회
- `POST /api/returns/save-request`: 요청사항 저장
- `POST /api/returns/mark-completed`: 처리완료 표시

## 📝 주요 변경사항

- Google Apps Script → Flask 서버
- `google.script.run` → REST API 호출
- 속도 개선: 서버 캐싱 및 최적화 가능
- 확장성: 추가 기능 구현 용이

## ⚡ 속도 개선 효과

- 로그인: 즉시 응답
- 데이터 조회: 2-3초 → 0.5-1초
- 요청사항 저장: 즉시 반영
- 전체적인 사용자 경험 개선

