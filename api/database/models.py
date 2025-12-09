"""
PostgreSQL 데이터베이스 모델 (Neon Postgres)
DATABASE_URL 환경 변수가 있으면 PostgreSQL 사용, 없으면 SQLite 사용 (호환성)
"""
import os
from datetime import datetime
from typing import Optional, List, Dict, Tuple

# 데이터베이스 연결 문자열
DATABASE_URL = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')

# PostgreSQL 사용 여부 확인
USE_POSTGRESQL = bool(DATABASE_URL)

if USE_POSTGRESQL:
    # PostgreSQL 사용
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from psycopg2 import IntegrityError, OperationalError
    print("PostgreSQL 데이터베이스 사용 (Neon)")
else:
    # SQLite 사용 (로컬 개발용)
    import sqlite3
    from sqlite3 import OperationalError, IntegrityError
    # 데이터베이스 파일 경로
    if os.environ.get('VERCEL'):
        DB_PATH = os.path.join('/tmp', 'data.db')
    else:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        DB_PATH = os.path.join(project_root, 'data.db')
    print("SQLite 데이터베이스 사용 (로컬)")


def get_db_connection():
    """데이터베이스 연결 가져오기"""
    if USE_POSTGRESQL:
        # PostgreSQL 연결 (Neon의 경우 SSL 필요)
        try:
            # DATABASE_URL에 이미 SSL 정보가 포함되어 있을 수 있음
            # Neon은 기본적으로 SSL을 요구하므로, URL에 sslmode가 없으면 추가
            if 'sslmode' not in DATABASE_URL and 'sslmode=' not in DATABASE_URL:
                # URL에 쿼리 파라미터가 있는지 확인
                if '?' in DATABASE_URL:
                    conn = psycopg2.connect(DATABASE_URL + '&sslmode=require', connect_timeout=10)
                else:
                    conn = psycopg2.connect(DATABASE_URL + '?sslmode=require', connect_timeout=10)
            else:
                conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
            
            # PostgreSQL은 기본적으로 autocommit=True이므로 명시적으로 설정하지 않음
            # 트랜잭션은 각 함수에서 명시적으로 commit/rollback 처리
            return conn
        except Exception as e:
            print(f"[오류] PostgreSQL 연결 오류: {e}")
            import traceback
            traceback.print_exc()
            raise
    else:
        # SQLite 연결
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        # SQLite에서 FOREIGN KEY 활성화 (연결마다 필요)
        conn.execute('PRAGMA foreign_keys = ON')
        return conn


