"""
파레트 보관료 관리 시스템 - API 라우트
"""
from flask import Blueprint, request, jsonify, Response
from datetime import date, datetime
from api.pallets.models import (
    update_pallet_status_batch,
    create_pallet, update_pallet_status, get_pallet_by_id, get_pallets,
    calculate_fee, get_pallet_fee, set_pallet_fee,
    generate_monthly_settlement, get_settlements, get_settlement_detail,
    update_settlement_status, delete_settlement, delete_settlement,
    get_monthly_revenue, get_daily_fees_batch
)

# Blueprint 생성
pallets_bp = Blueprint('pallets', __name__, url_prefix='/api/pallets')


def get_user_context():
    """
    요청 헤더에서 사용자 정보 추출
    Google Apps Script 등 외부 호출 시 헤더가 없을 수 있으므로 기본값 제공
    """
    # 헤더 값 디코딩 (encodeURIComponent로 인코딩된 값)
    role_encoded = request.headers.get('X-User-Role', '')
    company_encoded = request.headers.get('X-Company-Name', '')
    username_encoded = request.headers.get('X-User-Name', '') or request.headers.get('X-Username', '')
    
    # API 키 확인 (Google Apps Script 등 외부 호출용)
    api_key = request.headers.get('X-API-Key', '')
    
    import urllib.parse
    role = urllib.parse.unquote(role_encoded) if role_encoded else ''
    company_name = urllib.parse.unquote(company_encoded) if company_encoded else ''
    username = urllib.parse.unquote(username_encoded) if username_encoded else ''
    
    # 헤더가 없고 API 키가 있는 경우 (Google Apps Script 등 외부 호출)
    if not role and not company_name and not username and api_key:
        # API 키 검증 (환경 변수에서 가져오거나 설정 파일에서)
        import os
        valid_api_key = os.getenv('PALLET_SYNC_API_KEY', '')
        if api_key == valid_api_key or not valid_api_key:  # API 키가 설정되지 않았으면 허용
            role = '관리자'  # 외부 동기화는 관리자 권한으로 처리
            username = 'Google Forms Sync'
            # company_name은 요청 body에서 가져옴
    
    return role, company_name, username


# ========================================
# 파레트 관리 API
# ========================================

@pallets_bp.route('/inbound', methods=['POST'])
def pallet_inbound():
    """
    파레트 입고 (단일/대량)
    Google Apps Script 등 외부 호출 지원
    """
    try:
        role, company_name, username = get_user_context()
        data = request.get_json() or {}
        
        # 디버깅: 요청 데이터 로깅
        print(f"[DEBUG] pallet_inbound 요청 - role: {role}, company_name: {company_name}, username: {username}")
        print(f"[DEBUG] pallet_inbound 요청 - data keys: {list(data.keys())}")
        print(f"[DEBUG] pallet_inbound 요청 - data.get('company_name'): {data.get('company_name')}")
        print(f"[DEBUG] pallet_inbound 요청 - data.get('pallets'): {type(data.get('pallets'))}")
        if isinstance(data.get('pallets'), list):
            print(f"[DEBUG] pallet_inbound 요청 - pallets count: {len(data.get('pallets', []))}")
            if len(data.get('pallets', [])) > 0:
                print(f"[DEBUG] pallet_inbound 요청 - first pallet: {data.get('pallets')[0]}")
        
        # Google Apps Script 등 외부 호출 시 username이 없으면 기본값 설정
        if not username:
            username = 'Google Forms Sync'
        
        # 대량 입고인지 먼저 확인
        is_bulk_inbound = isinstance(data.get('pallets'), list)
        
        # 관리자가 아닌 경우, 헤더의 company_name 사용
        # 외부 호출 시 data에 company_name이 있으면 사용
        if role != '관리자':
            data['company_name'] = company_name or data.get('company_name', '')
        
        # 관리자인 경우, 요청 본문의 company_name 사용
        # 단, 대량 입고인 경우는 각 pallet_data에 company_name이 있는지 확인
        if role == '관리자':
            if is_bulk_inbound:
                # 대량 입고: 각 pallet_data에 company_name이 있는지 확인
                missing_company = False
                for pallet_data in data.get('pallets', []):
                    company_name_value = pallet_data.get('company_name')
                    if not company_name_value or not str(company_name_value).strip():
                        missing_company = True
                        print(f"[DEBUG] 화주사명 누락 - pallet_data: {pallet_data}")
                        break
                if missing_company:
                    return jsonify({
                        'success': False,
                        'message': '화주사명이 필요합니다. (대량 입고의 경우 각 품목에 화주사명이 필요합니다)'
                    }), 400
            else:
                # 단일 입고: 최상위 company_name 확인
                company_name_value = data.get('company_name')
                if not company_name_value or not str(company_name_value).strip():
                    print(f"[DEBUG] 화주사명 누락 - data: {data}")
                    return jsonify({
                        'success': False,
                        'message': '화주사명이 필요합니다.'
                    }), 400
        
        # 대량 입고 처리
        if is_bulk_inbound:
            # 대량 입고
            results = []
            errors = []
            
            for pallet_data in data['pallets']:
                if role != '관리자':
                    pallet_data['company_name'] = company_name
                
                success, message, pallet = create_pallet(
                    pallet_id=pallet_data.get('pallet_id'),  # pallet_id 전달
                    company_name=pallet_data.get('company_name'),
                    product_name=pallet_data.get('product_name'),
                    in_date=pallet_data.get('in_date'),
                    storage_location=pallet_data.get('storage_location'),
                    quantity=pallet_data.get('quantity', 1),
                    is_service=pallet_data.get('is_service', False),
                    notes=pallet_data.get('notes'),
                    created_by=username
                )
                
                if success:
                    results.append(pallet)
                else:
                    errors.append(message)
            
            if results:
                return jsonify({
                    'success': True,
                    'message': f'{len(results)}개 파레트 입고 완료',
                    'data': results,
                    'errors': errors if errors else None
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'message': '모든 파레트 입고 실패',
                    'errors': errors
                }), 400
        else:
            # 단일 입고
            request_pallet_id = data.get('pallet_id')
            print(f"[DEBUG] 단일 입고 - request_pallet_id: {request_pallet_id}")
            
            success, message, pallet = create_pallet(
                pallet_id=request_pallet_id,  # Google Apps Script에서 보낸 pallet_id 사용
                company_name=data.get('company_name'),
                product_name=data.get('product_name'),
                in_date=data.get('in_date'),
                storage_location=data.get('storage_location'),
                quantity=data.get('quantity', 1),
                is_service=data.get('is_service', False),
                notes=data.get('notes'),
                created_by=username
            )
            
            print(f"[DEBUG] create_pallet 결과 - success: {success}, message: {message}")
            
            if success:
                return jsonify({
                    'success': True,
                    'message': message,
                    'data': pallet
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'message': message
                }), 400
                
    except Exception as e:
        print(f"파레트 입고 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'파레트 입고 실패: {str(e)}'
        }), 500


@pallets_bp.route('/outbound', methods=['POST'])
def pallet_outbound():
    """
    파레트 보관종료 (단일 또는 대량 처리)
    
    Request Body:
        - pallet_id: 단일 파레트 ID (기존 방식, 호환성 유지)
        - pallet_ids: 파레트 ID 배열 (대량 처리)
        - out_date: 보관종료일 (YYYY-MM-DD 형식, 선택사항, 기본값: 오늘)
        - notes: 비고 (선택사항)
    """
    try:
        from datetime import datetime
        role, company_name, username = get_user_context()
        data = request.get_json() or {}
        
        pallet_id = data.get('pallet_id')  # 단일 처리 (호환성)
        pallet_ids = data.get('pallet_ids')  # 대량 처리
        out_date_str = data.get('out_date')
        notes = data.get('notes')
        
        # 날짜 파싱
        out_date = None
        if out_date_str:
            try:
                out_date = datetime.strptime(out_date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': '날짜 형식이 올바르지 않습니다. (YYYY-MM-DD 형식 필요)'
                }), 400
        
        # 대량 처리 모드
        if pallet_ids:
            if not isinstance(pallet_ids, list) or len(pallet_ids) == 0:
                return jsonify({
                    'success': False,
                    'message': '파레트 ID 배열이 필요합니다.'
                }), 400
            
            result = update_pallet_status_batch(
                pallet_ids=pallet_ids,
                out_date=out_date,
                processed_by=username,
                notes=notes
            )
            
            if result['success_count'] > 0:
                message = f"{result['success_count']}개 파레트 보관종료 완료"
                if result['failed_count'] > 0:
                    message += f", {result['failed_count']}개 실패"
                
                return jsonify({
                    'success': True,
                    'message': message,
                    'processed': result['processed'],
                    'failed': result['failed'],
                    'errors': result['errors'],
                    'success_count': result['success_count'],
                    'failed_count': result['failed_count']
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'message': '모든 파레트 보관종료에 실패했습니다.',
                    'failed': result['failed'],
                    'errors': result['errors']
                }), 400
        
        # 단일 처리 모드 (기존 방식, 호환성 유지)
        elif pallet_id:
            if not pallet_id:
                return jsonify({
                    'success': False,
                    'message': '파레트 ID가 필요합니다.'
                }), 400
            
            success, message, pallet = update_pallet_status(
                pallet_id=pallet_id,
                out_date=out_date,
                processed_by=username,
                notes=notes
            )
            
            if success:
                return jsonify({
                    'success': True,
                    'message': message,
                    'data': pallet
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'message': message
                }), 400
        else:
            return jsonify({
                'success': False,
                'message': '파레트 ID 또는 파레트 ID 배열이 필요합니다.'
            }), 400
            
    except Exception as e:
        print(f"파레트 보관종료 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'파레트 보관종료 실패: {str(e)}'
        }), 500


