"""
반품 데이터 API 라우트
"""
from flask import Blueprint, request, jsonify
import os
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Blueprint 생성
returns_bp = Blueprint('returns', __name__, url_prefix='/api/returns')

# 스프레드시트 ID
SPREADSHEET_ID = '1utFJtDnIzJHpCMKu1WJkU8HR8SH1TB76cK9flw9jTuU'

# Google Sheets API 스코프
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


def get_credentials():
    """
    Google API 인증 정보 가져오기
    """
    try:
        # 환경 변수에서 인증 정보 가져오기 (배포 시)
        creds_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
        if creds_json:
            import json
            creds_info = json.loads(creds_json)
            credentials = service_account.Credentials.from_service_account_info(
                creds_info, scopes=SCOPES)
            return credentials
        
        # 로컬 개발용: service_account.json 파일 사용
        creds_path = os.path.join(os.path.dirname(__file__), '../../service_account.json')
        if os.path.exists(creds_path):
            credentials = service_account.Credentials.from_service_account_file(
                creds_path, scopes=SCOPES)
            return credentials
        
        return None
    except Exception as e:
        print(f"인증 정보 로드 실패: {e}")
        return None


def get_sheet_names():
    """
    스프레드시트의 모든 시트 이름 가져오기
    """
    try:
        credentials = get_credentials()
        if not credentials:
            return []
        
        service = build('sheets', 'v4', credentials=credentials)
        sheet_metadata = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        sheets = sheet_metadata.get('sheets', [])
        
        sheet_names = []
        for sheet in sheets:
            title = sheet.get('properties', {}).get('title', '')
            # 월별 시트만 가져오기 (예: "2025년11월", "2025년12월" 등)
            if '년' in title and '월' in title:
                sheet_names.append(title)
        
        # 정렬 (최신순)
        sheet_names.sort(reverse=True)
        return sheet_names
        
    except Exception as e:
        print(f'시트 목록 가져오기 실패: {e}')
        return []


def get_returns_by_company(company, sheet_name, role):
    """
    화주사별 반품 데이터 조회
    
    Args:
        company: 화주명
        sheet_name: 시트명 (예: "2025년11월")
        role: 권한 ("관리자" 또는 "화주사")
    
    Returns:
        dict: {
            'success': bool,
            'data': list,
            'count': int,
            'message': str
        }
    """
    try:
        credentials = get_credentials()
        if not credentials:
            return {
                'success': False,
                'data': [],
                'count': 0,
                'message': '서버 인증 오류가 발생했습니다.'
            }
        
        service = build('sheets', 'v4', credentials=credentials)
        sheet = service.spreadsheets()
        
        # 시트명이 없으면 현재 월 시트 사용
        if not sheet_name:
            today = datetime.now()
            sheet_name = f"{today.year}년{today.month}월"
        
        # 데이터 읽기 (3행부터, A~O열)
        range_name = f'{sheet_name}!A3:O'
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        
        # Rich text 값 읽기 (사진 링크 추출용)
        result_rich = sheet.get(
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
                        # 하이퍼링크 추출
                        links = []
                        if 'textFormatRuns' in cell.get('effectiveFormat', {}):
                            # 텍스트 포맷에서 링크 추출 (간단한 방법)
                            pass
                        rich_row.append(links)
                    rich_data.append(rich_row)
        
        results = []
        is_admin = (role and role.strip() == '관리자')
        
        for i, row in enumerate(values):
            if len(row) < 5:
                continue
            
            row_company = row[1].strip() if len(row) > 1 and row[1] else ''
            customer_name = row[3].strip() if len(row) > 3 and row[3] else ''
            tracking_number = row[4].strip() if len(row) > 4 and row[4] else ''
            
            # 유효한 데이터 확인
            has_customer_name = customer_name and len(customer_name) > 0
            has_tracking_number = tracking_number and len(tracking_number) > 0
            is_numeric_tracking = has_tracking_number and bool(tracking_number.replace(' ', '').replace('-', '').isdigit())
            
            if not (has_customer_name and is_numeric_tracking):
                continue
            
            # 권한 확인
            should_include = is_admin or (row_company == company)
            if not should_include:
                continue
            
            # 사진 링크 추출 (K열, 10번 인덱스)
            photo_links = []
            if len(row) > 10 and row[10]:
                # 간단한 하이퍼링크 추출 (나중에 개선)
                photo_text = row[10]
                # 하이퍼링크는 rich text에서 추출해야 함 (현재는 텍스트만)
                if photo_text:
                    photo_links.append({'text': photo_text, 'url': ''})
            
            result_item = {
                'rowIndex': i + 3,  # 실제 시트 행 번호
                '반품 접수일': row[0] if len(row) > 0 else '',
                '화주명': row_company,
                '제품': row[2] if len(row) > 2 else '',
                '고객명': customer_name,
                '송장번호': tracking_number,
                '반품/교환/오배송': row[5] if len(row) > 5 else '',
                '재고상태': row[6] if len(row) > 6 else '',
                '검품유무': row[7] if len(row) > 7 else '',
                '처리완료': row[8] if len(row) > 8 else '',
                '비고': row[9] if len(row) > 9 else '',
                '사진': photo_links,
                '다른외부택배사': row[11] if len(row) > 11 else '',
                '배송비': row[12] if len(row) > 12 else '',
                '화주사요청': row[13] if len(row) > 13 else '',
                '화주사확인완료': row[14] if len(row) > 14 else ''
            }
            
            results.append(result_item)
        
        # 최신순 정렬
        results.sort(key=lambda x: (
            x['반품 접수일'] if x['반품 접수일'] else '',
        ), reverse=True)
        
        return {
            'success': True,
            'data': results,
            'count': len(results),
            'message': f'{len(results)}건의 데이터를 조회했습니다.'
        }
        
    except HttpError as error:
        print(f'HTTP 에러 발생: {error}')
        return {
            'success': False,
            'data': [],
            'count': 0,
            'message': f'데이터 조회 중 오류: {str(error)}'
        }
    except Exception as e:
        print(f'데이터 조회 오류: {e}')
        return {
            'success': False,
            'data': [],
            'count': 0,
            'message': f'데이터 조회 중 오류: {str(e)}'
        }


@returns_bp.route('/sheets', methods=['GET'])
def get_sheets():
    """
    사용 가능한 시트 목록 조회 API
    
    Returns:
        {
            "success": bool,
            "sheets": list,
            "message": str
        }
    """
    try:
        sheet_names = get_sheet_names()
        return jsonify({
            'success': True,
            'sheets': sheet_names,
            'message': f'{len(sheet_names)}개의 시트를 찾았습니다.'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'sheets': [],
            'message': f'시트 목록 조회 실패: {str(e)}'
        }), 500


@returns_bp.route('/data', methods=['GET'])
def get_returns():
    """
    화주사별 반품 데이터 조회 API
    
    Query Parameters:
        - company: 화주명 (필수)
        - month: 시트명 (선택, 예: "2025년11월")
        - role: 권한 (선택, "관리자" 또는 "화주사")
    
    Returns:
        {
            "success": bool,
            "data": list,
            "count": int,
            "message": str
        }
    """
    try:
        company = request.args.get('company', '').strip()
        month = request.args.get('month', '').strip()
        role = request.args.get('role', '').strip()
        
        if not company:
            return jsonify({
                'success': False,
                'data': [],
                'count': 0,
                'message': '화주명이 필요합니다.'
            }), 400
        
        result = get_returns_by_company(company, month, role)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'data': [],
            'count': 0,
            'message': f'데이터 조회 중 오류: {str(e)}'
        }), 500


