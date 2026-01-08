"""
파레트 보관료 관리 시스템 - 데이터베이스 함수
"""
import os
import math
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Tuple
from api.database.models import get_db_connection, USE_POSTGRESQL

# ========================================
# 파레트 관리 함수
# ========================================

def generate_pallet_id(in_date: date = None) -> str:
    """
    파레트 ID 자동 생성 (년월일_001 형식)
    
    Args:
        in_date: 입고일 (없으면 현재일, date 객체 또는 문자열)
    
    Returns:
        파레트 ID (str, 예: "251226_001")
    """
    if in_date is None:
        in_date = date.today()
    elif isinstance(in_date, str):
        # 문자열이면 date 객체로 변환
        try:
            in_date = datetime.strptime(in_date, '%Y-%m-%d').date()
        except ValueError:
            # 변환 실패 시 오늘 날짜 사용
            in_date = date.today()
    
    date_str = in_date.strftime("%y%m%d")
    
    # 같은 날짜에 입고된 파레트 개수 확인
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRESQL:
            cursor.execute('''
                SELECT COUNT(*) FROM pallets 
                WHERE pallet_id LIKE %s
            ''', (f"{date_str}_%",))
        else:
            cursor.execute('''
                SELECT COUNT(*) FROM pallets 
                WHERE pallet_id LIKE ?
            ''', (f"{date_str}_%",))
        
        count = cursor.fetchone()[0]
        sequence = count + 1
        
        return f"{date_str}_{str(sequence).zfill(3)}"
    finally:
        cursor.close()
        conn.close()