@pallets_bp.route('/list', methods=['GET'])
def pallet_list():
    """
    파레트 목록 조회
    
    Query Parameters:
        - company: 화주사명 (관리자 모드에서 필터링용)
        - status: 상태 필터 (입고됨, 보관종료, 서비스, 전체)
        - month: 월 필터 (YYYY-MM 형식)
        - pallet_id: 파레트 ID 부분 일치 검색
        - product_name: 품목명 부분 일치 검색
    """
    try:
        role, company_name, username = get_user_context()
        
        filter_company = request.args.get('company', '').strip()
        status = request.args.get('status', '전체')
        month = request.args.get('month')
        pallet_id_filter = request.args.get('pallet_id', '').strip()
        product_name_filter = request.args.get('product_name', '').strip()
        
        # 화주사인 경우 필수 (company_name이 헤더에 있으면 사용)
        if role != '관리자':
            # 관리자가 아니면 항상 자신의 company_name 사용
            final_company = company_name
        else:
            # 관리자인 경우: filter_company가 있으면 그것 사용, 없으면 전체
            final_company = filter_company if filter_company else None
        
        # 상태 필터링 (전체가 아닌 경우에만)
        status_filter = None if status == '전체' else status
        
        pallets = get_pallets(
            company_name=final_company,
            status=status_filter,
            month=month,
            role=role,
            pallet_id=pallet_id_filter if pallet_id_filter else None,
            product_name=product_name_filter if product_name_filter else None
        )
        
        # 보관료 계산 추가 및 date 객체를 문자열로 변환
        from api.pallets.models import calculate_fee, calculate_storage_days, calculate_daily_fee, get_daily_fees_batch
        import math
        from datetime import timedelta
        
        # 현재 월의 시작일과 종료일 계산 (파레트 현황에서 항상 현재 월 기준으로 계산)
        today = date.today()
        current_month_start = date(today.year, today.month, 1)
        if today.month == 12:
            current_month_end = date(today.year + 1, 1, 1) - timedelta(days=1)
        else:
            current_month_end = date(today.year, today.month + 1, 1) - timedelta(days=1)
        
        # month 파라미터가 있으면 해당 월의 시작일과 종료일 계산 (필터용)
        month_start = None
        month_end = None
        if month:
            try:
                year, month_num = map(int, month.split('-'))
                month_start = date(year, month_num, 1)
                if month_num == 12:
                    month_end = date(year + 1, 1, 1) - timedelta(days=1)
                else:
                    month_end = date(year, month_num + 1, 1) - timedelta(days=1)
            except (ValueError, TypeError):
                month_start = None
                month_end = None
        
        # 성능 최적화: 모든 화주사의 일일 보관료를 한 번에 조회 (캐싱)
        # month 파라미터가 있으면 해당 월의 시작일, 없으면 현재 월의 시작일로 조회
        fee_date = month_start if (month and month_start) else current_month_start
        company_names = [p.get('company_name', '') for p in pallets if p.get('company_name')]
        daily_fees_cache = get_daily_fees_batch(company_names, fee_date) if company_names else {}
        default_daily_fee = round(16000 / 30.0, 2)  # 기본값: 533.33원
        
        for pallet in pallets:
            try:
                # date 객체를 그대로 사용 (파싱 오버헤드 제거)
                in_date_obj = pallet.get('in_date')
                if in_date_obj and isinstance(in_date_obj, str):
                    # 문자열인 경우에만 파싱 (호환성 유지)
                    try:
                        in_date_obj = datetime.strptime(in_date_obj, '%Y-%m-%d').date()
                    except (ValueError, TypeError) as e:
                        print(f"⚠️ 입고일 파싱 오류 (pallet_id: {pallet.get('pallet_id')}): {e}")
                        in_date_obj = None
                elif in_date_obj and not isinstance(in_date_obj, date):
                    in_date_obj = None
                
                out_date_obj = pallet.get('out_date')
                if out_date_obj and isinstance(out_date_obj, str):
                    # 문자열인 경우에만 파싱 (호환성 유지)
                    try:
                        out_date_obj = datetime.strptime(out_date_obj, '%Y-%m-%d').date()
                    except (ValueError, TypeError) as e:
                        print(f"⚠️ 보관종료일 파싱 오류 (pallet_id: {pallet.get('pallet_id')}): {e}")
                        out_date_obj = None
                elif out_date_obj and not isinstance(out_date_obj, date):
                    out_date_obj = None
                
                # date 객체를 문자열로 변환 (JSON 직렬화를 위해)
                if in_date_obj and isinstance(in_date_obj, date):
                    pallet['in_date'] = in_date_obj.isoformat()
                elif in_date_obj:
                    pallet['in_date'] = str(in_date_obj)
                
                if out_date_obj and isinstance(out_date_obj, date):
                    pallet['out_date'] = out_date_obj.isoformat()
                elif out_date_obj:
                    pallet['out_date'] = str(out_date_obj)
                
                if in_date_obj:
                    is_service = pallet.get('is_service', 0) == 1
                    
                    # 총보관일수 계산 (입고일부터 보관종료일 또는 현재까지)
                    total_storage_days = calculate_storage_days(
                        in_date_obj,
                        out_date_obj
                    )
                    pallet['total_storage_days'] = total_storage_days
                    
                    # 월보관일수 계산 (month 파라미터가 있으면 해당 월, 없으면 현재 월)
                    if month and month_start and month_end:
                        # month 파라미터가 있으면 해당 월의 보관일수 계산
                        monthly_storage_start = max(in_date_obj, month_start)
                        if out_date_obj:
                            monthly_storage_end = min(out_date_obj, month_end)
                        else:
                            monthly_storage_end = min(month_end, date.today())
                        monthly_storage_days = max(0, (monthly_storage_end - monthly_storage_start).days + 1)
                        # month 파라미터가 있을 때는 storage_days도 해당 월 기준으로 설정
                        pallet['storage_days'] = monthly_storage_days
                        pallet['monthly_storage_days'] = monthly_storage_days
                    else:
                        # month 파라미터가 없으면 현재 월 기준으로 계산
                        monthly_storage_start = max(in_date_obj, current_month_start)
                        if out_date_obj:
                            monthly_storage_end = min(out_date_obj, current_month_end)
                        else:
                            monthly_storage_end = min(current_month_end, date.today())
                        monthly_storage_days = max(0, (monthly_storage_end - monthly_storage_start).days + 1)
                        pallet['monthly_storage_days'] = monthly_storage_days
                        # 호환성을 위해 storage_days는 총보관일수로 설정 (기존 코드와의 호환)
                        pallet['storage_days'] = total_storage_days
                    
                    # 보관료는 월보관일수 기준으로 계산 (캐시에서 조회)
                    if is_service:
                        pallet['current_fee'] = 0
                    else:
                        company_name_key = pallet.get('company_name', '')
                        daily_fee = daily_fees_cache.get(company_name_key, default_daily_fee)
                        calculated_fee = daily_fee * pallet.get('monthly_storage_days', monthly_storage_days)
                        pallet['current_fee'] = math.ceil(calculated_fee / 100) * 100
                else:
                    pallet['total_storage_days'] = 0
                    pallet['monthly_storage_days'] = 0
                    pallet['storage_days'] = 0
                    pallet['current_fee'] = 0
            except Exception as e:
                print(f"⚠️ 파레트 데이터 처리 오류 (pallet_id: {pallet.get('pallet_id')}): {e}")
                import traceback
                traceback.print_exc()
                # 기본값 설정
                pallet['total_storage_days'] = pallet.get('total_storage_days', 0)
                pallet['monthly_storage_days'] = pallet.get('monthly_storage_days', 0)
                pallet['storage_days'] = pallet.get('storage_days', 0)
                pallet['current_fee'] = pallet.get('current_fee', 0)
        
        return jsonify({
            'success': True,
            'data': pallets,
            'count': len(pallets)
        }), 200
        
    except Exception as e:
        print(f"파레트 목록 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'파레트 목록 조회 실패: {str(e)}'
        }), 500


@pallets_bp.route('/<string:pallet_id>', methods=['GET'])
def pallet_detail(pallet_id):
    """
    파레트 상세 조회
    """
    try:
        role, company_name, username = get_user_context()
        
        pallet = get_pallet_by_id(pallet_id)
        if not pallet:
            return jsonify({
                'success': False,
                'message': '파레트를 찾을 수 없습니다.'
            }), 404
        
        # 권한 확인
        if role != '관리자' and pallet.get('company_name') != company_name:
            return jsonify({
                'success': False,
                'message': '권한이 없습니다.'
            }), 403
        
        return jsonify({
            'success': True,
            'data': pallet
        }), 200
        
    except Exception as e:
        print(f"파레트 상세 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'파레트 상세 조회 실패: {str(e)}'
        }), 500


@pallets_bp.route('/<string:pallet_id>', methods=['PUT'])
def pallet_update(pallet_id):
    """
    파레트 정보 수정
    """
    try:
        role, company_name, username = get_user_context()
        
        pallet = get_pallet_by_id(pallet_id)
        if not pallet:
            return jsonify({
                'success': False,
                'message': '파레트를 찾을 수 없습니다.'
            }), 404
        
        # 권한 확인
        if role != '관리자' and pallet.get('company_name') != company_name:
            return jsonify({
                'success': False,
                'message': '권한이 없습니다.'
            }), 403
        
        data = request.get_json() or {}
        # TODO: 파레트 정보 수정 로직 구현
        
        return jsonify({
            'success': True,
            'message': '파레트 정보 수정 완료'
        }), 200
        
    except Exception as e:
        print(f"파레트 정보 수정 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'파레트 정보 수정 실패: {str(e)}'
        }), 500


@pallets_bp.route('/<string:pallet_id>/out-date', methods=['PUT'])
def pallet_update_out_date(pallet_id):
    """
    보관종료된 파레트의 출고일 수정
    """
    try:
        from datetime import datetime
        role, company_name, username = get_user_context()
        
        pallet = get_pallet_by_id(pallet_id)
        if not pallet:
            return jsonify({
                'success': False,
                'message': '파레트를 찾을 수 없습니다.'
            }), 404
        
        # 보관종료된 파레트만 수정 가능
        if pallet.get('status') != '보관종료':
            return jsonify({
                'success': False,
                'message': '보관종료된 파레트만 출고일을 수정할 수 있습니다.'
            }), 400
        
        # 권한 확인
        if role != '관리자' and pallet.get('company_name') != company_name:
            return jsonify({
                'success': False,
                'message': '권한이 없습니다.'
            }), 403
        
        data = request.get_json() or {}
        out_date_str = data.get('out_date')
        notes = data.get('notes')
        
        if not out_date_str:
            return jsonify({
                'success': False,
                'message': '출고일이 필요합니다.'
            }), 400
        
        # 날짜 파싱
        try:
            out_date = datetime.strptime(out_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'message': '날짜 형식이 올바르지 않습니다. (YYYY-MM-DD 형식 필요)'
            }), 400
        
        # 출고일 업데이트
        from api.database.models import get_db_connection, USE_POSTGRESQL
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            if USE_POSTGRESQL:
                cursor.execute('''
                    UPDATE pallets 
                    SET out_date = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE pallet_id = %s
                ''', (out_date, pallet_id))
                
                # 트랜잭션 이력 저장 (출고일 수정)
                cursor.execute('''
                    INSERT INTO pallet_transactions (
                        pallet_id, transaction_type, quantity, transaction_date,
                        processed_by, notes, created_at
                    ) VALUES (%s, %s, %s, CURRENT_TIMESTAMP, %s, %s, CURRENT_TIMESTAMP)
                ''', (pallet_id, '출고일수정', pallet.get('quantity', 1), username, notes))
            else:
                cursor.execute('''
                    UPDATE pallets 
                    SET out_date = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE pallet_id = ?
                ''', (out_date, pallet_id))
                
                # 트랜잭션 이력 저장 (출고일 수정)
                cursor.execute('''
                    INSERT INTO pallet_transactions (
                        pallet_id, transaction_type, quantity, transaction_date,
                        processed_by, notes, created_at
                    ) VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?, CURRENT_TIMESTAMP)
                ''', (pallet_id, '출고일수정', pallet.get('quantity', 1), username, notes))
            
            conn.commit()
            
            # 업데이트된 파레트 정보 조회
            updated_pallet = get_pallet_by_id(pallet_id)
            
            return jsonify({
                'success': True,
                'message': f'출고일이 {out_date_str}로 변경되었습니다.',
                'data': updated_pallet
            }), 200
            
        except Exception as e:
            conn.rollback() if USE_POSTGRESQL else None
            raise e
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        print(f"출고일 수정 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'출고일 수정 실패: {str(e)}'
        }), 500


