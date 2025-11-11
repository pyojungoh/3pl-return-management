"""
인증 API 라우트 (SQLite 데이터베이스 기반)
"""
from flask import Blueprint, request, jsonify
from api.database.models import (
    get_company_by_username,
    get_all_companies,
    get_companies_statistics,
    get_available_months,
    create_company,
    delete_company,
    update_company_password,
    update_company_password_by_id,
    update_company_certificate,
    update_company_info,
    update_last_login
)

# Blueprint 생성
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    로그인 API (데이터베이스 기반)
    
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
        
        # 데이터베이스에서 계정 정보 조회
        company = get_company_by_username(username)
        
        if not company:
            return jsonify({
                'success': False,
                'message': '아이디 또는 비밀번호가 일치하지 않습니다.'
            }), 401
        
        # 비밀번호 확인
        if company['password'] != password:
            return jsonify({
                'success': False,
                'message': '아이디 또는 비밀번호가 일치하지 않습니다.'
            }), 401
        
        # 로그인 성공 - 최근 로그인 시간 업데이트
        update_last_login(username)
        
        # 로그인 성공
        role = (company['role'] or '화주사').strip()
        print(f"✅ 로그인 성공: {company['company_name']} ({company['username']}), 권한: '{role}'")
        
        return jsonify({
            'success': True,
            'company': company['company_name'],
            'username': company['username'],
            'role': role,
            'message': '로그인 성공'
        })
        
    except Exception as e:
        print(f"❌ 로그인 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'로그인 중 오류가 발생했습니다: {str(e)}'
        }), 500


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    화주사 회원가입 API
    
    Request Body:
        {
            "company_name": "화주사명",
            "username": "아이디",
            "password": "비밀번호",
            "business_number": "사업자번호" (선택),
            "business_name": "사업자명" (선택),
            "business_address": "주소" (선택),
            "business_tel": "전화번호" (선택),
            "business_email": "이메일" (선택)
        }
    
    Returns:
        {
            "success": bool,
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
        
        company_name = data.get('company_name', '').strip()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        role = data.get('role', '').strip() or '화주사'
        business_number = data.get('business_number', '').strip() or None
        business_name = data.get('business_name', '').strip() or None
        business_address = data.get('business_address', '').strip() or None
        business_tel = data.get('business_tel', '').strip() or None
        business_email = data.get('business_email', '').strip() or None
        
        if not company_name or not username or not password:
            return jsonify({
                'success': False,
                'message': '화주사명, 아이디, 비밀번호는 필수입니다.'
            }), 400
        
        if role not in ['화주사', '관리자']:
            return jsonify({
                'success': False,
                'message': '권한은 화주사 또는 관리자 중 하나를 선택해야 합니다.'
            }), 400
        
        # 아이디 중복 확인
        existing = get_company_by_username(username)
        if existing:
            return jsonify({
                'success': False,
                'message': '이미 사용 중인 아이디입니다.'
            }), 400
        
        # 화주사 계정 생성
        success = create_company(
            company_name=company_name,
            username=username,
            password=password,
            role=role,
            business_number=business_number,
            business_name=business_name,
            business_address=business_address,
            business_tel=business_tel,
            business_email=business_email
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': '화주사 계정이 생성되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': '화주사 계정 생성에 실패했습니다.'
            }), 500
        
    except Exception as e:
        print(f"❌ 회원가입 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'회원가입 중 오류가 발생했습니다: {str(e)}'
        }), 500


@auth_bp.route('/change-password', methods=['POST'])
def change_password():
    """
    비밀번호 변경 API
    
    Request Body:
        {
            "username": "아이디",
            "old_password": "기존 비밀번호",
            "new_password": "새 비밀번호"
        }
    
    Returns:
        {
            "success": bool,
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
        old_password = data.get('old_password', '').strip()
        new_password = data.get('new_password', '').strip()
        
        if not username or not old_password or not new_password:
            return jsonify({
                'success': False,
                'message': '아이디, 기존 비밀번호, 새 비밀번호를 모두 입력해주세요.'
            }), 400
        
        # 비밀번호 변경
        success = update_company_password(username, old_password, new_password)
        
        if success:
            return jsonify({
                'success': True,
                'message': '비밀번호가 변경되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': '기존 비밀번호가 일치하지 않거나 변경에 실패했습니다.'
            }), 400
        
    except Exception as e:
        print(f"❌ 비밀번호 변경 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'비밀번호 변경 중 오류가 발생했습니다: {str(e)}'
        }), 500


@auth_bp.route('/update-info', methods=['POST'])
def update_info():
    """
    화주사 정보 업데이트 API (사업자 정보)
    
    Request Body:
        {
            "username": "아이디",
            "business_number": "사업자번호" (선택),
            "business_name": "사업자명" (선택),
            "business_address": "주소" (선택),
            "business_tel": "전화번호" (선택),
            "business_email": "이메일" (선택)
        }
    
    Returns:
        {
            "success": bool,
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
        
        if not username:
            return jsonify({
                'success': False,
                'message': '아이디를 입력해주세요.'
            }), 400
        
        business_number = data.get('business_number', '').strip() or None
        business_name = data.get('business_name', '').strip() or None
        business_address = data.get('business_address', '').strip() or None
        business_tel = data.get('business_tel', '').strip() or None
        business_email = data.get('business_email', '').strip() or None
        
        # 화주사 정보 업데이트
        success = update_company_info(
            username=username,
            business_number=business_number,
            business_name=business_name,
            business_address=business_address,
            business_tel=business_tel,
            business_email=business_email
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': '화주사 정보가 업데이트되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': '화주사 정보 업데이트에 실패했습니다.'
            }), 500
        
    except Exception as e:
        print(f"❌ 화주사 정보 업데이트 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'화주사 정보 업데이트 중 오류가 발생했습니다: {str(e)}'
        }), 500


