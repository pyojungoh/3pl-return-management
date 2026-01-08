"""
파레트 현황 및 화주사별 현황 확인 스크립트
"""
import sys
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.database.models import get_db_connection, normalize_company_name, get_company_search_keywords, USE_POSTGRESQL
from api.pallets.models import get_companies_with_pallets, get_settlements

# DB 연결 정보 확인
print(f"USE_POSTGRESQL: {USE_POSTGRESQL}")
if USE_POSTGRESQL:
    db_url = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')
    if db_url:
        # URL에서 호스트 정보만 추출 (보안)
        if '@' in db_url and '://' in db_url:
            parts = db_url.split('@')
            if len(parts) > 1:
                host_part = parts[1].split('/')[0] if '/' in parts[1] else parts[1]
                print(f"DB 호스트: {host_part.split('?')[0]}")
        print("✅ PostgreSQL 연결 정보 확인됨")
    else:
        print("❌ DATABASE_URL 환경 변수가 없습니다.")
else:
    print("ℹ️  SQLite 사용 중 (로컬 DB)")

def check_pallets_status():
    """파레트 현황 및 화주사별 현황 확인"""
    
    print("=" * 80)
    print("파레트 현황 및 화주사별 현황 확인")
    print("=" * 80)
    
    conn = get_db_connection()
    
    try:
        if USE_POSTGRESQL:
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        # 1. pallets 테이블 존재 여부 확인
        print("\n[1. pallets 테이블 확인]")
        print("-" * 80)
        
        if USE_POSTGRESQL:
            cursor.execute('''
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'pallets'
                ) as exists
            ''')
            result = cursor.fetchone()
            table_exists = result['exists'] if result else False
        else:
            cursor.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='pallets'
            ''')
            result = cursor.fetchone()
            table_exists = result is not None
        
        if not table_exists:
            print("❌ pallets 테이블이 존재하지 않습니다.")
            return
        
        print("✅ pallets 테이블 존재")
        
        # 2. TKS 관련 파레트 조회 (띄어쓰기, 대문자 무시)
        print("\n[2. TKS 관련 파레트 현황]")
        print("-" * 80)
        
        # 모든 파레트 조회 후 Python에서 필터링
        if USE_POSTGRESQL:
            cursor.execute('''
                SELECT pallet_id, company_name, status, in_date, out_date, product_name
                FROM pallets 
                WHERE company_name IS NOT NULL AND company_name != ''
                ORDER BY company_name, in_date DESC
            ''')
        else:
            cursor.execute('''
                SELECT pallet_id, company_name, status, in_date, out_date, product_name
                FROM pallets 
                WHERE company_name IS NOT NULL AND company_name != ''
                ORDER BY company_name, in_date DESC
            ''')
        
        all_pallets = cursor.fetchall()
        print(f"전체 파레트 수: {len(all_pallets)}")
        
        # TKS 관련 파레트 필터링
        tks_pallets = []
        tks_company_names = set()
        
        for row in all_pallets:
            if USE_POSTGRESQL:
                company_name = row['company_name']
            else:
                company_name = row[1]
            
            if not company_name:
                continue
            
            normalized = normalize_company_name(company_name)
            if 'tks' in normalized and '컴퍼니' in normalized:
                tks_pallets.append(row)
                tks_company_names.add(company_name)
        
        print(f"\nTKS 관련 파레트 수: {len(tks_pallets)}개")
        print(f"TKS 관련 화주사명 종류: {len(tks_company_names)}개")
        print(f"화주사명 목록: {sorted(tks_company_names)}")
        
        # 상태별 집계
        status_count = {}
        for row in tks_pallets:
            if USE_POSTGRESQL:
                status = row['status']
            else:
                status = row[2]
            
            status_count[status] = status_count.get(status, 0) + 1
        
        print(f"\n상태별 파레트 수:")
        for status, count in sorted(status_count.items()):
            print(f"  - {status}: {count}개")
        
        # 화주사명별 집계
        print(f"\n화주사명별 파레트 수:")
        company_count = {}
        for row in tks_pallets:
            if USE_POSTGRESQL:
                company_name = row['company_name']
            else:
                company_name = row[1]
            
            company_count[company_name] = company_count.get(company_name, 0) + 1
        
        for company, count in sorted(company_count.items()):
            normalized = normalize_company_name(company)
            print(f"  - '{company}' (정규화: '{normalized}'): {count}개")
        
        # 3. 화주사별 현황 조회 (get_companies_with_pallets)
        print("\n[3. 화주사별 현황 (get_companies_with_pallets)]")
        print("-" * 80)
        
        companies_list = get_companies_with_pallets()
        print(f"화주사 목록 수: {len(companies_list)}개")
        
        # TKS 관련 화주사 필터링
        tks_companies_in_list = []
        for company in companies_list:
            normalized = normalize_company_name(company)
            if 'tks' in normalized and '컴퍼니' in normalized:
                tks_companies_in_list.append(company)
        
        print(f"\nTKS 관련 화주사 목록: {len(tks_companies_in_list)}개")
        for company in sorted(tks_companies_in_list):
            normalized = normalize_company_name(company)
            print(f"  - '{company}' (정규화: '{normalized}')")
        
        # 4. 정산 내역 조회 (get_settlements)
        print("\n[4. 정산 내역 조회 (get_settlements)]")
        print("-" * 80)
        
        # 각 TKS 화주사명으로 정산 내역 조회 테스트
        test_companies = ['TKS 컴퍼니', 'TKS컴퍼니', 'tks컴퍼니']
        if tks_companies_in_list:
            test_companies.extend(tks_companies_in_list[:3])
        
        test_companies = list(set(test_companies))  # 중복 제거
        
        for test_company in test_companies:
            print(f"\n조회 화주사: '{test_company}'")
            try:
                settlements = get_settlements(company_name=test_company)
                print(f"  조회된 정산 내역 수: {len(settlements)}개")
                
                if settlements:
                    for sett in settlements[:3]:  # 처음 3개만 출력
                        print(f"    - 정산월: {sett.get('settlement_month')}, 화주사: '{sett.get('company_name')}', 파레트 수: {sett.get('total_pallets')}")
                else:
                    print("  ❌ 정산 내역 없음")
            except Exception as e:
                print(f"  ❌ 오류: {e}")
                import traceback
                traceback.print_exc()
        
        # 5. pallet_monthly_settlements 테이블 확인
        print("\n[5. pallet_monthly_settlements 테이블 확인]")
        print("-" * 80)
        
        # 테이블 존재 여부 확인
        if USE_POSTGRESQL:
            cursor.execute('''
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'pallet_monthly_settlements'
                ) as exists
            ''')
            result = cursor.fetchone()
            table_exists = result['exists'] if result else False
        else:
            cursor.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='pallet_monthly_settlements'
            ''')
            result = cursor.fetchone()
            table_exists = result is not None
        
        if not table_exists:
            print("❌ pallet_monthly_settlements 테이블이 존재하지 않습니다.")
        else:
            print("✅ pallet_monthly_settlements 테이블 존재")
            
            # TKS 관련 정산 내역 조회
            if USE_POSTGRESQL:
                cursor.execute('''
                    SELECT company_name, settlement_month, total_pallets, total_fee, id
                    FROM pallet_monthly_settlements 
                    ORDER BY settlement_month DESC, company_name
                ''')
            else:
                cursor.execute('''
                    SELECT company_name, settlement_month, total_pallets, total_fee, id
                    FROM pallet_monthly_settlements 
                    ORDER BY settlement_month DESC, company_name
                ''')
            
            all_settlements = cursor.fetchall()
            print(f"전체 정산 내역 수: {len(all_settlements)}개")
            
            # TKS 관련 정산 내역 필터링
            tks_settlements = []
            for row in all_settlements:
                if USE_POSTGRESQL:
                    company_name = row['company_name']
                else:
                    company_name = row[0]
                
                if not company_name:
                    continue
                
                normalized = normalize_company_name(company_name)
                if 'tks' in normalized and '컴퍼니' in normalized:
                    tks_settlements.append(row)
            
            print(f"\nTKS 관련 정산 내역 수: {len(tks_settlements)}개")
            for row in tks_settlements[:10]:  # 처음 10개만 출력
                if USE_POSTGRESQL:
                    print(f"  - ID: {row['id']}, 화주사: '{row['company_name']}', 정산월: {row['settlement_month']}, 파레트 수: {row['total_pallets']}")
                else:
                    print(f"  - ID: {row[4]}, 화주사: '{row[0]}', 정산월: {row[1]}, 파레트 수: {row[2]}")
        
        # 6. 원인 분석
        print("\n[6. 원인 분석]")
        print("-" * 80)
        
        print(f"파레트 테이블의 TKS 화주사명 종류: {len(tks_company_names)}개")
        print(f"화주사 목록의 TKS 화주사명 종류: {len(tks_companies_in_list)}개")
        
        if len(tks_company_names) != len(tks_companies_in_list):
            print("⚠️  파레트 테이블과 화주사 목록의 화주사명 종류가 다릅니다!")
            print(f"  파레트 테이블: {sorted(tks_company_names)}")
            print(f"  화주사 목록: {sorted(tks_companies_in_list)}")
        
        # 각 화주사명의 키워드 확인
        print(f"\n각 화주사명의 키워드:")
        all_tks_companies = list(tks_company_names) + tks_companies_in_list
        all_tks_companies = list(set(all_tks_companies))
        
        for company in sorted(all_tks_companies):
            try:
                keywords = get_company_search_keywords(company)
                normalized = normalize_company_name(company)
                print(f"  '{company}' (정규화: '{normalized}') → 키워드: {keywords}")
            except Exception as e:
                print(f"  '{company}' → 오류: {e}")
        
    finally:
        cursor.close()
        conn.close()
    
    print("\n" + "=" * 80)
    print("확인 완료")
    print("=" * 80)

if __name__ == "__main__":
    check_pallets_status()