def create_pallet(pallet_id: str = None, company_name: str = None,
                 product_name: str = None, in_date: date = None,
                 storage_location: str = None, quantity: int = 1,
                 is_service: bool = False, notes: str = None,
                 created_by: str = None) -> Tuple[bool, str, Optional[Dict]]:
    """
    파레트 입고 처리
    
    Returns:
        (success, message, data)
    """
    # in_date가 문자열이면 date 객체로 변환
    if in_date is None:
        in_date = date.today()
    elif isinstance(in_date, str):
        try:
            in_date = datetime.strptime(in_date, '%Y-%m-%d').date()
        except ValueError:
            return False, f"입고일 형식이 올바르지 않습니다: {in_date}", None
    
    if pallet_id is None:
        pallet_id = generate_pallet_id(in_date)
    
    # 디버깅: 요청받은 pallet_id 로깅
    print(f"[DEBUG] create_pallet 호출 - pallet_id: {pallet_id}, company_name: {company_name}")
    
    # 중복 체크 (INSERT 전에 미리 확인)
    existing_pallet = get_pallet_by_id(pallet_id)
    if existing_pallet:
        print(f"[DEBUG] 중복 체크 실패 - pallet_id {pallet_id}가 이미 존재함")
        return False, f"파레트 ID가 이미 존재합니다: {pallet_id}", None
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        print(f"[DEBUG] INSERT 시도 - pallet_id: {pallet_id}")
        if USE_POSTGRESQL:
            cursor.execute('''
                INSERT INTO pallets (
                    pallet_id, company_name, product_name, status,
                    in_date, storage_location, quantity, is_service,
                    notes, created_by, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (pallet_id, company_name, product_name, '입고됨',
                  in_date, storage_location, quantity, 1 if is_service else 0,
                  notes, created_by))
            
            # 트랜잭션 이력 저장
            cursor.execute('''
                INSERT INTO pallet_transactions (
                    pallet_id, transaction_type, quantity, transaction_date,
                    processed_by, notes, created_at
                ) VALUES (%s, %s, %s, CURRENT_TIMESTAMP, %s, %s, CURRENT_TIMESTAMP)
            ''', (pallet_id, '입고', quantity, created_by, notes))
        else:
            cursor.execute('''
                INSERT INTO pallets (
                    pallet_id, company_name, product_name, status,
                    in_date, storage_location, quantity, is_service,
                    notes, created_by, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (pallet_id, company_name, product_name, '입고됨',
                  in_date, storage_location, quantity, 1 if is_service else 0,
                  notes, created_by))
            
            # 트랜잭션 이력 저장
            cursor.execute('''
                INSERT INTO pallet_transactions (
                    pallet_id, transaction_type, quantity, transaction_date,
                    processed_by, notes, created_at
                ) VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?, CURRENT_TIMESTAMP)
            ''', (pallet_id, '입고', quantity, created_by, notes))
        
        conn.commit()
        
        # 생성된 파레트 정보 조회
        pallet = get_pallet_by_id(pallet_id)
        
        print(f"[DEBUG] INSERT 성공 - pallet_id: {pallet_id}")
        return True, "파레트 입고 완료", pallet
    except Exception as e:
        conn.rollback() if USE_POSTGRESQL else None
        error_msg = str(e)
        error_msg_lower = error_msg.lower()
        print(f"[DEBUG] INSERT 실패 - pallet_id: {pallet_id}, 오류: {error_msg}")
        
        if 'unique' in error_msg_lower or 'duplicate' in error_msg_lower:
            # 요청한 pallet_id를 명확히 사용 (데이터베이스 오류 메시지의 ID가 아닌)
            print(f"[DEBUG] UNIQUE 제약 조건 위반 - 요청한 pallet_id: {pallet_id}")
            return False, f"파레트 ID가 이미 존재합니다: {pallet_id}", None
        print(f"[DEBUG] 기타 오류 - pallet_id: {pallet_id}, 오류: {error_msg}")
        return False, f"파레트 입고 실패: {error_msg}", None
    finally:
        cursor.close()
        conn.close()


def update_pallet_status(pallet_id: str, out_date: date = None,
                        processed_by: str = None, notes: str = None) -> Tuple[bool, str, Optional[Dict]]:
    """
    파레트 보관종료 처리
    
    Returns:
        (success, message, data)
    """
    if out_date is None:
        out_date = date.today()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 파레트 정보 조회
        pallet = get_pallet_by_id(pallet_id)
        if not pallet:
            return False, "파레트를 찾을 수 없습니다", None
        
        if pallet['status'] == '보관종료':
            return False, "이미 보관종료된 파레트입니다", None
        
        # 보관종료 처리
        if USE_POSTGRESQL:
            cursor.execute('''
                UPDATE pallets 
                SET status = %s, out_date = %s, updated_at = CURRENT_TIMESTAMP
                WHERE pallet_id = %s
            ''', ('보관종료', out_date, pallet_id))
            
            # 트랜잭션 이력 저장
            cursor.execute('''
                INSERT INTO pallet_transactions (
                    pallet_id, transaction_type, quantity, transaction_date,
                    processed_by, notes, created_at
                ) VALUES (%s, %s, %s, CURRENT_TIMESTAMP, %s, %s, CURRENT_TIMESTAMP)
            ''', (pallet_id, '보관종료', pallet.get('quantity', 1), processed_by, notes))
        else:
            cursor.execute('''
                UPDATE pallets 
                SET status = ?, out_date = ?, updated_at = CURRENT_TIMESTAMP
                WHERE pallet_id = ?
            ''', ('보관종료', out_date, pallet_id))
            
            # 트랜잭션 이력 저장
            cursor.execute('''
                INSERT INTO pallet_transactions (
                    pallet_id, transaction_type, quantity, transaction_date,
                    processed_by, notes, created_at
                ) VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?, CURRENT_TIMESTAMP)
            ''', (pallet_id, '보관종료', pallet.get('quantity', 1), processed_by, notes))
        
        conn.commit()
        
        # 업데이트된 파레트 정보 조회
        updated_pallet = get_pallet_by_id(pallet_id)
        
        return True, "파레트 보관종료 완료", updated_pallet
    except Exception as e:
        conn.rollback() if USE_POSTGRESQL else None
        return False, f"보관종료 처리 실패: {str(e)}", None
    finally:
        cursor.close()
        conn.close()


def update_pallet_status_batch(pallet_ids: List[str], out_date: date = None, processed_by: str = None, notes: str = None) -> Dict:
    """
    파레트 보관종료 대량 처리
    
    Args:
        pallet_ids: 파레트 ID 리스트
        out_date: 보관종료일 (없으면 오늘)
        processed_by: 처리자
        notes: 비고
    
    Returns:
        {
            'success_count': int,
            'failed_count': int,
            'processed': List[str],
            'failed': List[str],
            'errors': List[str]
        }
    """
    if out_date is None:
        out_date = date.today()
    
    if not pallet_ids or len(pallet_ids) == 0:
        return {
            'success_count': 0,
            'failed_count': 0,
            'processed': [],
            'failed': [],
            'errors': ['파레트 ID가 없습니다.']
        }
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    processed = []
    failed = []
    errors = []
    
    try:
        for pallet_id in pallet_ids:
            try:
                # 파레트 정보 조회
                pallet = get_pallet_by_id(pallet_id)
                if not pallet:
                    failed.append(pallet_id)
                    errors.append(f'{pallet_id}: 파레트를 찾을 수 없습니다')
                    continue
                
                if pallet['status'] == '보관종료':
                    failed.append(pallet_id)
                    errors.append(f'{pallet_id}: 이미 보관종료된 파레트입니다')
                    continue
                
                # 보관종료 처리
                if USE_POSTGRESQL:
                    cursor.execute('''
                        UPDATE pallets 
                        SET status = %s, out_date = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE pallet_id = %s
                    ''', ('보관종료', out_date, pallet_id))
                    
                    # 트랜잭션 이력 저장
                    cursor.execute('''
                        INSERT INTO pallet_transactions (
                            pallet_id, transaction_type, quantity, transaction_date,
                            processed_by, notes, created_at
                        ) VALUES (%s, %s, %s, CURRENT_TIMESTAMP, %s, %s, CURRENT_TIMESTAMP)
                    ''', (pallet_id, '보관종료', pallet.get('quantity', 1), processed_by, notes))
                else:
                    cursor.execute('''
                        UPDATE pallets 
                        SET status = ?, out_date = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE pallet_id = ?
                    ''', ('보관종료', out_date, pallet_id))
                    
                    # 트랜잭션 이력 저장
                    cursor.execute('''
                        INSERT INTO pallet_transactions (
                            pallet_id, transaction_type, quantity, transaction_date,
                            processed_by, notes, created_at
                        ) VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?, CURRENT_TIMESTAMP)
                    ''', (pallet_id, '보관종료', pallet.get('quantity', 1), processed_by, notes))
                
                processed.append(pallet_id)
                
            except Exception as e:
                failed.append(pallet_id)
                errors.append(f'{pallet_id}: {str(e)}')
                continue
        
        # 모든 처리 완료 후 커밋
        conn.commit()
        
        return {
            'success_count': len(processed),
            'failed_count': len(failed),
            'processed': processed,
            'failed': failed,
            'errors': errors
        }
        
    except Exception as e:
        conn.rollback() if USE_POSTGRESQL else None
        return {
            'success_count': len(processed),
            'failed_count': len(failed) + (len(pallet_ids) - len(processed) - len(failed)),
            'processed': processed,
            'failed': failed + [pid for pid in pallet_ids if pid not in processed and pid not in failed],
            'errors': errors + [f'대량 처리 중 오류: {str(e)}']
        }
    finally:
        cursor.close()
        conn.close()


def get_pallet_by_id(pallet_id: str) -> Optional[Dict]:
    """
    파레트 상세 조회
    """
    conn = get_db_connection()
    
    try:
        if USE_POSTGRESQL:
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute('SELECT * FROM pallets WHERE pallet_id = %s', (pallet_id,))
        else:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM pallets WHERE pallet_id = ?', (pallet_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        if USE_POSTGRESQL:
            return dict(row)
        else:
            return dict(zip([col[0] for col in cursor.description], row))
    finally:
        cursor.close()
        conn.close()


def delete_pallet(pallet_id: str) -> Tuple[bool, str]:
    """
    파레트 삭제
    
    Returns:
        (success, message)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 파레트 존재 확인
        pallet = get_pallet_by_id(pallet_id)
        if not pallet:
            return False, "파레트를 찾을 수 없습니다."
        
        # 관련 데이터 삭제 (트랜잭션 이력, 보관료 계산 내역)
        if USE_POSTGRESQL:
            # 보관료 계산 내역 삭제
            cursor.execute('DELETE FROM pallet_fee_calculations WHERE pallet_id = %s', (pallet_id,))
            # 트랜잭션 이력 삭제
            cursor.execute('DELETE FROM pallet_transactions WHERE pallet_id = %s', (pallet_id,))
            # 파레트 삭제
            cursor.execute('DELETE FROM pallets WHERE pallet_id = %s', (pallet_id,))
        else:
            # 보관료 계산 내역 삭제
            cursor.execute('DELETE FROM pallet_fee_calculations WHERE pallet_id = ?', (pallet_id,))
            # 트랜잭션 이력 삭제
            cursor.execute('DELETE FROM pallet_transactions WHERE pallet_id = ?', (pallet_id,))
            # 파레트 삭제
            cursor.execute('DELETE FROM pallets WHERE pallet_id = ?', (pallet_id,))
        
        conn.commit()
        return True, "파레트가 삭제되었습니다."
    except Exception as e:
        conn.rollback() if USE_POSTGRESQL else None
        return False, f"파레트 삭제 실패: {str(e)}"
    finally:
        cursor.close()
        conn.close()


def get_pallets(company_name: str = None, status: str = None,
                month: str = None, role: str = '화주사',
                pallet_id: str = None, product_name: str = None) -> List[Dict]:
    """
    파레트 목록 조회
    
    Args:
        company_name: 화주사명 (화주사인 경우 필수)
        status: 상태 필터 (입고됨, 보관종료, 서비스, 전체)
        month: 월 필터 (YYYY-MM 형식)
        role: 권한 (관리자, 화주사)
        pallet_id: 파레트 ID 부분 일치 검색 (LIKE 검색)
        product_name: 품목명 부분 일치 검색 (LIKE 검색)
    """
    conn = get_db_connection()
    
    try:
        if USE_POSTGRESQL:
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        query = "SELECT * FROM pallets WHERE 1=1"
        params = []
        
        # 화주사 필터링
        if role != '관리자' and company_name:
            if USE_POSTGRESQL:
                query += " AND company_name = %s"
            else:
                query += " AND company_name = ?"
            params.append(company_name)
        elif company_name:
            if USE_POSTGRESQL:
                query += " AND company_name = %s"
            else:
                query += " AND company_name = ?"
            params.append(company_name)
        
        # 상태 필터링
        if status and status != '전체':
            if USE_POSTGRESQL:
                query += " AND status = %s"
            else:
                query += " AND status = ?"
            params.append(status)
        
        # 파레트 ID 부분 일치 검색 (LIKE)
        if pallet_id and pallet_id.strip():
            if USE_POSTGRESQL:
                query += " AND pallet_id LIKE %s"
            else:
                query += " AND pallet_id LIKE ?"
            params.append(f'%{pallet_id.strip()}%')
        
        # 품목명 부분 일치 검색 (LIKE)
        if product_name and product_name.strip():
            if USE_POSTGRESQL:
                query += " AND product_name LIKE %s"
            else:
                query += " AND product_name LIKE ?"
            params.append(f'%{product_name.strip()}%')
        
        # 월 필터링
        if month:
            year, month_num = map(int, month.split('-'))
            start_date = date(year, month_num, 1)
            if month_num == 12:
                end_date = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(year, month_num + 1, 1) - timedelta(days=1)
            
            if USE_POSTGRESQL:
                query += " AND in_date <= %s AND (out_date IS NULL OR out_date >= %s)"
            else:
                query += " AND in_date <= ? AND (out_date IS NULL OR out_date >= ?)"
            params.extend([end_date, start_date])
        
        query += " ORDER BY in_date DESC, pallet_id DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        if USE_POSTGRESQL:
            return [dict(row) for row in rows]
        else:
            return [dict(zip([col[0] for col in cursor.description], row)) for row in rows]
    finally:
        cursor.close()
        conn.close()


# ========================================
# 보관료 계산 함수
# ========================================

def get_monthly_fee(company_name: str, as_of_date: date = None) -> int:
    """
    화주사별 월 보관료 조회
    
    Returns:
        월 보관료 (원, int), 기본값: 16000
    """
    if as_of_date is None:
        as_of_date = date.today()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRESQL:
            cursor.execute('''
                SELECT monthly_fee FROM pallet_fees
                WHERE company_name = %s AND effective_from <= %s
                ORDER BY effective_from DESC
                LIMIT 1
            ''', (company_name, as_of_date))
        else:
            cursor.execute('''
                SELECT monthly_fee FROM pallet_fees
                WHERE company_name = ? AND effective_from <= ?
                ORDER BY effective_from DESC
                LIMIT 1
            ''', (company_name, as_of_date))
        
        row = cursor.fetchone()
        if row:
            return int(row[0])
        
        return 16000  # 기본값
    finally:
        cursor.close()
        conn.close()


def calculate_daily_fee(company_name: str, as_of_date: date = None) -> float:
    """
    일일 보관료 계산
    
    ✅ 수정: 월 보관료를 30일로 나누어 30일 보관 시 정확히 월 보관료가 되도록 함
    
    Returns:
        일일 보관료 (float)
    """
    monthly_fee = get_monthly_fee(company_name, as_of_date)
    daily_fee = monthly_fee / 30.0  # 30일 기준으로 계산 (30일 보관 = 월 보관료)
    return round(daily_fee, 2)


def get_daily_fees_batch(company_names: List[str], as_of_date: date = None) -> Dict[str, float]:
    """
    화주사별 일일 보관료 일괄 조회 (성능 최적화용)
    
    Args:
        company_names: 화주사명 리스트
        as_of_date: 기준일 (선택사항, 없으면 현재일)
    
    Returns:
        화주사별 일일 보관료 딕셔너리 {company_name: daily_fee}
        기본값: 16000원 / 30.0 = 533.33원
    """
    if not company_names:
        return {}
    
    if as_of_date is None:
        as_of_date = date.today()
    
    # 중복 제거
    unique_companies = list(set(company_names))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 모든 화주사의 보관료를 한 번에 조회
        # PostgreSQL: ANY 배열 사용
        # SQLite: IN 절 사용
        if USE_POSTGRESQL:
            cursor.execute('''
                SELECT DISTINCT ON (company_name) company_name, monthly_fee
                FROM pallet_fees
                WHERE company_name = ANY(%s) AND effective_from <= %s
                ORDER BY company_name, effective_from DESC
            ''', (unique_companies, as_of_date))
        else:
            # SQLite: IN 절로 변환
            # 호환성을 위해 서브쿼리 + JOIN 방식 사용 (ROW_NUMBER 대신)
            placeholders = ','.join(['?' for _ in unique_companies])
            params = list(unique_companies) + [as_of_date]
            cursor.execute(f'''
                SELECT pf1.company_name, pf1.monthly_fee
                FROM pallet_fees pf1
                INNER JOIN (
                    SELECT company_name, MAX(effective_from) as max_date
                    FROM pallet_fees
                    WHERE company_name IN ({placeholders}) AND effective_from <= ?
                    GROUP BY company_name
                ) pf2 ON pf1.company_name = pf2.company_name AND pf1.effective_from = pf2.max_date
            ''', params)
        
        rows = cursor.fetchall()
        
        # 딕셔너리로 변환
        result = {}
        for row in rows:
            company_name = row[0]
            monthly_fee = int(row[1])
            daily_fee = monthly_fee / 30.0
            result[company_name] = round(daily_fee, 2)
        
        # 조회되지 않은 화주사는 기본값 사용
        default_daily_fee = round(16000 / 30.0, 2)  # 533.33
        for company_name in unique_companies:
            if company_name not in result:
                result[company_name] = default_daily_fee
        
        return result
    finally:
        cursor.close()
        conn.close()


def calculate_storage_days(in_date: date, out_date: date = None,
                          as_of_date: date = None) -> int:
    """
    보관일수 계산
    
    Returns:
        보관일수 (int)
    """
    if as_of_date is None:
        as_of_date = date.today()
    
    end_date = out_date if out_date else as_of_date
    storage_days = (end_date - in_date).days + 1
    return max(0, storage_days)


def calculate_fee(company_name: str, in_date: date, out_date: date = None,
                 is_service: bool = False, as_of_date: date = None) -> int:
    """
    보관료 계산 (백원 단위 올림)
    
    Returns:
        보관료 (원, int, 백원 단위 올림)
    """
    if is_service:
        return 0
    
    daily_fee = calculate_daily_fee(company_name, as_of_date)
    storage_days = calculate_storage_days(in_date, out_date, as_of_date)
    calculated_fee = daily_fee * storage_days
    rounded_fee = math.ceil(calculated_fee / 100) * 100
    
    return int(rounded_fee)


# ========================================
# 화주사별 보관료 설정 함수
# ========================================

def get_pallet_fee(company_name: str) -> Optional[Dict]:
    """
    화주사별 보관료 설정 조회
    """
    conn = get_db_connection()
    
    try:
        if USE_POSTGRESQL:
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute('''
                SELECT * FROM pallet_fees
                WHERE company_name = %s
                ORDER BY effective_from DESC
                LIMIT 1
            ''', (company_name,))
        else:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM pallet_fees
                WHERE company_name = ?
                ORDER BY effective_from DESC
                LIMIT 1
            ''', (company_name,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        if USE_POSTGRESQL:
            return dict(row)
        else:
            return dict(zip([col[0] for col in cursor.description], row))
    finally:
        cursor.close()
        conn.close()


def set_pallet_fee(company_name: str, monthly_fee: int,
                  effective_from: date = None, notes: str = None) -> Tuple[bool, str]:
    """
    화주사별 보관료 설정 생성/수정
    
    Returns:
        (success, message)
    """
    if effective_from is None:
        effective_from = date.today()
    
    daily_fee = round(monthly_fee / 30.0, 2)  # 30일 기준으로 계산 (30일 보관 = 월 보관료)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRESQL:
            cursor.execute('''
                INSERT INTO pallet_fees (
                    company_name, monthly_fee, daily_fee, effective_from,
                    notes, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (company_name) 
                DO UPDATE SET 
                    monthly_fee = EXCLUDED.monthly_fee,
                    daily_fee = EXCLUDED.daily_fee,
                    effective_from = EXCLUDED.effective_from,
                    notes = EXCLUDED.notes,
                    updated_at = CURRENT_TIMESTAMP
            ''', (company_name, monthly_fee, daily_fee, effective_from, notes))
        else:
            cursor.execute('''
                INSERT OR REPLACE INTO pallet_fees (
                    company_name, monthly_fee, daily_fee, effective_from,
                    notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (company_name, monthly_fee, daily_fee, effective_from, notes))
        
        conn.commit()
        return True, "보관료 설정 완료"
    except Exception as e:
        conn.rollback() if USE_POSTGRESQL else None
        return False, f"보관료 설정 실패: {str(e)}"
    finally:
        cursor.close()
        conn.close()


# ========================================
# 월별 정산 함수
# ========================================

def get_settlement_month(target_date: date = None) -> str:
    """
    정산월 계산 (YYYY-MM 형식)
    
    Args:
        target_date: 기준일 (없으면 현재일)
    
    Returns:
        정산월 (str, 예: "2025-01")
    """
    if target_date is None:
        target_date = date.today()
    
    # 다음달 초에 전월 정산 생성
    # 예: 2월 1일이면 1월 정산 생성
    settlement_month = target_date.replace(day=1) - timedelta(days=1)
    
    return settlement_month.strftime("%Y-%m")


def get_pallets_for_settlement(company_name: str = None,
                              start_date: date = None,
                              end_date: date = None) -> List[Dict]:
    """
    정산 대상 파레트 조회
    
    ✅ 개선사항:
    - 화주사명 정규화 및 해시태그 기능 지원
    - 같은 화주사는 하나로 통합 (TKS 컴퍼니, tks컴퍼니, TKS컴퍼니 → 하나로 통합)
    """
    from api.database.models import normalize_company_name, get_company_search_keywords
    
    conn = get_db_connection()
    
    try:
        if USE_POSTGRESQL:
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        query = "SELECT * FROM pallets WHERE 1=1"
        params = []
        
        # 화주사 필터링 (성능 최적화: DB 레벨에서 필터링)
        if company_name:
            # 단순 문자열 매칭으로 변경 (정규화 로직 제거로 성능 향상)
            # 정산 계산 시에는 정확한 화주사명 매칭만 필요
            if start_date and end_date:
                if USE_POSTGRESQL:
                    cursor.execute('''
                        SELECT id, pallet_id, company_name, product_name, in_date, out_date, 
                               status, is_service, created_at, updated_at
                        FROM pallets 
                        WHERE company_name = %s 
                          AND in_date <= %s 
                          AND (out_date IS NULL OR out_date >= %s)
                        ORDER BY in_date
                    ''', (company_name, end_date, start_date))
                else:
                    cursor.execute('''
                        SELECT id, pallet_id, company_name, product_name, in_date, out_date, 
                               status, is_service, created_at, updated_at
                        FROM pallets 
                        WHERE company_name = ? 
                          AND in_date <= ? 
                          AND (out_date IS NULL OR out_date >= ?)
                        ORDER BY in_date
                    ''', (company_name, end_date, start_date))
            else:
                if USE_POSTGRESQL:
                    cursor.execute('''
                        SELECT id, pallet_id, company_name, product_name, in_date, out_date, 
                               status, is_service, created_at, updated_at
                        FROM pallets 
                        WHERE company_name = %s
                        ORDER BY in_date
                    ''', (company_name,))
                else:
                    cursor.execute('''
                        SELECT id, pallet_id, company_name, product_name, in_date, out_date, 
                               status, is_service, created_at, updated_at
                        FROM pallets 
                        WHERE company_name = ?
                        ORDER BY in_date
                    ''', (company_name,))
            
            rows = cursor.fetchall()
            
            if USE_POSTGRESQL:
                return [dict(row) for row in rows]
            else:
                return [dict(zip([col[0] for col in cursor.description], row)) for row in rows]
        else:
            # 화주사 필터링 없음 (필요한 컬럼만 선택하여 성능 향상)
            if start_date and end_date:
                if USE_POSTGRESQL:
                    cursor.execute('''
                        SELECT id, pallet_id, company_name, product_name, in_date, out_date, 
                               status, is_service, created_at, updated_at
                        FROM pallets 
                        WHERE in_date <= %s AND (out_date IS NULL OR out_date >= %s)
                        ORDER BY company_name, in_date
                    ''', (end_date, start_date))
                else:
                    cursor.execute('''
                        SELECT id, pallet_id, company_name, product_name, in_date, out_date, 
                               status, is_service, created_at, updated_at
                        FROM pallets 
                        WHERE in_date <= ? AND (out_date IS NULL OR out_date >= ?)
                        ORDER BY company_name, in_date
                    ''', (end_date, start_date))
            else:
                if USE_POSTGRESQL:
                    cursor.execute('''
                        SELECT id, pallet_id, company_name, product_name, in_date, out_date, 
                               status, is_service, created_at, updated_at
                        FROM pallets 
                        ORDER BY company_name, in_date
                    ''')
                else:
                    cursor.execute('''
                        SELECT id, pallet_id, company_name, product_name, in_date, out_date, 
                               status, is_service, created_at, updated_at
                        FROM pallets 
                        ORDER BY company_name, in_date
                    ''')
            
            rows = cursor.fetchall()
            
            if USE_POSTGRESQL:
                return [dict(row) for row in rows]
            else:
                return [dict(zip([col[0] for col in cursor.description], row)) for row in rows]
    finally:
        cursor.close()
        conn.close()


def generate_monthly_settlement(settlement_month: str = None,
                                company_name: str = None) -> Tuple[bool, str, Dict]:
    """
    월별 정산 생성
    
    Returns:
        (success, message, data)
    """
    if settlement_month is None:
        settlement_month = get_settlement_month()
    
    # 정산월의 시작일과 종료일 계산
    year, month = map(int, settlement_month.split('-'))
    start_date = date(year, month, 1)
    
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    # 해당 월에 보관했던 모든 파레트 조회
    pallets = get_pallets_for_settlement(company_name, start_date, end_date)
    
    if not pallets:
        return False, "정산할 파레트가 없습니다", {}
    
    # 화주사별로 그룹화 (정규화 및 해시태그 지원)
    from api.database.models import normalize_company_name, get_company_search_keywords
    
    company_settlements = {}
    company_normalized_map = {}  # 정규화된 이름 -> 대표 화주사명 매핑
    
    # 특정 화주사의 정산 생성 시 해당 화주사의 키워드 목록 가져오기
    target_company_keywords = None
    target_company_normalized = None
    if company_name:
        try:
            target_company_keywords = get_company_search_keywords(company_name)
            if not target_company_keywords:
                target_company_keywords = [company_name]
        except Exception as e:
            print(f"[경고] 대상 화주사 '{company_name}' 키워드 조회 실패: {e}")
            target_company_keywords = [company_name]
        target_company_normalized = [normalize_company_name(kw) for kw in target_company_keywords]
    
    for pallet in pallets:
        raw_company = pallet['company_name']
        if not raw_company:
            continue
        
        # 특정 화주사의 정산 생성 시, 해당 화주사의 파레트만 포함
        if company_name:
            pallet_company_normalized = normalize_company_name(raw_company)
            if pallet_company_normalized not in target_company_normalized:
                # 해당 화주사가 아닌 파레트는 건너뜀
                continue
        
        # 정규화된 키워드 목록 가져오기 (본인 이름 + 해시태그)
        try:
            search_keywords = get_company_search_keywords(raw_company)
            if not search_keywords:
                search_keywords = [raw_company]
        except Exception as e:
            print(f"[경고] 화주사 '{raw_company}' 키워드 조회 실패: {e}")
            search_keywords = [raw_company]
        
        normalized_keywords = [normalize_company_name(kw) for kw in search_keywords]
        
        # 대표 화주사명 결정 (이미 매핑된 것이 있으면 사용, 없으면 원본 사용)
        representative_company = raw_company
        for normalized_kw in normalized_keywords:
            if normalized_kw in company_normalized_map:
                representative_company = company_normalized_map[normalized_kw]
                break
        
        # 매핑 업데이트
        for normalized_kw in normalized_keywords:
            if normalized_kw not in company_normalized_map:
                company_normalized_map[normalized_kw] = representative_company
        
        company = representative_company
        
        if company not in company_settlements:
            company_settlements[company] = {
                'total_pallets': 0,
                'total_storage_days': 0,
                'total_fee': 0,
                'pallets': []
            }
        
        # 보관일수 계산 (해당 월 내에서만)
        in_date = pallet['in_date']
        out_date = pallet.get('out_date')
        is_service = pallet.get('is_service', 0) == 1
        
        # 보관 시작일: 입고일과 정산월 시작일 중 늦은 날
        storage_start = max(in_date, start_date)
        
        # 보관 종료일: 보관종료일과 정산월 종료일 중 이른 날 (보관중인 경우 오늘 날짜도 고려)
        if out_date:
            storage_end = min(out_date, end_date)
        else:
            # 보관중인 경우: 정산월 종료일과 오늘 날짜 중 이른 날
            storage_end = min(end_date, date.today())
        
        # 보관일수 계산 (음수 방지)
        storage_days = max(0, (storage_end - storage_start).days + 1)
        
        # 보관료 계산 (파레트별) - 각 파레트의 보관일수에 따라 개별 계산
        if is_service:
            fee = 0
        else:
            daily_fee = calculate_daily_fee(company, storage_start)
            calculated_fee = daily_fee * storage_days
            fee = math.ceil(calculated_fee / 100) * 100
        
        # 정산 데이터에 추가
        # 파레트 개수: 입고중(status='입고됨') 또는 서비스 상태만 카운트
        status = pallet.get('status', '입고됨')
        if status == '입고됨' or is_service:
            company_settlements[company]['total_pallets'] += 1
        company_settlements[company]['total_storage_days'] += storage_days
        # 각 파레트별 보관료를 합산 (파레트 개수로 곱하지 않음)
        company_settlements[company]['total_fee'] += fee
        company_settlements[company]['pallets'].append({
            'pallet_id': pallet['pallet_id'],
            'product_name': pallet.get('product_name'),
            'in_date': in_date,
            'out_date': out_date,
            'storage_days': storage_days,
            'daily_fee': calculate_daily_fee(company, storage_start),
            'rounded_fee': fee,
            'is_service': is_service
        })
    
    # 데이터베이스에 저장
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 정산 생성 전 기존 파레트 상세 데이터 삭제 (중복 방지)
        # 특정 화주사의 정산 생성 시: 해당 화주사의 파레트만 삭제
        # 전체 정산 생성 시: 해당 정산월의 모든 파레트 상세 삭제
        if company_name:
            # 특정 화주사의 정산 생성: 해당 화주사의 파레트만 삭제
            # 정산 내역에서 해당 화주사의 파레트 ID 목록 가져오기
            pallet_ids_to_delete = []
            for settlement in company_settlements.values():
                for pallet_detail in settlement['pallets']:
                    pallet_ids_to_delete.append(pallet_detail['pallet_id'])
            
            if pallet_ids_to_delete:
                if USE_POSTGRESQL:
                    # PostgreSQL: ANY 대신 IN 사용
                    placeholders = ','.join(['%s' for _ in pallet_ids_to_delete])
                    cursor.execute(f'''
                        DELETE FROM pallet_fee_calculations 
                        WHERE settlement_month = %s AND pallet_id IN ({placeholders})
                    ''', [settlement_month] + pallet_ids_to_delete)
                else:
                    placeholders = ','.join(['?' for _ in pallet_ids_to_delete])
                    cursor.execute(f'''
                        DELETE FROM pallet_fee_calculations 
                        WHERE settlement_month = ? AND pallet_id IN ({placeholders})
                    ''', [settlement_month] + pallet_ids_to_delete)
        else:
            # 전체 정산 생성: 해당 정산월의 모든 파레트 상세 삭제
            if USE_POSTGRESQL:
                cursor.execute('DELETE FROM pallet_fee_calculations WHERE settlement_month = %s', (settlement_month,))
            else:
                cursor.execute('DELETE FROM pallet_fee_calculations WHERE settlement_month = ?', (settlement_month,))
        
        for company, settlement in company_settlements.items():
            # 정산 내역 저장
            if USE_POSTGRESQL:
                cursor.execute('''
                    INSERT INTO pallet_monthly_settlements (
                        company_name, settlement_month, total_pallets,
                        total_storage_days, total_fee, status,
                        created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT (company_name, settlement_month)
                    DO UPDATE SET
                        total_pallets = EXCLUDED.total_pallets,
                        total_storage_days = EXCLUDED.total_storage_days,
                        total_fee = EXCLUDED.total_fee,
                        updated_at = CURRENT_TIMESTAMP
                ''', (company, settlement_month, settlement['total_pallets'],
                      settlement['total_storage_days'], settlement['total_fee'], '대기'))
            else:
                cursor.execute('''
                    INSERT OR REPLACE INTO pallet_monthly_settlements (
                        company_name, settlement_month, total_pallets,
                        total_storage_days, total_fee, status,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (company, settlement_month, settlement['total_pallets'],
                      settlement['total_storage_days'], settlement['total_fee'], '대기'))
            
            # 파레트별 보관료 상세 저장
            for pallet_detail in settlement['pallets']:
                if USE_POSTGRESQL:
                    cursor.execute('''
                        INSERT INTO pallet_fee_calculations (
                            pallet_id, settlement_month, storage_days,
                            daily_fee, calculated_fee, rounded_fee,
                            is_service, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT DO NOTHING
                    ''', (pallet_detail['pallet_id'], settlement_month,
                          pallet_detail['storage_days'], pallet_detail['daily_fee'],
                          pallet_detail['rounded_fee'], pallet_detail['rounded_fee'],
                          1 if pallet_detail['is_service'] else 0))
                else:
                    cursor.execute('''
                        INSERT OR IGNORE INTO pallet_fee_calculations (
                            pallet_id, settlement_month, storage_days,
                            daily_fee, calculated_fee, rounded_fee,
                            is_service, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (pallet_detail['pallet_id'], settlement_month,
                          pallet_detail['storage_days'], pallet_detail['daily_fee'],
                          pallet_detail['rounded_fee'], pallet_detail['rounded_fee'],
                          1 if pallet_detail['is_service'] else 0))
        
        # 정산월별 화주사 목록 저장 (성능 최적화)
        # 특정 화주사의 정산 생성 시: 해당 화주사만 삭제 후 재저장
        # 전체 정산 생성 시: 해당 정산월의 모든 화주사 목록 삭제 후 새로 저장
        if company_name:
            # 특정 화주사의 정산 생성: 해당 화주사만 삭제 후 재저장
            # 대상 화주사와 관련된 모든 키워드를 고려하여 삭제
            try:
                target_keywords = get_company_search_keywords(company_name)
                if not target_keywords:
                    target_keywords = [company_name]
            except Exception as e:
                print(f"[경고] 화주사 키워드 조회 실패: {e}")
                target_keywords = [company_name]
            
            # 정규화된 키워드로 해당 화주사 찾기
            target_normalized = [normalize_company_name(kw) for kw in target_keywords]
            
            if USE_POSTGRESQL:
                # 해당 정산월의 모든 화주사 목록 조회
                cursor.execute('SELECT DISTINCT company_name FROM pallet_settlement_companies WHERE settlement_month = %s', (settlement_month,))
                existing_companies = [row[0] for row in cursor.fetchall() if row[0]]
                
                # 정규화된 키워드와 일치하는 화주사만 삭제
                for existing_company in existing_companies:
                    existing_normalized = normalize_company_name(existing_company)
                    if existing_normalized in target_normalized:
                        cursor.execute('DELETE FROM pallet_settlement_companies WHERE settlement_month = %s AND company_name = %s', 
                                     (settlement_month, existing_company))
            else:
                cursor.execute('SELECT DISTINCT company_name FROM pallet_settlement_companies WHERE settlement_month = ?', (settlement_month,))
                existing_companies = [row[0] for row in cursor.fetchall() if row[0]]
                
                for existing_company in existing_companies:
                    existing_normalized = normalize_company_name(existing_company)
                    if existing_normalized in target_normalized:
                        cursor.execute('DELETE FROM pallet_settlement_companies WHERE settlement_month = ? AND company_name = ?', 
                                     (settlement_month, existing_company))
        else:
            # 전체 정산 생성: 해당 정산월의 모든 화주사 목록 삭제 후 새로 저장
            if USE_POSTGRESQL:
                cursor.execute('DELETE FROM pallet_settlement_companies WHERE settlement_month = %s', (settlement_month,))
            else:
                cursor.execute('DELETE FROM pallet_settlement_companies WHERE settlement_month = ?', (settlement_month,))
        
        # 화주사 목록 저장 (ON CONFLICT로 중복 방지)
        for company in company_settlements.keys():
            if USE_POSTGRESQL:
                cursor.execute('''
                    INSERT INTO pallet_settlement_companies (settlement_month, company_name, created_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (settlement_month, company_name) DO NOTHING
                ''', (settlement_month, company))
            else:
                cursor.execute('''
                    INSERT OR IGNORE INTO pallet_settlement_companies (settlement_month, company_name, created_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (settlement_month, company))
        
        conn.commit()
        
        return True, f"정산 생성 완료: {len(company_settlements)}개 화주사", {
            'settlement_month': settlement_month,
            'total_companies': len(company_settlements),
            'total_pallets': sum(s['total_pallets'] for s in company_settlements.values()),
            'total_fee': sum(s['total_fee'] for s in company_settlements.values())
        }
    except Exception as e:
        conn.rollback() if USE_POSTGRESQL else None
        return False, f"정산 생성 실패: {str(e)}", {}
    finally:
        cursor.close()
        conn.close()


def get_settlements(company_name: str = None, settlement_month: str = None,
                   role: str = '화주사') -> List[Dict]:
    """
    월별 정산 내역 조회
    
    ✅ 개선사항:
    - 화주사명 정규화 및 해시태그 기능 지원
    - 같은 화주사는 하나로 통합 (TKS 컴퍼니, tks컴퍼니, TKS컴퍼니 → 하나로 통합)
    """
    from api.database.models import normalize_company_name, get_company_search_keywords
    
    conn = get_db_connection()
    
    try:
        if USE_POSTGRESQL:
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        query = "SELECT * FROM pallet_monthly_settlements WHERE 1=1"
        params = []
        
        # 화주사 필터링 (정규화 및 해시태그 지원)
        if company_name:
            # 검색 가능한 키워드 목록 가져오기 (본인 이름 + 해시태그)
            try:
                search_keywords = get_company_search_keywords(company_name)
                if not search_keywords:
                    search_keywords = [company_name]
            except Exception as e:
                print(f"[경고] 화주사 '{company_name}' 키워드 조회 실패: {e}")
                search_keywords = [company_name]
            
            normalized_keywords = [normalize_company_name(kw) for kw in search_keywords]
            
            # 모든 정산 내역을 가져온 후 필터링
            if settlement_month:
                if USE_POSTGRESQL:
                    cursor.execute('SELECT * FROM pallet_monthly_settlements WHERE settlement_month = %s ORDER BY settlement_month DESC, company_name', (settlement_month,))
                else:
                    cursor.execute('SELECT * FROM pallet_monthly_settlements WHERE settlement_month = ? ORDER BY settlement_month DESC, company_name', (settlement_month,))
            else:
                if USE_POSTGRESQL:
                    cursor.execute('SELECT * FROM pallet_monthly_settlements ORDER BY settlement_month DESC, company_name')
                else:
                    cursor.execute('SELECT * FROM pallet_monthly_settlements ORDER BY settlement_month DESC, company_name')
            
            rows = cursor.fetchall()
            
            # 정규화된 키워드로 필터링
            result = []
            for row in rows:
                if USE_POSTGRESQL:
                    settlement = dict(row)
                else:
                    settlement = dict(zip([col[0] for col in cursor.description], row))
                
                settlement_company_normalized = normalize_company_name(settlement.get('company_name', ''))
                if settlement_company_normalized in normalized_keywords:
                    result.append(settlement)
            
            return result
        else:
            # 화주사 필터링 없음 - 모든 정산 내역 조회 후 정규화하여 통합
            if settlement_month:
                if USE_POSTGRESQL:
                    query += " AND settlement_month = %s"
                else:
                    query += " AND settlement_month = ?"
                params.append(settlement_month)
            
            query += " ORDER BY settlement_month DESC, company_name"
            
            if USE_POSTGRESQL:
                cursor.execute(query, params)
            else:
                cursor.execute(query, params)
            
            rows = cursor.fetchall()
            
            # 모든 정산 내역을 가져온 후 정규화하여 통합
            all_settlements = []
            if USE_POSTGRESQL:
                all_settlements = [dict(row) for row in rows]
            else:
                all_settlements = [dict(zip([col[0] for col in cursor.description], row)) for row in rows]
            
            # 화주사명 정규화 및 통합
            # 1. 각 화주사명에 대해 정규화된 키워드 목록 생성 (본인 이름 + 해시태그)
            company_keywords_map = {}  # 정규화된 키워드 -> 원본 화주사명 매핑
            company_representatives = {}  # 정규화된 키워드 -> 대표 화주사명
            
            for settlement in all_settlements:
                raw_company = settlement.get('company_name', '')
                if not raw_company:
                    continue
                
                # 검색 가능한 키워드 목록 가져오기 (본인 이름 + 해시태그)
                try:
                    keywords = get_company_search_keywords(raw_company)
                    if not keywords:
                        keywords = [raw_company]
                except Exception as e:
                    print(f"[경고] 화주사 '{raw_company}' 키워드 조회 실패: {e}")
                    keywords = [raw_company]
                
                # 각 키워드에 대해 매핑 생성
                normalized_company = normalize_company_name(raw_company)
                
                for keyword in keywords:
                    normalized_keyword = normalize_company_name(keyword)
                    
                    # 이미 다른 화주사가 이 키워드를 사용하고 있는지 확인
                    if normalized_keyword in company_keywords_map:
                        # 기존 대표 화주사명과 비교하여 우선순위 결정 (더 짧거나 알파벳 순서가 앞서는 것)
                        existing_rep = company_representatives[normalized_keyword]
                        if len(raw_company) < len(existing_rep) or (len(raw_company) == len(existing_rep) and raw_company < existing_rep):
                            company_representatives[normalized_keyword] = raw_company
                            company_keywords_map[normalized_keyword] = raw_company
                    else:
                        company_keywords_map[normalized_keyword] = raw_company
                        company_representatives[normalized_keyword] = raw_company
            
            # 2. 각 정산 내역에 대해 대표 화주사명 찾기 및 통합
            merged_settlements = {}  # (settlement_month, representative_company) -> 통합된 정산 내역
            
            for settlement in all_settlements:
                raw_company = settlement.get('company_name', '')
                if not raw_company:
                    continue
                
                normalized = normalize_company_name(raw_company)
                representative = company_representatives.get(normalized, raw_company)
                
                # 정산월과 대표 화주사명으로 키 생성
                settlement_month_key = settlement.get('settlement_month', '')
                merge_key = (settlement_month_key, representative)
                
                if merge_key not in merged_settlements:
                    # 새로운 정산 내역 생성 (대표 화주사명으로)
                    merged_settlement = settlement.copy()
                    merged_settlement['company_name'] = representative
                    merged_settlements[merge_key] = merged_settlement
                else:
                    # 기존 정산 내역에 통합 (파레트 수, 보관일수, 보관료 합산)
                    existing = merged_settlements[merge_key]
                    existing['total_pallets'] = existing.get('total_pallets', 0) + settlement.get('total_pallets', 0)
                    existing['total_storage_days'] = existing.get('total_storage_days', 0) + settlement.get('total_storage_days', 0)
                    existing['total_fee'] = existing.get('total_fee', 0) + settlement.get('total_fee', 0)
            
            # 3. 정렬된 목록 반환
            result = list(merged_settlements.values())
            result.sort(key=lambda x: (x.get('settlement_month') or '', x.get('company_name', '')))
            return result
    finally:
        cursor.close()
        conn.close()


def update_settlement_status(settlement_id: int, status: str) -> Tuple[bool, str]:
    """
    정산 상태 업데이트
    
    Args:
        settlement_id: 정산 ID
        status: 새로운 상태 ('대기', '확정', '완료')
    
    Returns:
        (success, message)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 유효한 상태인지 확인
        valid_statuses = ['대기', '확정', '완료']
        if status not in valid_statuses:
            return False, f"유효하지 않은 상태입니다. 가능한 상태: {', '.join(valid_statuses)}"
        
        # 정산 내역 존재 확인
        if USE_POSTGRESQL:
            cursor.execute('SELECT id FROM pallet_monthly_settlements WHERE id = %s', (settlement_id,))
        else:
            cursor.execute('SELECT id FROM pallet_monthly_settlements WHERE id = ?', (settlement_id,))
        
        if not cursor.fetchone():
            return False, "정산 내역을 찾을 수 없습니다."
        
        # 상태 업데이트
        if USE_POSTGRESQL:
            cursor.execute('''
                UPDATE pallet_monthly_settlements 
                SET status = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (status, settlement_id))
        else:
            cursor.execute('''
                UPDATE pallet_monthly_settlements 
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, settlement_id))
        
        conn.commit()
        return True, f"정산 상태가 '{status}'로 변경되었습니다."
    except Exception as e:
        conn.rollback() if USE_POSTGRESQL else None
        return False, f"정산 상태 업데이트 실패: {str(e)}"
    finally:
        cursor.close()
        conn.close()