@pallets_bp.route('/<string:pallet_id>', methods=['DELETE'])
def pallet_delete(pallet_id):
    """
    파레트 삭제
    """
    try:
        role, company_name, username = get_user_context()
        
        if role != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 파레트를 삭제할 수 있습니다.'
            }), 403
        
        pallet = get_pallet_by_id(pallet_id)
        if not pallet:
            return jsonify({
                'success': False,
                'message': '파레트를 찾을 수 없습니다.'
            }), 404
        
        from api.pallets.models import delete_pallet
        success, message = delete_pallet(pallet_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        print(f"파레트 삭제 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'파레트 삭제 실패: {str(e)}'
        }), 500


# ========================================
# 보관료 설정 API
# ========================================

@pallets_bp.route('/fees', methods=['GET'])
def get_fees():
    """
    보관료 설정 조회
    """
    try:
        role, company_name, username = get_user_context()
        
        filter_company = request.args.get('company', '')
        
        # 화주사인 경우 필수
        if role != '관리자':
            filter_company = company_name
        
        if not filter_company:
            return jsonify({
                'success': False,
                'message': '화주사명이 필요합니다.'
            }), 400
        
        fee = get_pallet_fee(filter_company)
        
        return jsonify({
            'success': True,
            'data': fee
        }), 200
        
    except Exception as e:
        print(f"보관료 설정 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'보관료 설정 조회 실패: {str(e)}'
        }), 500


@pallets_bp.route('/fees', methods=['POST'])
def set_fees():
    """
    보관료 설정 저장
    """
    try:
        role, company_name, username = get_user_context()
        
        data = request.get_json() or {}
        target_company = data.get('company_name', '')
        
        # 화주사인 경우 필수
        if role != '관리자':
            target_company = company_name
        
        if not target_company:
            return jsonify({
                'success': False,
                'message': '화주사명이 필요합니다.'
            }), 400
        
        monthly_fee = data.get('monthly_fee')
        effective_from = data.get('effective_from')
        notes = data.get('notes')
        
        if monthly_fee is None:
            return jsonify({
                'success': False,
                'message': '월 보관료가 필요합니다.'
            }), 400
        
        # effective_from 날짜 파싱
        effective_from_date = None
        if effective_from:
            try:
                from datetime import datetime
                effective_from_date = datetime.strptime(effective_from, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': '적용 시작일 형식이 올바르지 않습니다.'
                }), 400
        
        success, message = set_pallet_fee(
            company_name=target_company,
            monthly_fee=monthly_fee,
            effective_from=effective_from_date,
            notes=notes
        )
        
        if success:
            # 저장된 보관료 정보 반환 (30일 기준: 30일 보관 = 월 보관료)
            daily_fee = round(monthly_fee / 30.0, 2)
            return jsonify({
                'success': True,
                'message': message,
                'data': {
                    'monthly_fee': monthly_fee,
                    'daily_fee': daily_fee,
                    'effective_from': effective_from or date.today().isoformat(),
                    'notes': notes
                }
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        print(f"보관료 설정 저장 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'보관료 설정 저장 실패: {str(e)}'
        }), 500


@pallets_bp.route('/fees/calculate', methods=['GET'])
def calculate_fees():
    """
    보관료 실시간 계산
    """
    try:
        role, company_name, username = get_user_context()
        
        filter_company = request.args.get('company', '')
        in_date = request.args.get('in_date')
        out_date = request.args.get('out_date')
        is_service = request.args.get('is_service', 'false').lower() == 'true'
        
        # 화주사인 경우 필수
        if role != '관리자':
            filter_company = company_name
        
        if not filter_company or not in_date:
            return jsonify({
                'success': False,
                'message': '화주사명과 입고일이 필요합니다.'
            }), 400
        
        from datetime import datetime
        in_date_obj = datetime.strptime(in_date, '%Y-%m-%d').date()
        out_date_obj = datetime.strptime(out_date, '%Y-%m-%d').date() if out_date else None
        
        fee = calculate_fee(filter_company, in_date_obj, out_date_obj, is_service)
        
        return jsonify({
            'success': True,
            'data': {
                'fee': fee,
                'formatted_fee': f'{fee:,}원'
            }
        }), 200
        
    except Exception as e:
        print(f"보관료 계산 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'보관료 계산 실패: {str(e)}'
        }), 500


# ========================================
# 월별 정산 API
# ========================================