def init_db():
    """데이터베이스 초기화 (테이블 생성)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRESQL:
            # PostgreSQL 테이블 생성
            # 화주사 계정 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS companies (
                    id SERIAL PRIMARY KEY,
                    company_name TEXT NOT NULL,
                    username TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT '화주사',
                    business_number TEXT,
                    business_name TEXT,
                    business_address TEXT,
                    business_tel TEXT,
                    business_email TEXT,
                    business_certificate_url TEXT,
                    search_keywords TEXT,
                    last_login TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # companies 테이블에 search_keywords 필드 추가 (마이그레이션)
            try:
                cursor.execute('ALTER TABLE companies ADD COLUMN IF NOT EXISTS search_keywords TEXT')
            except Exception:
                pass
            
            # 반품 내역 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS returns (
                    id SERIAL PRIMARY KEY,
                    return_date TEXT,
                    company_name TEXT NOT NULL,
                    product TEXT,
                    customer_name TEXT NOT NULL,
                    tracking_number TEXT NOT NULL,
                    return_type TEXT,
                    stock_status TEXT,
                    inspection TEXT,
                    completed TEXT,
                    memo TEXT,
                    photo_links TEXT,
                    other_courier TEXT,
                    shipping_fee TEXT,
                    client_request TEXT,
                    client_confirmed TEXT,
                    month TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(customer_name, tracking_number, month)
                )
            ''')
            
            # 인덱스 생성
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_returns_company 
                ON returns(company_name, month)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_returns_tracking 
                ON returns(tracking_number)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_returns_date 
                ON returns(return_date)
            ''')
            
            # 판매 스케쥴 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS schedules (
                    id SERIAL PRIMARY KEY,
                    company_name TEXT NOT NULL,
                    title TEXT NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    event_description TEXT,
                    request_note TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 스케쥴 인덱스 생성
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_schedules_company 
                ON schedules(company_name)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_schedules_dates 
                ON schedules(start_date, end_date)
            ''')
            
            # schedule_type 컬럼 추가 (없는 경우에만)
            try:
                cursor.execute('ALTER TABLE schedules ADD COLUMN schedule_type TEXT')
                print("[성공] schedules 테이블에 schedule_type 컬럼이 추가되었습니다.")
            except Exception as e:
                # 컬럼이 이미 존재하는 경우 무시
                if 'duplicate column' not in str(e).lower() and 'already exists' not in str(e).lower():
                    print(f"[경고] schedule_type 컬럼 추가 중 오류 (무시 가능): {e}")
            
            # 알림 플래그 컬럼 추가 (없는 경우에만)
            notification_columns = [
                'notification_sent_registered',
                'notification_sent_before_start',
                'notification_sent_start',
                'notification_sent_end'
            ]
            for col in notification_columns:
                try:
                    cursor.execute(f'ALTER TABLE schedules ADD COLUMN IF NOT EXISTS {col} BOOLEAN DEFAULT FALSE')
                    print(f"[성공] schedules 테이블에 {col} 컬럼이 추가되었습니다.")
                except Exception as e:
                    error_msg = str(e).lower()
                    if 'duplicate column' not in error_msg and 'already exists' not in error_msg:
                        print(f"[경고] {col} 컬럼 추가 중 오류 (무시 가능): {e}")
                        # 트랜잭션 오류인 경우 rollback 후 계속 진행
                        if 'aborted' in error_msg or 'transaction' in error_msg:
                            try:
                                conn.rollback()
                                print(f"[복구] 트랜잭션 rollback 후 계속 진행")
                            except:
                                pass
            
            # PostgreSQL - 스케줄 타입 테이블
            try:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS schedule_types (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE,
                        display_order INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
            except Exception as e:
                error_msg = str(e).lower()
                if 'aborted' in error_msg or 'transaction' in error_msg:
                    try:
                        conn.rollback()
                        print(f"[복구] 트랜잭션 rollback 후 schedule_types 테이블 생성 재시도")
                        cursor.execute('''
                            CREATE TABLE IF NOT EXISTS schedule_types (
                                id SERIAL PRIMARY KEY,
                                name TEXT NOT NULL UNIQUE,
                                display_order INTEGER DEFAULT 0,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            )
                        ''')
                    except Exception as e2:
                        print(f"[경고] schedule_types 테이블 생성 중 오류: {e2}")
                else:
                    print(f"[경고] schedule_types 테이블 생성 중 오류: {e}")
            
            # 기본 스케줄 타입 추가 (없는 경우에만)
            default_types = ['입고', '출고', '행사', '연휴', '기타']
            for idx, type_name in enumerate(default_types):
                try:
                    cursor.execute('''
                        INSERT INTO schedule_types (name, display_order)
                        VALUES (%s, %s)
                        ON CONFLICT (name) DO NOTHING
                    ''', (type_name, idx))
                except Exception as e:
                    print(f"[경고] 기본 스케줄 타입 추가 중 오류 (무시 가능): {e}")
            
            # PostgreSQL - 스케줄 메모 테이블 (관리자 전용)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS schedule_memos (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    company_name TEXT,
                    content TEXT NOT NULL,
                    updated_by TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 기존 테이블 마이그레이션 (memo_content → title, company_name, content)
            try:
                # title 컬럼이 없으면 추가
                cursor.execute('ALTER TABLE schedule_memos ADD COLUMN IF NOT EXISTS title TEXT')
                cursor.execute('ALTER TABLE schedule_memos ADD COLUMN IF NOT EXISTS company_name TEXT')
                cursor.execute('ALTER TABLE schedule_memos ADD COLUMN IF NOT EXISTS content TEXT')
                
                # memo_content가 있고 content가 비어있으면 마이그레이션
                try:
                    cursor.execute('''
                        UPDATE schedule_memos 
                        SET content = COALESCE(memo_content, ''), 
                            title = COALESCE(memo_content, '')
                        WHERE (content IS NULL OR content = '') 
                        AND memo_content IS NOT NULL
                    ''')
                except Exception:
                    # memo_content 컬럼이 없으면 무시
                    pass
            except Exception as e:
                # 컬럼이 이미 존재하거나 다른 오류인 경우 무시
                if 'duplicate column' not in str(e).lower() and 'does not exist' not in str(e).lower():
                    print(f"[경고] schedule_memos 테이블 마이그레이션 중 오류 (무시 가능): {e}")
            
            conn.commit()
            
            # PostgreSQL - 게시판 카테고리 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS board_categories (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    display_order INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # PostgreSQL - 게시판 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS boards (
                    id SERIAL PRIMARY KEY,
                    category_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    author_name TEXT NOT NULL,
                    author_role TEXT NOT NULL,
                    is_pinned BOOLEAN DEFAULT FALSE,
                    view_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES board_categories(id) ON DELETE CASCADE
                )
            ''')
            
            # PostgreSQL - 게시판 첨부파일 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS board_files (
                    id SERIAL PRIMARY KEY,
                    board_id INTEGER NOT NULL,
                    file_name TEXT NOT NULL,
                    file_url TEXT NOT NULL,
                    file_size INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE
                )
            ''')
            
            # 게시판 인덱스 생성
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_boards_category 
                ON boards(category_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_boards_pinned 
                ON boards(is_pinned, created_at DESC)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_board_files_board 
                ON board_files(board_id)
            ''')
            
            # PostgreSQL - 팝업 관리 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS popups (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    image_url TEXT,
                    width INTEGER DEFAULT 600,
                    height INTEGER DEFAULT 400,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 기존 테이블에 컬럼 추가 (마이그레이션)
            try:
                cursor.execute('ALTER TABLE popups ADD COLUMN IF NOT EXISTS image_url TEXT')
            except Exception:
                pass
            try:
                cursor.execute('ALTER TABLE popups ADD COLUMN IF NOT EXISTS width INTEGER DEFAULT 600')
            except Exception:
                pass
            try:
                cursor.execute('ALTER TABLE popups ADD COLUMN IF NOT EXISTS height INTEGER DEFAULT 400')
            except Exception:
                pass
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_popups_dates 
                ON popups(start_date, end_date, is_active)
            ''')
            
            # PostgreSQL - 헤더 배너 테이블
            try:
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
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_header_banners_active_order 
                    ON header_banners(is_active, display_order)
                ''')
                print("[성공] header_banners 테이블 생성 완료")
            except Exception as e:
                error_msg = str(e).lower()
                if 'aborted' in error_msg or 'transaction' in error_msg:
                    try:
                        conn.rollback()
                        print(f"[복구] 트랜잭션 rollback 후 header_banners 테이블 생성 재시도")
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
                        cursor.execute('''
                            CREATE INDEX IF NOT EXISTS idx_header_banners_active_order 
                            ON header_banners(is_active, display_order)
                        ''')
                        print("[성공] header_banners 테이블 생성 완료 (재시도)")
                    except Exception as e2:
                        print(f"[경고] header_banners 테이블 생성 중 오류: {e2}")
                else:
                    print(f"[경고] header_banners 테이블 생성 중 오류 (무시 가능): {e}")
            
            # PostgreSQL - C/S 접수 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS customer_service (
                    id SERIAL PRIMARY KEY,
                    company_name TEXT NOT NULL,
                    username TEXT NOT NULL,
                    date DATE NOT NULL,
                    month TEXT NOT NULL,
                    issue_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    management_number TEXT,
                    generated_management_number TEXT,
                    customer_name TEXT,
                    status TEXT DEFAULT '접수',
                    admin_message TEXT,
                    processor TEXT,
                    processed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # C/S 테이블에 새 필드 추가 (마이그레이션)
            try:
                cursor.execute('ALTER TABLE customer_service ADD COLUMN IF NOT EXISTS date DATE')
            except Exception:
                pass
            try:
                cursor.execute('ALTER TABLE customer_service ADD COLUMN IF NOT EXISTS month TEXT')
            except Exception:
                pass
            try:
                cursor.execute('ALTER TABLE customer_service ADD COLUMN IF NOT EXISTS management_number TEXT')
            except Exception:
                pass
            try:
                cursor.execute('ALTER TABLE customer_service ADD COLUMN IF NOT EXISTS customer_name TEXT')
            except Exception:
                pass
                pass
            try:
                cursor.execute('ALTER TABLE customer_service ADD COLUMN IF NOT EXISTS generated_management_number TEXT')
            except Exception:
                pass
            try:
                cursor.execute('ALTER TABLE customer_service ADD COLUMN IF NOT EXISTS admin_message TEXT')
            except Exception:
                pass
            try:
                cursor.execute('ALTER TABLE customer_service ADD COLUMN IF NOT EXISTS processor TEXT')
            except Exception:
                pass
            try:
                cursor.execute('ALTER TABLE customer_service ADD COLUMN IF NOT EXISTS processed_at TIMESTAMP')
            except Exception:
                pass
            # admin_response를 admin_message로 변경 (기존 데이터 호환)
            try:
                cursor.execute('ALTER TABLE customer_service ADD COLUMN IF NOT EXISTS admin_response TEXT')
                # admin_response가 있고 admin_message가 없으면 복사
                cursor.execute('''
                    UPDATE customer_service 
                    SET admin_message = admin_response 
                    WHERE admin_message IS NULL AND admin_response IS NOT NULL
                ''')
            except Exception:
                pass
            
            # C/S 인덱스 생성
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_cs_company 
                ON customer_service(company_name, created_at)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_cs_status 
                ON customer_service(status, created_at)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_cs_month 
                ON customer_service(month, created_at)
            ''')

            # PostgreSQL - 특수작업 작업 종류 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS special_work_types (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    default_unit_price INTEGER DEFAULT 0,
                    display_order INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # PostgreSQL - 특수작업 작업 목록 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS special_works (
                    id SERIAL PRIMARY KEY,
                    company_name TEXT NOT NULL,
                    work_type_id INTEGER NOT NULL,
                    work_date DATE NOT NULL,
                    quantity REAL NOT NULL,
                    unit_price INTEGER NOT NULL,
                    total_price INTEGER NOT NULL,
                    photo_links TEXT,
                    memo TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (work_type_id) REFERENCES special_work_types(id) ON DELETE CASCADE
                )
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_special_works_company 
                ON special_works(company_name, work_date)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_special_works_type 
                ON special_works(work_type_id)
            ''')
            
        else:
            # SQLite 테이블 생성 (기존 코드)
            # 화주사 계정 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_name TEXT NOT NULL,
                    username TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT '화주사',
                    business_number TEXT,
                    business_name TEXT,
                    business_address TEXT,
                    business_tel TEXT,
                    business_email TEXT,
                    search_keywords TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 기존 테이블에 사업자 정보 컬럼 추가 (마이그레이션)
            try:
                cursor.execute('ALTER TABLE companies ADD COLUMN business_number TEXT')
            except OperationalError:
                pass
            
            try:
                cursor.execute('ALTER TABLE companies ADD COLUMN business_name TEXT')
            except OperationalError:
                pass
            
            try:
                cursor.execute('ALTER TABLE companies ADD COLUMN business_address TEXT')
            except OperationalError:
                pass
            
            try:
                cursor.execute('ALTER TABLE companies ADD COLUMN business_tel TEXT')
            except OperationalError:
                pass
            
            try:
                cursor.execute('ALTER TABLE companies ADD COLUMN business_email TEXT')
            except OperationalError:
                pass
            
            try:
                cursor.execute('ALTER TABLE companies ADD COLUMN business_certificate_url TEXT')
            except OperationalError:
                pass
            
            # companies 테이블에 search_keywords 필드 추가 (화주사명 별칭 저장용)
            try:
                cursor.execute('ALTER TABLE companies ADD COLUMN search_keywords TEXT')
            except OperationalError:
                pass
            
            try:
                cursor.execute('ALTER TABLE companies ADD COLUMN last_login TIMESTAMP')
            except OperationalError:
                pass
            
            # 반품 내역 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS returns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    return_date TEXT,
                    company_name TEXT NOT NULL,
                    product TEXT,
                    customer_name TEXT NOT NULL,
                    tracking_number TEXT NOT NULL,
                    return_type TEXT,
                    stock_status TEXT,
                    inspection TEXT,
                    completed TEXT,
                    memo TEXT,
                    photo_links TEXT,
                    other_courier TEXT,
                    shipping_fee TEXT,
                    client_request TEXT,
                    client_confirmed TEXT,
                    month TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(customer_name, tracking_number, month)
                )
            ''')
            
            # 인덱스 생성
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_returns_company 
                ON returns(company_name, month)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_returns_tracking 
                ON returns(tracking_number)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_returns_date 
                ON returns(return_date)
            ''')
            
            # SQLite - 스케쥴 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_name TEXT NOT NULL,
                    title TEXT NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    event_description TEXT,
                    request_note TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 스케쥴 인덱스 생성
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_schedules_company 
                ON schedules(company_name)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_schedules_dates 
                ON schedules(start_date, end_date)
            ''')
            
            # schedule_type 컬럼 추가 (없는 경우에만)
            try:
                cursor.execute('ALTER TABLE schedules ADD COLUMN schedule_type TEXT')
                print("[성공] schedules 테이블에 schedule_type 컬럼이 추가되었습니다.")
            except Exception as e:
                # 컬럼이 이미 존재하는 경우 무시
                if 'duplicate column' not in str(e).lower() and 'already exists' not in str(e).lower():
                    print(f"[경고] schedule_type 컬럼 추가 중 오류 (무시 가능): {e}")
            
            # 알림 플래그 컬럼 추가 (없는 경우에만)
            notification_columns = [
                'notification_sent_registered',
                'notification_sent_before_start',
                'notification_sent_start',
                'notification_sent_end'
            ]
            for col in notification_columns:
                try:
                    cursor.execute(f'ALTER TABLE schedules ADD COLUMN {col} INTEGER DEFAULT 0')
                    print(f"[성공] schedules 테이블에 {col} 컬럼이 추가되었습니다.")
                except Exception as e:
                    if 'duplicate column' not in str(e).lower() and 'already exists' not in str(e).lower():
                        print(f"[경고] {col} 컬럼 추가 중 오류 (무시 가능): {e}")
            
            # SQLite - 스케줄 타입 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS schedule_types (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    display_order INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 기본 스케줄 타입 추가 (없는 경우에만)
            default_types = ['입고', '출고', '행사', '연휴', '기타']
            for idx, type_name in enumerate(default_types):
                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO schedule_types (name, display_order)
                        VALUES (?, ?)
                    ''', (type_name, idx))
                except Exception as e:
                    print(f"[경고] 기본 스케줄 타입 추가 중 오류 (무시 가능): {e}")
            
            # SQLite - 스케줄 메모 테이블 (관리자 전용)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS schedule_memos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    company_name TEXT,
                    content TEXT NOT NULL,
                    updated_by TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 기존 테이블 마이그레이션 (memo_content → title, company_name, content)
            try:
                # 기존 컬럼 확인
                cursor.execute("PRAGMA table_info(schedule_memos)")
                columns = [col[1] for col in cursor.fetchall()]
                
                # memo_content 컬럼이 있고 title이 없으면 마이그레이션
                if 'memo_content' in columns and 'title' not in columns:
                    print("[마이그레이션] schedule_memos 테이블 구조 업데이트 중...")
                    # 임시 테이블 생성
                    cursor.execute('''
                        CREATE TABLE schedule_memos_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            title TEXT NOT NULL,
                            company_name TEXT,
                            content TEXT NOT NULL,
                            updated_by TEXT,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                    # 기존 데이터 마이그레이션 (memo_content를 content로 복사, title은 빈 문자열)
                    cursor.execute('''
                        INSERT INTO schedule_memos_new (id, title, company_name, content, updated_by, updated_at, created_at)
                        SELECT id, COALESCE(memo_content, '') as title, NULL as company_name, COALESCE(memo_content, '') as content, updated_by, updated_at, created_at
                        FROM schedule_memos
                    ''')
                    # 기존 테이블 삭제
                    cursor.execute('DROP TABLE schedule_memos')
                    # 새 테이블 이름 변경
                    cursor.execute('ALTER TABLE schedule_memos_new RENAME TO schedule_memos')
                    print("[마이그레이션] schedule_memos 테이블 구조 업데이트 완료")
                # title 컬럼이 없으면 추가
                elif 'title' not in columns:
                    cursor.execute('ALTER TABLE schedule_memos ADD COLUMN title TEXT NOT NULL DEFAULT ""')
                    cursor.execute('ALTER TABLE schedule_memos ADD COLUMN company_name TEXT')
                    cursor.execute('ALTER TABLE schedule_memos ADD COLUMN content TEXT NOT NULL DEFAULT ""')
                    # 기존 memo_content를 content와 title로 복사
                    if 'memo_content' in columns:
                        cursor.execute('UPDATE schedule_memos SET content = COALESCE(memo_content, ""), title = COALESCE(memo_content, "") WHERE content = "" OR title = ""')
            except Exception as e:
                print(f"[경고] schedule_memos 테이블 마이그레이션 중 오류 (무시 가능): {e}")
            
            conn.commit()
            
            # SQLite - 게시판 카테고리 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS board_categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    display_order INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # SQLite - 게시판 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS boards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    author_name TEXT NOT NULL,
                    author_role TEXT NOT NULL,
                    is_pinned INTEGER DEFAULT 0,
                    view_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES board_categories(id) ON DELETE CASCADE
                )
            ''')
            
            # SQLite - 게시판 첨부파일 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS board_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    board_id INTEGER NOT NULL,
                    file_name TEXT NOT NULL,
                    file_url TEXT NOT NULL,
                    file_size INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE
                )
            ''')
            
            # 게시판 인덱스 생성
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_boards_category 
                ON boards(category_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_boards_pinned 
                ON boards(is_pinned, created_at DESC)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_board_files_board 
                ON board_files(board_id)
            ''')
            
            # SQLite - 팝업 관리 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS popups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    image_url TEXT,
                    width INTEGER DEFAULT 600,
                    height INTEGER DEFAULT 400,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 기존 테이블에 컬럼 추가 (마이그레이션)
            try:
                cursor.execute('ALTER TABLE popups ADD COLUMN image_url TEXT')
            except OperationalError:
                pass
            try:
                cursor.execute('ALTER TABLE popups ADD COLUMN width INTEGER DEFAULT 600')
            except OperationalError:
                pass
            try:
                cursor.execute('ALTER TABLE popups ADD COLUMN height INTEGER DEFAULT 400')
            except OperationalError:
                pass
            
            # companies 테이블에 search_keywords 필드 추가 (화주사명 별칭 저장용)
            try:
                cursor.execute('ALTER TABLE companies ADD COLUMN search_keywords TEXT')
            except OperationalError:
                pass
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_popups_dates 
                ON popups(start_date, end_date, is_active)
            ''')
            
            # SQLite - 헤더 배너 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS header_banners (
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
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_header_banners_active_order 
                ON header_banners(is_active, display_order)
            ''')
            
            # SQLite - C/S 접수 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS customer_service (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_name TEXT NOT NULL,
                    username TEXT NOT NULL,
                    date DATE NOT NULL,
                    month TEXT NOT NULL,
                    issue_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    management_number TEXT,
                    generated_management_number TEXT,
                    customer_name TEXT,
                    status TEXT DEFAULT '접수',
                    admin_message TEXT,
                    processor TEXT,
                    processed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # C/S 테이블에 새 필드 추가 (마이그레이션)
            try:
                cursor.execute('ALTER TABLE customer_service ADD COLUMN date DATE')
            except OperationalError:
                pass
            try:
                cursor.execute('ALTER TABLE customer_service ADD COLUMN month TEXT')
            except OperationalError:
                pass
            try:
                cursor.execute('ALTER TABLE customer_service ADD COLUMN management_number TEXT')
            except OperationalError:
                pass
            try:
                cursor.execute('ALTER TABLE customer_service ADD COLUMN customer_name TEXT')
            except OperationalError:
                pass
                pass
            try:
                cursor.execute('ALTER TABLE customer_service ADD COLUMN generated_management_number TEXT')
            except OperationalError:
                pass
            try:
                cursor.execute('ALTER TABLE customer_service ADD COLUMN admin_message TEXT')
            except OperationalError:
                pass
            try:
                cursor.execute('ALTER TABLE customer_service ADD COLUMN processor TEXT')
            except OperationalError:
                pass
            try:
                cursor.execute('ALTER TABLE customer_service ADD COLUMN processed_at TIMESTAMP')
            except OperationalError:
                pass
            # admin_response를 admin_message로 변경 (기존 데이터 호환)
            try:
                cursor.execute('ALTER TABLE customer_service ADD COLUMN admin_response TEXT')
                # admin_response가 있고 admin_message가 없으면 복사
                cursor.execute('''
                    UPDATE customer_service 
                    SET admin_message = admin_response 
                    WHERE admin_message IS NULL AND admin_response IS NOT NULL
                ''')
            except OperationalError:
                pass
            
            # C/S 인덱스 생성
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_cs_company 
                ON customer_service(company_name, created_at)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_cs_status 
                ON customer_service(status, created_at)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_cs_month 
                ON customer_service(month, created_at)
            ''')

            # SQLite - 특수작업 작업 종류 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS special_work_types (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    default_unit_price INTEGER DEFAULT 0,
                    display_order INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # SQLite - 특수작업 작업 목록 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS special_works (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_name TEXT NOT NULL,
                    work_type_id INTEGER NOT NULL,
                    work_date DATE NOT NULL,
                    quantity REAL NOT NULL,
                    unit_price INTEGER NOT NULL,
                    total_price INTEGER NOT NULL,
                    photo_links TEXT,
                    memo TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (work_type_id) REFERENCES special_work_types(id) ON DELETE CASCADE
                )
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_special_works_company 
                ON special_works(company_name, work_date)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_special_works_type 
                ON special_works(work_type_id)
            ''')
        
        conn.commit()
        print("데이터베이스 초기화 완료")
    
    except Exception as e:
        print(f"데이터베이스 초기화 오류: {e}")
        import traceback
        traceback.print_exc()
        try:
            conn.rollback()
            print("[복구] 트랜잭션 rollback 완료")
            
            # rollback 후 header_banners 테이블이 없으면 생성 시도
            if USE_POSTGRESQL:
                try:
                    cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'header_banners')")
                    table_exists = cursor.fetchone()[0]
                    if not table_exists:
                        print("[복구] header_banners 테이블이 없어서 생성 시도")
                        cursor.execute('''
                            CREATE TABLE header_banners (
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
                        cursor.execute('''
                            CREATE INDEX IF NOT EXISTS idx_header_banners_active_order 
                            ON header_banners(is_active, display_order)
                        ''')
                        conn.commit()
                        print("[성공] header_banners 테이블 생성 완료 (복구)")
                except Exception as e2:
                    print(f"[경고] header_banners 테이블 복구 중 오류: {e2}")
                    import traceback
                    traceback.print_exc()
        except Exception as rollback_error:
            print(f"[경고] rollback 중 오류: {rollback_error}")
    finally:
        cursor.close()
        conn.close()


def get_company_by_username(username: str) -> Optional[Dict]:
    """화주사 계정 조회"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute('SELECT * FROM companies WHERE username = %s', (username,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM companies WHERE username = ?', (username,))
            row = cursor.fetchone()
            if row:
                # SQLite Row 객체를 dict로 변환 (row_factory가 Row로 설정되어 있음)
                try:
                    # Row 객체는 dict처럼 사용 가능하지만, 명시적으로 변환
                    if hasattr(row, 'keys'):
                        return dict(row)
                    else:
                        # 튜플인 경우 수동 변환
                        return {
                            'id': row[0],
                            'company_name': row[1],
                            'username': row[2],
                            'password': row[3],
                            'role': row[4] if len(row) > 4 else '화주사',
                            'business_number': row[5] if len(row) > 5 else None,
                            'business_name': row[6] if len(row) > 6 else None,
                            'business_address': row[7] if len(row) > 7 else None,
                            'business_tel': row[8] if len(row) > 8 else None,
                            'business_email': row[9] if len(row) > 9 else None,
                            'business_certificate_url': row[10] if len(row) > 10 else None,
                            'last_login': row[11] if len(row) > 11 else None,
                            'created_at': row[12] if len(row) > 12 else None,
                            'updated_at': row[13] if len(row) > 13 else None
                        }
                except Exception as e:
                    print(f"[오류] SQLite row 변환 오류: {e}")
                    print(f"   Row 타입: {type(row)}, Row 내용: {row}")
                    raise
            return None
        except Exception as e:
            print(f"[오류] get_company_by_username 오류: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            conn.close()


def get_all_companies() -> List[Dict]:
    """모든 화주사 계정 조회"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute('''
                SELECT id, company_name, username, role, 
                       business_number, business_name, business_address, 
                       business_tel, business_email, business_certificate_url,
                       search_keywords, last_login, created_at, updated_at
                FROM companies
                ORDER BY created_at DESC
            ''')
            rows = cursor.fetchall()
            result = []
            for row in rows:
                row_dict = dict(row)
                # datetime 객체를 문자열로 변환
                for key, value in row_dict.items():
                    if isinstance(value, datetime):
                        row_dict[key] = value.strftime('%Y-%m-%d %H:%M:%S') if value else None
                result.append(row_dict)
            return result
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            # SQLite에서 존재하는 컬럼 확인
            cursor.execute("PRAGMA table_info(companies)")
            columns_info = cursor.fetchall()
            available_columns = [col[1] for col in columns_info]  # col[1]은 컬럼명
            
            # 기본 컬럼 목록
            desired_columns = [
                'id', 'company_name', 'username', 'role',
                'business_number', 'business_name', 'business_address',
                'business_tel', 'business_email', 'business_certificate_url',
                'search_keywords', 'last_login', 'created_at', 'updated_at'
            ]
            
            # 존재하는 컬럼만 선택
            select_columns = [col for col in desired_columns if col in available_columns]
            
            if not select_columns:
                print('[경고] companies 테이블에 컬럼이 없습니다.')
                return []
            
            # 모든 컬럼 조회 (존재하지 않는 컬럼은 NULL로 처리)
            cursor.execute('SELECT * FROM companies ORDER BY created_at DESC')
            rows = cursor.fetchall()
            
            # Row 객체를 dict로 변환 (존재하지 않는 컬럼은 None으로 설정)
            # conn.row_factory가 sqlite3.Row로 설정되어 있으므로 row.keys() 사용 가능
            result = []
            for row in rows:
                row_dict = {}
                # 실제 존재하는 컬럼만 추가
                for key in row.keys():
                    row_dict[key] = row[key]
                # 존재하지 않는 컬럼은 None으로 설정
                for col in desired_columns:
                    if col not in row_dict:
                        row_dict[col] = None
                result.append(row_dict)
            
            return result
        except Exception as e:
            print(f"[오류] get_all_companies SQLite 오류: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            conn.close()


def create_company(company_name: str, username: str, password: str, role: str = '화주사',
                  business_number: str = None, business_name: str = None,
                  business_address: str = None, business_tel: str = None,
                  business_email: str = None, business_certificate_url: str = None):
    """화주사 계정 생성"""
    conn = get_db_connection()
    
    print(f"[정보] create_company 호출 - company_name: '{company_name}', username: '{username}', role: '{role}'")
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO companies (company_name, username, password, role,
                                     business_number, business_name, business_address,
                                     business_tel, business_email, business_certificate_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (company_name, username, password, role,
                  business_number, business_name, business_address,
                  business_tel, business_email, business_certificate_url))
            conn.commit()
            print(f"[성공] 화주사 계정 생성 성공: {company_name} ({username})")
            return True
        except IntegrityError as e:
            conn.rollback()
            print(f"[오류] 화주사 계정 생성 실패 (중복): {username} - {e}")
            return False
        except Exception as e:
            conn.rollback()
            print(f"[오류] 화주사 계정 생성 실패 (오류): {username} - {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO companies (company_name, username, password, role,
                                     business_number, business_name, business_address,
                                     business_tel, business_email, business_certificate_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (company_name, username, password, role,
                  business_number, business_name, business_address,
                  business_tel, business_email, business_certificate_url))
            conn.commit()
            print(f"[성공] 화주사 계정 생성 성공: {company_name} ({username})")
            return True
        except sqlite3.IntegrityError as e:
            print(f"[오류] 화주사 계정 생성 실패 (중복): {username} - {e}")
            return False
        except Exception as e:
            print(f"[오류] 화주사 계정 생성 실패 (오류): {username} - {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            conn.close()


def update_company_password(username: str, old_password: str, new_password: str) -> bool:
    """화주사 비밀번호 변경"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT password FROM companies WHERE username = %s', (username,))
            row = cursor.fetchone()
            if not row or row[0] != old_password:
                return False
            
            cursor.execute('''
                UPDATE companies 
                SET password = %s, updated_at = CURRENT_TIMESTAMP
                WHERE username = %s
            ''', (new_password, username))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"비밀번호 변경 오류: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT password FROM companies WHERE username = ?', (username,))
            row = cursor.fetchone()
            if not row or row[0] != old_password:
                return False
            
            cursor.execute('''
                UPDATE companies 
                SET password = ?, updated_at = CURRENT_TIMESTAMP
                WHERE username = ?
            ''', (new_password, username))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"비밀번호 변경 오류: {e}")
            return False
        finally:
            conn.close()


