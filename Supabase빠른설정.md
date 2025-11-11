# Supabase 빠른 설정 (5분 완료)

## ✅ 영구 데이터베이스로 전환하면 재시작 시 데이터가 유지됩니다!

## 1단계: Supabase 프로젝트 생성 (2분)

1. https://supabase.com 접속
2. "Start your project" 클릭
3. GitHub 계정으로 로그인
4. "New Project" 클릭
5. 프로젝트 정보 입력:
   - Name: `3pl-return-management`
   - Database Password: (비밀번호 설정 - 기억해두세요!)
   - Region: `Southeast Asia (Seoul)` 선택
6. "Create new project" 클릭
7. 프로젝트 생성 대기 (약 2분)

## 2단계: 연결 정보 가져오기 (1분)

1. 프로젝트 생성 후 → Settings → Database
2. "Connection string" 섹션 찾기
3. "URI" 탭 선택
4. 연결 문자열 복사:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxx.supabase.co:5432/postgres
   ```
5. `[YOUR-PASSWORD]` 부분을 실제 비밀번호로 변경

## 3단계: Vercel 환경 변수 설정 (1분)

1. Vercel 대시보드 → 프로젝트 → Settings → Environment Variables
2. "New Variable" 클릭
3. 입력:
   - Name: `DATABASE_URL`
   - Value: Supabase에서 복사한 연결 문자열 (비밀번호 포함)
   - Environment: Production, Preview, Development 모두 선택
4. "Save" 클릭

## 4단계: 코드 수정 (제가 해드리겠습니다)

준비되면 알려주세요!

## 완료 후
- ✅ 데이터가 영구 저장됨
- ✅ 재시작 시에도 데이터 유지
- ✅ 자동 백업
- ✅ 무료 플랜으로 충분

