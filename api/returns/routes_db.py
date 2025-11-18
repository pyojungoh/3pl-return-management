"""
반품 관리 API 라우트 (SQLite 데이터베이스 기반)
"""
from flask import Blueprint, request, jsonify, Response
import csv
import io
from urllib.parse import quote
from api.database.models import (
    get_returns_by_company,
    get_available_months,
    save_client_request,
    mark_as_completed,
    get_return_by_id,
    update_memo,
    delete_return,
    create_return,
    update_return
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
        
        # 화주사인 경우 사업자 정보 확인
        requires_business_info = False
        if role != '관리자':
            from api.database.models import get_company_by_username
            username = request.args.get('username', '').strip()
            if username:
                company_info = get_company_by_username(username)
                if company_info:
                    # 사업자 정보 필수 필드 확인
                    business_number = company_info.get('business_number', '').strip() if company_info.get('business_number') else ''
                    business_name = company_info.get('business_name', '').strip() if company_info.get('business_name') else ''
                    business_address = company_info.get('business_address', '').strip() if company_info.get('business_address') else ''
                    business_tel = company_info.get('business_tel', '').strip() if company_info.get('business_tel') else ''
                    business_email = company_info.get('business_email', '').strip() if company_info.get('business_email') else ''
                    
                    # 필수 필드 중 하나라도 없으면 사업자 정보 입력 필요
                    if not business_number or not business_name or not business_address or not business_tel or not business_email:
                        requires_business_info = True
                        print(f"⚠️ 화주사 '{username}'의 사업자 정보가 불완전합니다.")
        
        # 디버깅: 파라미터 확인
        print(f"📊 반품 데이터 조회 - company: '{company}', month: '{month}', role: '{role}'")
        
        # 사업자 정보가 필요한 경우 데이터 조회 전에 플래그 반환
        if requires_business_info:
            return jsonify({
                'success': False,
                'data': [],
                'count': 0,
                'requires_business_info': True,
                'message': '사업자 정보를 입력해주세요.'
            }), 200  # 200으로 반환하여 프론트엔드에서 정상 처리 가능하도록
        
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
            # ID로 정렬 (내림차순) - None 값 처리
            -(x.get('id') or 0)
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


@returns_bp.route('/update', methods=['POST'])
def update_return_route():
    """
    반품 데이터 업데이트 API (관리자 전용)
    
    Request Body:
        {
            "id": int,              # 반품 ID
            "company_name": str,     # 화주명 (선택)
            "product": str,          # 제품 (선택)
            "return_type": str,      # 반품/교환/오배송 (선택)
            "stock_status": str      # 재고상태 (선택)
        }
    """
    try:
        data = request.get_json()
        return_id = data.get('id')
        
        if not return_id:
            return jsonify({
                'success': False,
                'message': '반품 ID가 필요합니다.'
            }), 400
        
        # 업데이트할 데이터만 추출
        update_data = {}
        if 'company_name' in data:
            update_data['company_name'] = data.get('company_name', '').strip()
        if 'product' in data:
            update_data['product'] = data.get('product', '').strip()
        if 'return_type' in data:
            update_data['return_type'] = data.get('return_type', '').strip()
        if 'stock_status' in data:
            update_data['stock_status'] = data.get('stock_status', '').strip()
        
        if not update_data:
            return jsonify({
                'success': False,
                'message': '업데이트할 데이터가 없습니다.'
            }), 400
        
        if update_return(return_id, update_data):
            return jsonify({
                'success': True,
                'message': '반품 데이터가 업데이트되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': '반품 데이터 업데이트에 실패했습니다.'
            }), 500
        
    except Exception as e:
        print(f'❌ 반품 업데이트 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'반품 업데이트 중 오류: {str(e)}'
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
        
        # 디버깅: 입력 데이터 확인
        print(f"📝 반품등록 요청 데이터:")
        print(f"   고객명: {data.get('customer_name')}")
        print(f"   송장번호: {data.get('tracking_number')}")
        print(f"   화주명: {data.get('company_name')}")
        print(f"   월: {data.get('month')}")
        print(f"   제품: {data.get('product')}")
        
        # 필수 필드 확인
        if not data.get('customer_name') or not data.get('tracking_number') or not data.get('month'):
            return jsonify({
                'success': False,
                'message': '고객명, 송장번호, 월은 필수입니다.'
            }), 400
        
        return_id = create_return(data)
        print(f"   ✅ create_return 결과: return_id = {return_id}")
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


@returns_bp.route('/upload-csv', methods=['POST'])
def upload_csv_route():
    """
    CSV 파일 업로드하여 반품 데이터 일괄 등록
    
    Request:
        - file: CSV 파일 (multipart/form-data)
        - month: 월 (예: "2025년11월") - 선택사항, 파일명에서 추출 시도
        - force: 기존 데이터 덮어쓰기 여부 (기본값: false)
    """
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': 'CSV 파일이 없습니다.'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': '파일을 선택해주세요.'
            }), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({
                'success': False,
                'message': 'CSV 파일만 업로드 가능합니다.'
            }), 400
        
        # 월 파라미터 확인
        month = request.form.get('month', '').strip()
        force = request.form.get('force', 'false').lower() == 'true'
        
        # 파일명에서 월 추출 시도 (예: "2025년11월.csv" -> "2025년11월")
        if not month and file.filename:
            filename_without_ext = file.filename.replace('.csv', '').strip()
            # "2025년11월" 형식인지 확인
            if '년' in filename_without_ext and '월' in filename_without_ext:
                month = filename_without_ext
        
        if not month:
            return jsonify({
                'success': False,
                'message': '월 정보가 필요합니다. 파일명에 월 정보를 포함하거나 월을 입력해주세요. (예: 2025년11월.csv)'
            }), 400
        
        # CSV 파일 읽기
        file_content = file.read().decode('utf-8-sig')  # BOM 제거
        csv_reader = csv.reader(io.StringIO(file_content))
        all_rows = list(csv_reader)
        
        # 최소 길이 체크: 헤더 1줄 + 데이터 1줄 이상
        if len(all_rows) < 2:
            return jsonify({
                'success': False,
                'message': 'CSV 파일이 너무 짧습니다. (최소 헤더 1줄 + 데이터 1줄 필요)'
            }), 400
        
        # 헤더 찾기 (admin/routes.py와 동일한 로직)
        header_row_idx = None
        for i, row in enumerate(all_rows):
            if row and len(row) > 0:
                first_cell = str(row[0]).strip()
                if '접수일' in first_cell or (i == 2 and len(row) > 1 and '화주명' in str(row[1])):
                    header_row_idx = i
                    break
        
        if header_row_idx is None:
            # 헤더를 찾지 못한 경우, 첫 번째 비어있지 않은 행을 헤더로 사용
            for i, row in enumerate(all_rows):
                if row and len(row) > 0 and any(cell.strip() for cell in row):
                    header_row_idx = i
                    break
            if header_row_idx is None:
                return jsonify({
                    'success': False,
                    'message': 'CSV 헤더를 찾을 수 없습니다.'
                }), 400
        
        if header_row_idx >= len(all_rows):
            return jsonify({
                'success': False,
                'message': 'CSV 헤더를 찾을 수 없습니다.'
            }), 400
        
        # 데이터 행이 있는지 확인
        if header_row_idx + 1 >= len(all_rows):
            return jsonify({
                'success': False,
                'message': 'CSV 파일에 데이터 행이 없습니다. (헤더만 있고 데이터가 없음)'
            }), 400
        
        header_row = all_rows[header_row_idx]
        merged_header_row = list(header_row)
        
        # 헤더 병합 처리
        if header_row_idx + 1 < len(all_rows):
            next_row = all_rows[header_row_idx + 1]
            if next_row and len(next_row) > 0:
                first_cell_next = str(next_row[0]).strip() if next_row[0] else ''
                is_header_continuation = (
                    not first_cell_next or 
                    first_cell_next.startswith('(') or 
                    '불량/정상' in first_cell_next or
                    first_cell_next.startswith('(불량') or
                    (len(merged_header_row) > 0 and merged_header_row[-1] and '재고상태' in str(merged_header_row[-1]))
                )
                
                if is_header_continuation:
                    last_header_cell = str(merged_header_row[-1]) if merged_header_row[-1] else ''
                    first_next_cell = str(next_row[0]) if next_row and next_row[0] else ''
                    merged_cell = (last_header_cell + ' ' + first_next_cell).strip()
                    merged_header_row = merged_header_row[:-1] + [merged_cell] + list(next_row[1:])
                    header_row_idx += 1
        
        # 헤더 정규화
        normalized_headers = []
        for h in merged_header_row:
            if h:
                normalized = str(h).strip().replace('\n', ' ').replace('\r', ' ')
                normalized = ' '.join(normalized.split())
                normalized_headers.append(normalized)
            else:
                normalized_headers.append('')
        
        # 컬럼 인덱스 찾기 (admin/routes.py와 동일한 로직)
        column_indices = {}
        for idx, header in enumerate(normalized_headers):
            header_clean = header.strip().lower()
            
            # 정확한 매칭 우선
            if '반품 접수일' in header or ('접수일' in header and '반품' in header):
                if 'return_date' not in column_indices:
                    column_indices['return_date'] = idx
            elif header_clean == '화주명' or ('화주명' in header and '화주' in header):
                if 'company_name' not in column_indices:
                    column_indices['company_name'] = idx
                    print(f"   ✅ 화주명 컬럼 발견: 인덱스 {idx}, 헤더: '{header}'")
            elif header_clean == '제품':
                if 'product' not in column_indices:
                    column_indices['product'] = idx
            elif header_clean == '고객명' or ('고객명' in header and '고객' in header):
                if 'customer_name' not in column_indices:
                    column_indices['customer_name'] = idx
            elif '송장번호' in header or ('송장' in header and '번호' in header):
                if 'tracking_number' not in column_indices:
                    column_indices['tracking_number'] = idx
            elif '반품/교환/오배송' in header or '반품/교환' in header:
                if 'return_type' not in column_indices:
                    column_indices['return_type'] = idx
            elif '재고상태' in header and ('불량' in header or '정상' in header):
                if 'stock_status' not in column_indices:
                    column_indices['stock_status'] = idx
            elif header_clean == '검품유무' or '검품유무' in header:
                if 'inspection' not in column_indices:
                    column_indices['inspection'] = idx
            elif header_clean == '처리완료' or '처리완료' in header:
                if 'completed' not in column_indices:
                    column_indices['completed'] = idx
            elif header_clean == '비고':  # 정확한 매칭
                if 'memo' not in column_indices:
                    column_indices['memo'] = idx
            elif header_clean == '사진':
                if 'photo_links' not in column_indices:
                    column_indices['photo_links'] = idx
            elif header_clean == 'qr코드' or 'qr' in header_clean:
                # QR코드는 사용하지 않지만 인덱스 추적용
                pass
            elif header_clean == '금액':
                if 'shipping_fee' not in column_indices:
                    column_indices['shipping_fee'] = idx
            elif '화주사요청' in header or ('화주사' in header and '요청' in header):
                if 'client_request' not in column_indices:
                    column_indices['client_request'] = idx
            elif '화주사확인완료' in header or ('화주사' in header and '확인' in header):
                if 'client_confirmed' not in column_indices:
                    column_indices['client_confirmed'] = idx
        
        # 디버깅: 컬럼 인덱스 매핑 출력
        print(f"📋 컬럼 인덱스 매핑: {column_indices}")
        print(f"   헤더 목록: {normalized_headers[:15]}")
        if 'company_name' not in column_indices:
            print(f"   ⚠️ 화주명 컬럼을 찾을 수 없습니다!")
            # 기본 인덱스 시도 (일반적인 CSV 구조 기준: 1번째 컬럼)
            if len(normalized_headers) > 1:
                column_indices['company_name'] = 1
                print(f"   🔧 기본 인덱스 1로 화주명 컬럼 설정")
        
        # 필수 컬럼 확인
        if 'customer_name' not in column_indices or 'tracking_number' not in column_indices:
            return jsonify({
                'success': False,
                'message': 'CSV 파일에 고객명 또는 송장번호 컬럼이 없습니다.'
            }), 400
        
        # 데이터 처리
        results = {'success': 0, 'skip': 0, 'error': 0, 'errors': []}
        data_start_idx = header_row_idx + 1
        
        for row_idx, row in enumerate(all_rows[data_start_idx:], start=data_start_idx):
            if not row or len(row) == 0:
                continue
            
            # 빈 행 스킵
            if all(not cell or str(cell).strip() == '' for cell in row[:5]):
                continue
            
            try:
                # 행 길이 확장 (컬럼 개수 맞추기)
                while len(row) < len(normalized_headers):
                    row.append('')
                
                # 안전한 컬럼 값 추출 함수 (admin/routes.py와 동일)
                def get_col(idx, default=''):
                    if idx is not None and idx < len(row):
                        return str(row[idx]).strip() if row[idx] else default
                    return default
                
                # 데이터 추출
                customer_name = get_col(column_indices.get('customer_name'))
                tracking_number = get_col(column_indices.get('tracking_number'))
                
                if not customer_name or not tracking_number:
                    continue
                
                # 기존 데이터 확인 (force가 False인 경우)
                if not force:
                    # 간단한 중복 체크는 생략 (필요시 추가)
                    pass
                
                # 반품 데이터 생성 (admin/routes.py와 동일한 방식)
                return_data = {
                    'return_date': get_col(column_indices.get('return_date')) or None,
                    'company_name': get_col(column_indices.get('company_name')) or '',
                    'product': get_col(column_indices.get('product')) or None,
                    'customer_name': customer_name,
                    'tracking_number': tracking_number,
                    'return_type': get_col(column_indices.get('return_type')) or None,
                    'stock_status': get_col(column_indices.get('stock_status')) or None,
                    'inspection': get_col(column_indices.get('inspection')) or None,
                    'completed': get_col(column_indices.get('completed')) or None,
                    'memo': get_col(column_indices.get('memo')) or None,
                    'photo_links': get_col(column_indices.get('photo_links')) or None,
                    'other_courier': None,
                    'shipping_fee': get_col(column_indices.get('shipping_fee')) or None,
                    'client_request': get_col(column_indices.get('client_request')) or None,
                    'client_confirmed': get_col(column_indices.get('client_confirmed')) or None,
                    'month': month
                }
                
                # 디버깅: 처음 몇 개 데이터만 상세 로그
                if results['success'] < 3:
                    print(f"   데이터 샘플 #{results['success'] + 1}:")
                    print(f"     고객명: {customer_name}, 송장번호: {tracking_number}")
                    print(f"     화주명 컬럼 인덱스: {column_indices.get('company_name')}, 값: '{return_data['company_name']}'")
                    print(f"     비고 컬럼 인덱스: {column_indices.get('memo')}, 값: '{return_data['memo']}'")
                    print(f"     반품 접수일 컬럼 인덱스: {column_indices.get('return_date')}, 값: '{return_data['return_date']}'")
                    print(f"     전체 행 데이터 (처음 10개): {row[:10]}")
                
                # 화주명이 없으면 경고 (하지만 계속 진행)
                if not return_data['company_name']:
                    print(f"   ⚠️ 화주명이 없습니다. 고객명: {customer_name}, 송장번호: {tracking_number}")
                    # 빈 값 허용 (나중에 수정 가능)
                
                return_id = create_return(return_data)
                if return_id:
                    results['success'] += 1
                else:
                    results['skip'] += 1
                    
            except Exception as e:
                results['error'] += 1
                error_msg = f"행 {row_idx + 1}: {str(e)}"
                results['errors'].append(error_msg)
                print(f"❌ CSV 업로드 오류 (행 {row_idx + 1}): {e}")
        
        return jsonify({
            'success': True,
            'message': f'CSV 업로드 완료: 성공 {results["success"]}건, 스킵 {results["skip"]}건, 오류 {results["error"]}건',
            'results': results
        })
        
    except Exception as e:
        print(f'❌ CSV 업로드 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'CSV 업로드 중 오류: {str(e)}'
        }), 500