@pallets_bp.route('/settlements', methods=['GET'])
def settlements_list():
    """
    월별 정산 내역 조회 (정산 내역이 없으면 파레트 목록 기반으로 임시 정산 내역 생성)
    month 파라미터가 없으면 모든 월별 정산 내역을 반환 (전체 합계 제외)
    """
    try:
        role, company_name, username = get_user_context()
        
        filter_company = request.args.get('company', '') or (company_name if role != '관리자' else '')
        settlement_month = request.args.get('month')
        all_months = request.args.get('all_months', 'false').lower() == 'true'  # 모든 월별 데이터 요청
        
        # 화주사인 경우 필수 (company_name이 헤더에 있으면 사용)
        if role != '관리자' and not filter_company and not company_name:
            return jsonify({
                'success': False,
                'data': [],
                'count': 0,
                'message': '화주사명이 필요합니다.'
            }), 400
        
        # 정산 내역 조회
        final_company = filter_company if filter_company else (company_name if role != '관리자' else None)
        
        # all_months가 true이면 모든 월별 정산 내역을 한 번에 조회
        if all_months and not settlement_month:
            # 먼저 DB에 저장된 정산 내역 조회 (월별)
            settlements = get_settlements(
                company_name=final_company if final_company else None,
                settlement_month=None,  # 모든 월
                role=role
            )
            
            # 최근 24개월 목록 생성
            from datetime import date
            today = date.today()
            all_settlement_months = []
            for i in range(24):
                target_date = date(today.year, today.month, 1)
                for _ in range(i):
                    if target_date.month == 1:
                        target_date = date(target_date.year - 1, 12, 1)
                    else:
                        target_date = date(target_date.year, target_date.month - 1, 1)
                settlement_month_str = f"{target_date.year}-{target_date.month:02d}"
                all_settlement_months.append(settlement_month_str)
            
            # DB에 없는 월별 정산 내역이 있으면 임시 생성
            existing_months = {s.get('settlement_month') for s in settlements if s.get('settlement_month')}
            missing_months = [m for m in all_settlement_months if m not in existing_months]
            
            # DB에 없는 월별 정산 내역 생성 (임시)
            if missing_months:
                from api.pallets.models import get_pallets_for_settlement, calculate_daily_fee, calculate_fee
                import math
                from datetime import timedelta
                
                # 파레트 전체 목록 한 번만 조회 (화주사 필터링은 함수 내부에서 처리)
                pallets = get_pallets_for_settlement(
                    company_name=final_company if final_company else None,
                    start_date=None,
                    end_date=None
                )
                
                # 화주사별 일일 보관료 캐시 (성능 최적화)
                daily_fee_cache = {}
                
                # 성능 최적화: 각 월별 날짜 범위를 미리 계산
                month_ranges = []
                for month_str in missing_months:
                    year, month = map(int, month_str.split('-'))
                    month_start = date(year, month, 1)
                    if month == 12:
                        month_end = date(year + 1, 1, 1) - timedelta(days=1)
                    else:
                        month_end = date(year, month + 1, 1) - timedelta(days=1)
                    month_ranges.append((month_str, month_start, month_end))
                
                # 각 월별로 임시 정산 내역 생성
                for month_str, month_start, month_end in month_ranges:
                    # 해당 월에 해당하는 파레트만 필터링 (성능 최적화: 리스트 컴프리헨션 사용)
                    month_pallets = [
                        pallet for pallet in pallets
                        if pallet['in_date'] <= month_end and (pallet.get('out_date') is None or pallet.get('out_date') >= month_start)
                    ]
                    
                    if month_pallets:
                        # 임시 정산 내역 계산
                        # 입고중(status='입고됨')과 서비스(is_service=1) 상태만 카운트
                        total_pallets = 0
                        total_storage_days = 0
                        total_fee = 0
                        
                        for pallet in month_pallets:
                            in_date = pallet['in_date']
                            out_date = pallet.get('out_date')
                            is_service = pallet.get('is_service', 0) == 1
                            status = pallet.get('status', '입고됨')
                            
                            # 입고중(status='입고됨') 또는 서비스 상태만 카운트
                            if status == '입고됨' or is_service:
                                total_pallets += 1
                            
                            if not is_service:
                                # 해당 월 내 보관일수 계산
                                storage_start = max(in_date, month_start)
                                if out_date:
                                    storage_end = min(out_date, month_end)
                                else:
                                    storage_end = min(month_end, date.today())
                                
                                # 보관일수 계산 (음수 방지)
                                pallet_storage_days = max(0, (storage_end - storage_start).days + 1)
                                total_storage_days += pallet_storage_days
                                
                                # 보관료 계산 (캐시 사용)
                                company_name = pallet['company_name']
                                cache_key = f"{company_name}_{storage_start}"
                                if cache_key not in daily_fee_cache:
                                    daily_fee_cache[cache_key] = calculate_daily_fee(company_name, storage_start)
                                daily_fee = daily_fee_cache[cache_key]
                                
                                calculated_fee = daily_fee * pallet_storage_days
                                fee = math.ceil(calculated_fee / 100) * 100
                                total_fee += fee
                        
                        settlements.append({
                            'id': None,
                            'company_name': final_company,
                            'settlement_month': month_str,
                            'total_pallets': total_pallets,
                            'total_storage_days': total_storage_days,
                            'total_fee': total_fee,
                            'status': '미생성',
                            'created_at': None,
                            'updated_at': None
                        })
            
            # settlement_month 기준으로 정렬 (최신순)
            settlements.sort(key=lambda x: x.get('settlement_month', ''), reverse=True)
        else:
            # 기존 로직 (단일 월 또는 전체 합계)
            settlements = get_settlements(
                company_name=final_company if final_company else None,
                settlement_month=settlement_month,
                role=role
            )
            
            # 정산 내역이 없으면 파레트 목록 기반으로 임시 정산 내역 생성 (all_months가 false일 때만)
            if not settlements:
                from api.pallets.models import get_pallets_for_settlement, calculate_daily_fee, calculate_fee, calculate_storage_days
                from datetime import date, timedelta
                import math
                
                # 정산월이 있으면 해당 월만, 없으면 전체 기간
                if settlement_month:
                    year, month = map(int, settlement_month.split('-'))
                    start_date = date(year, month, 1)
                    if month == 12:
                        end_date = date(year + 1, 1, 1) - timedelta(days=1)
                    else:
                        end_date = date(year, month + 1, 1) - timedelta(days=1)
                else:
                    # 전체 기간: 오늘까지
                    start_date = None
                    end_date = None
            
            # 파레트 목록 조회
            pallets = get_pallets_for_settlement(
                company_name=final_company if final_company else None,
                start_date=start_date,
                end_date=end_date
            )
            
            # 화주사 필터링이 있으면 추가 필터링
            if final_company:
                pallets = [p for p in pallets if p['company_name'] == final_company]
            
            if pallets:
                # 화주사별로 그룹화하여 임시 정산 내역 생성
                company_settlements = {}
                
                for pallet in pallets:
                    company = pallet['company_name']
                    
                    if company not in company_settlements:
                        company_settlements[company] = {
                            'total_pallets': 0,
                            'total_storage_days': 0,
                            'total_fee': 0,
                            'first_in_date': None,
                            'last_out_date': None
                        }
                    
                    in_date = pallet['in_date']
                    out_date = pallet.get('out_date')
                    is_service = pallet.get('is_service', 0) == 1
                    
                    # 첫 입고일과 마지막 보관종료일 추적
                    if company_settlements[company]['first_in_date'] is None or in_date < company_settlements[company]['first_in_date']:
                        company_settlements[company]['first_in_date'] = in_date
                    
                    if out_date:
                        if company_settlements[company]['last_out_date'] is None or out_date > company_settlements[company]['last_out_date']:
                            company_settlements[company]['last_out_date'] = out_date
                    
                    # 보관료 계산 (파레트별) - 각 파레트의 보관일수에 따라 개별 계산 후 합산
                    if is_service:
                        fee = 0
                    else:
                        if settlement_month:
                            # 정산월이 있으면 해당 월 내에서만 계산
                            storage_start = max(in_date, start_date)
                            if out_date:
                                storage_end = min(out_date, end_date)
                            else:
                                storage_end = end_date
                            # 보관일수 계산 (음수 방지)
                            pallet_storage_days = max(0, (storage_end - storage_start).days + 1)
                            daily_fee = calculate_daily_fee(company, storage_start)
                            calculated_fee = daily_fee * pallet_storage_days
                            fee = math.ceil(calculated_fee / 100) * 100
                        else:
                            # 전체 기간 보관료 계산
                            fee = calculate_fee(company, in_date, out_date, is_service)
                    
                    # 파레트 개수만 증가 (보관료는 각 파레트별로 계산된 값을 합산)
                    company_settlements[company]['total_pallets'] += 1
                    # 각 파레트별 보관료를 합산 (파레트 개수로 곱하지 않음)
                    company_settlements[company]['total_fee'] += fee
                    
                    # 월별 보관일수 계산: 각 파레트의 해당 월 내 보관일수를 합산
                    if settlement_month:
                        # 해당 월 내 보관일수 계산
                        storage_start = max(in_date, start_date)
                        if out_date:
                            storage_end = min(out_date, end_date)
                        else:
                            storage_end = min(end_date, date.today())
                        
                        pallet_storage_days = max(0, (storage_end - storage_start).days + 1)
                        company_settlements[company]['total_storage_days'] += pallet_storage_days
                
                # 정산월이 없을 때만 전체 기간 기준으로 계산 (월별은 이미 위에서 계산됨)
                for company, settlement_data in company_settlements.items():
                    if not settlement_month:
                        first_in_date = settlement_data['first_in_date']
                        last_out_date = settlement_data['last_out_date']
                        
                        # 정산월이 없으면: 첫 입고일부터 마지막 보관종료일(또는 오늘)까지
                        if last_out_date:
                            # 전부 보관종료된 경우: 마지막 보관종료일까지
                            storage_end = last_out_date
                        else:
                            # 보관중인 파레트가 있는 경우: 오늘까지
                            storage_end = date.today()
                        total_storage_days = (storage_end - first_in_date).days + 1
                        settlement_data['total_storage_days'] = max(0, total_storage_days)
                
                # 임시 정산 내역 생성 (DB에 저장하지 않음)
                for company, settlement_data in company_settlements.items():
                    settlements.append({
                        'id': None,  # 임시 정산 내역
                        'company_name': company,
                        'settlement_month': settlement_month or '전체',
                        'total_pallets': settlement_data['total_pallets'],
                        'total_storage_days': settlement_data['total_storage_days'],
                        'total_fee': settlement_data['total_fee'],
                        'status': '미생성',
                        'created_at': None,
                        'updated_at': None
                    })
        
        return jsonify({
            'success': True,
            'data': settlements,
            'count': len(settlements)
        }), 200
        
    except Exception as e:
        print(f"정산 내역 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'정산 내역 조회 실패: {str(e)}'
        }), 500


@pallets_bp.route('/settlements/generate', methods=['POST'])
def generate_settlement():
    """
    월별 정산 생성
    """
    try:
        role, company_name, username = get_user_context()
        
        if role != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 정산을 생성할 수 있습니다.'
            }), 403
        
        data = request.get_json() or {}
        settlement_month = data.get('settlement_month')
        filter_company = data.get('company_name')
        
        success, message, result = generate_monthly_settlement(
            settlement_month=settlement_month,
            company_name=filter_company
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'data': result
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        print(f"정산 생성 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'정산 생성 실패: {str(e)}'
        }), 500


@pallets_bp.route('/settlements/<int:settlement_id>/detail', methods=['GET'])
def settlement_detail(settlement_id):
    """
    정산 상세 조회
    """
    try:
        role, company_name, username = get_user_context()
        
        settlement = get_settlement_detail(settlement_id)
        if not settlement:
            return jsonify({
                'success': False,
                'message': '정산 내역을 찾을 수 없습니다.'
            }), 404
        
        # 권한 확인
        if role != '관리자' and settlement.get('company_name') != company_name:
            return jsonify({
                'success': False,
                'message': '권한이 없습니다.'
            }), 403
        
        return jsonify({
            'success': True,
            'data': settlement
        }), 200
        
    except Exception as e:
        print(f"정산 상세 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'정산 상세 조회 실패: {str(e)}'
        }), 500


@pallets_bp.route('/settlements/<int:settlement_id>/confirm', methods=['PUT'])
def confirm_settlement(settlement_id):
    """
    정산 확정
    """
    try:
        role, company_name, username = get_user_context()
        
        if role != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 정산을 확정할 수 있습니다.'
            }), 403
        
        data = request.get_json() or {}
        status = data.get('status', '확정')
        
        success, message = update_settlement_status(settlement_id, status)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        print(f"정산 상태 변경 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'정산 상태 변경 실패: {str(e)}'
        }), 500


@pallets_bp.route('/settlements/<int:settlement_id>', methods=['DELETE'])
def delete_settlement_route(settlement_id):
    """
    정산 내역 삭제
    """
    try:
        role, company_name, username = get_user_context()
        
        if role != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 정산 내역을 삭제할 수 있습니다.'
            }), 403
        
        success, message = delete_settlement(settlement_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        print(f"정산 삭제 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'정산 삭제 실패: {str(e)}'
        }), 500


@pallets_bp.route('/settlements/generate-all', methods=['POST'])
def generate_all_settlements():
    """
    전체 화주사 정산 일괄 생성
    """
    try:
        role, company_name, username = get_user_context()
        
        if role != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 정산을 일괄 생성할 수 있습니다.'
            }), 403
        
        data = request.get_json() or {}
        settlement_month = data.get('settlement_month')
        
        if not settlement_month:
            return jsonify({
                'success': False,
                'message': '정산월을 지정해주세요.'
            }), 400
        
        # 전체 화주사 정산 생성 (company_name=None)
        success, message, result = generate_monthly_settlement(
            settlement_month=settlement_month,
            company_name=None  # None이면 전체 화주사
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'data': result
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        print(f"정산 일괄 생성 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'정산 일괄 생성 실패: {str(e)}'
        }), 500


@pallets_bp.route('/settlements/confirm-all', methods=['PUT'])
def confirm_all_settlements():
    """
    특정 월의 전체 정산 내역 일괄 확정
    """
    try:
        role, company_name, username = get_user_context()
        
        if role != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 정산을 일괄 확정할 수 있습니다.'
            }), 403
        
        settlement_month = request.args.get('settlement_month')
        
        if not settlement_month:
            return jsonify({
                'success': False,
                'message': '정산월을 지정해주세요.'
            }), 400
        
        data = request.get_json() or {}
        status = data.get('status', '확정')
        
        from api.pallets.models import confirm_all_settlements_by_month
        
        success, message = confirm_all_settlements_by_month(settlement_month, status)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
    except Exception as e:
        print(f"전체 정산 확정 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'전체 정산 확정 중 오류가 발생했습니다: {str(e)}'
        }), 500