def delete_company(company_id: int) -> bool:
    """화주사 계정 삭제"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM companies WHERE id = %s', (company_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"화주사 삭제 오류: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM companies WHERE id = ?', (company_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"화주사 삭제 오류: {e}")
            return False
        finally:
            conn.close()


def update_company_password_by_id(company_id: int, new_password: str) -> bool:
    """화주사 비밀번호 변경 (ID로)"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE companies 
                SET password = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (new_password, company_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"비밀번호 변경 오류: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE companies 
                SET password = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (new_password, company_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"비밀번호 변경 오류: {e}")
            return False
        finally:
            conn.close()


def update_company_certificate(company_id: int, certificate_url: str) -> bool:
    """화주사 사업자 등록증 URL 업데이트"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE companies 
                SET business_certificate_url = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (certificate_url, company_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"사업자 등록증 업데이트 오류: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE companies 
                SET business_certificate_url = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (certificate_url, company_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"사업자 등록증 업데이트 오류: {e}")
            return False
        finally:
            conn.close()


def update_last_login(username: str) -> bool:
    """로그인 시 최근 로그인 시간 업데이트"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE companies 
                SET last_login = CURRENT_TIMESTAMP
                WHERE username = %s
            ''', (username,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"최근 로그인 시간 업데이트 오류: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE companies 
                SET last_login = CURRENT_TIMESTAMP
                WHERE username = ?
            ''', (username,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"최근 로그인 시간 업데이트 오류: {e}")
            return False
        finally:
            conn.close()


def get_companies_statistics() -> Dict:
    """화주사 통계 조회 (관리자 수, 화주사 수)"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM companies WHERE role = '관리자'")
            admin_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM companies WHERE role = '화주사' OR role IS NULL OR role = ''")
            company_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM companies')
            total_count = cursor.fetchone()[0]
            
            return {
                'admin_count': admin_count,
                'company_count': company_count,
                'total_count': total_count
            }
        except Exception as e:
            print(f"통계 조회 오류: {e}")
            import traceback
            traceback.print_exc()
            # 오류 발생 시 트랜잭션 롤백
            try:
                conn.rollback()
            except:
                pass
            return {
                'admin_count': 0,
                'company_count': 0,
                'total_count': 0
            }
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM companies WHERE role = '관리자'")
            admin_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM companies WHERE role = '화주사' OR role IS NULL OR role = ''")
            company_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM companies')
            total_count = cursor.fetchone()[0]
            
            return {
                'admin_count': admin_count,
                'company_count': company_count,
                'total_count': total_count
            }
        except Exception as e:
            print(f"통계 조회 오류: {e}")
            return {
                'admin_count': 0,
                'company_count': 0,
                'total_count': 0
            }
        finally:
            conn.close()


def update_company_info(username: str, business_number: str = None,
                       business_name: str = None, business_address: str = None,
                       business_tel: str = None, business_email: str = None,
                       search_keywords: str = None) -> bool:
    """화주사 정보 업데이트 (사업자 정보 + 검색 키워드)"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            updates = []
            values = []
            
            if business_number is not None:
                updates.append('business_number = %s')
                values.append(business_number)
            if business_name is not None:
                updates.append('business_name = %s')
                values.append(business_name)
            if business_address is not None:
                updates.append('business_address = %s')
                values.append(business_address)
            if business_tel is not None:
                updates.append('business_tel = %s')
                values.append(business_tel)
            if business_email is not None:
                updates.append('business_email = %s')
                values.append(business_email)
            if search_keywords is not None:
                updates.append('search_keywords = %s')
                values.append(search_keywords)
            
            if not updates:
                return False
            
            updates.append('updated_at = CURRENT_TIMESTAMP')
            values.append(username)
            
            cursor.execute(f'''
                UPDATE companies 
                SET {', '.join(updates)}
                WHERE username = %s
            ''', values)
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"화주사 정보 업데이트 오류: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            updates = []
            values = []
            
            if business_number is not None:
                updates.append('business_number = ?')
                values.append(business_number)
            if business_name is not None:
                updates.append('business_name = ?')
                values.append(business_name)
            if business_address is not None:
                updates.append('business_address = ?')
                values.append(business_address)
            if business_tel is not None:
                updates.append('business_tel = ?')
                values.append(business_tel)
            if business_email is not None:
                updates.append('business_email = ?')
                values.append(business_email)
            
            if not updates:
                return False
            
            updates.append('updated_at = CURRENT_TIMESTAMP')
            values.append(username)
            
            cursor.execute(f'''
                UPDATE companies 
                SET {', '.join(updates)}
                WHERE username = ?
            ''', values)
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"화주사 정보 업데이트 오류: {e}")
            return False
        finally:
            conn.close()


def extract_day_number(date_str):
    """날짜 문자열에서 일자 숫자를 추출 (정렬용)"""
    if not date_str:
        return 0
    date_str = str(date_str).strip()
    
    if '-' in date_str:
        parts = date_str.split('-')
        if len(parts) >= 3:
            try:
                return int(parts[-1])
            except ValueError:
                return 0
    elif '/' in date_str:
        parts = date_str.split('/')
        if len(parts) >= 2:
            try:
                return int(parts[-1])
            except ValueError:
                return 0
    elif date_str.isdigit():
        return int(date_str)
    return 0


def normalize_company_name(name: str) -> str:
    """화주사명 정규화 (대소문자 무시, 공백 제거)"""
    if not name:
        return ''
    return ''.join(name.split()).lower()


