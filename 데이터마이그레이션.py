"""
CSV 파일에서 데이터베이스로 마이그레이션 스크립트
로컬에서 실행하여 데이터베이스에 데이터를 넣습니다.
"""
import os
import sys
import csv
from datetime import datetime

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.database.models import init_db, create_company, create_return, get_company_by_username

def migrate_companies_from_csv(csv_file):
    """CSV 파일에서 화주사 계정 마이그레이션"""
    if not os.path.exists(csv_file):
        print(f"⚠️ 파일을 찾을 수 없습니다: {csv_file}")
        return 0
    
    migrated_count = 0
    
    try:
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            headers = next(reader, None)  # 헤더 건너뛰기
            
            if not headers:
                print("⚠️ CSV 파일이 비어있습니다.")
                return 0
            
            print(f"📋 화주사 계정 마이그레이션 시작...")
            print(f"   헤더: {headers}")
            
            for row_num, row in enumerate(reader, start=2):
                if not any(row):  # 빈 행 건너뛰기
                    continue
                
                try:
                    # CSV 형식에 따라 컬럼 인덱스 조정
                    # 예: 회사명, 아이디, 비밀번호, 권한
                    if len(row) >= 3:
                        company_name = row[0].strip() if row[0] else ''
                        username = row[1].strip() if row[1] else ''
                        password = row[2].strip() if row[2] else ''
                        role = row[3].strip() if len(row) > 3 and row[3] else '화주사'
                        
                        if company_name and username and password:
                            # 기존 계정 확인
                            existing = get_company_by_username(username)
                            if existing:
                                print(f"  ⚠️ 이미 존재: {username}")
                                continue
                            
                            # 계정 생성
                            success = create_company(
                                company_name=company_name,
                                username=username,
                                password=password,
                                role=role
                            )
                            
                            if success:
                                migrated_count += 1
                                if migrated_count % 10 == 0:
                                    print(f"  ... {migrated_count}개 마이그레이션 완료")
                            else:
                                print(f"  ❌ 실패: {username}")
                
                except Exception as e:
                    print(f"  ⚠️ {row_num}행 처리 중 오류: {e}")
                    continue
            
            print(f"✅ 화주사 계정 {migrated_count}개 마이그레이션 완료")
            return migrated_count
    
    except Exception as e:
        print(f"❌ 마이그레이션 오류: {e}")
        import traceback
        traceback.print_exc()
        return 0

def migrate_returns_from_csv(csv_file, month):
    """CSV 파일에서 반품 데이터 마이그레이션"""
    if not os.path.exists(csv_file):
        print(f"⚠️ 파일을 찾을 수 없습니다: {csv_file}")
        return 0
    
    migrated_count = 0
    
    try:
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            
            # 헤더 건너뛰기 (첫 번째 또는 두 번째 행)
            headers = next(reader, None)
            if headers and len(headers) > 0:
                # 두 번째 행도 헤더일 수 있으므로 확인
                second_row = next(reader, None)
                if second_row and any(second_row):
                    # 첫 번째 행이 헤더, 두 번째 행도 헤더일 수 있음
                    # 데이터가 시작되는 행 찾기
                    pass
            
            print(f"📊 {month} 마이그레이션 시작...")
            
            # CSV 파일을 다시 읽기
            f.seek(0)
            reader = csv.reader(f)
            
            # 헤더 행들 건너뛰기 (보통 2행)
            next(reader, None)  # 첫 번째 헤더
            headers = next(reader, None)  # 두 번째 헤더 (데이터 헤더)
            
            if not headers:
                print(f"⚠️ {month}: 헤더를 찾을 수 없습니다.")
                return 0
            
            print(f"   헤더: {headers[:5]}...")  # 처음 5개만 출력
            
            # 헤더 인덱스 찾기
            header_map = {}
            for i, header in enumerate(headers):
                header_lower = header.lower().strip() if header else ''
                if '접수일' in header or 'date' in header_lower:
                    header_map['return_date'] = i
                elif '화주' in header or 'company' in header_lower:
                    header_map['company_name'] = i
                elif '제품' in header or 'product' in header_lower:
                    header_map['product'] = i
                elif '고객' in header or 'customer' in header_lower:
                    header_map['customer_name'] = i
                elif '송장' in header or 'tracking' in header_lower:
                    header_map['tracking_number'] = i
                elif '반품' in header and '교환' in header:
                    header_map['return_type'] = i
                elif '재고' in header or 'stock' in header_lower:
                    header_map['stock_status'] = i
                elif '검품' in header or 'inspection' in header_lower:
                    header_map['inspection'] = i
                elif '처리' in header and '완료' in header:
                    header_map['completed'] = i
                elif '비고' in header or 'memo' in header_lower or 'note' in header_lower:
                    header_map['memo'] = i
                elif '사진' in header or 'photo' in header_lower:
                    header_map['photo_links'] = i
                elif '요청' in header or 'request' in header_lower:
                    header_map['client_request'] = i
            
            # 데이터 행 처리
            for row_num, row in enumerate(reader, start=3):
                if not any(row):  # 빈 행 건너뛰기
                    continue
                
                try:
                    # 필수 필드 확인
                    customer_name = row[header_map.get('customer_name', 3)].strip() if header_map.get('customer_name', 3) < len(row) else ''
                    tracking_number = row[header_map.get('tracking_number', 4)].strip() if header_map.get('tracking_number', 4) < len(row) else ''
                    
                    if not customer_name or not tracking_number:
                        continue  # 필수 필드가 없으면 건너뛰기
                    
                    # 반품 데이터 생성
                    return_data = {
                        'return_date': row[header_map.get('return_date', 0)].strip() if header_map.get('return_date', 0) < len(row) else '',
                        'company_name': row[header_map.get('company_name', 1)].strip() if header_map.get('company_name', 1) < len(row) else '',
                        'product': row[header_map.get('product', 2)].strip() if header_map.get('product', 2) < len(row) else '',
                        'customer_name': customer_name,
                        'tracking_number': tracking_number,
                        'return_type': row[header_map.get('return_type', 5)].strip() if header_map.get('return_type', 5) < len(row) else '',
                        'stock_status': row[header_map.get('stock_status', 6)].strip() if header_map.get('stock_status', 6) < len(row) else '',
                        'inspection': row[header_map.get('inspection', 7)].strip() if header_map.get('inspection', 7) < len(row) else '',
                        'completed': row[header_map.get('completed', 8)].strip() if header_map.get('completed', 8) < len(row) else '',
                        'memo': row[header_map.get('memo', 9)].strip() if header_map.get('memo', 9) < len(row) else '',
                        'photo_links': row[header_map.get('photo_links', 10)].strip() if header_map.get('photo_links', 10) < len(row) else '',
                        'client_request': row[header_map.get('client_request', 11)].strip() if header_map.get('client_request', 11) < len(row) else '',
                        'month': month
                    }
                    
                    # 반품 데이터 생성
                    return_id = create_return(return_data)
                    if return_id:
                        migrated_count += 1
                        if migrated_count % 100 == 0:
                            print(f"  ... {migrated_count}개 마이그레이션 완료")
                
                except Exception as e:
                    print(f"  ⚠️ {row_num}행 처리 중 오류: {e}")
                    continue
            
            print(f"✅ {month}: {migrated_count}개 마이그레이션 완료")
            return migrated_count
    
    except Exception as e:
        print(f"❌ {month} 마이그레이션 오류: {e}")
        import traceback
        traceback.print_exc()
        return 0

