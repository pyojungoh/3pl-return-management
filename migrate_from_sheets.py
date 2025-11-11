"""
Google Sheets → SQLite 마이그레이션 스크립트
"""
import os
import sys
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(__file__))

from api.database.models import init_db, create_company, create_return, get_db_connection

# Google Sheets 설정
SPREADSHEET_ID = '1utFJtDnIzJHpCMKu1WJkU8HR8SH1TB76cK9flw9jTuU'
ACCOUNT_SHEET_NAME = '화주사계정'

# Google Sheets API 스코프
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']


def get_credentials():
    """Google API 인증 정보 가져오기"""
    try:
        # 환경 변수에서 인증 정보 가져오기
        creds_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
        if creds_json:
            import json
            if isinstance(creds_json, str):
                creds_info = json.loads(creds_json)
            else:
                creds_info = creds_json
            
            credentials = service_account.Credentials.from_service_account_info(
                creds_info, scopes=SCOPES)
            return credentials
        
        # 로컬 파일에서 인증 정보 가져오기
        creds_path = os.path.join(os.path.dirname(__file__), 'service_account.json')
        if os.path.exists(creds_path):
            credentials = service_account.Credentials.from_service_account_file(
                creds_path, scopes=SCOPES)
            return credentials
        
        print("❌ 인증 정보를 찾을 수 없습니다.")
        print("   환경 변수 GOOGLE_SERVICE_ACCOUNT_JSON 또는 service_account.json 파일이 필요합니다.")
        return None
    except Exception as e:
        print(f"❌ 인증 정보 로드 실패: {e}")
        return None


def migrate_companies():
    """화주사 계정 마이그레이션"""
    print("📋 화주사 계정 마이그레이션 시작...")
    
    credentials = get_credentials()
    if not credentials:
        print("❌ 인증 실패. 마이그레이션을 중단합니다.")
        return False
    
    try:
        service = build('sheets', 'v4', credentials=credentials)
        sheet = service.spreadsheets()
        
        # 화주사계정 시트 데이터 읽기
        range_name = f'{ACCOUNT_SHEET_NAME}!A2:D'
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        
        migrated_count = 0
        for row in values:
            if len(row) < 4:
                continue
            
            company_name = row[0].strip() if row[0] else ''
            username = row[1].strip() if len(row) > 1 and row[1] else ''
            password = row[2].strip() if len(row) > 2 and row[2] else ''
            role = row[3].strip() if len(row) > 3 and row[3] else '화주사'
            
            if company_name and username and password:
                if create_company(company_name, username, password, role):
                    migrated_count += 1
                    print(f"  ✅ {company_name} ({username}) 마이그레이션 완료")
                else:
                    print(f"  ⚠️ {company_name} ({username}) 이미 존재하거나 오류 발생")
        
        print(f"✅ 화주사 계정 마이그레이션 완료: {migrated_count}개")
        return True
        
    except HttpError as error:
        print(f"❌ HTTP 에러 발생: {error}")
        return False
    except Exception as e:
        print(f"❌ 마이그레이션 오류: {e}")
        return False