def delete_settlement_by_month(settlement_month: str) -> Tuple[bool, str]:
    """
    특정 월의 전체 정산 내역 일괄 삭제
    
    Args:
        settlement_month: 정산월 (YYYY-MM 형식)
    
    Returns:
        (success, message)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 삭제할 정산 내역 개수 확인
        if USE_POSTGRESQL:
            cursor.execute('SELECT COUNT(*) FROM pallet_monthly_settlements WHERE settlement_month = %s', (settlement_month,))
            count = cursor.fetchone()[0]
        else:
            cursor.execute('SELECT COUNT(*) FROM pallet_monthly_settlements WHERE settlement_month = ?', (settlement_month,))
            count = cursor.fetchone()[0]
        
        if count == 0:
            return False, f"{settlement_month} 정산 내역이 없습니다."
        
        # 파레트별 보관료 상세 내역 삭제
        if USE_POSTGRESQL:
            cursor.execute('DELETE FROM pallet_fee_calculations WHERE settlement_month = %s', (settlement_month,))
        else:
            cursor.execute('DELETE FROM pallet_fee_calculations WHERE settlement_month = ?', (settlement_month,))
        
        # 정산월별 화주사 목록 삭제 (성능 최적화 테이블)
        if USE_POSTGRESQL:
            cursor.execute('DELETE FROM pallet_settlement_companies WHERE settlement_month = %s', (settlement_month,))
        else:
            cursor.execute('DELETE FROM pallet_settlement_companies WHERE settlement_month = ?', (settlement_month,))
        
        # 정산 내역 삭제
        if USE_POSTGRESQL:
            cursor.execute('DELETE FROM pallet_monthly_settlements WHERE settlement_month = %s', (settlement_month,))
        else:
            cursor.execute('DELETE FROM pallet_monthly_settlements WHERE settlement_month = ?', (settlement_month,))
        
        conn.commit()
        return True, f"{settlement_month} 정산 내역 {count}개가 삭제되었습니다."
    except Exception as e:
        conn.rollback() if USE_POSTGRESQL else None
        return False, f"정산 일괄 삭제 실패: {str(e)}"
    finally:
        cursor.close()
        conn.close()


def delete_settlement(settlement_id: int) -> Tuple[bool, str]:
    """
    정산 내역 삭제
    
    Args:
        settlement_id: 정산 ID
    
    Returns:
        (success, message)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 정산 내역 존재 확인
        if USE_POSTGRESQL:
            cursor.execute('SELECT id, settlement_month, company_name FROM pallet_monthly_settlements WHERE id = %s', (settlement_id,))
        else:
            cursor.execute('SELECT id, settlement_month, company_name FROM pallet_monthly_settlements WHERE id = ?', (settlement_id,))
        
        row = cursor.fetchone()
        if not row:
            return False, "정산 내역을 찾을 수 없습니다."
        
        if USE_POSTGRESQL:
            settlement_month = row[1]
            company_name_to_delete = row[2]
        else:
            settlement_month = row[1]
            company_name_to_delete = row[2]
        
        # 파레트별 보관료 상세 내역 삭제 (해당 화주사의 파레트만)
        if USE_POSTGRESQL:
            cursor.execute('''
                DELETE FROM pallet_fee_calculations 
                WHERE settlement_month = %s 
                AND pallet_id IN (
                    SELECT pallet_id FROM pallets WHERE company_name = %s
                )
            ''', (settlement_month, company_name_to_delete))
        else:
            cursor.execute('''
                DELETE FROM pallet_fee_calculations 
                WHERE settlement_month = ? 
                AND pallet_id IN (
                    SELECT pallet_id FROM pallets WHERE company_name = ?
                )
            ''', (settlement_month, company_name_to_delete))
        
        # 정산 내역 삭제
        if USE_POSTGRESQL:
            cursor.execute('DELETE FROM pallet_monthly_settlements WHERE id = %s', (settlement_id,))
        else:
            cursor.execute('DELETE FROM pallet_monthly_settlements WHERE id = ?', (settlement_id,))
        
        conn.commit()
        return True, "정산 내역이 삭제되었습니다."
    except Exception as e:
        conn.rollback() if USE_POSTGRESQL else None
        return False, f"정산 내역 삭제 실패: {str(e)}"
    finally:
        cursor.close()
        conn.close()