@pallets_bp.route('/settlements/delete-all', methods=['DELETE'])
def delete_all_settlements():
    """
    특정 월의 전체 정산 내역 일괄 삭제
    """
    try:
        role, company_name, username = get_user_context()
        
        if role != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 정산을 일괄 삭제할 수 있습니다.'
            }), 403
        
        settlement_month = request.args.get('settlement_month')
        
        if not settlement_month:
            return jsonify({
                'success': False,
                'message': '정산월을 지정해주세요.'
            }), 400
        
        from api.pallets.models import delete_settlement_by_month
        
        success, message = delete_settlement_by_month(settlement_month)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        print(f"정산 일괄 삭제 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'정산 일괄 삭제 실패: {str(e)}'
        }), 500


@pallets_bp.route('/settlements/export', methods=['GET'])
def export_settlements():
    """
    정산 내역 엑셀 다운로드 (UTF-8 BOM)
    """
    try:
        from flask import Response
        import io
        import csv
        from urllib.parse import quote
        from api.pallets.models import get_pallets_for_settlement, calculate_daily_fee, calculate_fee
        from datetime import date, timedelta
        import math
        
        role, company_name, username = get_user_context()
        
        filter_company = request.args.get('company', '') or (company_name if role != '관리자' else '')
        settlement_month = request.args.get('month')  # 선택적 필터
        
        # 화주사인 경우 필수
        if role != '관리자' and not filter_company and not company_name:
            return jsonify({
                'success': False,
                'message': '화주사명이 필요합니다.'
            }), 400
        
        final_company = filter_company if filter_company else (company_name if role != '관리자' else None)
        
        # 정산 내역 조회 (settlement_month 파라미터에 따라 필터링)
        settlements = get_settlements(
            company_name=final_company if final_company else None,
            settlement_month=settlement_month,  # 월별 필터 적용
            role=role
        )
        
        # 정산 내역이 없으면 파레트 목록 기반으로 임시 정산 내역 생성
        if not settlements:
            # settlement_month가 있으면 해당 월만, 없으면 전체 기간
            if settlement_month:
                year, month = map(int, settlement_month.split('-'))
                start_date = date(year, month, 1)
                if month == 12:
                    end_date = date(year + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = date(year, month + 1, 1) - timedelta(days=1)
            else:
                # 전체 기간
                start_date = None
                end_date = None
            
            pallets = get_pallets_for_settlement(
                company_name=final_company if final_company else None,
                start_date=start_date,
                end_date=end_date
            )
            
            if final_company:
                pallets = [p for p in pallets if p['company_name'] == final_company]
            
            if pallets:
                company_settlements = {}
                
                for pallet in pallets:
                    company = pallet['company_name']
                    
                    if company not in company_settlements:
                        company_settlements[company] = {
                            'total_pallets': 0,
                            'total_storage_days': 0,
                            'total_fee': 0,
                            'first_in_date': None,
                            'last_out_date': None
                        }
                    
                    in_date = pallet['in_date']
                    out_date = pallet.get('out_date')
                    is_service = pallet.get('is_service', 0) == 1
                    
                    if company_settlements[company]['first_in_date'] is None or in_date < company_settlements[company]['first_in_date']:
                        company_settlements[company]['first_in_date'] = in_date
                    
                    if out_date:
                        if company_settlements[company]['last_out_date'] is None or out_date > company_settlements[company]['last_out_date']:
                            company_settlements[company]['last_out_date'] = out_date
                    
                    # 보관료 계산 (파레트별) - 각 파레트의 보관일수에 따라 개별 계산 후 합산
                    if is_service:
                        fee = 0
                    else:
                        if settlement_month:
                            # 정산월이 있으면 해당 월 내에서만 계산
                            storage_start = max(in_date, start_date)
                            if out_date:
                                storage_end = min(out_date, end_date)
                            else:
                                storage_end = min(end_date, date.today())
                            pallet_storage_days = max(0, (storage_end - storage_start).days + 1)
                            daily_fee = calculate_daily_fee(company, storage_start)
                            calculated_fee = daily_fee * pallet_storage_days
                            fee = math.ceil(calculated_fee / 100) * 100
                        else:
                            # 전체 기간 보관료 계산
                            fee = calculate_fee(company, in_date, out_date, is_service)
                    
                    # 파레트 개수: 입고중(status='입고됨') 또는 서비스 상태만 카운트
                    status = pallet.get('status', '입고됨')
                    if status == '입고됨' or is_service:
                        company_settlements[company]['total_pallets'] += 1
                    company_settlements[company]['total_fee'] += fee
                    
                    # 월별 보관일수 계산: 각 파레트의 해당 월 내 보관일수를 합산
                    if settlement_month:
                        # 해당 월 내 보관일수 계산
                        storage_start = max(in_date, start_date)
                        if out_date:
                            storage_end = min(out_date, end_date)
                        else:
                            storage_end = min(end_date, date.today())
                        
                        pallet_storage_days = max(0, (storage_end - storage_start).days + 1)
                        company_settlements[company]['total_storage_days'] += pallet_storage_days
                
                # 정산월이 없을 때만 전체 기간 기준으로 계산 (월별은 이미 위에서 계산됨)
                for company, settlement_data in company_settlements.items():
                    if not settlement_month:
                        first_in_date = settlement_data['first_in_date']
                        last_out_date = settlement_data['last_out_date']
                        
                        if last_out_date:
                            storage_end = last_out_date
                        else:
                            storage_end = date.today()
                        total_storage_days = (storage_end - first_in_date).days + 1
                        settlement_data['total_storage_days'] = max(0, total_storage_days)
                
                for company, settlement_data in company_settlements.items():
                    settlements.append({
                        'id': None,
                        'company_name': company,
                        'settlement_month': settlement_month,  # settlement_month 파라미터 전달
                        'total_pallets': settlement_data['total_pallets'],
                        'total_storage_days': settlement_data['total_storage_days'],
                        'total_fee': settlement_data['total_fee'],
                        'status': '미생성',
                        'created_at': None,
                        'updated_at': None
                    })
        
        # CSV 데이터 생성
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 헤더: 정산 내역 요약
        writer.writerow(['파레트 보관료 정산 내역'])
        writer.writerow(['화주사', final_company or '전체'])
        writer.writerow(['다운로드 일시', date.today().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([])
        writer.writerow(['정산 내역 요약'])
        writer.writerow(['정산월', '화주사', '파레트 수', '보관일수', '보관료', '상태'])
        
        # 정산 내역 요약 데이터
        for settlement in settlements:
            writer.writerow([
                settlement.get('settlement_month', '전체') or '전체',
                settlement.get('company_name', ''),
                settlement.get('total_pallets', 0),
                settlement.get('total_storage_days', 0),
                settlement.get('total_fee', 0),
                settlement.get('status', '미생성') or '미생성'
            ])
        
        writer.writerow([])
        writer.writerow(['파레트별 상세 내역'])
        writer.writerow(['순번', '파레트 ID', '화주사', '품목명', '입고일', '갱신일', '보관종료일', '보관일수', '상태', '보관료'])
        
        # 파레트별 상세 내역
        # 정산이 생성되어 있으면 pallet_fee_calculations 테이블에서 조회, 없으면 pallets 테이블에서 조회
        pallets = []
        use_settlement_data = False  # 정산 데이터 사용 여부
        
        # settlement_month가 지정된 경우 해당 월의 시작일과 종료일 계산
        start_date = None
        end_date = None
        if settlement_month:
            year, month = map(int, settlement_month.split('-'))
            start_date = date(year, month, 1)
            if month == 12:
                end_date = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        # 정산이 생성되어 있는지 확인
        if settlement_month and settlements:
            # 정산이 생성되어 있는 경우: pallet_fee_calculations 테이블에서 조회 (정확한 데이터)
            from api.pallets.models import get_settlement_detail
            from datetime import datetime
            
            for settlement in settlements:
                if settlement.get('id') and settlement.get('settlement_month') == settlement_month:
                    # 정산 상세 내역 조회
                    settlement_detail = get_settlement_detail(settlement['id'])
                    if settlement_detail and settlement_detail.get('pallets'):
                        # 정산 상세의 파레트 목록 사용 (화주사 필터링 적용)
                        for pallet in settlement_detail['pallets']:
                            if not final_company or pallet.get('company_name') == final_company:
                                pallets.append(pallet)
                        use_settlement_data = True
        
        # 정산이 생성되어 있지 않거나 정산 상세에서 파레트를 가져오지 못한 경우
        if not pallets:
            pallets = get_pallets_for_settlement(
                company_name=final_company if final_company else None,
                start_date=start_date,
                end_date=end_date
            )
            
            if final_company:
                pallets = [p for p in pallets if p['company_name'] == final_company]
        
        # 순번과 함께 파레트별 상세 내역 작성
        for index, pallet in enumerate(pallets, 1):
            in_date = pallet.get('in_date')
            out_date = pallet.get('out_date')
            is_service = pallet.get('is_service', 0) == 1
            
            # 날짜 문자열을 date 객체로 변환
            if isinstance(in_date, str):
                try:
                    in_date = datetime.strptime(in_date.split()[0], '%Y-%m-%d').date()
                except:
                    in_date = None
            elif in_date and not isinstance(in_date, date):
                if hasattr(in_date, 'date'):
                    in_date = in_date.date()
                else:
                    in_date = None
            
            if out_date and isinstance(out_date, str):
                try:
                    out_date = datetime.strptime(out_date.split()[0], '%Y-%m-%d').date()
                except:
                    out_date = None
            elif out_date and not isinstance(out_date, date):
                if hasattr(out_date, 'date'):
                    out_date = out_date.date()
                else:
                    out_date = None
            
            # 보관일수 계산
            if use_settlement_data:
                # 정산 데이터에서 가져온 경우: 이미 계산된 storage_days 사용
                storage_days = pallet.get('storage_days', 0)
            else:
                # 파레트 테이블에서 가져온 경우: 새로 계산
                if in_date:
                    if settlement_month:
                        # 해당 월 내 보관일수 계산
                        storage_start = max(in_date, start_date)
                        if out_date:
                            storage_end = min(out_date, end_date)
                        else:
                            storage_end = min(end_date, date.today())
                        storage_days = max(0, (storage_end - storage_start).days + 1)
                    else:
                        # 전체 기간 보관일수 계산
                        if out_date:
                            storage_days = (out_date - in_date).days + 1
                        else:
                            storage_days = (date.today() - in_date).days + 1
                else:
                    storage_days = 0
            
            # 보관료 계산
            if use_settlement_data:
                # 정산 데이터에서 가져온 경우: 이미 계산된 rounded_fee 사용
                fee = pallet.get('rounded_fee', 0)
            else:
                # 파레트 테이블에서 가져온 경우: 새로 계산
                if is_service:
                    fee = 0
                else:
                    if settlement_month:
                        # 해당 월 내 보관료 계산
                        storage_start = max(in_date, start_date)
                        if out_date:
                            storage_end = min(out_date, end_date)
                        else:
                            storage_end = min(end_date, date.today())
                        pallet_storage_days = max(0, (storage_end - storage_start).days + 1)
                        daily_fee = calculate_daily_fee(pallet.get('company_name', ''), storage_start)
                        calculated_fee = daily_fee * pallet_storage_days
                        fee = math.ceil(calculated_fee / 100) * 100
                    else:
                        # 전체 기간 보관료 계산
                        fee = calculate_fee(pallet.get('company_name', ''), in_date, out_date, is_service)
            
            # 상태
            status = pallet.get('status', '입고됨')
            if is_service:
                status = '서비스'
            
            # 갱신일 계산 (보관이 1달 이상이면 매월 1일)
            renewal_date = None
            if in_date:
                if out_date:
                    months_diff = (out_date.year - in_date.year) * 12 + (out_date.month - in_date.month)
                    if months_diff >= 1:
                        renewal_date = date(out_date.year, out_date.month, 1)
                else:
                    today = date.today()
                    months_diff = (today.year - in_date.year) * 12 + (today.month - in_date.month)
                    if months_diff >= 1:
                        renewal_date = date(today.year, today.month, 1)
            
            writer.writerow([
                index,  # 순번
                pallet.get('pallet_id', ''),
                pallet.get('company_name', ''),
                pallet.get('product_name', ''),
                in_date.strftime('%Y-%m-%d') if in_date else '',
                renewal_date.strftime('%Y-%m-%d') if renewal_date else '',
                out_date.strftime('%Y-%m-%d') if out_date else '',
                storage_days,
                status,
                fee
            ])
        
        output.seek(0)
        
        # 파일명 생성
        filename = f"파레트_보관료_정산내역_{final_company or '전체'}"
        if settlement_month:
            filename += f"_{settlement_month}"
        filename += ".csv"
        encoded_filename = quote(filename.encode('utf-8'))
        
        response = Response(
            output.getvalue().encode('utf-8-sig'),  # UTF-8 BOM 추가로 Excel에서 한글 깨짐 방지
            mimetype='text/csv; charset=utf-8',
            headers={
                'Content-Disposition': f'attachment; filename*=UTF-8\'\'{encoded_filename}'
            }
        )
        
        return response
        
    except Exception as e:
        print(f'❌ 정산 내역 엑셀 다운로드 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'엑셀 다운로드 중 오류: {str(e)}'
        }), 500


# ========================================
# QR 코드 API
# ========================================

@pallets_bp.route('/qr/<pallet_id>', methods=['GET'])
def generate_qr(pallet_id):
    """
    QR 코드 생성 (파레트 ID 반환)
    """
    try:
        pallet = get_pallet_by_id(pallet_id)
        if not pallet:
            return jsonify({
                'success': False,
                'message': '파레트를 찾을 수 없습니다.'
            }), 404
        
        return jsonify({
            'success': True,
            'data': {
                'pallet_id': pallet_id,
                'qr_data': pallet_id
            }
        }), 200
        
    except Exception as e:
        print(f"QR 코드 생성 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'QR 코드 생성 실패: {str(e)}'
        }), 500


@pallets_bp.route('/qr/scan', methods=['POST'])
def scan_qr():
    """
    QR 코드 스캔 처리
    """
    try:
        role, company_name, username = get_user_context()
        data = request.get_json() or {}
        
        pallet_id = data.get('pallet_id')
        if not pallet_id:
            return jsonify({
                'success': False,
                'message': '파레트 ID가 필요합니다.'
            }), 400
        
        pallet = get_pallet_by_id(pallet_id)
        if not pallet:
            return jsonify({
                'success': False,
                'message': '파레트를 찾을 수 없습니다.'
            }), 404
        
        return jsonify({
            'success': True,
            'data': pallet
        }), 200
        
    except Exception as e:
        print(f"QR 코드 스캔 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'QR 코드 스캔 실패: {str(e)}'
        }), 500


