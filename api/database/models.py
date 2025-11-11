"""
PostgreSQL 데이터베이스 모델 (Neon Postgres)
DATABASE_URL 환경 변수가 있으면 PostgreSQL 사용, 없으면 SQLite 사용 (호환성)
"""
import os
from datetime import datetime
from typing import Optional, List, Dict

# 데이터베이스 연결 문자열
DATABASE_URL = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')

# PostgreSQL 사용 여부 확인
USE_POSTGRESQL = bool(DATABASE_URL)

if USE_POSTGRESQL:
    # PostgreSQL 사용
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from psycopg2 import IntegrityError, OperationalError
    print("✅ PostgreSQL 데이터베이스 사용 (Neon)")
else:
    # SQLite 사용 (로컬 개발용)
    import sqlite3
    # 데이터베이스 파일 경로
    if os.environ.get('VERCEL'):
        DB_PATH = os.path.join('/tmp', 'data.db')
    else:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        DB_PATH = os.path.join(project_root, 'data.db')
    print("⚠️ SQLite 데이터베이스 사용 (로컬)")


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
                    conn = psycopg2.connect(DATABASE_URL + '&sslmode=require')
                else:
                    conn = psycopg2.connect(DATABASE_URL + '?sslmode=require')
            else:
                conn = psycopg2.connect(DATABASE_URL)
            return conn
        except Exception as e:
            print(f"❌ PostgreSQL 연결 오류: {e}")
            raise
    else:
        # SQLite 연결
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
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
                    last_login TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
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
        
        conn.commit()
        print("✅ 데이터베이스 초기화 완료")
    
    except Exception as e:
        print(f"❌ 데이터베이스 초기화 오류: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
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
            return dict(row) if row else None
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
                       last_login, created_at, updated_at
                FROM companies
                ORDER BY created_at DESC
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
                SELECT id, company_name, username, role, 
                       business_number, business_name, business_address, 
                       business_tel, business_email, business_certificate_url,
                       last_login, created_at, updated_at
                FROM companies
                ORDER BY created_at DESC
            ''')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()


def create_company(company_name: str, username: str, password: str, role: str = '화주사',
                  business_number: str = None, business_name: str = None,
                  business_address: str = None, business_tel: str = None,
                  business_email: str = None, business_certificate_url: str = None):
    """화주사 계정 생성"""
    conn = get_db_connection()
    
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
            return True
        except IntegrityError:
            conn.rollback()
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
            return True
        except IntegrityError:
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
                       business_tel: str = None, business_email: str = None) -> bool:
    """화주사 정보 업데이트 (사업자 정보)"""
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


def get_returns_by_company(company: str, month: str, role: str = '화주사') -> List[Dict]:
    """화주사별 반품 데이터 조회 (최신 날짜부터 정렬)"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            if role == '관리자':
                cursor.execute('SELECT * FROM returns WHERE month = %s', (month,))
            else:
                cursor.execute('SELECT * FROM returns WHERE company_name = %s AND month = %s', (company, month))
            rows = cursor.fetchall()
            result = [dict(row) for row in rows]
            
            result.sort(key=lambda x: (
                not x.get('return_date') or x.get('return_date') == '',
                -extract_day_number(x.get('return_date', '')),
                -x.get('id', 0)
            ))
            return result
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            if role == '관리자':
                cursor.execute('SELECT * FROM returns WHERE month = ?', (month,))
            else:
                cursor.execute('SELECT * FROM returns WHERE company_name = ? AND month = ?', (company, month))
            rows = cursor.fetchall()
            result = [dict(row) for row in rows]
            
            result.sort(key=lambda x: (
                not x.get('return_date') or x.get('return_date') == '',
                -extract_day_number(x.get('return_date', '')),
                -x.get('id', 0)
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
            # 중복 데이터인 경우 업데이트
            conn.rollback()
            cursor.execute('''
                UPDATE returns SET
                    return_date = %s,
                    company_name = %s,
                    product = %s,
                    return_type = %s,
                    stock_status = %s,
                    inspection = %s,
                    completed = %s,
                    memo = %s,
                    photo_links = %s,
                    other_courier = %s,
                    shipping_fee = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE customer_name = %s AND tracking_number = %s AND month = %s
                RETURNING id
            ''', (
                return_data.get('return_date'),
                return_data.get('company_name'),
                return_data.get('product'),
                return_data.get('return_type'),
                return_data.get('stock_status'),
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
            return cursor.lastrowid
        except IntegrityError:
            cursor.execute('''
                UPDATE returns SET
                    return_date = ?,
                    company_name = ?,
                    product = ?,
                    return_type = ?,
                    stock_status = ?,
                    inspection = ?,
                    completed = ?,
                    memo = ?,
                    photo_links = ?,
                    other_courier = ?,
                    shipping_fee = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE customer_name = ? AND tracking_number = ? AND month = ?
            ''', (
                return_data.get('return_date'),
                return_data.get('company_name'),
                return_data.get('product'),
                return_data.get('return_type'),
                return_data.get('stock_status'),
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
            return row[0] if row else 0
        except Exception as e:
            print(f"반품 데이터 생성 오류: {e}")
            return 0
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


def find_return_by_tracking_number(tracking_number: str, month: str) -> Optional[Dict]:
    """송장번호로 반품 데이터 찾기 (QR 코드 검색용)"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            tracking_normalized = tracking_number.replace(' ', '').replace('-', '').strip()
            cursor.execute('''
                SELECT * FROM returns 
                WHERE month = %s AND (
                    tracking_number = %s OR
                    REPLACE(REPLACE(tracking_number, ' ', ''), '-', '') = %s
                )
            ''', (month, tracking_number.strip(), tracking_normalized))
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
            cursor.execute('''
                SELECT * FROM returns 
                WHERE month = ? AND (
                    tracking_number = ? OR
                    REPLACE(REPLACE(tracking_number, ' ', ''), '-', '') = ?
                )
            ''', (month, tracking_number.strip(), tracking_normalized))
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
            return True
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
            return True
        except Exception as e:
            print(f"사진 링크 업데이트 오류: {e}")
            return False
        finally:
            conn.close()
