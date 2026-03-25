"""
배포 DB(PostgreSQL)에 settlements.return_fee 컬럼 추가
로컬: DATABASE_URL 또는 POSTGRES_URL 환경변수 설정 후 실행
"""
import os
import sys

try:
    import psycopg2
except ImportError:
    print("psycopg2가 필요합니다. pip install psycopg2-binary")
    sys.exit(1)

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
if not DATABASE_URL:
    print("DATABASE_URL 또는 POSTGRES_URL 환경변수를 설정하세요.")
    sys.exit(1)

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()
try:
    cursor.execute("""
        ALTER TABLE settlements
        ADD COLUMN IF NOT EXISTS return_fee INTEGER DEFAULT 0
    """)
    conn.commit()
    print("settlements.return_fee 컬럼 추가 완료")
finally:
    cursor.close()
    conn.close()