@pallets_bp.route('/labels/filter', methods=['GET'])
def filter_labels():
    """
    라벨 출력용 파레트 필터링
    """
    try:
        role, company_name, username = get_user_context()
        
        # 필터 파라미터
        pallet_id_filter = request.args.get('pallet_id', '').strip()
        company_filter = request.args.get('company', '').strip()
        product_filter = request.args.get('product', '').strip()
        start_date_str = request.args.get('start_date', '').strip()
        end_date_str = request.args.get('end_date', '').strip()
        status_filter = request.args.get('status', '').strip()
        include_printed = request.args.get('include_printed', 'false').lower() == 'true'
        
        # 날짜 파싱
        start_date = None
        end_date = None
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except:
                pass
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except:
                pass
        
        # 데이터베이스 쿼리
        from api.database.models import get_db_connection, USE_POSTGRESQL
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # print_status 컬럼이 있는지 확인하고 없으면 추가
        try:
            if USE_POSTGRESQL:
                cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='pallets' AND column_name='print_status'")
                if cursor.fetchone() is None:
                    cursor.execute("ALTER TABLE pallets ADD COLUMN print_status TEXT DEFAULT '미출력'")
                    cursor.execute("ALTER TABLE pallets ADD COLUMN print_date TEXT")
                    conn.commit()
            else:
                cursor.execute("PRAGMA table_info(pallets)")
                columns = [row[1] for row in cursor.fetchall()]
                if 'print_status' not in columns:
                    cursor.execute("ALTER TABLE pallets ADD COLUMN print_status TEXT DEFAULT '미출력'")
                    cursor.execute("ALTER TABLE pallets ADD COLUMN print_date TEXT")
                    conn.commit()
        except Exception as e:
            # 컬럼이 이미 있거나 다른 오류인 경우 무시하고 계속 진행
            try:
                conn.rollback()
            except:
                pass
        
        # 파라미터 플레이스홀더 (PostgreSQL: %s, SQLite: ?)
        param_placeholder = '%s' if USE_POSTGRESQL else '?'
        
        # 기본 쿼리 (print_status 컬럼이 없을 수도 있으므로 COALESCE 사용)
        if USE_POSTGRESQL:
            query = "SELECT pallet_id, company_name, product_name, in_date, status, COALESCE(print_status, '미출력') as print_status FROM pallets WHERE 1=1"
        else:
            query = "SELECT pallet_id, company_name, product_name, in_date, status, COALESCE(print_status, '미출력') as print_status FROM pallets WHERE 1=1"
        params = []
        
        # 화주사 필터 (관리자가 아니면 자신의 화주사만)
        if role != '관리자' and company_name:
            query += f" AND company_name = {param_placeholder}"
            params.append(company_name)
        elif company_filter:
            query += f" AND company_name = {param_placeholder}"
            params.append(company_filter)
        
        # 파레트 ID 필터 (콤마 구분 다중 검색)
        if pallet_id_filter:
            id_terms = [term.strip() for term in pallet_id_filter.split(',') if term.strip()]
            if id_terms:
                id_conditions = []
                for term in id_terms:
                    if '_' in term:
                        # 정확 매칭
                        id_conditions.append(f"pallet_id = {param_placeholder}")
                        params.append(term)
                    else:
                        # 접두 매칭
                        id_conditions.append(f"pallet_id LIKE {param_placeholder}")
                        params.append(f"{term}%")
                if id_conditions:
                    query += " AND (" + " OR ".join(id_conditions) + ")"
        
        # 품목명 필터
        if product_filter:
            query += f" AND product_name LIKE {param_placeholder}"
            params.append(f"%{product_filter}%")
        
        # 입고일 필터
        if start_date:
            query += f" AND in_date >= {param_placeholder}"
            params.append(start_date.isoformat())
        if end_date:
            query += f" AND in_date <= {param_placeholder}"
            params.append(end_date.isoformat())
        
        # 상태 필터
        if status_filter and status_filter != '전체':
            query += f" AND status = {param_placeholder}"
            params.append(status_filter)
        
        # 출력 상태 필터 (include_printed가 false면 미출력만)
        if not include_printed:
            query += f" AND (print_status IS NULL OR print_status = '' OR print_status != '출력완료')"
        
        query += " ORDER BY in_date DESC, pallet_id DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # PostgreSQL의 경우 row_factory가 없으므로 수동 변환
        if USE_POSTGRESQL:
            from psycopg2.extras import RealDictCursor
            if isinstance(cursor, RealDictCursor):
                rows = [dict(row) for row in rows]
            else:
                # 일반 cursor인 경우
                columns = [desc[0] for desc in cursor.description]
                rows = [dict(zip(columns, row)) for row in rows]
        
        conn.close()
        
        # 결과 변환
        pallets = []
        for row in rows:
            if isinstance(row, dict):
                # 이미 dict인 경우 (PostgreSQL 변환 후)
                pallets.append({
                    'pallet_id': row.get('pallet_id', ''),
                    'company_name': row.get('company_name', ''),
                    'product_name': row.get('product_name', ''),
                    'in_date': row.get('in_date', ''),
                    'status': row.get('status', ''),
                    'print_status': row.get('print_status', '미출력')
                })
            else:
                # SQLite Row 객체인 경우
                pallets.append({
                    'pallet_id': row['pallet_id'],
                    'company_name': row['company_name'],
                    'product_name': row['product_name'],
                    'in_date': row['in_date'],
                    'status': row['status'],
                    'print_status': row.get('print_status', '미출력') if 'print_status' in row.keys() else '미출력'
                })
        
        return jsonify({
            'success': True,
            'data': pallets
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'필터링 중 오류가 발생했습니다: {str(e)}'
        }), 500


