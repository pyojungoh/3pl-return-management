import psycopg2


def main():
    conn = psycopg2.connect(
        "postgresql://neondb_owner:npg_CNqVFs9j2Bpi@ep-dark-queen-a4w25otz-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"
    )
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS special_work_batches (
            id SERIAL PRIMARY KEY,
            company_name TEXT NOT NULL,
            work_date DATE NOT NULL,
            total_amount INTEGER NOT NULL DEFAULT 0,
            entry_count INTEGER NOT NULL DEFAULT 0,
            photo_links TEXT,
            memo TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS special_work_batch_items (
            id SERIAL PRIMARY KEY,
            batch_id INTEGER NOT NULL REFERENCES special_work_batches(id) ON DELETE CASCADE,
            work_id INTEGER NOT NULL REFERENCES special_works(id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    cur.close()
    conn.close()
    print("Tables ensured.")


if __name__ == "__main__":
    main()