def get_company_search_keywords(company_name: str) -> List[str]:
    """화주사명으로 검색 가능한 키워드 목록 가져오기 (본인 이름 + 별칭)"""
    if not company_name:
        return []
    
    # 화주사 정보 조회
    conn = get_db_connection()
    try:
        if USE_POSTGRESQL:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            # company_name 또는 username으로 검색
            cursor.execute('''
                SELECT company_name, search_keywords 
                FROM companies 
                WHERE company_name = %s OR username = %s
                LIMIT 1
            ''', (company_name, company_name))
        else:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT company_name, search_keywords 
                FROM companies 
                WHERE company_name = ? OR username = ?
                LIMIT 1
            ''', (company_name, company_name))
        
        row = cursor.fetchone()
        if row:
            if USE_POSTGRESQL:
                company_data = dict(row)
            else:
                company_data = dict(row) if hasattr(row, 'keys') else {
                    'company_name': row[0],
                    'search_keywords': row[1] if len(row) > 1 else None
                }
            
            keywords = [normalize_company_name(company_data.get('company_name', ''))]
            
            # search_keywords 필드에서 별칭 추가
            search_keywords = company_data.get('search_keywords', '')
            if search_keywords:
                # 쉼표나 줄바꿈으로 구분된 별칭들
                aliases = [alias.strip() for alias in search_keywords.replace('\n', ',').split(',') if alias.strip()]
                keywords.extend([normalize_company_name(alias) for alias in aliases])
            
            return list(set(keywords))  # 중복 제거
        return [normalize_company_name(company_name)]
    except Exception as e:
        print(f"[경고] get_company_search_keywords 오류: {e}")
        return [normalize_company_name(company_name)]
    finally:
        if 'cursor' in locals():
            cursor.close()
        conn.close()


def get_returns_by_company(company: str, month: str, role: str = '화주사') -> List[Dict]:
    """화주사별 반품 데이터 조회 (최신 날짜부터 정렬)
    
    대소문자 무시, 공백 무시, 별칭(search_keywords) 지원
    """
    conn = get_db_connection()
    
    # 디버깅: 파라미터 확인
    print(f"🔍 get_returns_by_company - company: '{company}', month: '{month}', role: '{role}'")
    
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            if role == '관리자':
                # 관리자는 모든 데이터 조회
                cursor.execute('SELECT * FROM returns WHERE month = %s', (month,))
                print(f"   관리자 모드: 모든 데이터 조회 (month: {month})")
                rows = [dict(row) for row in cursor.fetchall()]
            else:
                # 화주사는 자신의 데이터만 조회
                if not company or not company.strip():
                    print(f"   [경고] 화주사인데 company가 비어있음! 빈 리스트 반환")
                    return []
                
                # 검색 가능한 키워드 목록 가져오기
                search_keywords = get_company_search_keywords(company.strip())
                print(f"   검색 키워드: {search_keywords}")
                
                # 모든 반품 데이터를 가져온 후 필터링 (대소문자 무시, 공백 무시)
                cursor.execute('SELECT * FROM returns WHERE month = %s', (month,))
                all_rows = cursor.fetchall()
                all_returns = [dict(row) for row in all_rows]
                
                # 정규화된 키워드로 필터링
                result = []
                for ret in all_returns:
                    ret_company_name = normalize_company_name(ret.get('company_name', ''))
                    if ret_company_name in search_keywords:
                        result.append(ret)
                
                print(f"   화주사 모드: '{company.strip()}' 데이터만 조회 (month: {month}, {len(result)}건)")
                rows = result
            
            print(f"   조회된 데이터: {len(rows)}건")
            if rows and len(rows) > 0:
                # ID가 없는 데이터에 ID 생성
                cursor_update = conn.cursor()
                try:
                    for item in rows:
                        if not item.get('id') or item.get('id') is None:
                            # 최대 ID 조회
                            cursor_update.execute('SELECT COALESCE(MAX(id), 0) FROM returns')
                            max_id = cursor_update.fetchone()[0]
                            new_id = max_id + 1
                            
                            # ID 업데이트
                            customer_name = item.get('customer_name')
                            tracking_number = item.get('tracking_number')
                            month = item.get('month')
                            
                            if customer_name and tracking_number and month:
                                cursor_update.execute('''
                                    UPDATE returns 
                                    SET id = %s 
                                    WHERE customer_name = %s 
                                    AND tracking_number = %s 
                                    AND month = %s 
                                    AND (id IS NULL OR id = 0)
                                ''', (new_id, customer_name, tracking_number, month))
                                item['id'] = new_id
                                print(f"   [성공] ID 생성: {new_id} - {customer_name}, {tracking_number}")
                    
                    conn.commit()
                finally:
                    cursor_update.close()
                
                # 화주사별로 몇 건인지 확인 (디버깅용)
                company_counts = {}
                for item in rows:
                    comp_name = item.get('company_name', '')
                    company_counts[comp_name] = company_counts.get(comp_name, 0) + 1
                print(f"   화주사별 데이터 개수: {company_counts}")
                if role != '관리자' and len(company_counts) > 1:
                    print(f"   [경고] 경고: 화주사 모드인데 여러 화주사 데이터가 조회됨!")
            
            rows.sort(key=lambda x: (
                not x.get('return_date') or x.get('return_date') == '',
                -extract_day_number(x.get('return_date', '')),
                -(x.get('id') or 0)
            ))
            return rows
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            if role == '관리자':
                cursor.execute('SELECT * FROM returns WHERE month = ?', (month,))
                print(f"   관리자 모드: 모든 데이터 조회 (month: {month})")
                rows = cursor.fetchall()
                result = [dict(row) for row in rows]
            else:
                if not company or not company.strip():
                    print(f"   [경고] 화주사인데 company가 비어있음! 빈 리스트 반환")
                    return []
                
                # 검색 가능한 키워드 목록 가져오기
                search_keywords = get_company_search_keywords(company.strip())
                print(f"   검색 키워드: {search_keywords}")
                
                # 모든 반품 데이터를 가져온 후 필터링 (대소문자 무시, 공백 무시)
                cursor.execute('SELECT * FROM returns WHERE month = ?', (month,))
                all_rows = cursor.fetchall()
                all_returns = [dict(row) for row in all_rows]
                
                # 정규화된 키워드로 필터링
                result = []
                for ret in all_returns:
                    ret_company_name = normalize_company_name(ret.get('company_name', ''))
                    if ret_company_name in search_keywords:
                        result.append(ret)
                
                print(f"   화주사 모드: '{company.strip()}' 데이터만 조회 (month: {month}, {len(result)}건)")
            
            print(f"   조회된 데이터: {len(result)}건")
            if result and len(result) > 0:
                # ID가 없는 데이터에 ID 생성
                cursor_update = conn.cursor()
                try:
                    for item in result:
                        if not item.get('id') or item.get('id') is None:
                            # 최대 ID 조회
                            cursor_update.execute('SELECT COALESCE(MAX(id), 0) FROM returns')
                            max_id = cursor_update.fetchone()[0]
                            new_id = max_id + 1
                            
                            # ID 업데이트
                            customer_name = item.get('customer_name')
                            tracking_number = item.get('tracking_number')
                            month = item.get('month')
                            
                            if customer_name and tracking_number and month:
                                cursor_update.execute('''
                                    UPDATE returns 
                                    SET id = ? 
                                    WHERE customer_name = ? 
                                    AND tracking_number = ? 
                                    AND month = ? 
                                    AND (id IS NULL OR id = 0)
                                ''', (new_id, customer_name, tracking_number, month))
                                item['id'] = new_id
                                print(f"   [성공] ID 생성: {new_id} - {customer_name}, {tracking_number}")
                    
                    conn.commit()
                finally:
                    cursor_update.close()
                
                company_counts = {}
                for item in result:
                    comp_name = item.get('company_name', '')
                    company_counts[comp_name] = company_counts.get(comp_name, 0) + 1
                print(f"   화주사별 데이터 개수: {company_counts}")
                if role != '관리자' and len(company_counts) > 1:
                    print(f"   [경고] 경고: 화주사 모드인데 여러 화주사 데이터가 조회됨!")
            
            result.sort(key=lambda x: (
                not x.get('return_date') or x.get('return_date') == '',
                -extract_day_number(x.get('return_date', '')),
                -(x.get('id') or 0)
            ))
            return result
        finally:
            conn.close()


def get_available_months() -> List[str]:
    """사용 가능한 월 목록 조회 (년도-월 형식, 현재 년월 포함)"""
    from datetime import datetime
    
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT DISTINCT month FROM returns ORDER BY month DESC')
            rows = cursor.fetchall()
            db_months = [row[0] for row in rows]
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT DISTINCT month FROM returns ORDER BY month DESC')
            rows = cursor.fetchall()
            db_months = [row[0] for row in rows]
        finally:
            conn.close()
    
    # 현재 년월 가져오기
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    current_month_str = f"{current_year}년{current_month}월"
    
    if current_month_str not in db_months:
        db_months.append(current_month_str)
    
    # 다음 월 자동 생성
    next_month = current_month + 1
    next_year = current_year
    if next_month > 12:
        next_month = 1
        next_year = current_year + 1
    next_month_str = f"{next_year}년{next_month}월"
    
    if next_month_str not in db_months:
        db_months.append(next_month_str)
    
    # 정렬
    def parse_month(month_str):
        try:
            if '년' in month_str and '월' in month_str:
                year_part = month_str.split('년')[0]
                month_part = month_str.split('년')[1].split('월')[0]
                return (int(year_part), int(month_part))
        except:
            pass
        return (0, 0)
    
    db_months.sort(key=parse_month, reverse=True)
    return db_months


def save_client_request(return_id: int, request_text: str) -> bool:
    """화주사 요청사항 저장"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE returns 
                SET client_request = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (request_text, return_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"요청사항 저장 오류: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE returns 
                SET client_request = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (request_text, return_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"요청사항 저장 오류: {e}")
            return False
        finally:
            conn.close()


def mark_as_completed(return_id: int, manager_name: str) -> bool:
    """반품 처리완료 표시 (이름만 저장)"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE returns 
                SET completed = %s, client_confirmed = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (manager_name, manager_name, return_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"처리완료 표시 오류: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE returns 
                SET completed = ?, client_confirmed = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (manager_name, manager_name, return_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"처리완료 표시 오류: {e}")
            return False
        finally:
            conn.close()


def create_return(return_data: Dict) -> int:
    """반품 데이터 생성"""
    print(f"💾 create_return 함수 호출:")
    print(f"   고객명: {return_data.get('customer_name')}")
    print(f"   송장번호: {return_data.get('tracking_number')}")
    print(f"   월: {return_data.get('month')}")
    print(f"   화주명: {return_data.get('company_name')}")
    
    # 빈 문자열을 None으로 변환 (데이터베이스에 NULL로 저장)
    def empty_to_none(value):
        """빈 문자열이나 공백만 있는 문자열을 None으로 변환"""
        if value is None:
            return None
        if isinstance(value, str) and value.strip() == '':
            return None
        return value
    
    # 반품 데이터의 빈 문자열 필드를 None으로 변환
    return_data = {
        'return_date': return_data.get('return_date'),
        'company_name': return_data.get('company_name'),
        'product': empty_to_none(return_data.get('product')),
        'customer_name': return_data.get('customer_name'),
        'tracking_number': return_data.get('tracking_number'),
        'return_type': empty_to_none(return_data.get('return_type')),
        'stock_status': empty_to_none(return_data.get('stock_status')),
        'inspection': empty_to_none(return_data.get('inspection')),
        'completed': empty_to_none(return_data.get('completed')),
        'memo': empty_to_none(return_data.get('memo')),
        'photo_links': empty_to_none(return_data.get('photo_links')),
        'other_courier': empty_to_none(return_data.get('other_courier')),
        'shipping_fee': empty_to_none(return_data.get('shipping_fee')),
        'client_request': empty_to_none(return_data.get('client_request')),
        'client_confirmed': empty_to_none(return_data.get('client_confirmed')),
        'month': return_data.get('month')
    }
    
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO returns (
                    return_date, company_name, product, customer_name, tracking_number,
                    return_type, stock_status, inspection, completed, memo,
                    photo_links, other_courier, shipping_fee, client_request,
                    client_confirmed, month
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                return_data.get('return_date'),
                return_data.get('company_name'),
                return_data.get('product'),
                return_data.get('customer_name'),
                return_data.get('tracking_number'),
                return_data.get('return_type'),
                return_data.get('stock_status'),
                return_data.get('inspection'),
                return_data.get('completed'),
                return_data.get('memo'),
                return_data.get('photo_links'),
                return_data.get('other_courier'),
                return_data.get('shipping_fee'),
                return_data.get('client_request'),
                return_data.get('client_confirmed'),
                return_data.get('month')
            ))
            conn.commit()
            row = cursor.fetchone()
            return row[0] if row else 0
        except IntegrityError:
            # 중복 데이터인 경우 업데이트 (기존 값 유지)
            conn.rollback()
            # 기존 데이터 조회하여 return_type과 stock_status 확인
            cursor.execute('''
                SELECT return_type, stock_status FROM returns 
                WHERE customer_name = %s AND tracking_number = %s AND month = %s
            ''', (
                return_data.get('customer_name'),
                return_data.get('tracking_number'),
                return_data.get('month')
            ))
            existing_row = cursor.fetchone()
            existing_return_type = existing_row[0] if existing_row else None
            existing_stock_status = existing_row[1] if existing_row else None
            
            # 새로운 값이 None이면 기존 값 유지, 아니면 새 값 사용
            new_return_type = return_data.get('return_type') if return_data.get('return_type') is not None else existing_return_type
            new_stock_status = return_data.get('stock_status') if return_data.get('stock_status') is not None else existing_stock_status
            
            cursor.execute('''
                UPDATE returns SET
                    return_date = %s,
                    company_name = %s,
                    product = %s,
                    return_type = %s,
                    stock_status = %s,
                    inspection = COALESCE(%s, inspection),
                    completed = COALESCE(%s, completed),
                    memo = COALESCE(%s, memo),
                    photo_links = COALESCE(%s, photo_links),
                    other_courier = COALESCE(%s, other_courier),
                    shipping_fee = COALESCE(%s, shipping_fee),
                    updated_at = CURRENT_TIMESTAMP
                WHERE customer_name = %s AND tracking_number = %s AND month = %s
                RETURNING id
            ''', (
                return_data.get('return_date'),
                return_data.get('company_name'),
                return_data.get('product'),
                new_return_type,
                new_stock_status,
                return_data.get('inspection'),
                return_data.get('completed'),
                return_data.get('memo'),
                return_data.get('photo_links'),
                return_data.get('other_courier'),
                return_data.get('shipping_fee'),
                return_data.get('customer_name'),
                return_data.get('tracking_number'),
                return_data.get('month')
            ))
            conn.commit()
            row = cursor.fetchone()
            return row[0] if row else 0
        except Exception as e:
            print(f"반품 데이터 생성 오류: {e}")
            conn.rollback()
            return 0
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO returns (
                    return_date, company_name, product, customer_name, tracking_number,
                    return_type, stock_status, inspection, completed, memo,
                    photo_links, other_courier, shipping_fee, client_request,
                    client_confirmed, month
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                return_data.get('return_date'),
                return_data.get('company_name'),
                return_data.get('product'),
                return_data.get('customer_name'),
                return_data.get('tracking_number'),
                return_data.get('return_type'),
                return_data.get('stock_status'),
                return_data.get('inspection'),
                return_data.get('completed'),
                return_data.get('memo'),
                return_data.get('photo_links'),
                return_data.get('other_courier'),
                return_data.get('shipping_fee'),
                return_data.get('client_request'),
                return_data.get('client_confirmed'),
                return_data.get('month')
            ))
            conn.commit()
            new_id = cursor.lastrowid
            print(f"   [성공] 새 반품 데이터 생성 완료: ID = {new_id}")
            if not new_id or new_id == 0:
                # ID가 없으면 조회해서 가져오기
                cursor.execute('''
                    SELECT id FROM returns 
                    WHERE customer_name = ? AND tracking_number = ? AND month = ?
                ''', (
                    return_data.get('customer_name'),
                    return_data.get('tracking_number'),
                    return_data.get('month')
                ))
                row = cursor.fetchone()
                if row:
                    if hasattr(row, 'keys'):
                        new_id = row['id']
                    else:
                        new_id = row[0]
            return new_id if new_id else 0
        except IntegrityError:
            # 기존 데이터 조회하여 return_type과 stock_status 확인
            cursor.execute('''
                SELECT return_type, stock_status FROM returns 
                WHERE customer_name = ? AND tracking_number = ? AND month = ?
            ''', (
                return_data.get('customer_name'),
                return_data.get('tracking_number'),
                return_data.get('month')
            ))
            existing_row = cursor.fetchone()
            existing_return_type = existing_row[0] if existing_row and len(existing_row) > 0 else None
            existing_stock_status = existing_row[1] if existing_row and len(existing_row) > 1 else None
            
            # 새로운 값이 None이면 기존 값 유지, 아니면 새 값 사용
            new_return_type = return_data.get('return_type') if return_data.get('return_type') is not None else existing_return_type
            new_stock_status = return_data.get('stock_status') if return_data.get('stock_status') is not None else existing_stock_status
            
            cursor.execute('''
                UPDATE returns SET
                    return_date = ?,
                    company_name = ?,
                    product = ?,
                    return_type = ?,
                    stock_status = ?,
                    inspection = COALESCE(?, inspection),
                    completed = COALESCE(?, completed),
                    memo = COALESCE(?, memo),
                    photo_links = COALESCE(?, photo_links),
                    other_courier = COALESCE(?, other_courier),
                    shipping_fee = COALESCE(?, shipping_fee),
                    updated_at = CURRENT_TIMESTAMP
                WHERE customer_name = ? AND tracking_number = ? AND month = ?
            ''', (
                return_data.get('return_date'),
                return_data.get('company_name'),
                return_data.get('product'),
                new_return_type,
                new_stock_status,
                return_data.get('inspection'),
                return_data.get('completed'),
                return_data.get('memo'),
                return_data.get('photo_links'),
                return_data.get('other_courier'),
                return_data.get('shipping_fee'),
                return_data.get('customer_name'),
                return_data.get('tracking_number'),
                return_data.get('month')
            ))
            conn.commit()
            cursor.execute('''
                SELECT id FROM returns 
                WHERE customer_name = ? AND tracking_number = ? AND month = ?
            ''', (
                return_data.get('customer_name'),
                return_data.get('tracking_number'),
                return_data.get('month')
            ))
            row = cursor.fetchone()
            if row:
                if hasattr(row, 'keys'):
                    existing_id = row['id']
                else:
                    existing_id = row[0]
                print(f"   [성공] 기존 반품 데이터 업데이트 완료: ID = {existing_id}")
                return existing_id if existing_id else 0
            return 0
        except Exception as e:
            print(f"반품 데이터 생성 오류: {e}")
            return 0
        finally:
            conn.close()


def fix_missing_return_ids():
    """ID가 없는 모든 반품 데이터에 ID 생성 (일괄 처리)"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            # ID가 NULL이거나 0인 데이터 찾기
            cursor.execute('SELECT * FROM returns WHERE id IS NULL OR id = 0')
            rows = cursor.fetchall()
            
            if len(rows) == 0:
                print("[성공] ID가 없는 데이터가 없습니다.")
                return
            
            print(f"[정보] ID가 없는 데이터 {len(rows)}건 발견")
            
            # 각 행에 대해 ID 생성
            for row in rows:
                # 고유한 ID 생성 (현재 최대 ID + 1)
                cursor.execute('SELECT COALESCE(MAX(id), 0) FROM returns')
                max_id = cursor.fetchone()[0]
                new_id = max_id + 1
                
                # Row 객체에서 데이터 추출
                customer_name = row.get('customer_name') if hasattr(row, 'get') else row[3] if len(row) > 3 else None
                tracking_number = row.get('tracking_number') if hasattr(row, 'get') else row[4] if len(row) > 4 else None
                month = row.get('month') if hasattr(row, 'get') else row[15] if len(row) > 15 else None
                
                if customer_name and tracking_number and month:
                    # 해당 데이터에 ID 업데이트
                    cursor.execute('''
                        UPDATE returns 
                        SET id = %s 
                        WHERE customer_name = %s 
                        AND tracking_number = %s 
                        AND month = %s 
                        AND (id IS NULL OR id = 0)
                    ''', (new_id, customer_name, tracking_number, month))
                    print(f"   ✅ ID 생성: {new_id} - {customer_name}, {tracking_number}")
            
            conn.commit()
            print(f"[성공] 총 {len(rows)}건의 데이터에 ID를 생성했습니다.")
            
        except Exception as e:
            conn.rollback()
            print(f"[오류] 오류 발생: {e}")
            import traceback
            traceback.print_exc()
        finally:
            cursor.close()
            conn.close()
    else:
        # SQLite
        cursor = conn.cursor()
        try:
            # ID가 NULL이거나 0인 데이터 찾기
            cursor.execute('SELECT * FROM returns WHERE id IS NULL OR id = 0')
            rows = cursor.fetchall()
            
            if len(rows) == 0:
                print("[성공] ID가 없는 데이터가 없습니다.")
                return
            
            print(f"[정보] ID가 없는 데이터 {len(rows)}건 발견")
            
            # 각 행에 대해 ID 생성
            for row in rows:
                # 고유한 ID 생성 (현재 최대 ID + 1)
                cursor.execute('SELECT COALESCE(MAX(id), 0) FROM returns')
                max_id = cursor.fetchone()[0]
                new_id = max_id + 1
                
                # SQLite Row 객체는 dict처럼 접근 가능
                try:
                    if hasattr(row, 'keys'):
                        # Row 객체 (dict-like)
                        customer_name = row['customer_name']
                        tracking_number = row['tracking_number']
                        month = row['month']
                    elif isinstance(row, dict):
                        customer_name = row.get('customer_name')
                        tracking_number = row.get('tracking_number')
                        month = row.get('month')
                    else:
                        # tuple인 경우 인덱스로 접근
                        customer_name = row[3] if len(row) > 3 else None
                        tracking_number = row[4] if len(row) > 4 else None
                        month = row[15] if len(row) > 15 else None
                except (KeyError, IndexError, TypeError) as e:
                    print(f"   [경고] 행 데이터 파싱 오류: {e}, row: {row}")
                    continue
                
                if customer_name and tracking_number and month:
                    # 해당 데이터에 ID 업데이트
                    cursor.execute('''
                        UPDATE returns 
                        SET id = ? 
                        WHERE customer_name = ? 
                        AND tracking_number = ? 
                        AND month = ? 
                        AND (id IS NULL OR id = 0)
                    ''', (new_id, customer_name, tracking_number, month))
                    print(f"   ✅ ID 생성: {new_id} - {customer_name}, {tracking_number}")
            
            conn.commit()
            print(f"[성공] 총 {len(rows)}건의 데이터에 ID를 생성했습니다.")
            
        except Exception as e:
            print(f"[오류] 오류 발생: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.close()


def get_return_by_id(return_id: int) -> Optional[Dict]:
    """반품 데이터 ID로 조회"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute('SELECT * FROM returns WHERE id = %s', (return_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM returns WHERE id = ?', (return_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


def update_memo(return_id: int, memo: str) -> bool:
    """비고 업데이트"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE returns 
                SET memo = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (memo, return_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"비고 업데이트 오류: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE returns 
                SET memo = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (memo, return_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"비고 업데이트 오류: {e}")
            return False
        finally:
            conn.close()


def update_return(return_id: int, return_data: Dict) -> bool:
    """반품 데이터 업데이트"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            updates = []
            values = []
            
            # 업데이트할 필드들
            if 'company_name' in return_data:
                updates.append('company_name = %s')
                values.append(return_data.get('company_name'))
            if 'product' in return_data:
                updates.append('product = %s')
                values.append(return_data.get('product'))
            if 'return_type' in return_data:
                updates.append('return_type = %s')
                values.append(return_data.get('return_type'))
            if 'stock_status' in return_data:
                updates.append('stock_status = %s')
                values.append(return_data.get('stock_status'))
            
            if not updates:
                return False
            
            updates.append('updated_at = CURRENT_TIMESTAMP')
            values.append(return_id)
            
            cursor.execute(f'''
                UPDATE returns 
                SET {', '.join(updates)}
                WHERE id = %s
            ''', values)
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"반품 데이터 업데이트 오류: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            updates = []
            values = []
            
            # 업데이트할 필드들
            if 'company_name' in return_data:
                updates.append('company_name = ?')
                values.append(return_data.get('company_name'))
            if 'product' in return_data:
                updates.append('product = ?')
                values.append(return_data.get('product'))
            if 'return_type' in return_data:
                updates.append('return_type = ?')
                values.append(return_data.get('return_type'))
            if 'stock_status' in return_data:
                updates.append('stock_status = ?')
                values.append(return_data.get('stock_status'))
            
            if not updates:
                return False
            
            updates.append('updated_at = CURRENT_TIMESTAMP')
            values.append(return_id)
            
            cursor.execute(f'''
                UPDATE returns 
                SET {', '.join(updates)}
                WHERE id = ?
            ''', values)
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"반품 데이터 업데이트 오류: {e}")
            return False
        finally:
            conn.close()


def delete_return(return_id: int) -> bool:
    """반품 데이터 삭제"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM returns WHERE id = %s', (return_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"반품 삭제 오류: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM returns WHERE id = ?', (return_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"반품 삭제 오류: {e}")
            return False
        finally:
            conn.close()


def normalize_month(month: str) -> str:
    """월 형식을 정규화 (예: "2025년11월", "2025년 11월" -> "2025년11월")"""
    if not month:
        return month
    # 공백 제거
    month = month.replace(' ', '').replace('-', '').strip()
    # "년"과 "월" 사이의 공백 제거
    if '년' in month and '월' in month:
        parts = month.split('년')
        if len(parts) == 2:
            year = parts[0]
            month_part = parts[1].replace('월', '').strip()
            return f"{year}년{month_part}월"
    return month


def find_return_by_tracking_number(tracking_number: str, month: str = None) -> Optional[Dict]:
    """송장번호로 반품 데이터 찾기 (QR 코드 검색용)
    
    Args:
        tracking_number: 송장번호
        month: 월 (예: "2025년11월"). None이면 모든 월에서 검색
    """
    # month 형식 정규화
    if month:
        month = normalize_month(month)
        print(f"   📅 정규화된 월: '{month}'")
    
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            tracking_normalized = tracking_number.replace(' ', '').replace('-', '').strip()
            
            # month가 지정된 경우 해당 월에서만 검색, 없으면 모든 월에서 검색
            if month:
                print(f"   🔎 PostgreSQL 검색: month='{month}', tracking_number='{tracking_number}'")
                # 먼저 정확한 매칭 시도
                cursor.execute('''
                    SELECT * FROM returns 
                    WHERE month = %s AND (
                        tracking_number = %s OR
                        REPLACE(REPLACE(tracking_number, ' ', ''), '-', '') = %s
                    )
                    ORDER BY created_at DESC
                    LIMIT 1
                ''', (month, tracking_number.strip(), tracking_normalized))
                row = cursor.fetchone()
                if row:
                    print(f"   [성공] 정확한 매칭으로 데이터 발견")
                    return dict(row)
                
                # 정확한 매칭이 실패하면 해당 월의 모든 데이터를 확인
                cursor.execute('SELECT DISTINCT month FROM returns WHERE month LIKE %s', (f'%{month[-2:]}%',))
                months_in_db = [r[0] for r in cursor.fetchall()]
                print(f"   📋 데이터베이스의 유사한 월 형식: {months_in_db}")
                
                # 유사한 월 형식으로 재검색 시도
                for db_month in months_in_db:
                    if month in db_month or db_month in month:
                        print(f"   🔄 유사한 월 형식으로 재검색: '{db_month}'")
                        cursor.execute('''
                            SELECT * FROM returns 
                            WHERE month = %s AND (
                                tracking_number = %s OR
                                REPLACE(REPLACE(tracking_number, ' ', ''), '-', '') = %s
                            )
                            ORDER BY created_at DESC
                            LIMIT 1
                        ''', (db_month, tracking_number.strip(), tracking_normalized))
                        row = cursor.fetchone()
                        if row:
                            print(f"   [성공] 유사한 월 형식으로 데이터 발견: '{db_month}'")
                            return dict(row)
                
                return None
            else:
                cursor.execute('''
                    SELECT * FROM returns 
                    WHERE (
                        tracking_number = %s OR
                        REPLACE(REPLACE(tracking_number, ' ', ''), '-', '') = %s
                    )
                    ORDER BY created_at DESC
                    LIMIT 1
                ''', (tracking_number.strip(), tracking_normalized))
            
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            print(f"송장번호 검색 오류: {e}")
            return None
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            tracking_normalized = tracking_number.replace(' ', '').replace('-', '').strip()
            
            # month가 지정된 경우 해당 월에서만 검색, 없으면 모든 월에서 검색
            if month:
                print(f"   🔎 SQLite 검색: month='{month}', tracking_number='{tracking_number}'")
                # 먼저 정확한 매칭 시도
                cursor.execute('''
                    SELECT * FROM returns 
                    WHERE month = ? AND (
                        tracking_number = ? OR
                        REPLACE(REPLACE(tracking_number, ' ', ''), '-', '') = ?
                    )
                    ORDER BY created_at DESC
                    LIMIT 1
                ''', (month, tracking_number.strip(), tracking_normalized))
                row = cursor.fetchone()
                if row:
                    print(f"   [성공] 정확한 매칭으로 데이터 발견")
                    return dict(row)
                
                # 정확한 매칭이 실패하면 해당 월의 모든 데이터를 확인
                cursor.execute('SELECT DISTINCT month FROM returns WHERE month LIKE ?', (f'%{month[-2:]}%',))
                months_in_db = [r[0] for r in cursor.fetchall()]
                print(f"   📋 데이터베이스의 유사한 월 형식: {months_in_db}")
                
                # 유사한 월 형식으로 재검색 시도
                for db_month in months_in_db:
                    if month in db_month or db_month in month:
                        print(f"   🔄 유사한 월 형식으로 재검색: '{db_month}'")
                        cursor.execute('''
                            SELECT * FROM returns 
                            WHERE month = ? AND (
                                tracking_number = ? OR
                                REPLACE(REPLACE(tracking_number, ' ', ''), '-', '') = ?
                            )
                            ORDER BY created_at DESC
                            LIMIT 1
                        ''', (db_month, tracking_number.strip(), tracking_normalized))
                        row = cursor.fetchone()
                        if row:
                            print(f"   [성공] 유사한 월 형식으로 데이터 발견: '{db_month}'")
                            return dict(row)
                
                return None
            else:
                cursor.execute('''
                    SELECT * FROM returns 
                    WHERE (
                        tracking_number = ? OR
                        REPLACE(REPLACE(tracking_number, ' ', ''), '-', '') = ?
                    )
                    ORDER BY created_at DESC
                    LIMIT 1
                ''', (tracking_number.strip(), tracking_normalized))
            
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            print(f"송장번호 검색 오류: {e}")
            return None
        finally:
            conn.close()


def update_photo_links(return_id: int, photo_links: str) -> bool:
    """사진 링크 업데이트"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE returns 
                SET photo_links = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (photo_links, return_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"사진 링크 업데이트 오류: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE returns 
                SET photo_links = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (photo_links, return_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"사진 링크 업데이트 오류: {e}")
            return False
        finally:
            conn.close()


# ========== 게시판 관련 함수 ==========

def create_board_category(name: str, display_order: int = 0) -> int:
    """게시판 카테고리 생성"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO board_categories (name, display_order)
                VALUES (%s, %s)
                RETURNING id
            ''', (name, display_order))
            conn.commit()
            row = cursor.fetchone()
            return row[0] if row else 0
        except Exception as e:
            print(f"카테고리 생성 오류: {e}")
            conn.rollback()
            return 0
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO board_categories (name, display_order)
                VALUES (?, ?)
            ''', (name, display_order))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"카테고리 생성 오류: {e}")
            return 0
        finally:
            conn.close()


def get_all_board_categories() -> List[Dict]:
    """모든 게시판 카테고리 조회"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute('''
                SELECT * FROM board_categories 
                ORDER BY display_order ASC, created_at ASC
            ''')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT * FROM board_categories 
                ORDER BY display_order ASC, created_at ASC
            ''')
            rows = cursor.fetchall()
            # SQLite Row 객체를 딕셔너리로 변환
            result = []
            for idx, row in enumerate(rows):
                if hasattr(row, 'keys'):
                    # 먼저 dict(row)로 변환
                    row_dict = dict(row)
                    
                    # Row 객체의 키 확인
                    row_keys = list(row_dict.keys())
                    
                    # id 필드를 찾아서 설정
                    # 1. 먼저 'id' 키가 있는지 확인
                    if 'id' in row_dict:
                        # id가 있지만 None이면 row[0] 사용
                        if row_dict['id'] is None and len(row) > 0:
                            row_dict['id'] = row[0]
                    else:
                        # id 키가 없으면 row[0] 사용 (SELECT b.id as id가 첫 번째 컬럼)
                        if len(row) > 0:
                            row_dict['id'] = row[0]
                        else:
                            # row[0]도 없으면 None
                            row_dict['id'] = None
                    
                    # 디버깅: 첫 번째 게시글만 로그 출력
                    if idx == 0:
                        print(f"🔍 게시글 Row 변환 - Row 키: {row_keys}")
                        print(f"🔍 게시글 Row 변환 - row[0] 값: {row[0] if len(row) > 0 else 'N/A'}")
                        print(f"🔍 게시글 Row 변환 - Dict 키: {list(row_dict.keys())}")
                        print(f"🔍 게시글 Row 변환 - 최종 id: {row_dict.get('id')}, 타입: {type(row_dict.get('id'))}")
                    result.append(row_dict)
                else:
                    # 튜플인 경우 (row_factory가 설정되지 않은 경우)
                    result.append({
                        'id': row[0] if len(row) > 0 else None,
                        'category_id': row[1] if len(row) > 1 else None,
                        'title': row[2] if len(row) > 2 else None,
                        'content': row[3] if len(row) > 3 else None,
                        'author_name': row[4] if len(row) > 4 else None,
                        'author_role': row[5] if len(row) > 5 else None,
                        'is_pinned': row[6] if len(row) > 6 else None,
                        'view_count': row[7] if len(row) > 7 else None,
                        'created_at': row[8] if len(row) > 8 else None,
                        'updated_at': row[9] if len(row) > 9 else None,
                        'category_name': row[10] if len(row) > 10 else None
                    })
            return result
        finally:
            conn.close()