@pallets_bp.route('/labels/mark-printed', methods=['POST'])
def mark_labels_printed():
    """
    선택된 라벨을 출력완료로 표시
    """
    try:
        data = request.get_json()
        pallet_ids = data.get('pallet_ids', [])
        
        if not pallet_ids:
            return jsonify({
                'success': False,
                'message': '출력완료로 표시할 파레트를 선택해주세요.'
            }), 400
        
        from api.database.models import get_db_connection, USE_POSTGRESQL
        from datetime import datetime
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # print_status 컬럼이 있는지 확인하고 없으면 추가
        try:
            if USE_POSTGRESQL:
                cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='pallets' AND column_name='print_status'")
                if cursor.fetchone() is None:
                    cursor.execute("ALTER TABLE pallets ADD COLUMN print_status TEXT DEFAULT '미출력'")
                    cursor.execute("ALTER TABLE pallets ADD COLUMN print_date TEXT")
                    conn.commit()
            else:
                cursor.execute("PRAGMA table_info(pallets)")
                columns = [row[1] for row in cursor.fetchall()]
                if 'print_status' not in columns:
                    cursor.execute("ALTER TABLE pallets ADD COLUMN print_status TEXT DEFAULT '미출력'")
                    cursor.execute("ALTER TABLE pallets ADD COLUMN print_date TEXT")
                    conn.commit()
        except Exception as e:
            # 컬럼이 이미 있거나 다른 오류인 경우 무시하고 계속 진행
            try:
                conn.rollback()
            except:
                pass
        
        # 출력완료 상태 업데이트
        param_placeholder = '%s' if USE_POSTGRESQL else '?'
        today = datetime.now().strftime('%Y-%m-%d')
        
        placeholders = ','.join([param_placeholder for _ in pallet_ids])
        query = f"UPDATE pallets SET print_status = '출력완료', print_date = {param_placeholder} WHERE pallet_id IN ({placeholders})"
        params = [today] + pallet_ids
        
        cursor.execute(query, params)
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'{len(pallet_ids)}개의 라벨이 출력완료로 표시되었습니다.'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'출력완료 표시 중 오류가 발생했습니다: {str(e)}'
        }), 500


@pallets_bp.route('/labels/print', methods=['POST'])
def print_labels():
    """
    선택된 라벨 PDF 생성 (12칸 레이아웃)
    """
    try:
        data = request.get_json()
        pallet_ids = data.get('pallet_ids', [])
        
        if not pallet_ids:
            return jsonify({
                'success': False,
                'message': '인쇄할 파레트를 선택해주세요.'
            }), 400
        
        # reportlab 라이브러리 확인 및 임포트
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm
            from reportlab.pdfgen import canvas
            from reportlab.lib.utils import ImageReader
            import io
            import urllib.request
            import urllib.parse
        except ImportError:
            return jsonify({
                'success': False,
                'message': 'PDF 생성 라이브러리가 설치되지 않았습니다. reportlab을 설치해주세요.'
            }), 500
        
        # 데이터베이스에서 파레트 정보 조회
        from api.database.models import get_db_connection, USE_POSTGRESQL
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 파라미터 플레이스홀더 (PostgreSQL: %s, SQLite: ?)
        param_placeholder = '%s' if USE_POSTGRESQL else '?'
        placeholders = ','.join([param_placeholder for _ in pallet_ids])
        cursor.execute(f"SELECT pallet_id, company_name, product_name, in_date FROM pallets WHERE pallet_id IN ({placeholders})", pallet_ids)
        rows = cursor.fetchall()
        
        # PostgreSQL의 경우 row_factory가 없으므로 수동 변환
        if USE_POSTGRESQL:
            columns = [desc[0] for desc in cursor.description]
            rows = [dict(zip(columns, row)) for row in rows]
        
        conn.close()
        
        if not rows:
            return jsonify({
                'success': False,
                'message': '선택한 파레트를 찾을 수 없습니다.'
            }), 404
        
        # PDF 생성
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        
        # 라벨 설정 (LS-3112: 12칸, 3열 × 4행)
        LABELS_PER_PAGE = 12
        LABELS_PER_ROW = 3
        LABEL_WIDTH = 63.5 * mm
        LABEL_HEIGHT = 70 * mm
        PAGE_WIDTH, PAGE_HEIGHT = A4
        
        # 마진 계산 (구글 앱스크립트와 동일)
        MARGIN_TOP = 22.4 * mm
        MARGIN_LEFT = 17 * mm
        MARGIN_RIGHT = 22.6 * mm
        MARGIN_BOTTOM = 0
        
        # 라벨 간격 계산
        LABEL_SPACING_X = (PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT - (LABEL_WIDTH * LABELS_PER_ROW)) / (LABELS_PER_ROW - 1) if LABELS_PER_ROW > 1 else 0
        LABEL_SPACING_Y = (PAGE_HEIGHT - MARGIN_TOP - MARGIN_BOTTOM - (LABEL_HEIGHT * 4)) / 3  # 4행이므로 간격은 3개
        
        # QR 코드를 미리 다운로드 (병렬 처리로 속도 향상)
        print(f"[PDF 생성] QR 코드 사전 다운로드 시작 (총 {len(rows)}개)...")
        import concurrent.futures
        
        def download_qr_code(row_data):
            """QR 코드 다운로드 함수 (바이트 데이터만 반환)"""
            try:
                if isinstance(row_data, dict):
                    pallet_id = row_data.get('pallet_id', '')
                    company = row_data.get('company_name', '') or ''
                    product = row_data.get('product_name', '') or ''
                else:
                    pallet_id = row_data['pallet_id']
                    company = row_data['company_name'] or ''
                    product = row_data['product_name'] or ''
                
                form_url = "https://docs.google.com/forms/d/e/1FAIpQLSdDmnWcW27tfDptUvuSjEgN8K7nNNQWecdpeMMhwftTtbiyIQ/viewform"
                qr_text = f"{form_url}?usp=pp_url&entry.419411235={urllib.parse.quote(pallet_id)}&entry.427884801=보관종료&entry.2110345042={urllib.parse.quote(company)}&entry.306824944={urllib.parse.quote(product)}"
                qr_url = f"https://quickchart.io/qr?text={urllib.parse.quote(qr_text)}&size=150&ecLevel=M"
                
                qr_response = urllib.request.urlopen(qr_url, timeout=3)
                qr_data = qr_response.read()
                if qr_data and len(qr_data) > 0:
                    return qr_data
            except Exception as e:
                print(f"[PDF 생성] QR 코드 다운로드 실패: {str(e)[:100]}")
            return None
        
        # 병렬로 QR 코드 다운로드 (최대 10개 동시, 바이트 데이터만 저장)
        qr_data_dict = {}
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                future_to_row = {executor.submit(download_qr_code, row): idx for idx, row in enumerate(rows)}
                completed = 0
                for future in concurrent.futures.as_completed(future_to_row):
                    idx = future_to_row[future]
                    try:
                        qr_data_dict[idx] = future.result()
                        completed += 1
                        if completed % 10 == 0:
                            print(f"[PDF 생성] QR 코드 다운로드 진행: {completed}/{len(rows)}")
                    except Exception as e:
                        qr_data_dict[idx] = None
                        print(f"[PDF 생성] QR 코드 다운로드 실패 (라벨 {idx + 1}): {str(e)[:50]}")
        except Exception as e:
            print(f"[PDF 생성] QR 코드 병렬 다운로드 중 오류: {str(e)}")
            import traceback
            traceback.print_exc()
            # 실패해도 계속 진행 (QR 코드 없이)
            qr_data_dict = {idx: None for idx in range(len(rows))}
        
        print(f"[PDF 생성] QR 코드 다운로드 완료 ({len([d for d in qr_data_dict.values() if d])}개 성공), PDF 그리기 시작...")
        
        count = 0
        total_rows = len(rows)
        
        for idx, row in enumerate(rows):
            if idx % 10 == 0 and idx > 0:
                print(f"[PDF 생성] 진행 중: {idx}/{total_rows} 라벨 처리 완료")
            
            # 새 페이지 시작 (12개마다)
            if count > 0 and count % LABELS_PER_PAGE == 0:
                c.showPage()
            
            # 라벨 위치 계산
            label_index = count % LABELS_PER_PAGE
            row_index = label_index // LABELS_PER_ROW
            col_index = label_index % LABELS_PER_ROW
            
            x = MARGIN_LEFT + col_index * (LABEL_WIDTH + LABEL_SPACING_X)
            y = PAGE_HEIGHT - MARGIN_TOP - (row_index + 1) * LABEL_HEIGHT - row_index * LABEL_SPACING_Y
            
            # 라벨 내용 그리기
            if isinstance(row, dict):
                pallet_id = row.get('pallet_id', '')
                company = row.get('company_name', '') or ''
                product = row.get('product_name', '') or ''
                in_date = row.get('in_date', '') or ''
            else:
                pallet_id = row['pallet_id']
                company = row['company_name'] or ''
                product = row['product_name'] or ''
                in_date = row['in_date'] or ''
            
            # 날짜 포맷팅
            try:
                if in_date:
                    date_obj = datetime.strptime(in_date, '%Y-%m-%d').date()
                    in_date_str = date_obj.strftime('%Y-%m-%d')
                else:
                    in_date_str = '-'
            except:
                in_date_str = str(in_date) if in_date else '-'
            
            # 미리 다운로드한 QR 코드 사용 (바이트 데이터를 ImageReader로 변환)
            qr_image = None
            qr_data = qr_data_dict.get(idx)
            if qr_data:
                try:
                    qr_image = ImageReader(io.BytesIO(qr_data))
                except Exception as e:
                    print(f"[PDF 생성] QR 코드 ImageReader 생성 실패 (라벨 {idx + 1}): {str(e)[:50]}")
            
            # 텍스트 그리기
            c.setFont("Helvetica-Bold", 11)
            c.drawString(x + 3*mm, y + LABEL_HEIGHT - 8*mm, f"파레트 ID: {pallet_id}")
            
            c.setFont("Helvetica-Bold", 11)
            c.drawString(x + 3*mm, y + LABEL_HEIGHT - 14*mm, product[:20] if product else '-')
            
            # QR 코드 그리기 (중앙)
            if qr_image:
                qr_width_mm = 40 * mm
                qr_height_mm = 40 * mm
                qr_x = x + (LABEL_WIDTH - qr_width_mm) / 2
                qr_y = y + LABEL_HEIGHT / 2 - qr_height_mm / 2
                c.drawImage(qr_image, qr_x, qr_y, width=qr_width_mm, height=qr_height_mm)
            
            # 하단 정보
            c.setFont("Helvetica-Bold", 11)
            c.drawString(x + 3*mm, y + 8*mm, f"화주사: {company[:15] if company else '-'}")
            
            c.setFont("Helvetica-Bold", 11)
            c.drawString(x + 3*mm, y + 3*mm, f"입고일: {in_date_str}")
            
            count += 1
        
        print(f"[PDF 생성] 모든 라벨 처리 완료 ({count}개), PDF 저장 중...")
        try:
            c.save()
            print(f"[PDF 생성] Canvas 저장 완료")
            buffer.seek(0)
            pdf_data = buffer.getvalue()
            print(f"[PDF 생성] PDF 데이터 추출 완료, 크기: {len(pdf_data)} bytes")
        except Exception as save_error:
            print(f"[PDF 생성] PDF 저장 중 오류: {str(save_error)}")
            import traceback
            traceback.print_exc()
            raise
        
        # PDF 응답 반환
        return Response(
            pdf_data,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename*=UTF-8\'\'파레트_라벨_{date.today().isoformat()}.pdf'
            }
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'PDF 생성 중 오류가 발생했습니다: {str(e)}'
        }), 500