@returns_bp.route('/save-request', methods=['POST'])
def save_request():
    """
    화주사 요청사항 저장 API
    
    Request Body:
        {
            "rowIndex": int,
            "month": str,
            "requestText": str
        }
    
    Returns:
        {
            "success": bool,
            "message": str
        }
    """
    try:
        data = request.get_json()
        row_index = data.get('rowIndex')
        month = data.get('month', '').strip()
        request_text = data.get('requestText', '').strip()
        
        if not row_index or not request_text:
            return jsonify({
                'success': False,
                'message': '필수 정보가 누락되었습니다.'
            }), 400
        
        credentials = get_credentials()
        if not credentials:
            return jsonify({
                'success': False,
                'message': '서버 인증 오류가 발생했습니다.'
            }), 500
        
        service = build('sheets', 'v4', credentials=credentials)
        sheet = service.spreadsheets()
        
        # 시트명이 없으면 현재 월 시트 사용
        if not month:
            today = datetime.now()
            month = f"{today.year}년{today.month}월"
        
        # N열(화주사요청)과 O열(화주사확인완료) 업데이트
        range_name = f'{month}!N{row_index}:O{row_index}'
        values = [[request_text, '요청완료']]
        
        body = {
            'values': values
        }
        
        result = sheet.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()
        
        return jsonify({
            'success': True,
            'message': '요청사항이 저장되었습니다.'
        })
        
    except HttpError as error:
        print(f'HTTP 에러 발생: {error}')
        return jsonify({
            'success': False,
            'message': f'저장 중 오류: {str(error)}'
        }), 500
    except Exception as e:
        print(f'저장 오류: {e}')
        return jsonify({
            'success': False,
            'message': f'저장 중 오류: {str(e)}'
        }), 500


@returns_bp.route('/mark-completed', methods=['POST'])
def mark_completed():
    """
    처리완료 표시 API (관리자 전용)
    
    Request Body:
        {
            "rowIndex": int,
            "month": str,
            "managerName": str
        }
    
    Returns:
        {
            "success": bool,
            "message": str
        }
    """
    try:
        data = request.get_json()
        row_index = data.get('rowIndex')
        month = data.get('month', '').strip()
        manager_name = data.get('managerName', '').strip()
        
        if not row_index or not manager_name:
            return jsonify({
                'success': False,
                'message': '필수 정보가 누락되었습니다.'
            }), 400
        
        credentials = get_credentials()
        if not credentials:
            return jsonify({
                'success': False,
                'message': '서버 인증 오류가 발생했습니다.'
            }), 500
        
        service = build('sheets', 'v4', credentials=credentials)
        sheet = service.spreadsheets()
        
        # 시트명이 없으면 현재 월 시트 사용
        if not month:
            today = datetime.now()
            month = f"{today.year}년{today.month}월"
        
        # I열(처리완료) 업데이트
        range_name = f'{month}!I{row_index}'
        values = [[manager_name]]
        
        body = {
            'values': values
        }
        
        result = sheet.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()
        
        return jsonify({
            'success': True,
            'message': '처리완료로 표시되었습니다.'
        })
        
    except HttpError as error:
        print(f'HTTP 에러 발생: {error}')
        return jsonify({
            'success': False,
            'message': f'저장 중 오류: {str(error)}'
        }), 500
    except Exception as e:
        print(f'저장 오류: {e}')
        return jsonify({
            'success': False,
            'message': f'저장 중 오류: {str(e)}'
        }), 500


@returns_bp.route('/health', methods=['GET'])
def health_check():
    """
    API 상태 확인
    """
    return jsonify({
        'status': 'ok',
        'service': 'returns_api',
        'message': '반품 데이터 API가 정상 작동 중입니다.'
    })