def update_board_category(category_id: int, name: str = None, display_order: int = None) -> bool:
    """게시판 카테고리 수정"""
    conn = get_db_connection()
    
    updates = []
    params = []
    
    if name is not None:
        updates.append('name = %s' if USE_POSTGRESQL else 'name = ?')
        params.append(name)
    if display_order is not None:
        updates.append('display_order = %s' if USE_POSTGRESQL else 'display_order = ?')
        params.append(display_order)
    
    if not updates:
        return False
    
    params.append(category_id)
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                UPDATE board_categories 
                SET {', '.join(updates)}
                WHERE id = %s
            ''', params)
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"카테고리 수정 오류: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                UPDATE board_categories 
                SET {', '.join(updates)}
                WHERE id = ?
            ''', params)
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"카테고리 수정 오류: {e}")
            return False
        finally:
            conn.close()


def delete_board_category(category_id: int) -> bool:
    """게시판 카테고리 삭제"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM board_categories WHERE id = %s', (category_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"카테고리 삭제 오류: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM board_categories WHERE id = ?', (category_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"카테고리 삭제 오류: {e}")
            return False
        finally:
            conn.close()


def create_board(board_data: Dict) -> int:
    """게시글 생성"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO boards (
                    category_id, title, content, author_name, author_role, is_pinned
                ) VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                board_data.get('category_id'),
                board_data.get('title'),
                board_data.get('content'),
                board_data.get('author_name'),
                board_data.get('author_role'),
                board_data.get('is_pinned', False)
            ))
            conn.commit()
            row = cursor.fetchone()
            return row[0] if row else 0
        except Exception as e:
            print(f"게시글 생성 오류: {e}")
            conn.rollback()
            return 0
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            # 기존 최대 ID 확인
            cursor.execute('SELECT MAX(id) FROM boards')
            max_id_row = cursor.fetchone()
            max_id = max_id_row[0] if max_id_row and max_id_row[0] is not None else 0
            
            # 새로운 ID 생성 (최대 ID + 1 또는 랜덤)
            import random
            import time
            # 최대 ID + 1을 기본으로 사용하되, 랜덤 요소 추가
            new_id = max_id + 1
            # 타임스탬프 기반 랜덤 값 추가 (중복 방지)
            random_component = int(time.time()) % 10000 + random.randint(1, 999)
            new_id = new_id + random_component
            
            # ID가 너무 크면 최대 ID + 1 사용
            if new_id > max_id + 100000:
                new_id = max_id + 1
            
            # 현재 시간을 KST로 가져오기
            from datetime import datetime, timezone, timedelta
            kst = timezone(timedelta(hours=9))
            created_at = datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute('''
                INSERT INTO boards (
                    id, category_id, title, content, author_name, author_role, is_pinned, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                new_id,
                board_data.get('category_id'),
                board_data.get('title'),
                board_data.get('content'),
                board_data.get('author_name'),
                board_data.get('author_role'),
                1 if board_data.get('is_pinned', False) else 0,
                created_at,
                created_at
            ))
            conn.commit()
            print(f"[성공] 게시글 생성 성공 - 생성된 ID: {new_id} (최대 ID: {max_id})")
            return new_id
        except Exception as e:
            print(f"[오류] 게시글 생성 오류: {e}")
            import traceback
            traceback.print_exc()
            return 0
        finally:
            conn.close()


def get_boards_by_category(category_id: int) -> List[Dict]:
    """카테고리별 게시글 조회 (공지사항 먼저, 그 다음 최신순)"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute('''
                SELECT b.*, bc.name as category_name
                FROM boards b
                JOIN board_categories bc ON b.category_id = bc.id
                WHERE b.category_id = %s
                ORDER BY b.is_pinned DESC, b.created_at DESC
            ''', (category_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT b.id as id, b.category_id, b.title, b.content, b.author_name, b.author_role, 
                       b.is_pinned, b.view_count, b.created_at, b.updated_at, bc.name as category_name
                FROM boards b
                JOIN board_categories bc ON b.category_id = bc.id
                WHERE b.category_id = ?
                ORDER BY b.is_pinned DESC, b.created_at DESC
            ''', (category_id,))
            rows = cursor.fetchall()
            # SQLite Row 객체를 딕셔너리로 변환
            result = []
            for idx, row in enumerate(rows):
                if hasattr(row, 'keys'):
                    # 먼저 dict(row)로 변환
                    row_dict = dict(row)
                    
                    # Row 객체의 키 확인
                    row_keys = list(row_dict.keys())
                    
                    # id 필드를 찾아서 설정
                    # 1. 먼저 'id' 키가 있는지 확인
                    if 'id' in row_dict:
                        # id가 있지만 None이면 row[0] 사용
                        if row_dict['id'] is None and len(row) > 0:
                            row_dict['id'] = row[0]
                    else:
                        # id 키가 없으면 row[0] 사용 (SELECT b.id as id가 첫 번째 컬럼)
                        if len(row) > 0:
                            row_dict['id'] = row[0]
                        else:
                            # row[0]도 없으면 None
                            row_dict['id'] = None
                    
                    # 디버깅: 첫 번째 게시글만 로그 출력
                    if idx == 0:
                        print(f"🔍 게시글 Row 변환 - Row 키: {row_keys}")
                        print(f"🔍 게시글 Row 변환 - row[0] 값: {row[0] if len(row) > 0 else 'N/A'}")
                        print(f"🔍 게시글 Row 변환 - Dict 키: {list(row_dict.keys())}")
                        print(f"🔍 게시글 Row 변환 - 최종 id: {row_dict.get('id')}, 타입: {type(row_dict.get('id'))}")
                    result.append(row_dict)
                else:
                    # 튜플인 경우 (row_factory가 설정되지 않은 경우)
                    result.append({
                        'id': row[0] if len(row) > 0 else None,
                        'category_id': row[1] if len(row) > 1 else None,
                        'title': row[2] if len(row) > 2 else None,
                        'content': row[3] if len(row) > 3 else None,
                        'author_name': row[4] if len(row) > 4 else None,
                        'author_role': row[5] if len(row) > 5 else None,
                        'is_pinned': row[6] if len(row) > 6 else None,
                        'view_count': row[7] if len(row) > 7 else None,
                        'created_at': row[8] if len(row) > 8 else None,
                        'updated_at': row[9] if len(row) > 9 else None,
                        'category_name': row[10] if len(row) > 10 else None
                    })
            return result
        finally:
            conn.close()