@pallets_bp.route('/companies', methods=['GET'])
def get_companies():
    """
    파레트를 보관 중인 화주사 목록 조회 (비활성화 상태 포함)
    """
    try:
        role, company_name, username = get_user_context()
        
        settlement_month = request.args.get('month')
        
        from api.pallets.models import get_companies_with_pallets
        from api.database.models import get_all_companies, is_company_deactivated
        
        # 파레트를 보관 중인 화주사 목록
        companies_with_pallets = get_companies_with_pallets(settlement_month=settlement_month)
        
        # 모든 화주사 정보 조회 (비활성화 상태 포함)
        all_companies = get_all_companies()
        
        # 화주사명을 키로 하는 딕셔너리 생성 (비활성화 상태 포함)
        companies_dict = {}
        for comp in all_companies:
            comp_name = comp.get('company_name', '')
            if comp_name:
                # is_active 처리 (SQLite는 INTEGER, PostgreSQL은 BOOLEAN)
                is_active = comp.get('is_active')
                if is_active is None:
                    is_active = True  # 기본값
                elif isinstance(is_active, int):
                    is_active = bool(is_active)  # SQLite: 1/0 -> True/False
                companies_dict[comp_name] = {
                    'company_name': comp_name,
                    'is_active': is_active
                }
        
        # 화주사 목록에 비활성화 상태 추가
        companies_list = []
        for comp_name in companies_with_pallets:
            # companies 테이블에 있는 경우 딕셔너리에서 가져오기
            if comp_name in companies_dict:
                company_info = companies_dict[comp_name]
            else:
                # companies 테이블에 없는 경우: deactivated_companies 테이블 확인
                is_deactivated = is_company_deactivated(comp_name)
                company_info = {
                    'company_name': comp_name,
                    'is_active': not is_deactivated  # 비활성화되어 있으면 False
                }
            companies_list.append(company_info)
        
        return jsonify({
            'success': True,
            'data': {
                'companies': companies_list
            }
        }), 200
        
    except Exception as e:
        print(f"화주사 목록 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'화주사 목록 조회 실패: {str(e)}'
        }), 500


@pallets_bp.route('/companies/<company_name>/toggle-active', methods=['PUT'])
def toggle_company_active(company_name):
    """
    화주사 비활성화/활성화 토글
    """
    try:
        role, current_company, username = get_user_context()
        
        if role != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 화주사를 비활성화할 수 있습니다.'
            }), 403
        
        from urllib.parse import unquote
        company_name = unquote(company_name)
        
        print(f"[비활성화] 요청 받음 - 화주사명: '{company_name}'")
        
        data = request.get_json() or {}
        print(f"[비활성화] 요청 데이터: {data}")
        
        is_active = data.get('is_active')
        
        # is_active가 None이거나 boolean이 아닌 경우 처리
        if is_active is None:
            print(f"[비활성화] 오류: is_active 파라미터가 없음")
            return jsonify({
                'success': False,
                'message': 'is_active 파라미터가 필요합니다.'
            }), 400
        
        # boolean으로 변환 (문자열 'true'/'false'도 처리)
        if isinstance(is_active, str):
            is_active = is_active.lower() in ('true', '1', 'yes')
        elif not isinstance(is_active, bool):
            is_active = bool(is_active)
        
        print(f"[비활성화] 처리할 is_active 값: {is_active} (타입: {type(is_active)})")
        
        from api.database.models import toggle_company_active_status
        
        success, message = toggle_company_active_status(company_name, is_active)
        
        print(f"[비활성화] 결과 - success: {success}, message: {message}")
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        print(f"화주사 비활성화/활성화 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'화주사 비활성화/활성화 실패: {str(e)}'
        }), 500


@pallets_bp.route('/revenue/monthly', methods=['GET'])
def get_monthly_revenue_route():
    """
    월별 보관료 수입 현황 조회 (관리자 전용)
    
    Query Parameters:
        start_month: 시작 월 (YYYY-MM 형식, 선택)
        end_month: 종료 월 (YYYY-MM 형식, 선택)
    
    Returns:
        {
            "success": bool,
            "data": {
                "summary": {
                    "total_revenue": int,
                    "average_revenue": float,
                    "max_revenue": int,
                    "min_revenue": int,
                    "total_months": int
                },
                "monthly_data": [...],
                "company_distribution": [...]
            }
        }
    """
    try:
        role, company_name, username = get_user_context()
        
        # 관리자만 접근 가능
        if role != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 접근할 수 있습니다.'
            }), 403
        
        start_month = request.args.get('start_month')
        end_month = request.args.get('end_month')
        
        data = get_monthly_revenue(start_month=start_month, end_month=end_month)
        
        return jsonify({
            'success': True,
            'data': data
        }), 200
        
    except Exception as e:
        print(f"월별 수입 현황 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'월별 수입 현황 조회 실패: {str(e)}'
        }), 500


@pallets_bp.route('/debug/company-check', methods=['GET'])
def debug_company_check():
    """
    디버깅: 화주사명 관련 DB 상태 확인
    """
    try:
        from api.database.models import get_db_connection, normalize_company_name, get_company_search_keywords
        from api.database.models import USE_POSTGRESQL
        
        company_name = request.args.get('company', 'TKS 컴퍼니')
        
        result = {
            'input_company': company_name,
            'normalized_input': normalize_company_name(company_name),
            'companies_table': [],
            'pallets_table': [],
            'settlements_table': [],
            'search_keywords': []
        }
        
        conn = get_db_connection()
        
        try:
            if USE_POSTGRESQL:
                from psycopg2.extras import RealDictCursor
                cursor = conn.cursor(cursor_factory=RealDictCursor)
            else:
                cursor = conn.cursor()
            
            # 1. companies 테이블에서 관련 화주사 조회
            if USE_POSTGRESQL:
                cursor.execute('''
                    SELECT company_name, username, search_keywords 
                    FROM companies 
                    WHERE LOWER(REPLACE(company_name, ' ', '')) LIKE %s 
                       OR LOWER(REPLACE(username, ' ', '')) LIKE %s
                    LIMIT 20
                ''', (f'%{normalize_company_name(company_name)}%', f'%{normalize_company_name(company_name)}%'))
            else:
                cursor.execute('''
                    SELECT company_name, username, search_keywords 
                    FROM companies 
                    WHERE LOWER(REPLACE(company_name, ' ', '')) LIKE ?
                       OR LOWER(REPLACE(username, ' ', '')) LIKE ?
                    LIMIT 20
                ''', (f'%{normalize_company_name(company_name)}%', f'%{normalize_company_name(company_name)}%'))
            
            companies_rows = cursor.fetchall()
            if USE_POSTGRESQL:
                result['companies_table'] = [dict(row) for row in companies_rows]
            else:
                result['companies_table'] = [
                    {
                        'company_name': row[0],
                        'username': row[1] if len(row) > 1 else None,
                        'search_keywords': row[2] if len(row) > 2 else None
                    }
                    for row in companies_rows
                ]
            
            # 2. pallets 테이블에서 관련 화주사 조회
            if USE_POSTGRESQL:
                cursor.execute('''
                    SELECT DISTINCT company_name, COUNT(*) as pallet_count
                    FROM pallets 
                    WHERE LOWER(REPLACE(company_name, ' ', '')) LIKE %s
                    GROUP BY company_name
                    ORDER BY company_name
                    LIMIT 20
                ''', (f'%{normalize_company_name(company_name)}%',))
            else:
                cursor.execute('''
                    SELECT DISTINCT company_name, COUNT(*) as pallet_count
                    FROM pallets 
                    WHERE LOWER(REPLACE(company_name, ' ', '')) LIKE ?
                    GROUP BY company_name
                    ORDER BY company_name
                    LIMIT 20
                ''', (f'%{normalize_company_name(company_name)}%',))
            
            pallets_rows = cursor.fetchall()
            if USE_POSTGRESQL:
                result['pallets_table'] = [dict(row) for row in pallets_rows]
            else:
                result['pallets_table'] = [
                    {
                        'company_name': row[0],
                        'pallet_count': row[1]
                    }
                    for row in pallets_rows
                ]
            
            # 3. pallet_monthly_settlements 테이블에서 관련 정산 내역 조회
            if USE_POSTGRESQL:
                cursor.execute('''
                    SELECT company_name, settlement_month, total_pallets, total_fee, id
                    FROM pallet_monthly_settlements 
                    WHERE LOWER(REPLACE(company_name, ' ', '')) LIKE %s
                    ORDER BY settlement_month DESC, company_name
                    LIMIT 20
                ''', (f'%{normalize_company_name(company_name)}%',))
            else:
                cursor.execute('''
                    SELECT company_name, settlement_month, total_pallets, total_fee, id
                    FROM pallet_monthly_settlements 
                    WHERE LOWER(REPLACE(company_name, ' ', '')) LIKE ?
                    ORDER BY settlement_month DESC, company_name
                    LIMIT 20
                ''', (f'%{normalize_company_name(company_name)}%',))
            
            settlements_rows = cursor.fetchall()
            if USE_POSTGRESQL:
                result['settlements_table'] = [dict(row) for row in settlements_rows]
            else:
                result['settlements_table'] = [
                    {
                        'company_name': row[0],
                        'settlement_month': row[1],
                        'total_pallets': row[2],
                        'total_fee': row[3],
                        'id': row[4]
                    }
                    for row in settlements_rows
                ]
            
            # 4. get_company_search_keywords 결과 확인
            try:
                keywords = get_company_search_keywords(company_name)
                result['search_keywords'] = keywords
            except Exception as e:
                result['search_keywords'] = f'오류: {str(e)}'
            
            # 5. 각 정산 내역의 화주사명으로 키워드 조회
            result['settlement_keywords'] = {}
            for settlement in result['settlements_table']:
                settlement_company = settlement.get('company_name', '')
                if settlement_company:
                    try:
                        keywords = get_company_search_keywords(settlement_company)
                        result['settlement_keywords'][settlement_company] = keywords
                    except Exception as e:
                        result['settlement_keywords'][settlement_company] = f'오류: {str(e)}'
            
        finally:
            cursor.close()
            conn.close()
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except Exception as e:
        print(f"디버깅 화주사 확인 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'디버깅 화주사 확인 실패: {str(e)}',
            'error': str(e)
        }), 500