@returns_bp.route('/download-template', methods=['GET'])
def download_csv_template():
    """
    CSV 서식 파일 다운로드 (UTF-8 BOM 인코딩)
    Excel에서 한글이 깨지지 않도록 BOM 포함
    """
    try:
        # CSV 데이터 생성
        csv_data = [
            ['반품 접수일', '화주명', '제품', '고객명', '송장번호', '반품/교환/오배송', 
             '재고상태 (불량/정상)', '검품유무', '처리완료', '비고', '사진', 'QR코드', 
             '금액', '화주사요청', '화주사확인완료'],
            ['2025-01-15', '제이제이', '상품A', '홍길동', '123456789', '반품', '정상', 
             '강', '강', '테스트 메모', '', '', '', '', ''],
            ['2025-01-16', '보딩패스', '상품B', '이기석', '987654321', '교환', '불량', 
             '표', '표', '', '', '', '', '', '']
        ]
        
        # CSV 문자열 생성
        # quoting=csv.QUOTE_MINIMAL: 필요한 경우만 따옴표 사용 (작은따옴표는 그대로 유지)
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
        writer.writerows(csv_data)
        csv_string = output.getvalue()
        output.close()
        
        # 작은따옴표가 포함된 송장번호가 제대로 저장되었는지 확인
        print(f"✅ CSV 템플릿 생성 완료 (송장번호 텍스트 형식 적용)")
        
        # UTF-8 BOM 추가 (Excel에서 한글 인식)
        csv_bytes = '\ufeff' + csv_string
        csv_bytes = csv_bytes.encode('utf-8-sig')
        
        # 파일명 인코딩 (한글 파일명 지원)
        filename_encoded = quote('반품내역_서식.csv')
        
        print(f"✅ CSV 템플릿 생성 완료: {len(csv_bytes)} bytes")
        
        response = Response(
            csv_bytes,
            mimetype='text/csv; charset=utf-8-sig',
            headers={
                'Content-Disposition': f'attachment; filename*=UTF-8\'\'{filename_encoded}',
                'Content-Type': 'text/csv; charset=utf-8-sig'
            }
        )
        return response
        
    except Exception as e:
        print(f'❌ CSV 템플릿 다운로드 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'CSV 템플릿 다운로드 중 오류: {str(e)}'
        }), 500