@auth_bp.route('/companies', methods=['GET'])
def get_companies():
    """
    모든 화주사 목록 조회 API
    
    Returns:
        {
            "success": bool,
            "companies": List[Dict],
            "count": int
        }
    """
    try:
        companies = get_all_companies()
        statistics = get_companies_statistics()
        
        # 비밀번호 필드는 제외
        for company in companies:
            if 'password' in company:
                del company['password']
        
        return jsonify({
            'success': True,
            'companies': companies,
            'count': len(companies),
            'statistics': statistics
        })
        
    except Exception as e:
        print(f"❌ 화주사 목록 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'화주사 목록 조회 중 오류가 발생했습니다: {str(e)}',
            'companies': [],
            'count': 0,
            'statistics': {
                'admin_count': 0,
                'company_count': 0,
                'total_count': 0
            }
        }), 500


@auth_bp.route('/company/<int:company_id>', methods=['DELETE'])
def delete_company_route(company_id):
    """
    화주사 계정 삭제 API
    
    Returns:
        {
            "success": bool,
            "message": str
        }
    """
    try:
        success = delete_company(company_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': '화주사 계정이 삭제되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': '화주사 계정 삭제에 실패했습니다.'
            }), 400
        
    except Exception as e:
        print(f"❌ 화주사 삭제 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'화주사 삭제 중 오류가 발생했습니다: {str(e)}'
        }), 500


@auth_bp.route('/company/<int:company_id>/password', methods=['POST'])
def change_company_password_by_id(company_id):
    """
    화주사 비밀번호 변경 API (ID로)
    
    Body:
        {
            "new_password": str
        }
    
    Returns:
        {
            "success": bool,
            "message": str
        }
    """
    try:
        data = request.get_json()
        new_password = data.get('new_password')
        
        if not new_password:
            return jsonify({
                'success': False,
                'message': '새 비밀번호를 입력해주세요.'
            }), 400
        
        success = update_company_password_by_id(company_id, new_password)
        
        if success:
            return jsonify({
                'success': True,
                'message': '비밀번호가 변경되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': '비밀번호 변경에 실패했습니다.'
            }), 400
        
    except Exception as e:
        print(f"❌ 비밀번호 변경 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'비밀번호 변경 중 오류가 발생했습니다: {str(e)}'
        }), 500


@auth_bp.route('/company/<int:company_id>/certificate', methods=['POST'])
def upload_company_certificate(company_id):
    """
    화주사 사업자 등록증 업로드 API
    
    Body:
        {
            "certificate_url": str
        }
    
    Returns:
        {
            "success": bool,
            "message": str
        }
    """
    try:
        data = request.get_json()
        certificate_url = data.get('certificate_url')
        
        if not certificate_url:
            return jsonify({
                'success': False,
                'message': '사업자 등록증 URL이 필요합니다.'
            }), 400
        
        success = update_company_certificate(company_id, certificate_url)
        
        if success:
            return jsonify({
                'success': True,
                'message': '사업자 등록증이 업로드되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': '사업자 등록증 업로드에 실패했습니다.'
            }), 400
        
    except Exception as e:
        print(f"❌ 사업자 등록증 업로드 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'사업자 등록증 업로드 중 오류가 발생했습니다: {str(e)}'
        }), 500


@auth_bp.route('/months', methods=['GET'])
def get_months():
    """
    사용 가능한 월 목록 조회 API
    
    Returns:
        {
            "success": bool,
            "months": List[str],
            "current_month": str
        }
    """
    try:
        from datetime import datetime
        
        months = get_available_months()
        now = datetime.now()
        current_month = f"{now.year}년{now.month}월"
        
        return jsonify({
            'success': True,
            'months': months,
            'current_month': current_month
        })
        
    except Exception as e:
        print(f"❌ 월 목록 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'월 목록 조회 중 오류가 발생했습니다: {str(e)}',
            'months': [],
            'current_month': ''
        }), 500


@auth_bp.route('/health', methods=['GET'])
def health_check():
    """헬스 체크"""
    return jsonify({
        'status': 'ok',
        'message': '인증 API가 정상적으로 작동하고 있습니다.'
    })

