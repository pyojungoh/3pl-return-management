# Vercel Postgres 코드 전환 가이드

## 환경 변수
Vercel Postgres 생성 시 자동으로 `POSTGRES_URL` 환경 변수가 설정됩니다.

## requirements.txt에 추가
```
psycopg2-binary==2.9.9
```

## 코드 수정
`api/database/models.py` 파일을 PostgreSQL로 전환해야 합니다.

### 주요 변경사항:
1. SQLite → PostgreSQL 연결
2. `?` 플레이스홀더 → `%s` 플레이스홀더
3. `INTEGER PRIMARY KEY AUTOINCREMENT` → `SERIAL PRIMARY KEY`
4. `sqlite3.Row` → `RealDictCursor`

준비되면 알려주세요. 코드 전환해드리겠습니다!

