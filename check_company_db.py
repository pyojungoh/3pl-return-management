"""
화주사명 관련 DB 상태 확인 스크립트
"""
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.database.models import get_db_connection, normalize_company_name, get_company_search_keywords, USE_POSTGRESQL

def check_company_db(company_name="TKS 컴퍼니"):
    """화주사명 관련 DB 상태 확인"""
    
    print("=" * 80)
    print(f"화주사명 DB 상태 확인: '{company_name}'")
    print("=" * 80)
    
    normalized_name = normalize_company_name(company_name)
    print(f"\n[입력 정보]")
    print(f"  원본 화주사명: {company_name}")
    print(f"  정규화된 이름: {normalized_name}")
    
    conn = get_db_connection()
    
    try:
        if USE_POSTGRESQL:
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        # 1. companies 테이블 조회
        print(f"\n[1. companies 테이블 조회]")
        print("-" * 80)
        
        if USE_POSTGRESQL:
            cursor.execute('''
                SELECT company_name, username, search_keywords 
                FROM companies 
                ORDER BY company_name
            ''')
        else:
            cursor.execute('''
                SELECT company_name, username, search_keywords 
                FROM companies 
                ORDER BY company_name
            ''')
        
        companies_rows = cursor.fetchall()
        print(f"전체 회사 수: {len(companies_rows)}")
        
        # TKS 관련 회사 찾기
        tks_companies = []
        for row in companies_rows:
            if USE_POSTGRESQL:
                comp_name = row['company_name']
                username = row.get('username', '')
                search_keywords = row.get('search_keywords', '')
            else:
                comp_name = row[0]
                username = row[1] if len(row) > 1 else ''
                search_keywords = row[2] if len(row) > 2 else ''
            
            comp_normalized = normalize_company_name(comp_name)
            username_normalized = normalize_company_name(username) if username else ''
            
            if (normalized_name in comp_normalized or 
                normalized_name in username_normalized or
                (search_keywords and normalized_name in normalize_company_name(search_keywords))):
                tks_companies.append({
                    'company_name': comp_name,
                    'username': username,
                    'search_keywords': search_keywords,
                    'normalized': comp_normalized
                })
        
        if tks_companies:
            print(f"\nTKS 관련 회사 ({len(tks_companies)}개):")
            for comp in tks_companies:
                print(f"  - company_name: '{comp['company_name']}'")
                print(f"    username: '{comp['username']}'")
                print(f"    search_keywords: '{comp['search_keywords']}'")
                print(f"    정규화: '{comp['normalized']}'")
                print()
        else:
            print("TKS 관련 회사를 찾을 수 없습니다.")
        
        # 2. pallets 테이블 조회 (테이블 존재 여부 확인)
        print(f"\n[2. pallets 테이블 조회]")
        print("-" * 80)
        
        # 테이블 존재 여부 확인
        if USE_POSTGRESQL:
            cursor.execute('''
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'pallets'
                )
            ''')
        else:
            cursor.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='pallets'
            ''')
        
        table_exists = cursor.fetchone()
        if USE_POSTGRESQL:
            table_exists = table_exists[0] if table_exists else False
        else:
            table_exists = table_exists is not None
        
        if not table_exists:
            print("pallets 테이블이 존재하지 않습니다.")
            tks_pallets = []
        else:
            if USE_POSTGRESQL:
                cursor.execute('''
                    SELECT DISTINCT company_name, COUNT(*) as pallet_count
                    FROM pallets 
                    WHERE company_name IS NOT NULL AND company_name != ''
                    GROUP BY company_name
                    ORDER BY company_name
                ''')
            else:
                cursor.execute('''
                    SELECT DISTINCT company_name, COUNT(*) as pallet_count
                    FROM pallets 
                    WHERE company_name IS NOT NULL AND company_name != ''
                    GROUP BY company_name
                    ORDER BY company_name
                ''')
            
            pallets_rows = cursor.fetchall()
            print(f"전체 화주사 수: {len(pallets_rows)}")
            
            # TKS 관련 화주사 찾기
            tks_pallets = []
            for row in pallets_rows:
                if USE_POSTGRESQL:
                    comp_name = row['company_name']
                    pallet_count = row['pallet_count']
                else:
                    comp_name = row[0]
                    pallet_count = row[1]
                
                comp_normalized = normalize_company_name(comp_name)
                if normalized_name in comp_normalized:
                    tks_pallets.append({
                        'company_name': comp_name,
                        'pallet_count': pallet_count,
                        'normalized': comp_normalized
                    })
            
                print(f"\nTKS 관련 화주사 ({len(tks_pallets)}개):")
                for pal in tks_pallets:
                    print(f"  - '{pal['company_name']}' (파레트 수: {pal['pallet_count']}, 정규화: '{pal['normalized']}')")
            else:
                print("TKS 관련 화주사를 찾을 수 없습니다.")
        
        # 3. pallet_monthly_settlements 테이블 조회 (테이블 존재 여부 확인)
        print(f"\n[3. pallet_monthly_settlements 테이블 조회]")
        print("-" * 80)
        
        # 테이블 존재 여부 확인
        if USE_POSTGRESQL:
            cursor.execute('''
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'pallet_monthly_settlements'
                )
            ''')
        else:
            cursor.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='pallet_monthly_settlements'
            ''')
        
        table_exists = cursor.fetchone()
        if USE_POSTGRESQL:
            table_exists = table_exists[0] if table_exists else False
        else:
            table_exists = table_exists is not None
        
        if not table_exists:
            print("pallet_monthly_settlements 테이블이 존재하지 않습니다.")
            tks_settlements = []
        else:
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
            
            settlements_rows = cursor.fetchall()
            print(f"전체 정산 내역 수: {len(settlements_rows)}")
            
            # TKS 관련 정산 내역 찾기
            tks_settlements = []
            for row in settlements_rows:
                if USE_POSTGRESQL:
                    comp_name = row['company_name']
                    settlement_month = row['settlement_month']
                    total_pallets = row['total_pallets']
                    total_fee = row['total_fee']
                    settlement_id = row['id']
                else:
                    comp_name = row[0]
                    settlement_month = row[1]
                    total_pallets = row[2]
                    total_fee = row[3]
                    settlement_id = row[4]
                
                comp_normalized = normalize_company_name(comp_name)
                if normalized_name in comp_normalized:
                    tks_settlements.append({
                        'company_name': comp_name,
                        'settlement_month': settlement_month,
                        'total_pallets': total_pallets,
                        'total_fee': total_fee,
                        'id': settlement_id,
                        'normalized': comp_normalized
                    })
            
                print(f"\nTKS 관련 정산 내역 ({len(tks_settlements)}개):")
                for sett in tks_settlements:
                    print(f"  - ID: {sett['id']}, 화주사: '{sett['company_name']}', 정산월: {sett['settlement_month']}")
                    print(f"    파레트 수: {sett['total_pallets']}, 총 보관료: {sett['total_fee']:,}원")
                    print(f"    정규화: '{sett['normalized']}'")
                    print()
            else:
                print("TKS 관련 정산 내역을 찾을 수 없습니다.")
        
        # 4. get_company_search_keywords 테스트
        print(f"\n[4. get_company_search_keywords 함수 테스트]")
        print("-" * 80)
        
        test_companies = [company_name]
        if tks_companies:
            test_companies.extend([comp['company_name'] for comp in tks_companies])
        if tks_pallets:
            test_companies.extend([pal['company_name'] for pal in tks_pallets[:3]])  # 처음 3개만
        if tks_settlements:
            test_companies.extend([sett['company_name'] for sett in tks_settlements[:3]])  # 처음 3개만
        
        test_companies = list(set(test_companies))  # 중복 제거
        
        for test_comp in test_companies:
            try:
                keywords = get_company_search_keywords(test_comp)
                print(f"  '{test_comp}' → 키워드: {keywords}")
            except Exception as e:
                print(f"  '{test_comp}' → 오류: {e}")
        
        # 5. 매칭 테스트
        print(f"\n[5. 매칭 테스트]")
        print("-" * 80)
        
        query_normalized = normalize_company_name(company_name)
        query_keywords = get_company_search_keywords(company_name)
        
        print(f"조회 대상: '{company_name}'")
        print(f"  정규화: '{query_normalized}'")
        print(f"  키워드: {query_keywords}")
        print()
        
        print("정산 내역 매칭 결과:")
        for sett in tks_settlements:
            sett_normalized = normalize_company_name(sett['company_name'])
            sett_keywords = get_company_search_keywords(sett['company_name'])
            
            direct_match = (sett_normalized == query_normalized)
            keyword_match = (sett_normalized in query_keywords) or (query_normalized in sett_keywords)
            keyword_intersection = set(query_keywords) & set(sett_keywords)
            
            print(f"  정산 ID {sett['id']}: '{sett['company_name']}'")
            print(f"    정규화: '{sett_normalized}'")
            print(f"    키워드: {sett_keywords}")
            print(f"    직접 매칭: {direct_match}")
            print(f"    키워드 매칭: {keyword_match}")
            print(f"    키워드 교집합: {keyword_intersection}")
            print(f"    최종 매칭: {direct_match or keyword_match or bool(keyword_intersection)}")
            print()
        
    finally:
        cursor.close()
        conn.close()
    
    print("=" * 80)
    print("확인 완료")
    print("=" * 80)

if __name__ == "__main__":
    check_company_db("TKS 컴퍼니")

