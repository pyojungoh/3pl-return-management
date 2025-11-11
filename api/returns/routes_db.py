"""
반품 관리 API 라우트 (SQLite 데이터베이스 기반)
"""
from flask import Blueprint, request, jsonify
from api.database.models import (
    get_returns_by_company,
    get_available_months,
    save_client_request,
    mark_as_completed,
    get_return_by_id,
    update_memo,
    delete_return,
    create_return
)

# Blueprint 생성
returns_bp = Blueprint('returns', __name__, url_prefix='/api/returns')


@returns_bp.route('/available-months', methods=['GET'])
def get_available_months_route():
    """
    사용 가능한 월 목록 조회 API
    
    Returns:
        {
            "success": bool,
            "months": List[str],
            "message": str
        }
    """
    try:
        months = get_available_months()
        return jsonify({
            'success': True,
            'months': months,
            'message': f'{len(months)}개의 월 데이터를 찾았습니다.'
        })
    except Exception as e:
        print(f'❌ 월 목록 조회 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'months': [],
            'message': f'월 목록 조회 중 오류: {str(e)}'
        }), 500


@returns_bp.route('/data', methods=['GET'])
def get_returns_data():
    """
    반품 데이터 조회 API
    
    Query Parameters:
        - company: 화주명
        - month: 월 (예: "2025년11월")
        - role: 권한 ("관리자" 또는 "화주사")
    
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
        role = request.args.get('role', '화주사').strip()
        
        if not month:
            from datetime import datetime
            today = datetime.now()
            month = f"{today.year}년{today.month}월"
        
        # 화주사인 경우 company 파라미터가 필수
        if role != '관리자' and not company:
            return jsonify({
                'success': False,
                'data': [],
                'count': 0,
                'message': '화주사명이 필요합니다.'
            }), 400
        
        # 디버깅: 파라미터 확인
        print(f"📊 반품 데이터 조회 - company: '{company}', month: '{month}', role: '{role}'")
        
        # 데이터베이스에서 조회
        returns = get_returns_by_company(company, month, role)
        
        # 디버깅: 조회 결과 확인
        print(f"   조회된 데이터: {len(returns)}건")
        if returns and len(returns) > 0:
            print(f"   첫 번째 데이터의 화주명: {returns[0].get('company_name', 'N/A')}")
        
        # 날짜에서 일자만 추출하는 함수
        def extract_day(date_str):
            """날짜 문자열에서 일자만 추출 (예: '2024-07-11' → '11', '11' → '11')"""
            if not date_str:
                return ''
            date_str = str(date_str).strip()
            # YYYY-MM-DD 형식에서 일자 추출
            if '-' in date_str:
                parts = date_str.split('-')
                if len(parts) >= 3:
                    return parts[-1].lstrip('0') or '0'  # 앞의 0 제거, 빈 문자열이면 '0'
            # MM/DD 형식에서 일자 추출
            elif '/' in date_str:
                parts = date_str.split('/')
                if len(parts) >= 2:
                    return parts[-1].lstrip('0') or '0'
            # 숫자만 있는 경우 (일자만)
            elif date_str.isdigit():
                return str(int(date_str))  # 앞의 0 제거
            # 기타 형식은 그대로 반환
            return date_str
        
        # 데이터 포맷팅 (기존 대시보드 형식에 맞춤)
        formatted_data = []
        for ret in returns:
            # 사진 링크 파싱
            photo_links = []
            if ret.get('photo_links'):
                photo_links_str = str(ret['photo_links']).strip()
                if photo_links_str:
                    # 여러 줄로 구분된 사진 링크 처리
                    for line in photo_links_str.split('\n'):
                        line = line.strip()
                        if not line:
                            continue
                        
                        # "사진1: URL" 형식인 경우
                        if ':' in line:
                            parts = line.split(':', 1)
                            if len(parts) == 2:
                                text = parts[0].strip()
                                url = parts[1].strip()
                                if url:  # URL이 있으면 링크로 표시
                                    photo_links.append({
                                        'text': text,
                                        'url': url
                                    })
                                else:  # URL이 없으면 텍스트만 표시
                                    photo_links.append({
                                        'text': text,
                                        'url': None
                                    })
                        # URL만 있는 경우 (http:// 또는 https://로 시작)
                        elif line.startswith('http://') or line.startswith('https://'):
                            photo_links.append({
                                'text': '사진',
                                'url': line
                            })
                        # 텍스트만 있는 경우 (예: "사진1")
                        else:
                            photo_links.append({
                                'text': line,
                                'url': None
                            })
            
            # 날짜에서 일자만 추출
            return_date = ret.get('return_date', '')
            day_only = extract_day(return_date)
            
            formatted_data.append({
                'id': ret['id'],
                'rowIndex': ret['id'],  # 호환성을 위해 id 사용
                '반품 접수일': day_only,  # 일자만 표시
                '화주명': ret.get('company_name', ''),
                '제품': ret.get('product', ''),
                '고객명': ret.get('customer_name', ''),
                '송장번호': ret.get('tracking_number', ''),
                '반품/교환/오배송': ret.get('return_type', ''),
                '재고상태': ret.get('stock_status', ''),
                '검품유무': ret.get('inspection', ''),
                '처리완료': ret.get('completed', ''),
                '비고': ret.get('memo', ''),
                '사진': photo_links,
                '다른외부택배사': ret.get('other_courier', ''),
                '배송비': ret.get('shipping_fee', ''),
                '화주사요청': ret.get('client_request', ''),
                '화주사확인완료': ret.get('client_confirmed', '')
            })
        
        # 최신 날짜부터 정렬 (서버에서 이미 정렬되었지만 클라이언트 측에서도 정렬 보장)
        def get_day_for_sort(date_str):
            """정렬용 일자 숫자 추출"""
            if not date_str:
                return 0
            try:
                return int(str(date_str).strip())
            except ValueError:
                return 0
        
        formatted_data.sort(key=lambda x: (
            # 날짜가 없으면 맨 아래로 (True가 뒤로 감)
            not x.get('반품 접수일') or x.get('반품 접수일') == '',
            # 날짜를 숫자로 변환하여 정렬 (내림차순)
            -get_day_for_sort(x.get('반품 접수일', '')),
            # ID로 정렬 (내림차순)
            -x.get('id', 0)
        ))
        
        return jsonify({
            'success': True,
            'data': formatted_data,
            'count': len(formatted_data),
            'message': f'{len(formatted_data)}건의 데이터를 조회했습니다.'
        })
        
    except Exception as e:
        print(f'❌ 데이터 조회 오류: {e}')
        import traceback
        traceback.print_exc()
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
            "rowIndex": int,  # 반품 ID
            "month": str,     # 월 (사용 안 함, 호환성 유지)
            "requestText": str
        }
    """
    try:
        data = request.get_json()
        return_id = data.get('rowIndex')  # 실제로는 ID
        request_text = data.get('requestText', '').strip()
        
        if not return_id or not request_text:
            return jsonify({
                'success': False,
                'message': '필수 데이터가 누락되었습니다.'
            }), 400
        
        # 데이터베이스에 저장
        if save_client_request(return_id, request_text):
            return jsonify({
                'success': True,
                'message': '요청사항이 성공적으로 저장되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': '요청사항 저장에 실패했습니다.'
            }), 500
        
    except Exception as e:
        print(f'❌ 요청사항 저장 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'요청사항 저장 중 오류: {str(e)}'
        }), 500


