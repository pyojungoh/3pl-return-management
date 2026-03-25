"""
거래명세서 모듈 - 데이터베이스 테이블 초기화
기존 api/database/models.py 수정 없이 별도 모듈로 테이블 생성
"""
from api.database.models import get_db_connection, USE_POSTGRESQL

_invoice_tables_initialized = False


def _ensure_invoice_statements_vat_included(cursor):
    """기존 DB에 vat_included 컬럼 추가 (부가세 단가 포함 여부)"""
    try:
        if USE_POSTGRESQL:
            cursor.execute('''
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'invoice_statements'
                  AND column_name = 'vat_included'
            ''')
            if not cursor.fetchone():
                cursor.execute(
                    'ALTER TABLE invoice_statements ADD COLUMN vat_included BOOLEAN DEFAULT FALSE'
                )
        else:
            cursor.execute('PRAGMA table_info(invoice_statements)')
            cols = [r[1] for r in cursor.fetchall()]
            if cols and 'vat_included' not in cols:
                cursor.execute(
                    'ALTER TABLE invoice_statements ADD COLUMN vat_included INTEGER DEFAULT 0'
                )
    except Exception as e:
        print(f'[경고] invoice_statements.vat_included 마이그레이션: {e}')


def init_invoice_tables():
    """거래명세서 관련 테이블 생성 (PostgreSQL/SQLite 호환)"""
    global _invoice_tables_initialized
    if _invoice_tables_initialized:
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if USE_POSTGRESQL:
            _create_invoice_tables_postgresql(cursor)
        else:
            _create_invoice_tables_sqlite(cursor)
        _ensure_invoice_statements_vat_included(cursor)
        conn.commit()
        _invoice_tables_initialized = True
        print("[성공] 거래명세서 테이블 초기화 완료")
    except Exception as e:
        conn.rollback()
        print(f"[오류] 거래명세서 테이블 초기화 실패: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        cursor.close()
        conn.close()


def _create_invoice_tables_postgresql(cursor):
    """PostgreSQL용 거래명세서 테이블 생성"""
    # 1. 상품 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoice_products (
            id SERIAL PRIMARY KEY,
            product_code TEXT NOT NULL UNIQUE,
            product_name TEXT NOT NULL,
            qty_per_carton INTEGER NOT NULL DEFAULT 1,
            purchase_price INTEGER NOT NULL DEFAULT 0,
            wholesale_price INTEGER NOT NULL DEFAULT 0,
            group_buy_price INTEGER NOT NULL DEFAULT 0,
            retail_price INTEGER NOT NULL DEFAULT 0,
            expiry_days INTEGER,
            memo TEXT,
            image_url TEXT,
            category TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. 거래처 테이블 (화주사 연결 또는 독립)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoice_customers (
            id SERIAL PRIMARY KEY,
            customer_name TEXT NOT NULL,
            contact_tel TEXT,
            address TEXT,
            business_number TEXT,
            representative TEXT,
            company_id INTEGER REFERENCES companies(id),
            memo TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 3. 거래명세서 마스터
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoice_statements (
            id SERIAL PRIMARY KEY,
            statement_no TEXT NOT NULL UNIQUE,
            statement_date DATE NOT NULL,
            customer_id INTEGER NOT NULL REFERENCES invoice_customers(id),
            total_amount INTEGER NOT NULL DEFAULT 0,
            vat_amount INTEGER DEFAULT 0,
            grand_total INTEGER NOT NULL DEFAULT 0,
            memo TEXT,
            vat_included BOOLEAN DEFAULT FALSE,
            is_paid BOOLEAN DEFAULT FALSE,
            paid_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 4. 거래명세서 상세 (품목)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoice_statement_items (
            id SERIAL PRIMARY KEY,
            statement_id INTEGER NOT NULL REFERENCES invoice_statements(id) ON DELETE CASCADE,
            product_id INTEGER NOT NULL REFERENCES invoice_products(id),
            product_name TEXT NOT NULL,
            qty INTEGER NOT NULL,
            unit_price INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 인덱스
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_invoice_products_code ON invoice_products(product_code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_invoice_products_active ON invoice_products(is_active)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_invoice_customers_company ON invoice_customers(company_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_invoice_statements_date ON invoice_statements(statement_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_invoice_statements_customer ON invoice_statements(customer_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_invoice_statements_paid ON invoice_statements(is_paid)')


def _create_invoice_tables_sqlite(cursor):
    """SQLite용 거래명세서 테이블 생성"""
    # 1. 상품 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoice_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_code TEXT NOT NULL UNIQUE,
            product_name TEXT NOT NULL,
            qty_per_carton INTEGER NOT NULL DEFAULT 1,
            purchase_price INTEGER NOT NULL DEFAULT 0,
            wholesale_price INTEGER NOT NULL DEFAULT 0,
            group_buy_price INTEGER NOT NULL DEFAULT 0,
            retail_price INTEGER NOT NULL DEFAULT 0,
            expiry_days INTEGER,
            memo TEXT,
            image_url TEXT,
            category TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. 거래처 테이블 (화주사 연결 또는 독립)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoice_customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            contact_tel TEXT,
            address TEXT,
            business_number TEXT,
            representative TEXT,
            company_id INTEGER REFERENCES companies(id),
            memo TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 3. 거래명세서 마스터
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoice_statements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            statement_no TEXT NOT NULL UNIQUE,
            statement_date DATE NOT NULL,
            customer_id INTEGER NOT NULL REFERENCES invoice_customers(id),
            total_amount INTEGER NOT NULL DEFAULT 0,
            vat_amount INTEGER DEFAULT 0,
            grand_total INTEGER NOT NULL DEFAULT 0,
            memo TEXT,
            vat_included INTEGER DEFAULT 0,
            is_paid INTEGER DEFAULT 0,
            paid_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 4. 거래명세서 상세 (품목)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoice_statement_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            statement_id INTEGER NOT NULL REFERENCES invoice_statements(id) ON DELETE CASCADE,
            product_id INTEGER NOT NULL REFERENCES invoice_products(id),
            product_name TEXT NOT NULL,
            qty INTEGER NOT NULL,
            unit_price INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 인덱스
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_invoice_products_code ON invoice_products(product_code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_invoice_products_active ON invoice_products(is_active)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_invoice_customers_company ON invoice_customers(company_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_invoice_statements_date ON invoice_statements(statement_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_invoice_statements_customer ON invoice_statements(customer_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_invoice_statements_paid ON invoice_statements(is_paid)')