def get_companies_with_pallets(settlement_month: str = None) -> List[str]:
    """
    파레트를 보관 중인 화주사 목록 조회
    
    ✅ 성능 최적화:
    - 저장된 화주사 목록(`pallet_settlement_companies`) 우선 사용
    - 배치 쿼리로 모든 화주사 키워드를 한 번에 조회 (N+1 문제 해결)
    - 키워드 캐싱으로 중복 쿼리 제거
    
    ✅ 화주사 태그 동기화 지원:
    - search_keywords 필드를 고려하여 동일 화주사 통합
    - "TKS 컴퍼니"와 "TKS컴퍼니" 같은 동일 화주사를 하나로 통합
    
    Args:
        settlement_month: 정산월 (YYYY-MM 형식). 지정되면 해당 월에 보관했던 화주사만 조회
    """
    from api.database.models import normalize_company_name
    
    conn = get_db_connection()
    
    try:
        if USE_POSTGRESQL:
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        # 1단계: 저장된 화주사 목록 우선 사용 (성능 최적화)
        stored_companies = []
        if settlement_month:
            # 지정된 정산월의 화주사 목록 조회
            if USE_POSTGRESQL:
                cursor.execute('''
                    SELECT DISTINCT company_name 
                    FROM pallet_settlement_companies 
                    WHERE settlement_month = %s
                    ORDER BY company_name
                ''', (settlement_month,))
            else:
                cursor.execute('''
                    SELECT DISTINCT company_name 
                    FROM pallet_settlement_companies 
                    WHERE settlement_month = ?
                    ORDER BY company_name
                ''', (settlement_month,))
        else:
            # 정산월이 없으면 모든 정산월의 화주사 목록 합집합 조회
            if USE_POSTGRESQL:
                cursor.execute('''
                    SELECT DISTINCT company_name 
                    FROM pallet_settlement_companies 
                    ORDER BY company_name
                ''')
            else:
                cursor.execute('''
                    SELECT DISTINCT company_name 
                    FROM pallet_settlement_companies 
                    ORDER BY company_name
                ''')
        
        stored_rows = cursor.fetchall()
        if USE_POSTGRESQL:
            stored_companies = [row['company_name'] for row in stored_rows if row.get('company_name')]
        else:
            stored_companies = [row[0] for row in stored_rows if row[0]]
        
        # 저장된 목록이 있으면 그것을 사용 (이미 정산 생성 시 통합되어 있음)
        if stored_companies:
            print(f"[화주사 목록 최적화] 저장된 목록 사용: {len(stored_companies)}개 (정산월: {settlement_month or '전체'})")
            return sorted(stored_companies)
        
        # 2단계: 저장된 목록이 없으면 파레트 테이블에서 조회
        print(f"[화주사 목록] 저장된 목록 없음, 파레트 테이블에서 조회")
        
        # 파레트 테이블에서 화주사명 목록 조회
        if settlement_month:
            # 정산월이 지정된 경우: 해당 월에 보관했던 파레트만 조회
            year, month = map(int, settlement_month.split('-'))
            from datetime import date, timedelta
            month_start = date(year, month, 1)
            if month == 12:
                month_end = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = date(year, month + 1, 1) - timedelta(days=1)
            
            if USE_POSTGRESQL:
                cursor.execute('''
                    SELECT DISTINCT company_name 
                    FROM pallets 
                    WHERE company_name IS NOT NULL AND company_name != ''
                    AND in_date <= %s
                    AND (out_date IS NULL OR out_date >= %s)
                    ORDER BY company_name
                ''', (month_end, month_start))
            else:
                cursor.execute('''
                    SELECT DISTINCT company_name 
                    FROM pallets 
                    WHERE company_name IS NOT NULL AND company_name != ''
                    AND in_date <= ?
                    AND (out_date IS NULL OR out_date >= ?)
                    ORDER BY company_name
                ''', (month_end, month_start))
        else:
            # 정산월이 없는 경우: 모든 파레트에서 조회
            if USE_POSTGRESQL:
                cursor.execute('''
                    SELECT DISTINCT company_name 
                    FROM pallets 
                    WHERE company_name IS NOT NULL AND company_name != ''
                    ORDER BY company_name
                ''')
            else:
                cursor.execute('''
                    SELECT DISTINCT company_name 
                    FROM pallets 
                    WHERE company_name IS NOT NULL AND company_name != ''
                    ORDER BY company_name
                ''')
        
        rows = cursor.fetchall()
        
        print(f"[화주사 목록] 파레트 테이블에서 조회 완료 (정산월: {settlement_month or '전체'}, 조회 건수: {len(rows) if rows else 0})")
        
        # 화주사명 목록 추출
        raw_companies = []
        if USE_POSTGRESQL:
            raw_companies = [row['company_name'] for row in rows if row.get('company_name')]
        else:
            raw_companies = [row[0] for row in rows if row[0]]
        
        if not raw_companies:
            print("[경고] 화주사 목록이 비어있습니다.")
            return []
        
        # 화주사 태그를 고려하여 동일 화주사 통합
        # 성능 최적화: 배치 쿼리로 모든 화주사 키워드를 한 번에 조회 (N+1 문제 해결)
        from api.database.models import get_company_search_keywords
        
        # 모든 화주사 키워드를 배치로 조회
        if USE_POSTGRESQL:
            placeholders = ','.join(['%s' for _ in raw_companies])
            cursor.execute(f'''
                SELECT company_name, search_keywords 
                FROM companies 
                WHERE company_name IN ({placeholders}) OR username IN ({placeholders})
            ''', raw_companies + raw_companies)
        else:
            placeholders = ','.join(['?' for _ in raw_companies])
            cursor.execute(f'''
                SELECT company_name, search_keywords 
                FROM companies 
                WHERE company_name IN ({placeholders}) OR username IN ({placeholders})
            ''', raw_companies + raw_companies)
        
        company_keywords_map = {}  # {화주사명: [정규화된_키워드_목록]}
        
        keyword_rows = cursor.fetchall()
        for row in keyword_rows:
            if USE_POSTGRESQL:
                company_name = row['company_name']
                search_keywords = row.get('search_keywords', '')
            else:
                company_name = row[0]
                search_keywords = row[1] if len(row) > 1 else ''
            
            keywords = [normalize_company_name(company_name)]
            if search_keywords:
                aliases = [alias.strip() for alias in search_keywords.replace('\n', ',').split(',') if alias.strip()]
                keywords.extend([normalize_company_name(alias) for alias in aliases])
            company_keywords_map[company_name] = keywords
        
        # 모든 화주사에 대해 키워드 설정 (없는 경우 기본값)
        for company in raw_companies:
            if company not in company_keywords_map:
                company_keywords_map[company] = [normalize_company_name(company)]
        
        # Union-Find 방식으로 동일 그룹 통합
        company_to_group = {}  # {화주사명: 그룹_ID}
        group_to_companies = {}  # {그룹_ID: [화주사명들]}
        group_id_counter = 0
        keyword_to_companies = {}  # {정규화된_키워드: [화주사명들]} - 빠른 검색용
        
        # 1단계: 키워드 인덱스 생성 (O(N))
        for company, keywords in company_keywords_map.items():
            for keyword in keywords:
                if keyword not in keyword_to_companies:
                    keyword_to_companies[keyword] = []
                keyword_to_companies[keyword].append(company)
        
        # 2단계: 그룹 할당 (O(N))
        for company in raw_companies:
            keywords = company_keywords_map.get(company, [normalize_company_name(company)])
            
            # 이미 그룹에 속한 화주사 찾기
            found_group = None
            for keyword in keywords:
                # 같은 키워드를 가진 다른 화주사 찾기
                other_companies = keyword_to_companies.get(keyword, [])
                for other_company in other_companies:
                    if other_company != company and other_company in company_to_group:
                        found_group = company_to_group[other_company]
                        break
                if found_group:
                    break
            
            # 그룹에 추가
            if found_group is not None:
                company_to_group[company] = found_group
                group_to_companies[found_group].append(company)
            else:
                # 새 그룹 생성
                new_group = group_id_counter
                group_id_counter += 1
                company_to_group[company] = new_group
                group_to_companies[new_group] = [company]
        
        # 2단계: 각 그룹의 대표 이름 선택 (가장 짧은 이름, 길이가 같으면 알파벳 순서)
        result_companies = []
        for group_companies in group_to_companies.values():
            representative = min(group_companies, key=lambda x: (len(x), x))
            result_companies.append(representative)
        
        # 정렬
        result_companies = sorted(result_companies)
        
        print(f"[화주사 태그 동기화] 원본: {len(raw_companies)}개 → 통합 후: {len(result_companies)}개")
        if len(raw_companies) != len(result_companies):
            print(f"  통합 그룹 수: {len(group_to_companies)}개")
            for group_id, companies_list in list(group_to_companies.items())[:5]:
                if len(companies_list) > 1:
                    print(f"    그룹 {group_id}: {companies_list} → {min(companies_list, key=lambda x: (len(x), x))}")
        
        return result_companies
    finally:
        cursor.close()
        conn.close()


