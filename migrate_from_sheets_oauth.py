"""
Google Sheets → SQLite 마이그레이션 스크립트 (OAuth 사용자 인증)
Google Cloud Console 없이 사용자 계정으로 접근
"""
import os
import sys
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(__file__))

from api.database.models import init_db, create_company, create_return

# Google Sheets 설정
SPREADSHEET_ID = '1utFJtDnIzJHpCMKu1WJkU8HR8SH1TB76cK9flw9jTuU'
ACCOUNT_SHEET_NAME = '화주사계정'


def migrate_from_csv():
    """
    Google Sheets를 CSV로 내보내서 마이그레이션
    1. Google Sheets에서 CSV로 다운로드
    2. 이 스크립트로 파싱하여 데이터베이스에 저장
    """
    print("=" * 50)
    print("Google Sheets CSV 마이그레이션")
    print("=" * 50)
    print("\n📋 사용 방법:")
    print("1. Google Sheets에서 '파일' → '다운로드' → 'CSV' 선택")
    print("2. 화주사계정 시트를 CSV로 다운로드 → 'companies.csv'로 저장")
    print("3. 각 월별 시트를 CSV로 다운로드 → 'YYYY년MM월.csv'로 저장")
    print("4. 이 스크립트 실행")
    print("\n" + "=" * 50)
    
    # CSV 파일 경로 확인
    csv_dir = os.path.join(os.path.dirname(__file__), 'csv_data')
    if not os.path.exists(csv_dir):
        os.makedirs(csv_dir)
        print(f"📁 CSV 파일을 저장할 폴더를 생성했습니다: {csv_dir}")
        print("   이 폴더에 CSV 파일을 저장한 후 다시 실행하세요.")
        return
    
    # 화주사 계정 마이그레이션
    companies_file = os.path.join(csv_dir, 'companies.csv')
    if os.path.exists(companies_file):
        print("\n📋 화주사 계정 마이그레이션 중...")
        migrate_companies_from_csv(companies_file)
    else:
        print(f"\n⚠️ {companies_file} 파일을 찾을 수 없습니다.")
        print("   Google Sheets에서 화주사계정 시트를 CSV로 다운로드하세요.")
    
    # 반품 데이터 마이그레이션
    print("\n📋 반품 데이터 마이그레이션 중...")
    csv_files = [f for f in os.listdir(csv_dir) if f.endswith('.csv') and f != 'companies.csv']
    
    if not csv_files:
        print(f"⚠️ CSV 파일을 찾을 수 없습니다.")
        print("   Google Sheets에서 월별 시트를 CSV로 다운로드하세요.")
        return
    
    for csv_file in csv_files:
        csv_path = os.path.join(csv_dir, csv_file)
        month = csv_file.replace('.csv', '')
        print(f"\n📊 {month} 시트 마이그레이션 중...")
        migrate_returns_from_csv(csv_path, month)
    
    print("\n" + "=" * 50)
    print("✅ 마이그레이션 완료!")
    print("=" * 50)


def migrate_companies_from_csv(csv_file):
    """CSV 파일에서 화주사 계정 마이그레이션"""
    import csv
    
    try:
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            next(reader)  # 헤더 스킵
            
            migrated_count = 0
            for row in reader:
                if len(row) < 4:
                    continue
                
                company_name = row[0].strip() if row[0] else ''
                username = row[1].strip() if len(row) > 1 and row[1] else ''
                password = row[2].strip() if len(row) > 2 and row[2] else ''
                role = row[3].strip() if len(row) > 3 and row[3] else '화주사'
                
                if company_name and username and password:
                    if create_company(company_name, username, password, role):
                        migrated_count += 1
                        print(f"  ✅ {company_name} ({username})")
                    else:
                        print(f"  ⚠️ {company_name} ({username}) - 이미 존재")
            
            print(f"✅ 화주사 계정 {migrated_count}개 마이그레이션 완료")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")


def migrate_returns_from_csv(csv_file, month):
    """CSV 파일에서 반품 데이터 마이그레이션"""
    import csv
    
    try:
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            next(reader)  # 헤더 스킵 (1행)
            next(reader)  # 헤더 스킵 (2행)
            
            migrated_count = 0
            for row in reader:
                if len(row) < 5:
                    continue
                
                # 필수 데이터 확인 (고객명, 송장번호)
                customer_name = row[3].strip() if len(row) > 3 and row[3] else ''
                tracking_number = row[4].strip() if len(row) > 4 and row[4] else ''
                
                if not customer_name or not tracking_number:
                    continue
                
                # 반품 데이터 생성
                return_data = {
                    'return_date': row[0] if len(row) > 0 else '',
                    'company_name': row[1].strip() if len(row) > 1 and row[1] else '',
                    'product': row[2] if len(row) > 2 else '',
                    'customer_name': customer_name,
                    'tracking_number': tracking_number,
                    'return_type': row[5] if len(row) > 5 else '',
                    'stock_status': row[6] if len(row) > 6 else '',
                    'inspection': row[7] if len(row) > 7 else '',
                    'completed': row[8] if len(row) > 8 else '',
                    'memo': row[9] if len(row) > 9 else '',
                    'photo_links': row[10] if len(row) > 10 else '',
                    'other_courier': row[11] if len(row) > 11 else '',
                    'shipping_fee': row[12] if len(row) > 12 else '',
                    'client_request': row[13] if len(row) > 13 else '',
                    'client_confirmed': row[14] if len(row) > 14 else '',
                    'month': month
                }
                
                if create_return(return_data):
                    migrated_count += 1
                    if migrated_count % 10 == 0:
                        print(f"  ... {migrated_count}개 마이그레이션 완료")
            
            print(f"✅ {month}: {migrated_count}개 마이그레이션 완료")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


def main():
    """메인 함수"""
    print("=" * 50)
    print("Google Sheets → SQLite 마이그레이션 (CSV 방식)")
    print("=" * 50)
    
    # 데이터베이스 초기화
    print("\n1. 데이터베이스 초기화...")
    init_db()
    
    # CSV 마이그레이션
    migrate_from_csv()


if __name__ == '__main__':
    main()