def migrate_returns():
    """반품 데이터 마이그레이션"""
    print("📋 반품 데이터 마이그레이션 시작...")
    
    credentials = get_credentials()
    if not credentials:
        print("❌ 인증 실패. 마이그레이션을 중단합니다.")
        return False
    
    try:
        service = build('sheets', 'v4', credentials=credentials)
        sheet_service = service.spreadsheets()
        
        # 시트 목록 가져오기
        sheet_metadata = sheet_service.get(spreadsheetId=SPREADSHEET_ID).execute()
        sheets = sheet_metadata.get('sheets', [])
        
        # 월별 시트만 필터링
        month_sheets = []
        for sheet in sheets:
            title = sheet['properties']['title']
            if '년' in title and '월' in title:
                month_sheets.append(title)
        
        month_sheets.sort(reverse=True)
        print(f"📅 발견된 월별 시트: {len(month_sheets)}개")
        
        total_migrated = 0
        
        for sheet_name in month_sheets:
            print(f"\n📊 {sheet_name} 시트 마이그레이션 중...")
            
            # 데이터 읽기 (3행부터, A~O열)
            range_name = f'{sheet_name}!A3:O'
            result = sheet_service.values().get(
                spreadsheetId=SPREADSHEET_ID,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            # Rich text 값 읽기 (사진 링크 추출용)
            result_rich = sheet_service.get(
                spreadsheetId=SPREADSHEET_ID,
                ranges=[range_name],
                includeGridData=True
            ).execute()
            
            # Rich text 데이터 추출
            rich_data = []
            if result_rich.get('sheets') and len(result_rich['sheets']) > 0:
                sheet_data = result_rich['sheets'][0]
                if 'data' in sheet_data and len(sheet_data['data']) > 0:
                    row_data = sheet_data['data'][0].get('rowData', [])
                    for row in row_data:
                        cell_data = row.get('values', [])
                        rich_row = []
                        for cell in cell_data:
                            links = []
                            if 'hyperlink' in cell:
                                links.append({
                                    'text': cell.get('formattedValue', '링크'),
                                    'url': cell['hyperlink']
                                })
                            elif 'textFormatRuns' in cell:
                                for run in cell.get('textFormatRuns', []):
                                    if 'link' in run.get('format', {}):
                                        links.append({
                                            'text': run.get('text', '링크'),
                                            'url': run['format']['link']['uri']
                                        })
                            rich_row.append(links)
                        rich_data.append(rich_row)
            
            migrated_count = 0
            for i, row in enumerate(values):
                if len(row) < 5:
                    continue
                
                # 필수 데이터 확인 (고객명, 송장번호)
                customer_name = row[3].strip() if len(row) > 3 and row[3] else ''
                tracking_number = row[4].strip() if len(row) > 4 and row[4] else ''
                
                if not customer_name or not tracking_number:
                    continue
                
                # 사진 링크 처리
                photo_links = ''
                if len(rich_data) > i and len(rich_data[i]) > 10:
                    links = rich_data[i][10]
                    if links:
                        photo_links = '\n'.join([f"{link['text']}: {link['url']}" for link in links])
                
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
                    'photo_links': photo_links,
                    'other_courier': row[11] if len(row) > 11 else '',
                    'shipping_fee': row[12] if len(row) > 12 else '',
                    'client_request': row[13] if len(row) > 13 else '',
                    'client_confirmed': row[14] if len(row) > 14 else '',
                    'month': sheet_name
                }
                
                if create_return(return_data):
                    migrated_count += 1
                    if migrated_count % 10 == 0:
                        print(f"  ... {migrated_count}개 마이그레이션 완료")
            
            total_migrated += migrated_count
            print(f"✅ {sheet_name}: {migrated_count}개 마이그레이션 완료")
        
        print(f"\n✅ 반품 데이터 마이그레이션 완료: 총 {total_migrated}개")
        return True
        
    except HttpError as error:
        print(f"❌ HTTP 에러 발생: {error}")
        return False
    except Exception as e:
        print(f"❌ 마이그레이션 오류: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 함수"""
    print("=" * 50)
    print("Google Sheets → SQLite 마이그레이션")
    print("=" * 50)
    
    # 데이터베이스 초기화
    print("\n1. 데이터베이스 초기화...")
    init_db()
    
    # 화주사 계정 마이그레이션
    print("\n2. 화주사 계정 마이그레이션...")
    migrate_companies()
    
    # 반품 데이터 마이그레이션
    print("\n3. 반품 데이터 마이그레이션...")
    migrate_returns()
    
    print("\n" + "=" * 50)
    print("✅ 마이그레이션 완료!")
    print("=" * 50)


if __name__ == '__main__':
    main()



