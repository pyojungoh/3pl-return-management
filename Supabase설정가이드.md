# Supabase 설정 가이드 (영구 데이터베이스)

## 1단계: Supabase 프로젝트 생성

1. **Supabase 접속**
   - https://supabase.com 접속
   - GitHub 계정으로 로그인

2. **새 프로젝트 생성**
   - "New Project" 클릭
   - 프로젝트 이름 입력
   - 데이터베이스 비밀번호 설정 (기억해두세요!)
   - 리전 선택 (가장 가까운 곳)
   - "Create new project" 클릭

3. **프로젝트 생성 대기** (약 2분)

## 2단계: 데이터베이스 연결 정보 가져오기

1. **Settings → Database 클릭**
2. **Connection string 찾기**
   - "Connection string" 섹션
   - "URI" 또는 "Connection pooling" 선택
   - 문자열 복사 (예: `postgresql://postgres:[PASSWORD]@db.xxx.supabase.co:5432/postgres`)

## 3단계: Vercel 환경 변수 설정

1. **Vercel 대시보드 접속**
2. **프로젝트 → Settings → Environment Variables**
3. **새 변수 추가:**
   - Name: `DATABASE_URL`
   - Value: Supabase에서 복사한 연결 문자열
   - Environment: Production, Preview, Development 모두 선택
4. **Save 클릭**

## 4단계: 코드 수정 (PostgreSQL 사용)

### requirements.txt에 추가:
```
psycopg2-binary==2.9.9
```

### api/database/models.py 수정:
- SQLite → PostgreSQL 전환
- 연결 문자열 사용

## 5단계: 데이터 마이그레이션

1. **로컬 SQLite 데이터베이스에서 데이터 추출**
2. **Supabase PostgreSQL로 데이터 이전**

## 완료!

이제 데이터가 영구적으로 저장됩니다!

