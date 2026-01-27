"""
배포 DB(PostgreSQL/Neon)에 settlements.collect_on_delivery_fee 컬럼 추가
작업규칙: 스키마 변경 시 배포 DB에 마이그레이션 스크립트 실행 필수
"""
import os
import sys

try:
    import psycopg2
except ImportError:
    print("❌ psycopg2가 필요합니다. pip install psycopg2-binary")
    sys.exit(1)

DATABASE_URL = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')
if not DATABASE_URL:
    DATABASE_URL = "postgresql://neondb_owner:npg_CNqVFs9j2Bpi@ep-dark-queen-a4w25otz-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"
    print("ℹ️  환경변수 DATABASE_URL 없음 → 배포 DB URL 사용")

print("=" * 50)
print("settlements.collect_on_delivery_fee 컬럼 추가 (배포 DB)")
print("=" * 50)

try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    print("✅ PostgreSQL 연결 성공")
except Exception as e:
    print(f"❌ PostgreSQL 연결 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    cursor.execute("""
        ALTER TABLE settlements
        ADD COLUMN IF NOT EXISTS collect_on_delivery_fee INTEGER DEFAULT 0
    """)
    conn.commit()
    print("✅ collect_on_delivery_fee 컬럼 추가 완료")
except Exception as e:
    print(f"❌ 오류: {e}")
    import traceback
    traceback.print_exc()
    conn.rollback()
    sys.exit(1)
finally:
    cursor.close()
    conn.close()

print("=" * 50)
