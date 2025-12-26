"""
파레트 보관료 관리 시스템 - API 라우트
"""
from flask import Blueprint, request, jsonify
from datetime import date, datetime
from api.pallets.models import (
    create_pallet, update_pallet_status, get_pallet_by_id, get_pallets,
    calculate_fee, get_pallet_fee, set_pallet_fee,
    generate_monthly_settlement, get_settlements, get_settlement_detail,
    update_settlement_status, delete_settlement, delete_settlement
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
        
        # Google Apps Script 등 외부 호출 시 username이 없으면 기본값 설정
        if not username:
            username = 'Google Forms Sync'
        
        # 관리자가 아닌 경우, 헤더의 company_name 사용
        # 외부 호출 시 data에 company_name이 있으면 사용
        if role != '관리자':
            data['company_name'] = company_name or data.get('company_name', '')
        
        # 관리자인 경우, 요청 본문의 company_name 사용
        if role == '관리자' and not data.get('company_name'):
            return jsonify({
                'success': False,
                'message': '화주사명이 필요합니다.'
            }), 400
        
        # 대량 입고인지 확인
        if isinstance(data.get('pallets'), list):
            # 대량 입고
            results = []
            errors = []
            
            for pallet_data in data['pallets']:
                if role != '관리자':
                    pallet_data['company_name'] = company_name
                
                success, message, pallet = create_pallet(
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
            success, message, pallet = create_pallet(
                company_name=data.get('company_name'),
                product_name=data.get('product_name'),
                in_date=data.get('in_date'),
                storage_location=data.get('storage_location'),
                quantity=data.get('quantity', 1),
                is_service=data.get('is_service', False),
                notes=data.get('notes'),
                created_by=username
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
    파레트 보관종료 (QR 스캔 또는 수동)
    """
    try:
        role, company_name, username = get_user_context()
        data = request.get_json() or {}
        
        pallet_id = data.get('pallet_id')
        out_date = data.get('out_date')
        notes = data.get('notes')
        
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
    """
    try:
        role, company_name, username = get_user_context()
        
        filter_company = request.args.get('company', '')
        status = request.args.get('status', '전체')
        month = request.args.get('month')
        
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
            role=role
        )
        
        # 보관료 계산 추가 및 date 객체를 문자열로 변환
        from api.pallets.models import calculate_fee, calculate_storage_days
        for pallet in pallets:
            # date 객체를 문자열로 변환 (JSON 직렬화를 위해)
            if pallet.get('in_date') and isinstance(pallet['in_date'], date):
                pallet['in_date'] = pallet['in_date'].isoformat()
            if pallet.get('out_date') and isinstance(pallet['out_date'], date):
                pallet['out_date'] = pallet['out_date'].isoformat()
            
            # 날짜 문자열을 date 객체로 변환하여 계산
            in_date_obj = pallet['in_date']
            if isinstance(in_date_obj, str):
                in_date_obj = datetime.strptime(in_date_obj, '%Y-%m-%d').date()
            out_date_obj = pallet.get('out_date')
            if out_date_obj and isinstance(out_date_obj, str):
                out_date_obj = datetime.strptime(out_date_obj, '%Y-%m-%d').date()
            
            pallet['storage_days'] = calculate_storage_days(
                in_date_obj,
                out_date_obj
            )
            pallet['current_fee'] = calculate_fee(
                pallet['company_name'],
                in_date_obj,
                out_date_obj,
                pallet.get('is_service', 0) == 1
            )
        
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
        
        success, message = set_pallet_fee(
            company_name=target_company,
            monthly_fee=monthly_fee,
            effective_from=effective_from,
            notes=notes
        )
        
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
    """
    try:
        role, company_name, username = get_user_context()
        
        filter_company = request.args.get('company', '') or (company_name if role != '관리자' else '')
        settlement_month = request.args.get('month')
        
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
        settlements = get_settlements(
            company_name=final_company if final_company else None,
            settlement_month=settlement_month,
            role=role
        )
        
        # 정산 내역이 없으면 파레트 목록 기반으로 임시 정산 내역 생성
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
                            pallet_storage_days = (storage_end - storage_start).days + 1
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
                
                # 총 보관일수 계산 (전체 기간 기준)
                for company, settlement_data in company_settlements.items():
                    first_in_date = settlement_data['first_in_date']
                    last_out_date = settlement_data['last_out_date']
                    
                    if settlement_month:
                        # 정산월이 있으면: 해당 월의 1일부터 마지막 보관종료일(또는 월말 또는 오늘)까지
                        # 정산월의 시작일은 항상 해당 월의 1일
                        storage_start = start_date  # 정산월의 1일
                        
                        if last_out_date:
                            # 전부 보관종료된 경우: 마지막 보관종료일과 월말 중 이른 날
                            storage_end = min(last_out_date, end_date)
                        else:
                            # 보관중인 파레트가 있는 경우: 월말과 오늘 중 이른 날
                            storage_end = min(end_date, date.today())
                        
                        total_storage_days = (storage_end - storage_start).days + 1
                    else:
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


@pallets_bp.route('/companies', methods=['GET'])
def get_companies():
    """
    파레트를 보관 중인 화주사 목록 조회
    """
    try:
        role, company_name, username = get_user_context()
        
        settlement_month = request.args.get('month')
        
        from api.pallets.models import get_companies_with_pallets
        companies = get_companies_with_pallets(settlement_month=settlement_month)
        
        return jsonify({
            'success': True,
            'data': {
                'companies': companies
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
