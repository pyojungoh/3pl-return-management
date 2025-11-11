# Vercel Postgres 설정 가이드

## 🚀 Vercel Postgres 설정 (5분 완료)

### 1단계: Vercel Postgres 생성

1. **Vercel 대시보드 접속**
   - https://vercel.com 접속
   - 프로젝트 선택

2. **Storage 생성**
   - 프로젝트 → **Storage** 탭 클릭
   - 또는 프로젝트 → **Settings** → **Storage** 클릭
   - **"Create Database"** 클릭

3. **Postgres 선택**
   - **"Postgres"** 선택
   - **"Create"** 클릭

4. **데이터베이스 생성 대기** (약 1-2분)

### 2단계: 환경 변수 확인

Vercel Postgres 생성 시 자동으로 환경 변수가 설정됩니다:
- `POSTGRES_URL` - PostgreSQL 연결 URL
- `POSTGRES_PRISMA_URL` - Prisma용 연결 URL
- `POSTGRES_URL_NON_POOLING` - 풀링 없는 연결 URL
- `POSTGRES_USER` - 사용자명
- `POSTGRES_HOST` - 호스트
- `POSTGRES_PASSWORD` - 비밀번호
- `POSTGRES_DATABASE` - 데이터베이스명

**확인 방법:**
- 프로젝트 → **Settings** → **Environment Variables**
- 위 환경 변수들이 자동으로 추가되어 있는지 확인

### 3단계: 연결 문자열 확인

**방법 1: 환경 변수에서 확인**
- `POSTGRES_URL` 환경 변수 값을 복사

**방법 2: Storage 탭에서 확인**
- Storage → Postgres → **".env.local"** 탭
- 연결 문자열 복사

연결 문자열 형식:
```
postgres://default:비밀번호@ep-xxx.region.aws.neon.tech:5432/verceldb?sslmode=require
```

### 4단계: 코드에서 사용

환경 변수 `POSTGRES_URL`을 사용하거나, 
필요시 `DATABASE_URL` 환경 변수에 `POSTGRES_URL` 값을 복사하여 설정

### 완료!

이제 PostgreSQL 데이터베이스가 준비되었습니다!

## 다음 단계

코드를 PostgreSQL로 전환하면 됩니다.
준비되면 알려주세요!

