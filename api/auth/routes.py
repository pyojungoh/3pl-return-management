"""
인증 API 라우트 (로그인)
"""
from flask import Blueprint, request, jsonify
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Blueprint 생성
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# 스프레드시트 ID
SPREADSHEET_ID = '1utFJtDnIzJHpCMKu1WJkU8HR8SH1TB76cK9flw9jTuU'
ACCOUNT_SHEET_NAME = '화주사계정'

# Google Sheets API 스코프
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']


def get_credentials():
    """
    Google API 인증 정보 가져오기
    """
    try:
        # 환경 변수에서 인증 정보 가져오기 (배포 시)
        creds_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
        if creds_json:
            try:
                import json
                # JSON 문자열인 경우 파싱
                if isinstance(creds_json, str):
                    creds_info = json.loads(creds_json)
                else:
                    creds_info = creds_json
                
                credentials = service_account.Credentials.from_service_account_info(
                    creds_info, scopes=SCOPES)
                print("✅ 환경 변수에서 인증 정보 로드 성공")
                return credentials
            except json.JSONDecodeError as e:
                print(f"❌ JSON 파싱 오류: {e}")
                print(f"JSON 내용 (처음 100자): {creds_json[:100]}")
                return None
            except Exception as e:
                print(f"❌ 서비스 계정 인증 정보 생성 실패: {e}")
                return None
        
        # 로컬 개발용: service_account.json 파일 사용
        creds_path = os.path.join(os.path.dirname(__file__), '../../service_account.json')
        if os.path.exists(creds_path):
            try:
                credentials = service_account.Credentials.from_service_account_file(
                    creds_path, scopes=SCOPES)
                print("✅ 로컬 파일에서 인증 정보 로드 성공")
                return credentials
            except Exception as e:
                print(f"❌ 로컬 파일 인증 정보 로드 실패: {e}")
                return None
        
        print("❌ 인증 정보를 찾을 수 없습니다. 환경 변수 GOOGLE_SERVICE_ACCOUNT_JSON을 확인하세요.")
        return None
    except Exception as e:
        print(f"❌ 인증 정보 로드 실패: {e}")
        import traceback
        print(traceback.format_exc())
        return None


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    로그인 API
    
    Request Body:
        {
            "username": "아이디",
            "password": "비밀번호"
        }
    
    Returns:
        {
            "success": bool,
            "company": str,
            "username": str,
            "role": str,
            "message": str
        }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '요청 데이터가 없습니다.'
            }), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return jsonify({
                'success': False,
                'message': '아이디와 비밀번호를 입력해주세요.'
            }), 400
        
        # Google Sheets에서 계정 정보 읽기
        print(f"로그인 시도: {username}")
        credentials = get_credentials()
        if not credentials:
            error_msg = '서버 인증 오류가 발생했습니다. 환경 변수 GOOGLE_SERVICE_ACCOUNT_JSON을 확인하세요.'
            print(f"❌ {error_msg}")
            return jsonify({
                'success': False,
                'message': error_msg
            }), 500
        
        print("Google Sheets API 호출 시작...")
        service = build('sheets', 'v4', credentials=credentials)
        sheet = service.spreadsheets()
        
        # 화주사계정 시트 데이터 읽기
        range_name = f'{ACCOUNT_SHEET_NAME}!A2:D'  # A열: 화주명, B열: 로그인ID, C열: 비밀번호, D열: 권한
        print(f"시트 읽기: {SPREADSHEET_ID}, 범위: {range_name}")
        
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        print(f"시트 데이터 행 수: {len(values)}")
        
        # 로그인 정보 확인
        for i, row in enumerate(values):
            if len(row) < 4:
                continue
            
            company = row[0].strip() if row[0] else ''
            login_id = row[1].strip() if len(row) > 1 and row[1] else ''
            login_pw = row[2].strip() if len(row) > 2 and row[2] else ''
            role = row[3].strip() if len(row) > 3 and row[3] else ''
            
            if login_id == username and login_pw == password:
                print(f"✅ 로그인 성공: {company}, 권한: {role}")
                return jsonify({
                    'success': True,
                    'company': company,
                    'username': username,
                    'role': role,
                    'message': '로그인 성공'
                })
        
        # 로그인 실패
        print(f"❌ 로그인 실패: 아이디 또는 비밀번호 불일치")
        return jsonify({
            'success': False,
            'message': '아이디 또는 비밀번호가 일치하지 않습니다.'
        }), 401
        
    except HttpError as error:
        error_details = f'HTTP 에러 발생: {error}'
        print(f"❌ {error_details}")
        import traceback
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'Google Sheets 접근 오류: {str(error)}'
        }), 500
    except Exception as e:
        error_details = f'로그인 오류: {e}'
        print(f"❌ {error_details}")
        import traceback
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'로그인 중 오류가 발생했습니다: {str(e)}'
        }), 500


@auth_bp.route('/health', methods=['GET'])
def health_check():
    """
    인증 API 상태 확인
    """
    return jsonify({
        'status': 'ok',
        'service': 'auth_api',
        'message': '인증 API가 정상 작동 중입니다.'
    })

