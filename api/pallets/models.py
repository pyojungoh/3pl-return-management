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
                month: str = None, role: str = '화주사') -> List[Dict]:
    """
    파레트 목록 조회
    
    Args:
        company_name: 화주사명 (화주사인 경우 필수)
        status: 상태 필터 (입고됨, 보관종료, 서비스, 전체)
        month: 월 필터 (YYYY-MM 형식)
        role: 권한 (관리자, 화주사)
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
    
    Returns:
        일일 보관료 (float)
    """
    monthly_fee = get_monthly_fee(company_name, as_of_date)
    daily_fee = monthly_fee / 30.44
    return round(daily_fee, 2)


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
    
    daily_fee = round(monthly_fee / 30.44, 2)
    
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
        
        # 화주사 필터링 (정규화 및 해시태그 지원)
        if company_name:
            # 검색 가능한 키워드 목록 가져오기 (본인 이름 + 해시태그)
            search_keywords = get_company_search_keywords(company_name)
            normalized_keywords = [normalize_company_name(kw) for kw in search_keywords]
            
            # 모든 파레트를 가져온 후 필터링 (정규화된 키워드로 매칭)
            if start_date and end_date:
                if USE_POSTGRESQL:
                    cursor.execute('''
                        SELECT * FROM pallets 
                        WHERE in_date <= %s AND (out_date IS NULL OR out_date >= %s)
                        ORDER BY company_name, in_date
                    ''', (end_date, start_date))
                else:
                    cursor.execute('''
                        SELECT * FROM pallets 
                        WHERE in_date <= ? AND (out_date IS NULL OR out_date >= ?)
                        ORDER BY company_name, in_date
                    ''', (end_date, start_date))
            else:
                if USE_POSTGRESQL:
                    cursor.execute('SELECT * FROM pallets ORDER BY company_name, in_date')
                else:
                    cursor.execute('SELECT * FROM pallets ORDER BY company_name, in_date')
            
            rows = cursor.fetchall()
            
            # 정규화된 키워드로 필터링
            result = []
            for row in rows:
                if USE_POSTGRESQL:
                    pallet = dict(row)
                else:
                    pallet = dict(zip([col[0] for col in cursor.description], row))
                
                pallet_company_normalized = normalize_company_name(pallet.get('company_name', ''))
                if pallet_company_normalized in normalized_keywords:
                    result.append(pallet)
            
            return result
        else:
            # 화주사 필터링 없음
            if start_date and end_date:
                if USE_POSTGRESQL:
                    query += " AND in_date <= %s AND (out_date IS NULL OR out_date >= %s)"
                else:
                    query += " AND in_date <= ? AND (out_date IS NULL OR out_date >= ?)"
                params.extend([end_date, start_date])
            
            query += " ORDER BY company_name, in_date"
            
            if USE_POSTGRESQL:
                cursor.execute(query, params)
            else:
                cursor.execute(query, params)
            
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
    
    for pallet in pallets:
        raw_company = pallet['company_name']
        if not raw_company:
            continue
        
        # 정규화된 키워드 목록 가져오기 (본인 이름 + 해시태그)
        search_keywords = get_company_search_keywords(raw_company)
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
        
        # 보관일수 계산
        storage_days = (storage_end - storage_start).days + 1
        
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
            search_keywords = get_company_search_keywords(company_name)
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
            # 화주사 필터링 없음
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
            
            if USE_POSTGRESQL:
                return [dict(row) for row in rows]
            else:
                return [dict(zip([col[0] for col in cursor.description], row)) for row in rows]
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
            cursor.execute('SELECT id, settlement_month FROM pallet_monthly_settlements WHERE id = %s', (settlement_id,))
        else:
            cursor.execute('SELECT id, settlement_month FROM pallet_monthly_settlements WHERE id = ?', (settlement_id,))
        
        row = cursor.fetchone()
        if not row:
            return False, "정산 내역을 찾을 수 없습니다."
        
        settlement_month = row[1] if USE_POSTGRESQL else row[1]
        
        # 파레트별 보관료 상세 내역 삭제
        if USE_POSTGRESQL:
            cursor.execute('DELETE FROM pallet_fee_calculations WHERE settlement_month = %s', (settlement_month,))
        else:
            cursor.execute('DELETE FROM pallet_fee_calculations WHERE settlement_month = ?', (settlement_month,))
        
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
    
    ✅ 개선사항:
    - 화주사명 정규화 (대소문자 무시, 공백 제거)
    - 해시태그 기능 지원 (search_keywords 필드 활용)
    - 같은 화주사는 하나로 통합 (TKS 컴퍼니, tks컴퍼니, TKS컴퍼니 → 하나로 통합)
    
    Args:
        settlement_month: 정산월 (YYYY-MM 형식). 지정되면 해당 월에 보관했던 화주사만 조회
    """
    from api.database.models import normalize_company_name, get_company_search_keywords
    
    conn = get_db_connection()
    
    try:
        if USE_POSTGRESQL:
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        if settlement_month:
            # 특정 월에 보관했던 화주사만 조회
            year, month = map(int, settlement_month.split('-'))
            start_date = date(year, month, 1)
            if month == 12:
                end_date = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(year, month + 1, 1) - timedelta(days=1)
            
            if USE_POSTGRESQL:
                cursor.execute('''
                    SELECT DISTINCT company_name 
                    FROM pallets 
                    WHERE in_date <= %s AND (out_date IS NULL OR out_date >= %s)
                    ORDER BY company_name
                ''', (end_date, start_date))
            else:
                cursor.execute('''
                    SELECT DISTINCT company_name 
                    FROM pallets 
                    WHERE in_date <= ? AND (out_date IS NULL OR out_date >= ?)
                    ORDER BY company_name
                ''', (end_date, start_date))
        else:
            # 전체 화주사 조회
            if USE_POSTGRESQL:
                cursor.execute('''
                    SELECT DISTINCT company_name 
                    FROM pallets 
                    ORDER BY company_name
                ''')
            else:
                cursor.execute('''
                    SELECT DISTINCT company_name 
                    FROM pallets 
                    ORDER BY company_name
                ''')
        
        rows = cursor.fetchall()
        
        # 원본 화주사명 목록
        raw_companies = []
        if USE_POSTGRESQL:
            raw_companies = [row['company_name'] for row in rows]
        else:
            raw_companies = [row[0] for row in rows]
        
        # 화주사명 정규화 및 통합
        # 1. 각 화주사명에 대해 정규화된 키워드 목록 생성 (본인 이름 + 해시태그)
        company_keywords_map = {}  # 정규화된 키워드 -> 원본 화주사명 매핑
        company_representatives = {}  # 정규화된 키워드 -> 대표 화주사명
        
        for company_name in raw_companies:
            if not company_name:
                continue
            
            # 검색 가능한 키워드 목록 가져오기 (본인 이름 + 해시태그)
            keywords = get_company_search_keywords(company_name)
            
            # 각 키워드에 대해 매핑 생성
            normalized_company = normalize_company_name(company_name)
            
            for keyword in keywords:
                normalized_keyword = normalize_company_name(keyword)
                
                # 이미 다른 화주사가 이 키워드를 사용하고 있는지 확인
                if normalized_keyword in company_keywords_map:
                    # 기존 대표 화주사명과 비교하여 우선순위 결정 (더 짧거나 알파벳 순서가 앞서는 것)
                    existing_rep = company_representatives[normalized_keyword]
                    if len(company_name) < len(existing_rep) or (len(company_name) == len(existing_rep) and company_name < existing_rep):
                        company_representatives[normalized_keyword] = company_name
                        company_keywords_map[normalized_keyword] = company_name
                else:
                    company_keywords_map[normalized_keyword] = company_name
                    company_representatives[normalized_keyword] = company_name
        
        # 2. 각 원본 화주사명에 대해 대표 화주사명 찾기
        final_companies = {}
        for company_name in raw_companies:
            if not company_name:
                continue
            
            normalized = normalize_company_name(company_name)
            representative = company_representatives.get(normalized, company_name)
            final_companies[representative] = True
        
        # 3. 정렬된 목록 반환
        return sorted(final_companies.keys())
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
                    p.created_at
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
                    p.created_at
                FROM pallet_fee_calculations pfc
                JOIN pallets p ON pfc.pallet_id = p.pallet_id
                WHERE pfc.settlement_month = ?
                ORDER BY pfc.pallet_id
            ''', (settlement['settlement_month'],))
        
        rows = cursor.fetchall()
        
        if USE_POSTGRESQL:
            settlement['pallets'] = [dict(row) for row in rows]
        else:
            settlement['pallets'] = [dict(zip([col[0] for col in cursor.description], row)) for row in rows]
        
        return settlement
    finally:
        cursor.close()
        conn.close()

