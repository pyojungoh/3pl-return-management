"""
SQLite 데이터베이스 모델
"""
import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict

# 데이터베이스 파일 경로
# Vercel serverless 환경에서는 /tmp 디렉토리 사용 (쓰기 가능)
# 로컬에서는 프로젝트 루트 디렉토리 사용
if os.environ.get('VERCEL'):
    # Vercel 환경: /tmp 디렉토리 사용 (쓰기 가능)
    DB_PATH = os.path.join('/tmp', 'data.db')
else:
    # 로컬 환경: 프로젝트 루트 디렉토리 사용
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    DB_PATH = os.path.join(project_root, 'data.db')


def get_db_connection():
    """데이터베이스 연결 가져오기"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 딕셔너리 형태로 결과 반환
    return conn


def init_db():
    """데이터베이스 초기화 (테이블 생성)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
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
    except sqlite3.OperationalError:
        pass  # 컬럼이 이미 있으면 무시
    
    try:
        cursor.execute('ALTER TABLE companies ADD COLUMN business_name TEXT')
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute('ALTER TABLE companies ADD COLUMN business_address TEXT')
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute('ALTER TABLE companies ADD COLUMN business_tel TEXT')
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute('ALTER TABLE companies ADD COLUMN business_email TEXT')
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute('ALTER TABLE companies ADD COLUMN business_certificate_url TEXT')
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute('ALTER TABLE companies ADD COLUMN last_login TIMESTAMP')
    except sqlite3.OperationalError:
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
    
    # 인덱스 생성 (검색 속도 향상)
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
    conn.close()
    print("✅ 데이터베이스 초기화 완료")


def get_company_by_username(username: str) -> Optional[Dict]:
    """화주사 계정 조회"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM companies WHERE username = ?
    ''', (username,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None


def get_all_companies() -> List[Dict]:
    """모든 화주사 계정 조회"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, company_name, username, role, 
               business_number, business_name, business_address, 
               business_tel, business_email, business_certificate_url,
               last_login, created_at, updated_at
        FROM companies
        ORDER BY created_at DESC
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def create_company(company_name: str, username: str, password: str, role: str = '화주사',
                  business_number: str = None, business_name: str = None,
                  business_address: str = None, business_tel: str = None,
                  business_email: str = None, business_certificate_url: str = None):
    """화주사 계정 생성"""
    conn = get_db_connection()
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
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def update_company_password(username: str, old_password: str, new_password: str) -> bool:
    """화주사 비밀번호 변경"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 기존 비밀번호 확인
        cursor.execute('''
            SELECT password FROM companies WHERE username = ?
        ''', (username,))
        
        row = cursor.fetchone()
        if not row or row[0] != old_password:
            return False
        
        # 비밀번호 변경
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
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            DELETE FROM companies WHERE id = ?
        ''', (company_id,))
        
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
    cursor = conn.cursor()
    
    try:
        # 관리자 수
        cursor.execute('''
            SELECT COUNT(*) FROM companies WHERE role = '관리자'
        ''')
        admin_count = cursor.fetchone()[0]
        
        # 화주사 수
        cursor.execute('''
            SELECT COUNT(*) FROM companies WHERE role = '화주사' OR role IS NULL OR role = ''
        ''')
        company_count = cursor.fetchone()[0]
        
        # 전체 수
        cursor.execute('''
            SELECT COUNT(*) FROM companies
        ''')
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
    cursor = conn.cursor()
    
    try:
        # 업데이트할 필드만 업데이트
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
    
    # YYYY-MM-DD 형식에서 일자 추출
    if '-' in date_str:
        parts = date_str.split('-')
        if len(parts) >= 3:
            try:
                return int(parts[-1])
            except ValueError:
                return 0
    # MM/DD 형식에서 일자 추출
    elif '/' in date_str:
        parts = date_str.split('/')
        if len(parts) >= 2:
            try:
                return int(parts[-1])
            except ValueError:
                return 0
    # 숫자만 있는 경우 (일자만)
    elif date_str.isdigit():
        return int(date_str)
    # 기타 형식은 0 반환
    return 0


def get_returns_by_company(company: str, month: str, role: str = '화주사') -> List[Dict]:
    """화주사별 반품 데이터 조회 (최신 날짜부터 정렬)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if role == '관리자':
        # 관리자는 모든 데이터 조회
        cursor.execute('''
            SELECT * FROM returns 
            WHERE month = ?
        ''', (month,))
    else:
        # 화주사는 자신의 데이터만 조회
        cursor.execute('''
            SELECT * FROM returns 
            WHERE company_name = ? AND month = ?
        ''', (company, month))
    
    rows = cursor.fetchall()
    conn.close()
    
    # Python에서 날짜를 파싱하여 정렬
    result = [dict(row) for row in rows]
    
    # 날짜를 기준으로 정렬 (최신 날짜부터)
    result.sort(key=lambda x: (
        # 날짜가 없으면 맨 아래로 (True가 뒤로 감)
        not x.get('return_date') or x.get('return_date') == '',
        # 일자 숫자로 정렬 (내림차순)
        -extract_day_number(x.get('return_date', '')),
        # ID로 정렬 (내림차순)
        -x.get('id', 0)
    ))
    
    return result