def get_monthly_revenue(start_month: str = None, end_month: str = None) -> Dict:
    """
    월별 보관료 수입 현황 조회
    
    Args:
        start_month: 시작 월 (YYYY-MM 형식, 선택)
        end_month: 종료 월 (YYYY-MM 형식, 선택)
    
    Returns:
        {
            "summary": {
                "total_revenue": int,
                "average_revenue": float,
                "max_revenue": int,
                "min_revenue": int,
                "total_months": int
            },
            "monthly_data": [
                {
                    "month": str,
                    "total_fee": int,
                    "company_count": int,
                    "average_fee": float
                },
                ...
            ],
            "company_distribution": [
                {
                    "company_name": str,
                    "total_fee": int,
                    "percentage": float
                },
                ...
            ]
        }
    """
    conn = get_db_connection()
    
    try:
        if USE_POSTGRESQL:
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        # 기본 쿼리
        query = "SELECT settlement_month, SUM(total_fee) as total_fee, COUNT(DISTINCT company_name) as company_count FROM pallet_monthly_settlements WHERE 1=1"
        params = []
        
        # 기간 필터링
        if start_month:
            query += " AND settlement_month >= %s" if USE_POSTGRESQL else " AND settlement_month >= ?"
            params.append(start_month)
        
        if end_month:
            query += " AND settlement_month <= %s" if USE_POSTGRESQL else " AND settlement_month <= ?"
            params.append(end_month)
        
        query += " GROUP BY settlement_month ORDER BY settlement_month DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # 월별 데이터 처리
        monthly_data = []
        total_revenue = 0
        revenue_list = []
        
        for row in rows:
            if USE_POSTGRESQL:
                month = row['settlement_month']
                total_fee = int(row['total_fee'] or 0)
                company_count = int(row['company_count'] or 0)
            else:
                month = row[0]
                total_fee = int(row[1] or 0)
                company_count = int(row[2] or 0)
            
            average_fee = total_fee / company_count if company_count > 0 else 0
            
            monthly_data.append({
                'month': month,
                'total_fee': total_fee,
                'company_count': company_count,
                'average_fee': round(average_fee, 2)
            })
            
            total_revenue += total_fee
            revenue_list.append(total_fee)
        
        # 통계 계산
        total_months = len(monthly_data)
        average_revenue = total_revenue / total_months if total_months > 0 else 0
        max_revenue = max(revenue_list) if revenue_list else 0
        min_revenue = min(revenue_list) if revenue_list else 0
        
        summary = {
            'total_revenue': total_revenue,
            'average_revenue': round(average_revenue, 2),
            'max_revenue': max_revenue,
            'min_revenue': min_revenue,
            'total_months': total_months
        }
        
        # 화주사별 수입 분포 조회
        company_query = "SELECT company_name, SUM(total_fee) as total_fee FROM pallet_monthly_settlements WHERE 1=1"
        company_params = []
        
        if start_month:
            company_query += " AND settlement_month >= %s" if USE_POSTGRESQL else " AND settlement_month >= ?"
            company_params.append(start_month)
        
        if end_month:
            company_query += " AND settlement_month <= %s" if USE_POSTGRESQL else " AND settlement_month <= ?"
            company_params.append(end_month)
        
        company_query += " GROUP BY company_name ORDER BY total_fee DESC"
        
        cursor.execute(company_query, company_params)
        company_rows = cursor.fetchall()
        
        company_distribution = []
        for row in company_rows:
            if USE_POSTGRESQL:
                company_name = row['company_name']
                company_total_fee = int(row['total_fee'] or 0)
            else:
                company_name = row[0]
                company_total_fee = int(row[1] or 0)
            
            percentage = (company_total_fee / total_revenue * 100) if total_revenue > 0 else 0
            
            company_distribution.append({
                'company_name': company_name,
                'total_fee': company_total_fee,
                'percentage': round(percentage, 2)
            })
        
        return {
            'summary': summary,
            'monthly_data': monthly_data,
            'company_distribution': company_distribution
        }
    finally:
        cursor.close()
        conn.close()


