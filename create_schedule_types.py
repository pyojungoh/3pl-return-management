import psycopg2

CONN_STR = "postgresql://neondb_owner:npg_CNqVFs9j2Bpi@ep-dark-queen-a4w25otz-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"

def main():
    conn = psycopg2.connect(CONN_STR)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS schedule_types (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        display_order INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    INSERT INTO schedule_types (name, display_order)
    VALUES
        ('입고', 0),
        ('출고', 1),
        ('행사', 2),
        ('연휴', 3),
        ('기타', 4)
    ON CONFLICT (name) DO NOTHING
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("schedule_types 테이블 생성 및 기본 데이터 입력 완료")

if __name__ == "__main__":
    main()