def get_all_boards() -> List[Dict]:
    """전체 게시글 조회 (관리자용)"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute('''
                SELECT b.*, bc.name as category_name
                FROM boards b
                JOIN board_categories bc ON b.category_id = bc.id
                ORDER BY b.is_pinned DESC, b.created_at DESC
            ''')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT b.id as id, b.category_id, b.title, b.content, b.author_name, b.author_role, 
                       b.is_pinned, b.view_count, b.created_at, b.updated_at, bc.name as category_name
                FROM boards b
                JOIN board_categories bc ON b.category_id = bc.id
                ORDER BY b.is_pinned DESC, b.created_at DESC
            ''')
            rows = cursor.fetchall()
            # SQLite Row 객체를 딕셔너리로 변환
            result = []
            for idx, row in enumerate(rows):
                if hasattr(row, 'keys'):
                    # 먼저 dict(row)로 변환
                    row_dict = dict(row)
                    
                    # Row 객체의 키 확인
                    row_keys = list(row_dict.keys())
                    
                    # id 필드를 찾아서 설정
                    # 1. 먼저 'id' 키가 있는지 확인
                    if 'id' in row_dict:
                        # id가 있지만 None이면 row[0] 사용
                        if row_dict['id'] is None and len(row) > 0:
                            row_dict['id'] = row[0]
                    else:
                        # id 키가 없으면 row[0] 사용 (SELECT b.id as id가 첫 번째 컬럼)
                        if len(row) > 0:
                            row_dict['id'] = row[0]
                        else:
                            # row[0]도 없으면 None
                            row_dict['id'] = None
                    
                    # 디버깅: 첫 번째 게시글만 로그 출력
                    if idx == 0:
                        print(f"🔍 게시글 Row 변환 - Row 키: {row_keys}")
                        print(f"🔍 게시글 Row 변환 - row[0] 값: {row[0] if len(row) > 0 else 'N/A'}")
                        print(f"🔍 게시글 Row 변환 - Dict 키: {list(row_dict.keys())}")
                        print(f"🔍 게시글 Row 변환 - 최종 id: {row_dict.get('id')}, 타입: {type(row_dict.get('id'))}")
                    result.append(row_dict)
                else:
                    # 튜플인 경우 (row_factory가 설정되지 않은 경우)
                    result.append({
                        'id': row[0] if len(row) > 0 else None,
                        'category_id': row[1] if len(row) > 1 else None,
                        'title': row[2] if len(row) > 2 else None,
                        'content': row[3] if len(row) > 3 else None,
                        'author_name': row[4] if len(row) > 4 else None,
                        'author_role': row[5] if len(row) > 5 else None,
                        'is_pinned': row[6] if len(row) > 6 else None,
                        'view_count': row[7] if len(row) > 7 else None,
                        'created_at': row[8] if len(row) > 8 else None,
                        'updated_at': row[9] if len(row) > 9 else None,
                        'category_name': row[10] if len(row) > 10 else None
                    })
            return result
        finally:
            conn.close()


def get_board_by_id(board_id: int) -> Optional[Dict]:
    """게시글 ID로 조회"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute('''
                SELECT b.*, bc.name as category_name
                FROM boards b
                JOIN board_categories bc ON b.category_id = bc.id
                WHERE b.id = %s
            ''', (board_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT b.id as id, b.category_id, b.title, b.content, b.author_name, b.author_role, 
                       b.is_pinned, b.view_count, b.created_at, b.updated_at, bc.name as category_name
                FROM boards b
                JOIN board_categories bc ON b.category_id = bc.id
                WHERE b.id = ?
            ''', (board_id,))
            row = cursor.fetchone()
            # SQLite Row 객체를 딕셔너리로 변환
            return dict(row) if row else None
        finally:
            conn.close()


def update_board(board_id: int, board_data: Dict) -> bool:
    """게시글 수정"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE boards SET
                    category_id = %s,
                    title = %s,
                    content = %s,
                    is_pinned = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (
                board_data.get('category_id'),
                board_data.get('title'),
                board_data.get('content'),
                board_data.get('is_pinned', False),
                board_id
            ))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"게시글 수정 오류: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE boards SET
                    category_id = ?,
                    title = ?,
                    content = ?,
                    is_pinned = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                board_data.get('category_id'),
                board_data.get('title'),
                board_data.get('content'),
                1 if board_data.get('is_pinned', False) else 0,
                board_id
            ))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"게시글 수정 오류: {e}")
            return False
        finally:
            conn.close()


def delete_board(board_id: int) -> bool:
    """게시글 삭제"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM boards WHERE id = %s', (board_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"게시글 삭제 오류: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM boards WHERE id = ?', (board_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"게시글 삭제 오류: {e}")
            return False
        finally:
            conn.close()


def increment_board_view_count(board_id: int) -> bool:
    """게시글 조회수 증가"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE boards 
                SET view_count = view_count + 1
                WHERE id = %s
            ''', (board_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"조회수 증가 오류: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE boards 
                SET view_count = view_count + 1
                WHERE id = ?
            ''', (board_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"조회수 증가 오류: {e}")
            return False
        finally:
            conn.close()


def create_board_file(file_data: Dict) -> int:
    """게시글 첨부파일 생성"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO board_files (board_id, file_name, file_url, file_size)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            ''', (
                file_data.get('board_id'),
                file_data.get('file_name'),
                file_data.get('file_url'),
                file_data.get('file_size')
            ))
            conn.commit()
            row = cursor.fetchone()
            return row[0] if row else 0
        except Exception as e:
            print(f"첨부파일 생성 오류: {e}")
            conn.rollback()
            return 0
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO board_files (board_id, file_name, file_url, file_size)
                VALUES (?, ?, ?, ?)
            ''', (
                file_data.get('board_id'),
                file_data.get('file_name'),
                file_data.get('file_url'),
                file_data.get('file_size')
            ))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"첨부파일 생성 오류: {e}")
            return 0
        finally:
            conn.close()


def get_board_files(board_id: int) -> List[Dict]:
    """게시글 첨부파일 조회"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute('''
                SELECT * FROM board_files 
                WHERE board_id = %s
                ORDER BY created_at ASC
            ''', (board_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT * FROM board_files 
                WHERE board_id = ?
                ORDER BY created_at ASC
            ''', (board_id,))
            rows = cursor.fetchall()
            # SQLite Row 객체를 딕셔너리로 변환
            result = []
            for idx, row in enumerate(rows):
                if hasattr(row, 'keys'):
                    # 먼저 dict(row)로 변환
                    row_dict = dict(row)
                    
                    # Row 객체의 키 확인
                    row_keys = list(row_dict.keys())
                    
                    # id 필드를 찾아서 설정
                    # 1. 먼저 'id' 키가 있는지 확인
                    if 'id' in row_dict:
                        # id가 있지만 None이면 row[0] 사용
                        if row_dict['id'] is None and len(row) > 0:
                            row_dict['id'] = row[0]
                    else:
                        # id 키가 없으면 row[0] 사용 (SELECT b.id as id가 첫 번째 컬럼)
                        if len(row) > 0:
                            row_dict['id'] = row[0]
                        else:
                            # row[0]도 없으면 None
                            row_dict['id'] = None
                    
                    # 디버깅: 첫 번째 게시글만 로그 출력
                    if idx == 0:
                        print(f"🔍 게시글 Row 변환 - Row 키: {row_keys}")
                        print(f"🔍 게시글 Row 변환 - row[0] 값: {row[0] if len(row) > 0 else 'N/A'}")
                        print(f"🔍 게시글 Row 변환 - Dict 키: {list(row_dict.keys())}")
                        print(f"🔍 게시글 Row 변환 - 최종 id: {row_dict.get('id')}, 타입: {type(row_dict.get('id'))}")
                    result.append(row_dict)
                else:
                    # 튜플인 경우 (row_factory가 설정되지 않은 경우)
                    result.append({
                        'id': row[0] if len(row) > 0 else None,
                        'category_id': row[1] if len(row) > 1 else None,
                        'title': row[2] if len(row) > 2 else None,
                        'content': row[3] if len(row) > 3 else None,
                        'author_name': row[4] if len(row) > 4 else None,
                        'author_role': row[5] if len(row) > 5 else None,
                        'is_pinned': row[6] if len(row) > 6 else None,
                        'view_count': row[7] if len(row) > 7 else None,
                        'created_at': row[8] if len(row) > 8 else None,
                        'updated_at': row[9] if len(row) > 9 else None,
                        'category_name': row[10] if len(row) > 10 else None
                    })
            return result
        finally:
            conn.close()


def delete_board_file(file_id: int) -> bool:
    """게시글 첨부파일 삭제"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM board_files WHERE id = %s', (file_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"첨부파일 삭제 오류: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM board_files WHERE id = ?', (file_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"첨부파일 삭제 오류: {e}")
            return False
        finally:
            conn.close()


# ========== 판매 스케쥴 관련 함수 ==========

def create_schedule(schedule_data: Dict) -> int:
    """판매 스케쥴 생성"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO schedules (
                    company_name, title, start_date, end_date, 
                    event_description, request_note, schedule_type
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                schedule_data.get('company_name'),
                schedule_data.get('title'),
                schedule_data.get('start_date'),
                schedule_data.get('end_date'),
                schedule_data.get('event_description'),
                schedule_data.get('request_note'),
                schedule_data.get('schedule_type')
            ))
            conn.commit()
            row = cursor.fetchone()
            return row[0] if row else 0
        except Exception as e:
            print(f"스케쥴 생성 오류: {e}")
            conn.rollback()
            return 0
        finally:
            cursor.close()
            conn.close()
    else:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            import random
            import time
            from datetime import datetime, timezone, timedelta
            
            # 랜덤 ID 생성 (중복 체크)
            max_attempts = 10
            new_id = None
            for attempt in range(max_attempts):
                # 타임스탬프 기반 + 랜덤 숫자
                timestamp_part = int(time.time() * 1000) % 1000000  # 마지막 6자리
                random_part = random.randint(1000, 9999)  # 4자리 랜덤
                candidate_id = timestamp_part * 10000 + random_part
                
                # 중복 체크
                cursor.execute('SELECT id FROM schedules WHERE id = ?', (candidate_id,))
                if cursor.fetchone() is None:
                    new_id = candidate_id
                    break
            
            # 모든 시도 실패 시 순차적 ID 사용
            if new_id is None:
                cursor.execute('SELECT MAX(id) FROM schedules')
                max_id_row = cursor.fetchone()
                max_id = max_id_row[0] if max_id_row and max_id_row[0] is not None else 0
                new_id = max_id + 1 + random.randint(1, 1000)
            
            # 현재 시간을 KST로 가져오기
            kst = timezone(timedelta(hours=9))
            created_at = datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute('''
                INSERT INTO schedules (
                    id, company_name, title, start_date, end_date, 
                    event_description, request_note, schedule_type, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                new_id,
                schedule_data.get('company_name'),
                schedule_data.get('title'),
                schedule_data.get('start_date'),
                schedule_data.get('end_date'),
                schedule_data.get('event_description'),
                schedule_data.get('request_note'),
                schedule_data.get('schedule_type'),
                created_at,
                created_at
            ))
            conn.commit()
            print(f"[성공] 스케줄 생성 성공 - 생성된 ID: {new_id}")
            return new_id
        except Exception as e:
            print(f"스케쥴 생성 오류: {e}")
            import traceback
            traceback.print_exc()
            return 0
        finally:
            conn.close()


def get_schedules_by_company(company_name: str) -> List[Dict]:
    """화주사별 스케쥴 조회"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute('''
                SELECT * FROM schedules 
                WHERE company_name = %s
                ORDER BY start_date DESC, created_at DESC
            ''', (company_name,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            cursor.close()
            conn.close()
    else:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT id, company_name, title, start_date, end_date, 
                       event_description, request_note, schedule_type, 
                       created_at, updated_at
                FROM schedules 
                WHERE company_name = ?
                ORDER BY start_date DESC, created_at DESC
            ''', (company_name,))
            rows = cursor.fetchall()
            result = []
            for row in rows:
                # SQLite Row 객체를 명시적으로 딕셔너리로 변환
                row_dict = {}
                if hasattr(row, 'keys'):
                    # Row 객체인 경우
                    for key in row.keys():
                        row_dict[key] = row[key]
                    # ID가 없거나 None인 경우 row[0]에서 가져오기
                    if 'id' not in row_dict or row_dict['id'] is None:
                        row_dict['id'] = row[0] if len(row) > 0 else None
                else:
                    # 튜플인 경우
                    row_dict = {
                        'id': row[0] if len(row) > 0 else None,
                        'company_name': row[1] if len(row) > 1 else None,
                        'title': row[2] if len(row) > 2 else None,
                        'start_date': row[3] if len(row) > 3 else None,
                        'end_date': row[4] if len(row) > 4 else None,
                        'event_description': row[5] if len(row) > 5 else None,
                        'request_note': row[6] if len(row) > 6 else None,
                        'schedule_type': row[7] if len(row) > 7 else None,
                        'created_at': row[8] if len(row) > 8 else None,
                        'updated_at': row[9] if len(row) > 9 else None
                    }
                # ID 디버깅
                if row_dict.get('id') is None:
                    print(f'[경고] 스케줄 ID가 None입니다. Row: {row}, Dict: {row_dict}')
                result.append(row_dict)
            return result
        finally:
            conn.close()


def get_all_schedules() -> List[Dict]:
    """전체 스케쥴 조회 (관리자용)"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute('''
                SELECT * FROM schedules 
                ORDER BY start_date DESC, created_at DESC
            ''')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            cursor.close()
            conn.close()
    else:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT id, company_name, title, start_date, end_date, 
                       event_description, request_note, schedule_type, 
                       created_at, updated_at
                FROM schedules 
                ORDER BY start_date DESC, created_at DESC
            ''')
            rows = cursor.fetchall()
            result = []
            for row in rows:
                # SQLite Row 객체를 명시적으로 딕셔너리로 변환
                row_dict = {}
                if hasattr(row, 'keys'):
                    # Row 객체인 경우
                    for key in row.keys():
                        row_dict[key] = row[key]
                    # ID가 없거나 None인 경우 row[0]에서 가져오기
                    if 'id' not in row_dict or row_dict['id'] is None:
                        row_dict['id'] = row[0] if len(row) > 0 else None
                else:
                    # 튜플인 경우
                    row_dict = {
                        'id': row[0] if len(row) > 0 else None,
                        'company_name': row[1] if len(row) > 1 else None,
                        'title': row[2] if len(row) > 2 else None,
                        'start_date': row[3] if len(row) > 3 else None,
                        'end_date': row[4] if len(row) > 4 else None,
                        'event_description': row[5] if len(row) > 5 else None,
                        'request_note': row[6] if len(row) > 6 else None,
                        'schedule_type': row[7] if len(row) > 7 else None,
                        'created_at': row[8] if len(row) > 8 else None,
                        'updated_at': row[9] if len(row) > 9 else None
                    }
                # ID 디버깅
                if row_dict.get('id') is None:
                    print(f'[경고] 스케줄 ID가 None입니다. Row: {row}, Dict: {row_dict}')
                result.append(row_dict)
            return result
        finally:
            conn.close()


def get_schedules_by_date_range(start_date: str, end_date: str) -> List[Dict]:
    """날짜 범위로 스케쥴 조회 (달력용)"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute('''
                SELECT * FROM schedules 
                WHERE (start_date <= %s AND end_date >= %s)
                   OR (start_date BETWEEN %s AND %s)
                   OR (end_date BETWEEN %s AND %s)
                ORDER BY start_date ASC, company_name ASC
            ''', (end_date, start_date, start_date, end_date, start_date, end_date))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            cursor.close()
            conn.close()
    else:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT id, company_name, title, start_date, end_date, 
                       event_description, request_note, schedule_type, 
                       created_at, updated_at
                FROM schedules 
                WHERE (start_date <= ? AND end_date >= ?)
                   OR (start_date BETWEEN ? AND ?)
                   OR (end_date BETWEEN ? AND ?)
                ORDER BY start_date ASC, company_name ASC
            ''', (end_date, start_date, start_date, end_date, start_date, end_date))
            rows = cursor.fetchall()
            result = []
            for row in rows:
                # SQLite Row 객체를 명시적으로 딕셔너리로 변환
                row_dict = {}
                if hasattr(row, 'keys'):
                    # Row 객체인 경우
                    for key in row.keys():
                        row_dict[key] = row[key]
                    # ID가 없거나 None인 경우 row[0]에서 가져오기
                    if 'id' not in row_dict or row_dict['id'] is None:
                        row_dict['id'] = row[0] if len(row) > 0 else None
                else:
                    # 튜플인 경우
                    row_dict = {
                        'id': row[0] if len(row) > 0 else None,
                        'company_name': row[1] if len(row) > 1 else None,
                        'title': row[2] if len(row) > 2 else None,
                        'start_date': row[3] if len(row) > 3 else None,
                        'end_date': row[4] if len(row) > 4 else None,
                        'event_description': row[5] if len(row) > 5 else None,
                        'request_note': row[6] if len(row) > 6 else None,
                        'schedule_type': row[7] if len(row) > 7 else None,
                        'created_at': row[8] if len(row) > 8 else None,
                        'updated_at': row[9] if len(row) > 9 else None
                    }
                # ID 디버깅
                if row_dict.get('id') is None:
                    print(f'[경고] 스케줄 ID가 None입니다. Row: {row}, Dict: {row_dict}')
                result.append(row_dict)
            return result
        finally:
            conn.close()


