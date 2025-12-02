"""
PostgreSQL 헤더 배너 테이블 생성 스크립트
작업규칙에 따라 배포 환경에 직접 연결하여 테이블 생성
"""
import psycopg2
import os
import sys

# 배포 환경 DATABASE_URL (작업규칙에 명시된 값)
DATABASE_URL = "postgresql://neondb_owner:npg_CNqVFs9j2Bpi@ep-dark-queen-a4w25otz-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"

print("=" * 50)
print("PostgreSQL 헤더 배너 테이블 생성 (배포 환경)")
print("=" * 50)

# PostgreSQL에 직접 연결
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
    # 테이블이 이미 존재하는지 확인
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'header_banners'
        );
    """)
    table_exists = cursor.fetchone()[0]
    
    if table_exists:
        print("⚠️ header_banners 테이블이 이미 존재합니다.")
        print("   IF NOT EXISTS로 인해 테이블이 생성되지 않습니다.")
        print("   기존 테이블을 사용합니다.")
    else:
        print("✅ 테이블이 존재하지 않습니다. 생성합니다.")
    
    # 테이블 생성
    print("\n테이블 생성 중...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS header_banners (
            id SERIAL PRIMARY KEY,
            text TEXT NOT NULL,
            link_type TEXT DEFAULT 'none',
            board_post_id INTEGER,
            is_active BOOLEAN DEFAULT TRUE,
            display_order INTEGER DEFAULT 0,
            text_color TEXT DEFAULT '#2d3436',
            bg_color TEXT DEFAULT '#fff9e6',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 인덱스 생성
    print("인덱스 생성 중...")
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_header_banners_active_order 
        ON header_banners(is_active, display_order)
    ''')
    
    conn.commit()
    print("✅ header_banners 테이블 생성 완료!")
    
    # 테이블 구조 확인
    cursor.execute("""
        SELECT column_name, data_type, column_default, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'header_banners'
        ORDER BY ordinal_position;
    """)
    columns = cursor.fetchall()
    print("\n테이블 구조:")
    for col in columns:
        print(f"  - {col[0]} ({col[1]}) - 기본값: {col[2]}, NULL 허용: {col[3]}")
        
except Exception as e:
    print(f"❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()
    conn.rollback()
finally:
    cursor.close()
    conn.close()

print("\n" + "=" * 50)

