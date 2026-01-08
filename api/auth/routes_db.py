"""
인증 API 라우트 (SQLite 데이터베이스 기반)
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
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
        try:
            company = get_company_by_username(username)
            print(f"🔍 계정 조회 결과: {company}")
        except Exception as db_error:
            print(f"❌ 데이터베이스 조회 오류: {db_error}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'데이터베이스 조회 중 오류가 발생했습니다: {str(db_error)}'
            }), 500
        
        if not company:
            print(f"⚠️ 계정을 찾을 수 없음: {username}")
            return jsonify({
                'success': False,
                'message': '아이디 또는 비밀번호가 일치하지 않습니다.'
            }), 401
        
        # 비활성화된 계정 체크
        is_active = company.get('is_active')
        # SQLite는 INTEGER (1/0), PostgreSQL은 BOOLEAN (True/False)
        if is_active is False or is_active == 0 or (is_active is None and company.get('id')):
            # is_active가 None인 경우 기본값은 True이므로, 명시적으로 False나 0인 경우만 비활성화
            if is_active is False or is_active == 0:
                return jsonify({
                    'success': False,
                    'message': '계약이 종료되었거나 비활성화된 계정입니다.'
                }), 403
        
        # 비밀번호 확인
        print(f"🔐 비밀번호 확인: 입력된 비밀번호 길이={len(password)}, 저장된 비밀번호 길이={len(company.get('password', ''))}")
        if company.get('password') != password:
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
        
        # 필수 필드 처리 (None 체크)
        company_name = (data.get('company_name') or '').strip()
        username = (data.get('username') or '').strip()
        password = (data.get('password') or '').strip()
        role = (data.get('role') or '').strip() or '화주사'
        
        # 선택 필드 처리 (None 또는 빈 문자열 체크)
        business_number_raw = data.get('business_number')
        business_number = business_number_raw.strip() if business_number_raw else None
        
        business_name_raw = data.get('business_name')
        business_name = business_name_raw.strip() if business_name_raw else None
        
        business_address_raw = data.get('business_address')
        business_address = business_address_raw.strip() if business_address_raw else None
        
        business_tel_raw = data.get('business_tel')
        business_tel = business_tel_raw.strip() if business_tel_raw else None
        
        business_email_raw = data.get('business_email')
        business_email = business_email_raw.strip() if business_email_raw else None
        
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
        try:
            print(f"📝 화주사 계정 생성 시도 - company_name: '{company_name}', username: '{username}', role: '{role}'")
            
            # create_company 함수 호출 (True/False 반환)
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
            
            print(f"📝 create_company 반환값: {success} (타입: {type(success)})")
            
            if success:
                print(f"✅ 화주사 계정 생성 성공: {company_name} ({username})")
                # 생성된 계정 확인
                created_company = get_company_by_username(username)
                if created_company:
                    print(f"✅ 생성된 계정 확인: {created_company.get('company_name')} ({created_company.get('username')})")
                else:
                    print(f"⚠️ 생성된 계정을 찾을 수 없음: {username}")
                
                return jsonify({
                    'success': True,
                    'message': '화주사 계정이 생성되었습니다.'
                })
            else:
                print(f"❌ 화주사 계정 생성 실패: {company_name} ({username}) - create_company가 False 반환")
                # 중복 확인
                existing = get_company_by_username(username)
                if existing:
                    return jsonify({
                        'success': False,
                        'message': '이미 사용 중인 아이디입니다.'
                    }), 400
                else:
                    return jsonify({
                        'success': False,
                        'message': '화주사 계정 생성에 실패했습니다. (알 수 없는 오류)'
                    }), 500
        except Exception as e:
            print(f"❌ 화주사 계정 생성 중 예외 발생: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'화주사 계정 생성 중 오류가 발생했습니다: {str(e)}'
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
    화주사 정보 업데이트 API (사업자 정보 + 검색 키워드)
    
    Request Body:
        {
            "username": "아이디",
            "business_number": "사업자번호" (선택),
            "business_name": "사업자명" (선택),
            "business_address": "주소" (선택),
            "business_tel": "전화번호" (선택),
            "business_email": "이메일" (선택),
            "search_keywords": "검색 키워드 (쉼표로 구분, 예: tks,TKS컴퍼니)" (선택)
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
        
        # None 체크 후 strip 처리
        business_number_val = data.get('business_number')
        business_number = business_number_val.strip() if business_number_val else None
        
        business_name_val = data.get('business_name')
        business_name = business_name_val.strip() if business_name_val else None
        
        business_address_val = data.get('business_address')
        business_address = business_address_val.strip() if business_address_val else None
        
        business_tel_val = data.get('business_tel')
        business_tel = business_tel_val.strip() if business_tel_val else None
        
        business_email_val = data.get('business_email')
        business_email = business_email_val.strip() if business_email_val else None
        
        # 화주사 정보 업데이트
        search_keywords_val = data.get('search_keywords')
        search_keywords = search_keywords_val.strip() if search_keywords_val else None
        
        success = update_company_info(
            username=username,
            business_number=business_number,
            business_name=business_name,
            business_address=business_address,
            business_tel=business_tel,
            business_email=business_email,
            search_keywords=search_keywords
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
        
        # 비밀번호 필드는 제외하고 datetime 필드 처리
        for company in companies:
            if not isinstance(company, dict):
                print(f"⚠️ [get_companies] company가 dict가 아님: {type(company)}, 값: {company}")
                continue
            if 'password' in company:
                del company['password']
            # datetime 필드를 문자열로 변환 (JSON 직렬화를 위해)
            for key, value in company.items():
                if isinstance(value, datetime):
                    company[key] = value.strftime('%Y-%m-%d %H:%M:%S') if value else None
        
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


@auth_bp.route('/my-info', methods=['GET'])
def get_my_info():
    """
    현재 로그인한 사용자의 정보 조회 API
    
    Query Parameters:
        username: str (필수)
    
    Returns:
        {
            "success": bool,
            "data": Dict (화주사 정보, 비밀번호 제외)
        }
    """
    try:
        username = request.args.get('username', '').strip()
        
        if not username:
            return jsonify({
                'success': False,
                'message': '아이디가 필요합니다.'
            }), 400
        
        company = get_company_by_username(username)
        
        if not company:
            return jsonify({
                'success': False,
                'message': '화주사 정보를 찾을 수 없습니다.'
            }), 404
        
        # 비밀번호 필드 제외
        company_info = {k: v for k, v in company.items() if k != 'password'}
        
        return jsonify({
            'success': True,
            'data': company_info
        })
        
    except Exception as e:
        print(f"❌ 화주사 정보 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'화주사 정보 조회 중 오류가 발생했습니다: {str(e)}'
        }), 500


@auth_bp.route('/health', methods=['GET'])
def health_check():
    """헬스 체크"""
    return jsonify({
        'status': 'ok',
        'message': '인증 API가 정상적으로 작동하고 있습니다.'
    })