def get_settlement_detail(settlement_id: int) -> Optional[Dict]:
    """
    정산 상세 조회 (파레트별 내역 포함)
    """
    conn = get_db_connection()
    
    try:
        if USE_POSTGRESQL:
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        # 정산 기본 정보 조회
        if USE_POSTGRESQL:
            cursor.execute('SELECT * FROM pallet_monthly_settlements WHERE id = %s', (settlement_id,))
        else:
            cursor.execute('SELECT * FROM pallet_monthly_settlements WHERE id = ?', (settlement_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        if USE_POSTGRESQL:
            settlement = dict(row)
        else:
            settlement = dict(zip([col[0] for col in cursor.description], row))
        
        # 파레트별 상세 내역 조회 (pallets 테이블과 조인)
        # 정산 생성 시 이미 해당 화주사의 파레트만 pallet_fee_calculations에 저장되었으므로
        # 정산월의 모든 파레트를 조회하면 됨 (추가 화주사 필터링 불필요)
        if USE_POSTGRESQL:
            cursor.execute('''
                SELECT 
                    pfc.pallet_id,
                    pfc.storage_days,
                    pfc.daily_fee,
                    pfc.calculated_fee,
                    pfc.rounded_fee,
                    pfc.is_service,
                    p.in_date,
                    p.out_date,
                    p.status,
                    p.product_name,
                    p.company_name,
                    p.created_at,
                    p.updated_at
                FROM pallet_fee_calculations pfc
                JOIN pallets p ON pfc.pallet_id = p.pallet_id
                WHERE pfc.settlement_month = %s
                ORDER BY pfc.pallet_id
            ''', (settlement['settlement_month'],))
        else:
            cursor.execute('''
                SELECT 
                    pfc.pallet_id,
                    pfc.storage_days,
                    pfc.daily_fee,
                    pfc.calculated_fee,
                    pfc.rounded_fee,
                    pfc.is_service,
                    p.in_date,
                    p.out_date,
                    p.status,
                    p.product_name,
                    p.company_name,
                    p.created_at,
                    p.updated_at
                FROM pallet_fee_calculations pfc
                JOIN pallets p ON pfc.pallet_id = p.pallet_id
                WHERE pfc.settlement_month = ?
                ORDER BY pfc.pallet_id
            ''', (settlement['settlement_month'],))
        
        rows = cursor.fetchall()
        
        # 정산월의 시작일과 종료일 계산
        settlement_month = settlement['settlement_month']
        year, month = map(int, settlement_month.split('-'))
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        # 파레트별 상세 내역 처리 (보관료 재계산 - 해당 월 기준으로)
        pallets_list = []
        for row in rows:
            if USE_POSTGRESQL:
                pallet = dict(row)
            else:
                pallet = dict(zip([col[0] for col in cursor.description], row))
            
            # 정산 생성 시 이미 해당 화주사의 파레트만 저장되었으므로
            # 추가 화주사 필터링 불필요 (모든 파레트 포함)
            
            # 해당 월 내 보관일수 재계산
            in_date_str = pallet.get('in_date')
            out_date_str = pallet.get('out_date')
            is_service = pallet.get('is_service', 0) == 1
            
            # 날짜 문자열을 date 객체로 변환 (계산용)
            in_date_obj = None
            out_date_obj = None
            
            if in_date_str:
                if isinstance(in_date_str, str):
                    try:
                        in_date_obj = datetime.strptime(in_date_str, '%Y-%m-%d').date()
                    except:
                        # 날짜 형식이 다를 수 있으므로 다른 형식 시도
                        try:
                            in_date_obj = datetime.strptime(in_date_str.split()[0], '%Y-%m-%d').date()
                        except:
                            pass
                elif isinstance(in_date_str, date):
                    in_date_obj = in_date_str
                elif hasattr(in_date_str, 'date'):
                    in_date_obj = in_date_str.date()
                
                # 원본 문자열이 없으면 date 객체에서 문자열 생성
                if not isinstance(in_date_str, str) and in_date_obj:
                    pallet['in_date'] = in_date_obj.strftime('%Y-%m-%d')
            
            if out_date_str:
                if isinstance(out_date_str, str):
                    try:
                        out_date_obj = datetime.strptime(out_date_str, '%Y-%m-%d').date()
                    except:
                        try:
                            out_date_obj = datetime.strptime(out_date_str.split()[0], '%Y-%m-%d').date()
                        except:
                            pass
                elif isinstance(out_date_str, date):
                    out_date_obj = out_date_str
                elif hasattr(out_date_str, 'date'):
                    out_date_obj = out_date_str.date()
                
                # 원본 문자열이 없으면 date 객체에서 문자열 생성
                if not isinstance(out_date_str, str) and out_date_obj:
                    pallet['out_date'] = out_date_obj.strftime('%Y-%m-%d')
            
            # 해당 월 내 보관일수 계산
            if in_date_obj:
                storage_start = max(in_date_obj, start_date)
                if out_date_obj:
                    storage_end = min(out_date_obj, end_date)
                else:
                    storage_end = min(end_date, date.today())
                
                storage_days = max(0, (storage_end - storage_start).days + 1)
            else:
                # 입고일이 없으면 0일
                storage_days = 0
            
            pallet['storage_days'] = storage_days
            
            # 보관료 재계산: 일일 보관료 × 보관일수 (백원 단위 올림)
            daily_fee = pallet.get('daily_fee', 0)
            if is_service:
                rounded_fee = 0
            else:
                calculated_fee = daily_fee * storage_days
                rounded_fee = math.ceil(calculated_fee / 100) * 100
            
            pallet['rounded_fee'] = int(rounded_fee)
            
            # 날짜 필드가 문자열이 아닌 경우 문자열로 변환 (프론트엔드에서 사용)
            if 'created_at' in pallet and pallet['created_at']:
                if not isinstance(pallet['created_at'], str):
                    if isinstance(pallet['created_at'], date):
                        pallet['created_at'] = pallet['created_at'].strftime('%Y-%m-%d')
                    elif hasattr(pallet['created_at'], 'strftime'):
                        pallet['created_at'] = pallet['created_at'].strftime('%Y-%m-%d')
            
            if 'updated_at' in pallet and pallet['updated_at']:
                if not isinstance(pallet['updated_at'], str):
                    if isinstance(pallet['updated_at'], date):
                        pallet['updated_at'] = pallet['updated_at'].strftime('%Y-%m-%d')
                    elif hasattr(pallet['updated_at'], 'strftime'):
                        pallet['updated_at'] = pallet['updated_at'].strftime('%Y-%m-%d')
            
            pallets_list.append(pallet)
        
        settlement['pallets'] = pallets_list
        
        return settlement
    finally:
        cursor.close()
        conn.close()

