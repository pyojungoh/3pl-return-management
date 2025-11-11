# Neon 데이터베이스 환경 변수 설정

## 1단계: DATABASE_URL 복사

1. **Quickstart 섹션에서**
   - `.env.local` 탭이 선택되어 있는지 확인
   - `DATABASE_URL=********` 부분 확인

2. **비밀번호 보기**
   - "Show secret" 버튼 클릭 (눈 아이콘)
   - 비밀번호가 표시됨

3. **연결 문자열 복사**
   - "Copy Snippet" 버튼 클릭 (복사 아이콘)
   - 또는 `DATABASE_URL=` 뒤의 전체 값을 복사

## 2단계: Vercel 환경 변수 설정

1. **Vercel 대시보드 접속**
   - https://vercel.com 접속
   - 프로젝트 선택

2. **Environment Variables로 이동**
   - Settings → Environment Variables

3. **새 변수 추가**
   - "New Variable" 클릭
   - Name: `DATABASE_URL`
   - Value: 복사한 DATABASE_URL 값 (전체)
   - Environment: 
     - ✅ Production
     - ✅ Preview
     - ✅ Development
   - "Save" 클릭

## 3단계: 확인

- 환경 변수가 추가되었는지 확인
- `DATABASE_URL`이 목록에 있는지 확인

## 완료!

이제 코드를 PostgreSQL로 전환하면 됩니다!