def main():
    """메인 함수"""
    print("=" * 50)
    print("CSV → SQLite 데이터베이스 마이그레이션")
    print("=" * 50)
    
    # 데이터베이스 초기화
    print("\n[1/3] 데이터베이스 초기화 중...")
    init_db()
    print("✅ 데이터베이스 초기화 완료")
    
    # CSV 파일 경로
    csv_dir = os.path.join(os.path.dirname(__file__), 'csv_data')
    
    if not os.path.exists(csv_dir):
        print(f"\n❌ CSV 폴더를 찾을 수 없습니다: {csv_dir}")
        print("   csv_data 폴더를 생성하고 CSV 파일을 넣어주세요.")
        return
    
    # 화주사 계정 마이그레이션
    print("\n[2/3] 화주사 계정 마이그레이션 중...")
    companies_file = os.path.join(csv_dir, 'companies.csv')
    if os.path.exists(companies_file):
        migrate_companies_from_csv(companies_file)
    else:
        print("⚠️ companies.csv 파일을 찾을 수 없습니다.")
        print("   화주사 계정은 수동으로 등록하거나 나중에 추가하세요.")
    
    # 반품 데이터 마이그레이션
    print("\n[3/3] 반품 데이터 마이그레이션 중...")
    csv_files = [f for f in os.listdir(csv_dir) if f.endswith('.csv') and f != 'companies.csv']
    
    if not csv_files:
        print("⚠️ 반품 데이터 CSV 파일을 찾을 수 없습니다.")
        return
    
    total_migrated = 0
    for csv_file in sorted(csv_files):
        csv_path = os.path.join(csv_dir, csv_file)
        month = csv_file.replace('.csv', '')
        count = migrate_returns_from_csv(csv_path, month)
        total_migrated += count
    
    print("\n" + "=" * 50)
    print(f"✅ 마이그레이션 완료!")
    print(f"   총 {total_migrated}개의 반품 데이터가 마이그레이션되었습니다.")
    print("=" * 50)
    print("\n⚠️ 중요:")
    print("   1. data.db 파일을 GitHub에 커밋하세요.")
    print("   2. GitHub에 푸시하면 Vercel에서 자동 재배포됩니다.")
    print("   3. 하지만 Vercel은 /tmp 디렉토리를 사용하므로")
    print("      데이터베이스가 영구 저장되지 않을 수 있습니다.")
    print("   4. 운영 환경에서는 PostgreSQL 등 영구 데이터베이스를 사용하세요.")

if __name__ == '__main__':
    main()