def get_available_months() -> List[str]:
    """사용 가능한 월 목록 조회 (년도-월 형식, 현재 년월 포함)"""
    from datetime import datetime
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 데이터베이스에서 월 목록 가져오기
    cursor.execute('''
        SELECT DISTINCT month FROM returns 
        ORDER BY month DESC
    ''')
    
    rows = cursor.fetchall()
    db_months = [row[0] for row in rows]
    
    # 현재 년월 가져오기
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    current_month_str = f"{current_year}년{current_month}월"
    
    # 현재 월이 없으면 추가
    if current_month_str not in db_months:
        db_months.append(current_month_str)
    
    # 다음 월 자동 생성 (12월이면 다음 해 1월)
    next_month = current_month + 1
    next_year = current_year
    if next_month > 12:
        next_month = 1
        next_year = current_year + 1
    next_month_str = f"{next_year}년{next_month}월"
    
    # 다음 월이 없으면 자동 추가 (항상 추가)
    if next_month_str not in db_months:
        db_months.append(next_month_str)
    
    conn.close()
    
    # 년도별로 정렬 (최신 년도가 먼저)
    def parse_month(month_str):
        """월 문자열을 파싱해서 (년도, 월) 튜플 반환"""
        try:
            if '년' in month_str and '월' in month_str:
                year_part = month_str.split('년')[0]
                month_part = month_str.split('년')[1].split('월')[0]
                return (int(year_part), int(month_part))
        except:
            pass
        return (0, 0)
    
    # 정렬: 년도 내림차순, 월 내림차순
    db_months.sort(key=parse_month, reverse=True)
    
    return db_months


def save_client_request(return_id: int, request_text: str) -> bool:
    """화주사 요청사항 저장"""
    conn = get_db_connection()
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
    cursor = conn.cursor()
    
    try:
        # completed 컬럼에 이름만 저장하고, client_confirmed에도 이름만 저장
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
    except sqlite3.IntegrityError:
        # 중복 데이터인 경우 업데이트
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
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM returns WHERE id = ?
    ''', (return_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None


def update_memo(return_id: int, memo: str) -> bool:
    """비고 업데이트"""
    conn = get_db_connection()
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
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            DELETE FROM returns WHERE id = ?
        ''', (return_id,))
        
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
    cursor = conn.cursor()
    
    try:
        # 송장번호 정규화 (공백, 하이픈 제거)
        tracking_normalized = tracking_number.replace(' ', '').replace('-', '').strip()
        
        # 정확한 송장번호로 검색
        cursor.execute('''
            SELECT * FROM returns 
            WHERE month = ? AND (
                tracking_number = ? OR
                REPLACE(REPLACE(tracking_number, ' ', ''), '-', '') = ?
            )
        ''', (month, tracking_number.strip(), tracking_normalized))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
        
    except Exception as e:
        print(f"송장번호 검색 오류: {e}")
        conn.close()
        return None


def update_photo_links(return_id: int, photo_links: str) -> bool:
    """사진 링크 업데이트"""
    conn = get_db_connection()
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

