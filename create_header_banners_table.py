"""
헤더 배너 테이블 생성 스크립트
서버 재시작 없이 테이블을 생성합니다.
"""
import os
import sqlite3

# 데이터베이스 파일 경로
current_dir = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(current_dir, 'data.db')

print(f"데이터베이스 경로: {DB_PATH}")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    # 테이블이 이미 존재하는지 확인
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='header_banners'")
    if cursor.fetchone():
        print("⚠️ header_banners 테이블이 이미 존재합니다.")
        response = input("테이블을 삭제하고 다시 생성하시겠습니까? (y/N): ")
        if response.lower() == 'y':
            cursor.execute("DROP TABLE header_banners")
            print("✅ 기존 테이블 삭제 완료")
        else:
            print("취소되었습니다.")
            conn.close()
            exit(0)
    
    # 테이블 생성
    cursor.execute('''
        CREATE TABLE header_banners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            link_type TEXT DEFAULT 'none',
            board_post_id INTEGER,
            is_active INTEGER DEFAULT 1,
            display_order INTEGER DEFAULT 0,
            text_color TEXT DEFAULT '#2d3436',
            bg_color TEXT DEFAULT '#fff9e6',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 인덱스 생성
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_header_banners_active_order 
        ON header_banners(is_active, display_order)
    ''')
    
    conn.commit()
    print("✅ header_banners 테이블 생성 완료!")
    
    # 테이블 구조 확인
    cursor.execute("PRAGMA table_info(header_banners)")
    columns = cursor.fetchall()
    print("\n테이블 구조:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
        
except Exception as e:
    print(f"❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()
    conn.rollback()
finally:
    conn.close()