def get_schedule_by_id(schedule_id: int) -> Optional[Dict]:
    """스케쥴 ID로 조회"""
    from datetime import datetime, date
    
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute('SELECT * FROM schedules WHERE id = %s', (schedule_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            result = dict(row)
            # 날짜 형식 변환 (YYYY-MM-DD 형식으로)
            if result.get('start_date'):
                start_date = result['start_date']
                if isinstance(start_date, (datetime, date)):
                    result['start_date'] = start_date.strftime('%Y-%m-%d')
                elif isinstance(start_date, str):
                    # 이미 문자열이면 그대로 사용 (YYYY-MM-DD 형식이어야 함)
                    if 'T' in start_date:
                        result['start_date'] = start_date.split('T')[0]
                    elif ' ' in start_date:
                        result['start_date'] = start_date.split(' ')[0]
            
            if result.get('end_date'):
                end_date = result['end_date']
                if isinstance(end_date, (datetime, date)):
                    result['end_date'] = end_date.strftime('%Y-%m-%d')
                elif isinstance(end_date, str):
                    # 이미 문자열이면 그대로 사용 (YYYY-MM-DD 형식이어야 함)
                    if 'T' in end_date:
                        result['end_date'] = end_date.split('T')[0]
                    elif ' ' in end_date:
                        result['end_date'] = end_date.split(' ')[0]
            
            return result
        finally:
            cursor.close()
            conn.close()
    else:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM schedules WHERE id = ?', (schedule_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            result = dict(row)
            # 날짜 형식 변환 (YYYY-MM-DD 형식으로)
            if result.get('start_date'):
                start_date = result['start_date']
                if isinstance(start_date, str):
                    if 'T' in start_date:
                        result['start_date'] = start_date.split('T')[0]
                    elif ' ' in start_date:
                        result['start_date'] = start_date.split(' ')[0]
            
            if result.get('end_date'):
                end_date = result['end_date']
                if isinstance(end_date, str):
                    if 'T' in end_date:
                        result['end_date'] = end_date.split('T')[0]
                    elif ' ' in end_date:
                        result['end_date'] = end_date.split(' ')[0]
            
            return result
        finally:
            conn.close()


def update_schedule(schedule_id: int, schedule_data: Dict) -> bool:
    """스케쥴 수정"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE schedules SET
                    title = %s,
                    start_date = %s,
                    end_date = %s,
                    event_description = %s,
                    request_note = %s,
                    schedule_type = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (
                schedule_data.get('title'),
                schedule_data.get('start_date'),
                schedule_data.get('end_date'),
                schedule_data.get('event_description'),
                schedule_data.get('request_note'),
                schedule_data.get('schedule_type'),
                schedule_id
            ))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"스케쥴 수정 오류: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE schedules SET
                    title = ?,
                    start_date = ?,
                    end_date = ?,
                    event_description = ?,
                    request_note = ?,
                    schedule_type = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                schedule_data.get('title'),
                schedule_data.get('start_date'),
                schedule_data.get('end_date'),
                schedule_data.get('event_description'),
                schedule_data.get('request_note'),
                schedule_data.get('schedule_type'),
                schedule_id
            ))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"스케쥴 수정 오류: {e}")
            return False
        finally:
            conn.close()


def delete_schedule(schedule_id: int, role: str = '관리자', company_name: str = '') -> bool:
    """스케쥴 삭제"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            # 삭제 전 스케줄 정보 확인
            cursor.execute('SELECT id, title, company_name, start_date, end_date, schedule_type FROM schedules WHERE id = %s', (schedule_id,))
            before = cursor.fetchone()
            
            if not before:
                print(f'[경고] 삭제할 스케줄을 찾을 수 없습니다: id={schedule_id}')
                return False
            
            schedule_type = before.get('schedule_type', '')
            title = before.get('title', '')
            start_date = before.get('start_date', '')
            end_date = before.get('end_date', '')
            
            print(f'🔍 삭제 전 스케줄 확인: id={schedule_id}, title={title}, company={before.get("company_name")}, type={schedule_type}')
            
            # "모든화주사" 타입인지 확인
            is_all_companies = schedule_type and (schedule_type.startswith('모든화주사') or schedule_type == '모든화주사')
            
            if is_all_companies:
                if role == '관리자':
                    # 관리자 모드: "모든화주사" 타입의 모든 스케줄 일괄 삭제
                    print(f'🔍 관리자 모드 - "모든화주사" 타입 스케줄 일괄 삭제: title={title}, start={start_date}, end={end_date}')
                    cursor.execute('''
                        DELETE FROM schedules 
                        WHERE title = %s 
                        AND start_date = %s 
                        AND end_date = %s
                        AND (schedule_type LIKE '모든화주사%%' OR schedule_type = '모든화주사')
                    ''', (title, start_date, end_date))
                    conn.commit()
                    deleted_count = cursor.rowcount
                    print(f'[성공] "모든화주사" 스케줄 일괄 삭제 성공: 삭제된 행 수={deleted_count}')
                    return deleted_count > 0
                else:
                    # 화주사 모드: 본인의 스케줄만 삭제
                    print(f'🔍 화주사 모드 - 본인 스케줄만 삭제: company={company_name}, title={title}, start={start_date}, end={end_date}')
                    cursor.execute('''
                        DELETE FROM schedules 
                        WHERE company_name = %s
                        AND title = %s 
                        AND start_date = %s 
                        AND end_date = %s
                        AND (schedule_type LIKE '모든화주사%%' OR schedule_type = '모든화주사')
                    ''', (company_name, title, start_date, end_date))
                    conn.commit()
                    deleted_count = cursor.rowcount
                    print(f'[성공] 화주사 스케줄 삭제 성공: company={company_name}, 삭제된 행 수={deleted_count}')
                    return deleted_count > 0
            else:
                # 일반 스케줄: ID로 삭제
                cursor.execute('DELETE FROM schedules WHERE id = %s', (schedule_id,))
                conn.commit()
                deleted_count = cursor.rowcount
                print(f'[성공] 스케줄 삭제 성공: id={schedule_id}, 삭제된 행 수={deleted_count}')
                return deleted_count > 0
        except Exception as e:
            print(f"스케쥴 삭제 오류: {e}")
            import traceback
            traceback.print_exc()
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            # ID 타입 확인 및 변환
            schedule_id_int = int(schedule_id)
            print(f'🔍 삭제 시도: schedule_id={schedule_id} (타입: {type(schedule_id)}, 변환: {schedule_id_int})')
            
            # 삭제 전 확인 - 모든 ID 타입으로 검색
            cursor.execute('SELECT id, title, company_name, start_date, end_date, schedule_type, rowid FROM schedules WHERE id = ?', (schedule_id_int,))
            before = cursor.fetchone()
            
            if not before:
                # 문자열로도 시도
                cursor.execute('SELECT id, title, company_name, start_date, end_date, schedule_type, rowid FROM schedules WHERE CAST(id AS TEXT) = ?', (str(schedule_id),))
                before = cursor.fetchone()
            
            if before:
                before_dict = dict(before) if hasattr(before, 'keys') else before
                schedule_type = before_dict.get('schedule_type', '')
                title = before_dict.get('title', '')
                start_date = before_dict.get('start_date', '')
                end_date = before_dict.get('end_date', '')
                
                print(f'🔍 삭제 전 스케줄 확인: id={before_dict.get("id")}, title={title}, company={before_dict.get("company_name")}, type={schedule_type}')
                
                # "모든화주사" 타입인지 확인
                is_all_companies = schedule_type and (schedule_type.startswith('모든화주사') or schedule_type == '모든화주사')
                
                if is_all_companies:
                    if role == '관리자':
                        # 관리자 모드: "모든화주사" 타입의 모든 스케줄 일괄 삭제
                        print(f'🔍 관리자 모드 - "모든화주사" 타입 스케줄 일괄 삭제: title={title}, start={start_date}, end={end_date}')
                        cursor.execute('''
                            DELETE FROM schedules 
                            WHERE title = ? 
                            AND start_date = ? 
                            AND end_date = ?
                            AND (schedule_type LIKE '모든화주사%' OR schedule_type = '모든화주사')
                        ''', (title, start_date, end_date))
                        conn.commit()
                        deleted_count = cursor.rowcount
                        print(f'[성공] "모든화주사" 스케줄 일괄 삭제 성공: 삭제된 행 수={deleted_count}')
                        return deleted_count > 0
                    else:
                        # 화주사 모드: 본인의 스케줄만 삭제
                        print(f'🔍 화주사 모드 - 본인 스케줄만 삭제: company={company_name}, title={title}, start={start_date}, end={end_date}')
                        cursor.execute('''
                            DELETE FROM schedules 
                            WHERE company_name = ?
                            AND title = ? 
                            AND start_date = ? 
                            AND end_date = ?
                            AND (schedule_type LIKE '모든화주사%' OR schedule_type = '모든화주사')
                        ''', (company_name, title, start_date, end_date))
                        conn.commit()
                        deleted_count = cursor.rowcount
                        print(f'[성공] 화주사 스케줄 삭제 성공: company={company_name}, 삭제된 행 수={deleted_count}')
                        return deleted_count > 0
                else:
                    # 일반 스케줄: rowid로 삭제 (더 확실함)
                    rowid = before_dict.get('rowid')
                    if rowid:
                        cursor.execute('DELETE FROM schedules WHERE rowid = ?', (rowid,))
                        conn.commit()
                        deleted_count = cursor.rowcount
                        print(f'🔍 rowid로 삭제 시도: rowid={rowid}, 삭제된 행 수={deleted_count}')
                    else:
                        # rowid가 없으면 ID로 삭제
                        cursor.execute('DELETE FROM schedules WHERE id = ?', (schedule_id_int,))
                        conn.commit()
                        deleted_count = cursor.rowcount
                        print(f'🔍 id로 삭제 시도: id={schedule_id_int}, 삭제된 행 수={deleted_count}')
                    
                    # 삭제 후 확인
                    if rowid:
                        cursor.execute('SELECT id FROM schedules WHERE rowid = ?', (rowid,))
                    else:
                        cursor.execute('SELECT id FROM schedules WHERE id = ?', (schedule_id_int,))
                    after = cursor.fetchone()
                    
                    if deleted_count > 0:
                        print(f'✅ 스케줄 삭제 성공: id={schedule_id_int}, 삭제된 행 수={deleted_count}')
                        if after:
                            print(f'[경고] 경고: 삭제 후에도 스케줄이 존재합니다!')
                        return True
                    else:
                        print(f'[오류] 스케줄 삭제 실패: id={schedule_id_int}, 삭제된 행 수={deleted_count}')
                        return False
            else:
                print(f'[경고] 삭제할 스케줄을 찾을 수 없습니다: id={schedule_id} (int: {schedule_id_int})')
                # 모든 스케줄 ID 확인 (디버깅용)
                cursor.execute('SELECT id, title, company_name FROM schedules LIMIT 5')
                all_schedules = cursor.fetchall()
                print(f'🔍 현재 스케줄 샘플: {[dict(s) if hasattr(s, "keys") else s for s in all_schedules]}')
                return False
        except Exception as e:
            print(f"스케쥴 삭제 오류: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            conn.close()


# ========== 팝업 관리 관련 함수 ==========

def create_popup(popup_data: Dict) -> int:
    """팝업 생성"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO popups (title, content, image_url, width, height, start_date, end_date, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                popup_data.get('title'),
                popup_data.get('content'),
                popup_data.get('image_url'),
                popup_data.get('width', 600),
                popup_data.get('height', 400),
                popup_data.get('start_date'),
                popup_data.get('end_date'),
                popup_data.get('is_active', True)
            ))
            conn.commit()
            row = cursor.fetchone()
            return row[0] if row else 0
        except Exception as e:
            print(f"팝업 생성 오류: {e}")
            conn.rollback()
            return 0
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO popups (title, content, image_url, width, height, start_date, end_date, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                popup_data.get('title'),
                popup_data.get('content'),
                popup_data.get('image_url'),
                popup_data.get('width', 600),
                popup_data.get('height', 400),
                popup_data.get('start_date'),
                popup_data.get('end_date'),
                1 if popup_data.get('is_active', True) else 0
            ))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"팝업 생성 오류: {e}")
            return 0
        finally:
            conn.close()


def get_all_popups() -> List[Dict]:
    """모든 팝업 조회"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute('''
                SELECT * FROM popups 
                ORDER BY start_date DESC, created_at DESC
            ''')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT * FROM popups 
                ORDER BY start_date DESC, created_at DESC
            ''')
            rows = cursor.fetchall()
            # SQLite Row 객체를 딕셔너리로 변환
            result = []
            for idx, row in enumerate(rows):
                if hasattr(row, 'keys'):
                    # 먼저 dict(row)로 변환
                    row_dict = dict(row)
                    
                    # Row 객체의 키 확인
                    row_keys = list(row_dict.keys())
                    
                    # id 필드를 찾아서 설정
                    # 1. 먼저 'id' 키가 있는지 확인
                    if 'id' in row_dict:
                        # id가 있지만 None이면 row[0] 사용
                        if row_dict['id'] is None and len(row) > 0:
                            row_dict['id'] = row[0]
                    else:
                        # id 키가 없으면 row[0] 사용 (SELECT b.id as id가 첫 번째 컬럼)
                        if len(row) > 0:
                            row_dict['id'] = row[0]
                        else:
                            # row[0]도 없으면 None
                            row_dict['id'] = None
                    
                    # 디버깅: 첫 번째 게시글만 로그 출력
                    if idx == 0:
                        print(f"🔍 게시글 Row 변환 - Row 키: {row_keys}")
                        print(f"🔍 게시글 Row 변환 - row[0] 값: {row[0] if len(row) > 0 else 'N/A'}")
                        print(f"🔍 게시글 Row 변환 - Dict 키: {list(row_dict.keys())}")
                        print(f"🔍 게시글 Row 변환 - 최종 id: {row_dict.get('id')}, 타입: {type(row_dict.get('id'))}")
                    result.append(row_dict)
                else:
                    # 튜플인 경우 (row_factory가 설정되지 않은 경우)
                    result.append({
                        'id': row[0] if len(row) > 0 else None,
                        'category_id': row[1] if len(row) > 1 else None,
                        'title': row[2] if len(row) > 2 else None,
                        'content': row[3] if len(row) > 3 else None,
                        'author_name': row[4] if len(row) > 4 else None,
                        'author_role': row[5] if len(row) > 5 else None,
                        'is_pinned': row[6] if len(row) > 6 else None,
                        'view_count': row[7] if len(row) > 7 else None,
                        'created_at': row[8] if len(row) > 8 else None,
                        'updated_at': row[9] if len(row) > 9 else None,
                        'category_name': row[10] if len(row) > 10 else None
                    })
            return result
        finally:
            conn.close()


def get_active_popup() -> Optional[Dict]:
    """현재 날짜에 활성화된 팝업 조회"""
    from datetime import date
    today = date.today().isoformat()
    
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute('''
                SELECT * FROM popups 
                WHERE is_active = TRUE 
                AND start_date <= %s 
                AND end_date >= %s
                ORDER BY created_at DESC
                LIMIT 1
            ''', (today, today))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT * FROM popups 
                WHERE is_active = 1 
                AND start_date <= ? 
                AND end_date >= ?
                ORDER BY created_at DESC
                LIMIT 1
            ''', (today, today))
            row = cursor.fetchone()
            # SQLite Row 객체를 딕셔너리로 변환
            return {key: row[key] for key in row.keys()} if row else None
        finally:
            conn.close()


def get_popup_by_id(popup_id: int) -> Optional[Dict]:
    """팝업 ID로 조회"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute('SELECT * FROM popups WHERE id = %s', (popup_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM popups WHERE id = ?', (popup_id,))
            row = cursor.fetchone()
            # SQLite Row 객체를 딕셔너리로 변환
            return {key: row[key] for key in row.keys()} if row else None
        finally:
            conn.close()


def update_popup(popup_id: int, popup_data: Dict) -> bool:
    """팝업 수정"""
    conn = get_db_connection()
    
    updates = []
    params = []
    
    if 'title' in popup_data:
        updates.append('title = %s' if USE_POSTGRESQL else 'title = ?')
        params.append(popup_data['title'])
    if 'content' in popup_data:
        updates.append('content = %s' if USE_POSTGRESQL else 'content = ?')
        params.append(popup_data['content'])
    if 'start_date' in popup_data:
        updates.append('start_date = %s' if USE_POSTGRESQL else 'start_date = ?')
        params.append(popup_data['start_date'])
    if 'end_date' in popup_data:
        updates.append('end_date = %s' if USE_POSTGRESQL else 'end_date = ?')
        params.append(popup_data['end_date'])
    if 'image_url' in popup_data:
        updates.append('image_url = %s' if USE_POSTGRESQL else 'image_url = ?')
        params.append(popup_data['image_url'])
    if 'width' in popup_data:
        updates.append('width = %s' if USE_POSTGRESQL else 'width = ?')
        params.append(popup_data['width'])
    if 'height' in popup_data:
        updates.append('height = %s' if USE_POSTGRESQL else 'height = ?')
        params.append(popup_data['height'])
    if 'is_active' in popup_data:
        if USE_POSTGRESQL:
            updates.append('is_active = %s')
            params.append(popup_data['is_active'])
        else:
            updates.append('is_active = ?')
            params.append(1 if popup_data['is_active'] else 0)
    
    if not updates:
        return False
    
    updates.append('updated_at = CURRENT_TIMESTAMP')
    params.append(popup_id)
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                UPDATE popups 
                SET {', '.join(updates)}
                WHERE id = %s
            ''', params)
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"팝업 수정 오류: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                UPDATE popups 
                SET {', '.join(updates)}
                WHERE id = ?
            ''', params)
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"팝업 수정 오류: {e}")
            return False
        finally:
            conn.close()


def delete_popup(popup_id: int) -> bool:
    """팝업 삭제"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM popups WHERE id = %s', (popup_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"팝업 삭제 오류: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM popups WHERE id = ?', (popup_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"팝업 삭제 오류: {e}")
            return False
        finally:
            conn.close()


# ========== 헤더 배너 관리 관련 함수 ==========

def create_header_banner(banner_data: Dict) -> int:
    """헤더 배너 아이템 생성"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            insert_data = (
                banner_data.get('text', ''),
                banner_data.get('link_type', 'none'),
                banner_data.get('board_post_id'),
                banner_data.get('is_active', True),
                banner_data.get('display_order', 0),
                banner_data.get('text_color', '#2d3436'),
                banner_data.get('bg_color', '#fff9e6')
            )
            
            print(f"[헤더 배너 생성] PostgreSQL - 입력 데이터: {insert_data}")
            
            cursor.execute('''
                INSERT INTO header_banners (text, link_type, board_post_id, is_active, display_order, text_color, bg_color)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', insert_data)
            
            banner_id = cursor.fetchone()[0]
            conn.commit()
            print(f"[헤더 배너 생성] PostgreSQL - 생성된 ID: {banner_id}")
            return banner_id
        except Exception as e:
            import traceback
            print(f"❌ 헤더 배너 생성 오류: {e}")
            print(f"상세 오류: {traceback.format_exc()}")
            conn.rollback()
            return 0
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            # SQLite에서 FOREIGN KEY 활성화 (연결마다 필요)
            cursor.execute('PRAGMA foreign_keys = ON')
            
            cursor.execute('''
                INSERT INTO header_banners (text, link_type, board_post_id, is_active, display_order, text_color, bg_color)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                banner_data.get('text', ''),
                banner_data.get('link_type', 'none'),
                banner_data.get('board_post_id'),
                1 if banner_data.get('is_active', True) else 0,
                banner_data.get('display_order', 0),
                banner_data.get('text_color', '#2d3436'),
                banner_data.get('bg_color', '#fff9e6')
            ))
            conn.commit()
            banner_id = cursor.lastrowid
            print(f"[헤더 배너 생성] SQLite - 생성된 ID: {banner_id}")
            return banner_id
        except Exception as e:
            import traceback
            print(f"❌ 헤더 배너 생성 오류: {e}")
            print(f"상세 오류: {traceback.format_exc()}")
            try:
                conn.rollback()
            except:
                pass
            return 0
        finally:
            conn.close()


def get_all_header_banners() -> List[Dict]:
    """모든 헤더 배너 조회"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute('''
                SELECT * FROM header_banners 
                ORDER BY display_order ASC, created_at ASC
            ''')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT * FROM header_banners 
                ORDER BY display_order ASC, created_at ASC
            ''')
            rows = cursor.fetchall()
            result = []
            for row in rows:
                if hasattr(row, 'keys'):
                    row_dict = dict(row)
                    # SQLite는 BOOLEAN을 INTEGER로 저장하므로 변환
                    if 'is_active' in row_dict:
                        row_dict['is_active'] = bool(row_dict['is_active'])
                    result.append(row_dict)
                else:
                    result.append({
                        'id': row[0],
                        'text': row[1],
                        'link_type': row[2],
                        'board_post_id': row[3],
                        'is_active': bool(row[4]),
                        'display_order': row[5],
                        'text_color': row[6],
                        'bg_color': row[7],
                        'created_at': row[8],
                        'updated_at': row[9]
                    })
            return result
        finally:
            conn.close()


def get_active_header_banners() -> List[Dict]:
    """활성화된 헤더 배너만 조회"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute('''
                SELECT * FROM header_banners 
                WHERE is_active = TRUE
                ORDER BY display_order ASC, created_at ASC
            ''')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT * FROM header_banners 
                WHERE is_active = 1
                ORDER BY display_order ASC, created_at ASC
            ''')
            rows = cursor.fetchall()
            result = []
            for row in rows:
                if hasattr(row, 'keys'):
                    row_dict = dict(row)
                    row_dict['is_active'] = bool(row_dict['is_active'])
                    result.append(row_dict)
                else:
                    result.append({
                        'id': row[0],
                        'text': row[1],
                        'link_type': row[2],
                        'board_post_id': row[3],
                        'is_active': True,
                        'display_order': row[5],
                        'text_color': row[6],
                        'bg_color': row[7],
                        'created_at': row[8],
                        'updated_at': row[9]
                    })
            return result
        finally:
            conn.close()


def get_header_banner_by_id(banner_id: int) -> Optional[Dict]:
    """헤더 배너 ID로 조회"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute('SELECT * FROM header_banners WHERE id = %s', (banner_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM header_banners WHERE id = ?', (banner_id,))
            row = cursor.fetchone()
            if not row:
                return None
            if hasattr(row, 'keys'):
                row_dict = dict(row)
                row_dict['is_active'] = bool(row_dict['is_active'])
                return row_dict
            else:
                return {
                    'id': row[0],
                    'text': row[1],
                    'link_type': row[2],
                    'board_post_id': row[3],
                    'is_active': bool(row[4]),
                    'display_order': row[5],
                    'text_color': row[6],
                    'bg_color': row[7],
                    'created_at': row[8],
                    'updated_at': row[9]
                }
        finally:
            conn.close()


def update_header_banner(banner_id: int, banner_data: Dict) -> bool:
    """헤더 배너 수정"""
    conn = get_db_connection()
    
    updates = []
    params = []
    
    if 'text' in banner_data:
        updates.append('text = %s' if USE_POSTGRESQL else 'text = ?')
        params.append(banner_data['text'])
    if 'link_type' in banner_data:
        updates.append('link_type = %s' if USE_POSTGRESQL else 'link_type = ?')
        params.append(banner_data['link_type'])
    if 'board_post_id' in banner_data:
        updates.append('board_post_id = %s' if USE_POSTGRESQL else 'board_post_id = ?')
        params.append(banner_data['board_post_id'])
    if 'is_active' in banner_data:
        if USE_POSTGRESQL:
            updates.append('is_active = %s')
            params.append(banner_data['is_active'])
        else:
            updates.append('is_active = ?')
            params.append(1 if banner_data['is_active'] else 0)
    if 'display_order' in banner_data:
        updates.append('display_order = %s' if USE_POSTGRESQL else 'display_order = ?')
        params.append(banner_data['display_order'])
    if 'text_color' in banner_data:
        updates.append('text_color = %s' if USE_POSTGRESQL else 'text_color = ?')
        params.append(banner_data['text_color'])
    if 'bg_color' in banner_data:
        updates.append('bg_color = %s' if USE_POSTGRESQL else 'bg_color = ?')
        params.append(banner_data['bg_color'])
    
    if not updates:
        return False
    
    updates.append('updated_at = CURRENT_TIMESTAMP')
    params.append(banner_id)
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                UPDATE header_banners 
                SET {', '.join(updates)}
                WHERE id = %s
            ''', params)
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"헤더 배너 수정 오류: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                UPDATE header_banners 
                SET {', '.join(updates)}
                WHERE id = ?
            ''', params)
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"헤더 배너 수정 오류: {e}")
            return False
        finally:
            conn.close()


