import psycopg2
import os

# 환경 변수에서 DATABASE_URL을 가져오거나, 기본값 설정
CONN_STR = os.environ.get('DATABASE_URL', "postgresql://neondb_owner:npg_CNqVFs9j2Bpi@ep-dark-queen-a4w25otz-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require")

def main():
    print("Attempting to connect to PostgreSQL...")
    conn = None
    try:
        conn = psycopg2.connect(CONN_STR)
        cur = conn.cursor()
        print("Successfully connected to PostgreSQL.")

        # 기존 테이블이 있으면 삭제하고 새로 생성 (구조 변경)
        cur.execute("DROP TABLE IF EXISTS schedule_memos")
        print("기존 schedule_memos 테이블 삭제 완료")

        # 새로운 구조로 테이블 생성
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
        print("schedule_memos 테이블 생성 완료 (새 구조: title, company_name, content)")

    except psycopg2.Error as e:
        print(f"Error connecting to or creating table in PostgreSQL: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        if conn:
            conn.rollback()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
            print("PostgreSQL connection closed.")

if __name__ == "__main__":
    main()

