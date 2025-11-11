"""
SQLite → PostgreSQL 마이그레이션 스크립트
기존 SQLite 데이터베이스(data.db)의 데이터를 PostgreSQL로 마이그레이션
"""
import os
import sys
import sqlite3

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(__file__))

from api.database.models import get_db_connection, init_db, create_company, create_return

# SQLite 데이터베이스 경로
SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), 'data.db')


def migrate_companies():
    """화주사 계정 데이터 마이그레이션"""
    print("📋 화주사 계정 마이그레이션 중...")
    
    # SQLite에서 데이터 읽기
    sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()
    
    sqlite_cursor.execute('SELECT * FROM companies')
    companies = sqlite_cursor.fetchall()
    
    print(f"   총 {len(companies)}개의 화주사 계정 발견")
    
    # PostgreSQL로 마이그레이션
    success_count = 0
    skip_count = 0
    error_count = 0
    
    for company in companies:
        try:
            # 기존 계정이 있는지 확인
            from api.database.models import get_company_by_username
            existing = get_company_by_username(company['username'])
            
            if existing:
                print(f"   ⏭️  건너뜀: {company['username']} (이미 존재)")
                skip_count += 1
                continue
            
            # 새 계정 생성
            create_company(
                company_name=company['company_name'],
                username=company['username'],
                password=company['password'],
                role=company.get('role', '화주사'),
                business_number=company.get('business_number'),
                business_name=company.get('business_name'),
                business_address=company.get('business_address'),
                business_tel=company.get('business_tel'),
                business_email=company.get('business_email'),
                business_certificate_url=company.get('business_certificate_url')
            )
            print(f"   ✅ 마이그레이션: {company['username']}")
            success_count += 1
        except Exception as e:
            print(f"   ❌ 오류: {company['username']} - {e}")
            error_count += 1
    
    sqlite_conn.close()
    
    print(f"\n   ✅ 완료: {success_count}개 성공, {skip_count}개 건너뜀, {error_count}개 오류")
    return success_count, skip_count, error_count


def migrate_returns():
    """반품 데이터 마이그레이션"""
    print("\n📦 반품 데이터 마이그레이션 중...")
    
    # SQLite에서 데이터 읽기
    sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()
    
    sqlite_cursor.execute('SELECT * FROM returns')
    returns = sqlite_cursor.fetchall()
    
    print(f"   총 {len(returns)}개의 반품 데이터 발견")
    
    # PostgreSQL로 마이그레이션
    success_count = 0
    skip_count = 0
    error_count = 0
    
    for return_data in returns:
        try:
            # 반품 데이터 딕셔너리로 변환
            return_dict = {
                'return_date': return_data.get('return_date'),
                'company_name': return_data.get('company_name'),
                'product': return_data.get('product'),
                'customer_name': return_data.get('customer_name'),
                'tracking_number': return_data.get('tracking_number'),
                'return_type': return_data.get('return_type'),
                'stock_status': return_data.get('stock_status'),
                'inspection': return_data.get('inspection'),
                'completed': return_data.get('completed'),
                'memo': return_data.get('memo'),
                'photo_links': return_data.get('photo_links'),
                'other_courier': return_data.get('other_courier'),
                'shipping_fee': return_data.get('shipping_fee'),
                'client_request': return_data.get('client_request'),
                'client_confirmed': return_data.get('client_confirmed'),
                'month': return_data.get('month')
            }
            
            # 반품 데이터 생성 (중복 시 자동 업데이트)
            return_id = create_return(return_dict)
            
            if return_id:
                success_count += 1
                if success_count % 100 == 0:
                    print(f"   진행 중: {success_count}/{len(returns)}")
            else:
                skip_count += 1
        except Exception as e:
            print(f"   ❌ 오류: {return_data.get('customer_name', 'Unknown')} - {e}")
            error_count += 1
    
    sqlite_conn.close()
    
    print(f"\n   ✅ 완료: {success_count}개 성공, {skip_count}개 건너뜀, {error_count}개 오류")
    return success_count, skip_count, error_count


def main():
    """메인 마이그레이션 함수"""
    print("=" * 60)
    print("SQLite → PostgreSQL 마이그레이션")
    print("=" * 60)
    
    # SQLite 데이터베이스 확인
    if not os.path.exists(SQLITE_DB_PATH):
        print(f"\n❌ SQLite 데이터베이스를 찾을 수 없습니다: {SQLITE_DB_PATH}")
        print("   data.db 파일이 프로젝트 루트에 있는지 확인하세요.")
        return
    
    # PostgreSQL 연결 확인
    print("\n🔍 PostgreSQL 연결 확인 중...")
    try:
        init_db()
        print("✅ PostgreSQL 데이터베이스 연결 성공")
    except Exception as e:
        print(f"❌ PostgreSQL 데이터베이스 연결 실패: {e}")
        print("\n⚠️  DATABASE_URL 환경 변수가 설정되어 있는지 확인하세요.")
        print("   로컬에서 실행하는 경우:")
        print("   - Windows: set DATABASE_URL=postgresql://...")
        print("   - Linux/Mac: export DATABASE_URL=postgresql://...")
        return
    
    # 화주사 계정 마이그레이션
    print("\n" + "=" * 60)
    companies_success, companies_skip, companies_error = migrate_companies()
    
    # 반품 데이터 마이그레이션
    print("\n" + "=" * 60)
    returns_success, returns_skip, returns_error = migrate_returns()
    
    # 마이그레이션 결과 요약
    print("\n" + "=" * 60)
    print("마이그레이션 결과 요약")
    print("=" * 60)
    print(f"화주사 계정: {companies_success}개 성공, {companies_skip}개 건너뜀, {companies_error}개 오류")
    print(f"반품 데이터: {returns_success}개 성공, {returns_skip}개 건너뜀, {returns_error}개 오류")
    print("\n✅ 마이그레이션 완료!")
    print("\n⚠️  다음 단계:")
    print("1. Vercel에 코드를 푸시하세요 (git push)")
    print("2. Vercel에서 자동으로 배포됩니다")
    print("3. 배포 후 웹사이트에서 로그인하여 데이터가 정상적으로 표시되는지 확인하세요")


if __name__ == '__main__':
    main()

