"""
Google Sheets 반품 데이터 읽기 모듈
스프레드시트 ID: 1utFJtDnIzJHpCMKu1WJkU8HR8SH1TB76cK9flw9jTuU
"""
import os
import json
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# 스프레드시트 설정
SPREADSHEET_ID = '1utFJtDnIzJHpCMKu1WJkU8HR8SH1TB76cK9flw9jTuU'
RANGE_NAME = '2025년11월!A2:K'  # 헤더 제외하고 데이터만

# Google Sheets API 스코프
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']


def get_credentials():
    """
    Google API 인증 정보 가져오기
    service_account.json 파일이 필요합니다.
    """
    try:
        creds_path = os.path.join(os.path.dirname(__file__), 'service_account.json')
        if os.path.exists(creds_path):
            credentials = service_account.Credentials.from_service_account_file(
                creds_path, scopes=SCOPES)
            return credentials
        else:
            print(f"인증 파일을 찾을 수 없습니다: {creds_path}")
            return None
    except Exception as e:
        print(f"인증 정보 로드 실패: {e}")
        return None


def read_return_data():
    """
    Google Sheets에서 반품 데이터 읽기
    
    Returns:
        list: 반품 데이터 리스트
        [
            {
                'return_date': '반품 접수일',
                'company_name': '화주명',
                'product': '제품',
                'customer_name': '고객명',
                'tracking_number': '송장번호',
                'return_type': '반품/교환/오배송',
                'stock_status': '재고상태(불량/정상)',
                'inspection': '검품유무',
                'completed': '처리완료',
                'note': '비고',
                'photo': '사진'
            },
            ...
        ]
    """
    try:
        credentials = get_credentials()
        if not credentials:
            return {'error': 'Google API 인증 실패', 'data': []}
        
        service = build('sheets', 'v4', credentials=credentials)
        sheet = service.spreadsheets()
        
        # 데이터 읽기
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=RANGE_NAME
        ).execute()
        
        values = result.get('values', [])
        
        if not values:
            return {'error': None, 'data': [], 'message': '데이터가 없습니다.'}
        
        # 데이터 파싱
        return_data = []
        for row in values:
            # 빈 행 건너뛰기
            if not any(row):
                continue
            
            # 행 길이에 맞춰 데이터 추출
            data_item = {
                'return_date': row[0] if len(row) > 0 else '',
                'company_name': row[1] if len(row) > 1 else '',
                'product': row[2] if len(row) > 2 else '',
                'customer_name': row[3] if len(row) > 3 else '',
                'tracking_number': row[4] if len(row) > 4 else '',
                'return_type': row[5] if len(row) > 5 else '',
                'stock_status': row[6] if len(row) > 6 else '',
                'inspection': row[7] if len(row) > 7 else '',
                'completed': row[8] if len(row) > 8 else '',
                'note': row[9] if len(row) > 9 else '',
                'photo': row[10] if len(row) > 10 else ''
            }
            return_data.append(data_item)
        
        return {
            'error': None,
            'data': return_data,
            'count': len(return_data),
            'message': f'{len(return_data)}건의 데이터를 불러왔습니다.'
        }
        
    except HttpError as error:
        print(f'HTTP 에러 발생: {error}')
        return {'error': str(error), 'data': []}
    except Exception as e:
        print(f'데이터 읽기 실패: {e}')
        return {'error': str(e), 'data': []}


def filter_return_data(data, filters=None):
    """
    반품 데이터 필터링
    
    Args:
        data (list): 반품 데이터 리스트
        filters (dict): 필터 조건
            - company_name: 화주명
            - return_type: 반품/교환/오배송
            - stock_status: 정상/불량
            - completed: 처리완료 여부
    
    Returns:
        list: 필터링된 데이터
    """
    if not filters:
        return data
    
    filtered_data = data
    
    if filters.get('company_name'):
        filtered_data = [item for item in filtered_data 
                        if item['company_name'] == filters['company_name']]
    
    if filters.get('return_type'):
        filtered_data = [item for item in filtered_data 
                        if item['return_type'] == filters['return_type']]
    
    if filters.get('stock_status'):
        filtered_data = [item for item in filtered_data 
                        if item['stock_status'] == filters['stock_status']]
    
    if filters.get('completed') is not None:
        if filters['completed']:
            # 처리완료된 항목만
            filtered_data = [item for item in filtered_data 
                           if item['completed'] and item['completed'].strip()]
        else:
            # 미처리 항목만
            filtered_data = [item for item in filtered_data 
                           if not item['completed'] or not item['completed'].strip()]
    
    return filtered_data


def get_statistics(data):
    """
    반품 데이터 통계 생성
    
    Args:
        data (list): 반품 데이터 리스트
    
    Returns:
        dict: 통계 정보
    """
    stats = {
        'total': len(data),
        'by_company': {},
        'by_return_type': {},
        'by_stock_status': {},
        'completed_count': 0,
        'pending_count': 0
    }
    
    for item in data:
        # 화주별 통계
        company = item['company_name']
        if company:
            stats['by_company'][company] = stats['by_company'].get(company, 0) + 1
        
        # 반품 유형별 통계
        return_type = item['return_type']
        if return_type:
            stats['by_return_type'][return_type] = stats['by_return_type'].get(return_type, 0) + 1
        
        # 재고 상태별 통계
        stock_status = item['stock_status']
        if stock_status:
            stats['by_stock_status'][stock_status] = stats['by_stock_status'].get(stock_status, 0) + 1
        
        # 처리 상태별 통계
        if item['completed'] and item['completed'].strip():
            stats['completed_count'] += 1
        else:
            stats['pending_count'] += 1
    
    return stats


if __name__ == '__main__':
    # 테스트
    print("Google Sheets 데이터 읽기 테스트...")
    result = read_return_data()
    
    if result['error']:
        print(f"에러: {result['error']}")
    else:
        print(f"총 {result['count']}건의 데이터를 읽었습니다.")
        
        # 통계 출력
        stats = get_statistics(result['data'])
        print(f"\n통계:")
        print(f"- 전체: {stats['total']}건")
        print(f"- 처리완료: {stats['completed_count']}건")
        print(f"- 미처리: {stats['pending_count']}건")
        print(f"\n화주별:")
        for company, count in stats['by_company'].items():
            print(f"  - {company}: {count}건")