@returns_bp.route('/mark-completed', methods=['POST'])
def mark_as_completed_route():
    """
    반품 처리완료 표시 API
    
    Request Body:
        {
            "rowIndex": int,      # 반품 ID
            "month": str,          # 월 (사용 안 함, 호환성 유지)
            "managerName": str     # 관리자 이름
        }
    """
    try:
        data = request.get_json()
        return_id = data.get('rowIndex')  # 실제로는 ID
        manager_name = data.get('managerName', '').strip()
        
        if not return_id or not manager_name:
            return jsonify({
                'success': False,
                'message': '필수 데이터가 누락되었습니다.'
            }), 400
        
        # 데이터베이스에 저장
        if mark_as_completed(return_id, manager_name):
            return jsonify({
                'success': True,
                'message': '반품 건이 처리완료로 표시되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': '처리완료 표시에 실패했습니다.'
            }), 500
        
    except Exception as e:
        print(f'❌ 처리완료 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'처리완료 중 오류: {str(e)}'
        }), 500


@returns_bp.route('/update-memo', methods=['POST'])
def update_memo_route():
    """
    비고 업데이트 API
    
    Request Body:
        {
            "rowIndex": int,  # 반품 ID
            "memo": str        # 비고 내용
        }
    """
    try:
        data = request.get_json()
        return_id = data.get('rowIndex')
        memo = data.get('memo', '').strip()
        
        if not return_id:
            return jsonify({
                'success': False,
                'message': '필수 데이터가 누락되었습니다.'
            }), 400
        
        if update_memo(return_id, memo):
            return jsonify({
                'success': True,
                'message': '비고가 저장되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': '비고 저장에 실패했습니다.'
            }), 500
        
    except Exception as e:
        print(f'❌ 비고 업데이트 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'비고 업데이트 중 오류: {str(e)}'
        }), 500


@returns_bp.route('/delete', methods=['POST'])
def delete_return_route():
    """
    반품 데이터 삭제 API
    
    Request Body:
        {
            "rowIndex": int  # 반품 ID
        }
    """
    try:
        data = request.get_json()
        return_id = data.get('rowIndex')
        
        if not return_id:
            return jsonify({
                'success': False,
                'message': '필수 데이터가 누락되었습니다.'
            }), 400
        
        if delete_return(return_id):
            return jsonify({
                'success': True,
                'message': '반품 건이 삭제되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': '삭제에 실패했습니다.'
            }), 500
        
    except Exception as e:
        print(f'❌ 삭제 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'삭제 중 오류: {str(e)}'
        }), 500


@returns_bp.route('/create', methods=['POST'])
def create_return_route():
    """
    반품 데이터 생성 API
    
    Request Body:
        {
            "return_date": str,
            "company_name": str,
            "product": str,
            "customer_name": str,
            "tracking_number": str,
            "return_type": str,
            "stock_status": str,
            "inspection": str,
            "completed": str,
            "memo": str,
            "photo_links": str,
            "other_courier": str,
            "shipping_fee": str,
            "client_request": str,
            "client_confirmed": str,
            "month": str
        }
    """
    try:
        data = request.get_json()
        
        # 필수 필드 확인
        if not data.get('customer_name') or not data.get('tracking_number') or not data.get('month'):
            return jsonify({
                'success': False,
                'message': '고객명, 송장번호, 월은 필수입니다.'
            }), 400
        
        return_id = create_return(data)
        if return_id:
            return jsonify({
                'success': True,
                'message': '반품 내역이 등록되었습니다.',
                'id': return_id
            })
        else:
            return jsonify({
                'success': False,
                'message': '반품 내역 등록에 실패했습니다.'
            }), 500
        
    except Exception as e:
        print(f'❌ 반품 등록 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'반품 등록 중 오류: {str(e)}'
        }), 500