def delete_header_banner(banner_id: int) -> bool:
    """헤더 배너 삭제"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM header_banners WHERE id = %s', (banner_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"헤더 배너 삭제 오류: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM header_banners WHERE id = ?', (banner_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"헤더 배너 삭제 오류: {e}")
            return False
        finally:
            conn.close()


# ========== 스케줄 타입 관리 함수들 ==========

def create_schedule_type(name: str, display_order: int = 0) -> Tuple[int, Optional[str]]:
    """스케줄 타입 생성

    Returns:
        tuple[int, Optional[str]]: (생성된 타입 ID, 오류 메시지)
        - 성공 시 (type_id, None)
        - 실패 시 (0, 오류 메시지)
    """
    conn = get_db_connection()
    
    # 이름 정규화 (공백 제거, 대소문자 통일)
    normalized_name = name.strip()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            print(f'📝 [create_schedule_type] PostgreSQL 모드, 타입명: "{normalized_name}"')
            
            # 먼저 중복 체크 (대소문자 무시, 공백 무시)
            cursor.execute('''
                SELECT id, name FROM schedule_types 
                WHERE TRIM(LOWER(name)) = TRIM(LOWER(%s))
            ''', (normalized_name,))
            existing = cursor.fetchone()
            
            if existing:
                message = f"스케줄 타입 중복: '{normalized_name}' (기존: '{existing[1]}')"
                print(f"❌ [create_schedule_type] {message}")
                return 0, message
            
            print(f'✅ [create_schedule_type] 중복 없음, INSERT 시도: "{normalized_name}"')
            
            cursor.execute('''
                INSERT INTO schedule_types (name, display_order)
                VALUES (%s, %s)
                RETURNING id
            ''', (normalized_name, display_order))
            
            # RETURNING 결과는 commit 전에 가져와야 함
            row = cursor.fetchone()
            type_id = row[0] if row else 0
            
            print(f'📝 [create_schedule_type] INSERT 결과: type_id={type_id}')
            
            conn.commit()
            print(f'✅ [create_schedule_type] 커밋 완료: type_id={type_id}')
            
            return type_id, None
        except Exception as e:
            error_msg = str(e).lower()
            import traceback
            traceback.print_exc()
            if 'unique' in error_msg or 'duplicate' in error_msg:
                print(f"스케줄 타입 중복 (UNIQUE 제약조건): '{normalized_name}' - {e}")
            else:
                print(f"스케줄 타입 생성 오류: '{normalized_name}' - {e}")
                print(f"전체 에러: {traceback.format_exc()}")
            conn.rollback()
            return 0, str(e)
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            print(f'📝 [create_schedule_type] SQLite 모드, 타입명: "{normalized_name}"')
            
            # 먼저 중복 체크 (대소문자 무시, 공백 무시)
            cursor.execute('''
                SELECT id, name FROM schedule_types 
                WHERE TRIM(LOWER(name)) = TRIM(LOWER(?))
            ''', (normalized_name,))
            existing = cursor.fetchone()
            
            if existing:
                message = f"스케줄 타입 중복: '{normalized_name}' (기존: '{existing[1]}')"
                print(f"❌ [create_schedule_type] {message}")
                return 0, message
            
            print(f'✅ [create_schedule_type] 중복 없음, INSERT 시도: "{normalized_name}"')
            
            cursor.execute('''
                INSERT INTO schedule_types (name, display_order)
                VALUES (?, ?)
            ''', (normalized_name, display_order))
            
            type_id = cursor.lastrowid
            print(f'📝 [create_schedule_type] INSERT 결과: type_id={type_id}')
            
            conn.commit()
            print(f'✅ [create_schedule_type] 커밋 완료: type_id={type_id}')
            
            return type_id, None
        except Exception as e:
            error_msg = str(e).lower()
            import traceback
            traceback.print_exc()
            if 'unique' in error_msg or 'duplicate' in error_msg:
                print(f"스케줄 타입 중복 (UNIQUE 제약조건): '{normalized_name}' - {e}")
            else:
                print(f"스케줄 타입 생성 오류: '{normalized_name}' - {e}")
                print(f"전체 에러: {traceback.format_exc()}")
            return 0, str(e)
        finally:
            conn.close()


def get_all_schedule_types() -> List[Dict]:
    """모든 스케줄 타입 조회"""
    conn = get_db_connection()
    
    try:
        if USE_POSTGRESQL:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            try:
                cursor.execute('''
                    SELECT * FROM schedule_types 
                    ORDER BY display_order ASC, created_at ASC
                ''')
                rows = cursor.fetchall()
                result = []
                for row in rows:
                    row_dict = dict(row)
                    # datetime 객체를 문자열로 변환
                    for key, value in row_dict.items():
                        if isinstance(value, datetime):
                            row_dict[key] = value.strftime('%Y-%m-%d %H:%M:%S') if value else None
                    result.append(row_dict)
                return result
            finally:
                cursor.close()
                conn.close()
        else:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    SELECT * FROM schedule_types 
                    ORDER BY display_order ASC, created_at ASC
                ''')
                rows = cursor.fetchall()
                result = []
                for row in rows:
                    if hasattr(row, 'keys'):
                        row_dict = dict(row)
                    else:
                        row_dict = {
                            'id': row[0],
                            'name': row[1],
                            'display_order': row[2],
                            'created_at': row[3],
                            'updated_at': row[4] if len(row) > 4 else None
                        }
                    result.append(row_dict)
                return result
            finally:
                conn.close()
    except Exception as e:
        print(f"[경고] schedule_types 테이블이 없거나 조회 중 오류: {e}")
        # 테이블이 없으면 기본 타입 반환
        default_types = ['입고', '출고', '행사', '연휴', '기타']
        return [{'id': i+1, 'name': name, 'display_order': i} for i, name in enumerate(default_types)]


def delete_schedule_type(type_id: int) -> bool:
    """스케줄 타입 삭제"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM schedule_types WHERE id = %s', (type_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"스케줄 타입 삭제 오류: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM schedule_types WHERE id = ?', (type_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"스케줄 타입 삭제 오류: {e}")
            return False
        finally:
            conn.close()