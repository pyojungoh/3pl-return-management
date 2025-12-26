import psycopg2

CONN_STR = "postgresql://neondb_owner:npg_CNqVFs9j2Bpi@ep-dark-queen-a4w25otz-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"

def main():
    conn = psycopg2.connect(CONN_STR)
    cur = conn.cursor()

    # 기존 테이블 삭제 (데이터 손실 주의)
    cur.execute("DROP TABLE IF EXISTS schedule_memos")
    
    # 새 테이블 생성 (제목, 화주사, 내용 필드 추가)
    cur.execute("""
    CREATE TABLE schedule_memos (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        company_name TEXT,
        content TEXT NOT NULL,
        updated_by TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("schedule_memos 테이블 구조 변경 완료 (제목, 화주사, 내용 필드 추가)")

if __name__ == "__main__":
    main()













