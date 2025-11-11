"""
관리자 전용 API 라우트 (데이터 마이그레이션 등)
"""
import os
import csv
from flask import Blueprint, request, jsonify
from api.database.models import (
    create_company,
    create_return,
    get_company_by_username,
    get_all_companies,
    init_db
)

# Blueprint 생성
admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


def check_admin_role(request):
    """관리자 권한 확인 (간단한 구현)"""
    # 실제로는 세션이나 토큰으로 확인해야 함
    # 여기서는 간단하게 요청 헤더나 쿼리 파라미터로 확인
    # 실제 운영 환경에서는 JWT 토큰 등을 사용해야 함
    return True  # 일단 모든 요청 허용 (개발 단계)


@admin_bp.route('/migrate-from-csv', methods=['POST'])
def migrate_from_csv():
    """
    CSV 파일에서 데이터를 PostgreSQL로 마이그레이션 (관리자 전용)
    
    Request Body:
        {
            "force": false  # true면 기존 데이터도 업데이트
        }
    """
    try:
        if not check_admin_role(request):
            return jsonify({
                'success': False,
                'message': '관리자 권한이 필요합니다.'
            }), 403
        
        force = request.get_json().get('force', False) if request.get_json() else False
        
        # CSV 파일 디렉토리
        csv_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'csv_data')
        
        if not os.path.exists(csv_dir):
            return jsonify({
                'success': False,
                'message': f'CSV 파일 디렉토리를 찾을 수 없습니다: {csv_dir}'
            }), 404
        
        results = {
            'companies': {'success': 0, 'skip': 0, 'error': 0, 'errors': []},
            'returns': {'success': 0, 'skip': 0, 'error': 0, 'errors': []}
        }
        
        # 1. 화주사 계정 마이그레이션
        companies_file = os.path.join(csv_dir, 'companies.csv')
        if os.path.exists(companies_file):
            print(f"📋 화주사 계정 마이그레이션 시작: {companies_file}")
            with open(companies_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        # CSV 컬럼명: 화주명,로그인ID,비밀번호,권한,연락처
                        username = row.get('로그인ID', row.get('username', '')).strip()
                        if not username:
                            continue
                        
                        # 기존 계정 확인
                        existing = get_company_by_username(username)
                        if existing and not force:
                            results['companies']['skip'] += 1
                            continue
                        
                        # 새 계정 생성
                        create_company(
                            company_name=row.get('화주명', row.get('company_name', '')).strip(),
                            username=username,
                            password=row.get('비밀번호', row.get('password', '')).strip(),
                            role=row.get('권한', row.get('role', '화주사')).strip(),
                            business_tel=row.get('연락처', row.get('business_tel', '')).strip() or None
                        )
                        results['companies']['success'] += 1
                    except Exception as e:
                        results['companies']['error'] += 1
                        error_msg = f"{row.get('로그인ID', row.get('username', 'Unknown'))}: {str(e)}"
                        results['companies']['errors'].append(error_msg)
                        print(f"❌ 오류: {error_msg}")
        
        # 2. 반품 데이터 마이그레이션
        import glob
        csv_files = glob.glob(os.path.join(csv_dir, '*.csv'))
        
        for csv_file in csv_files:
            filename = os.path.basename(csv_file)
            # companies.csv는 제외
            if filename == 'companies.csv':
                continue
            
            # 월 추출 (예: "2025년11월.csv" -> "2025년11월")
            month = filename.replace('.csv', '').strip()
            
            print(f"📦 반품 데이터 마이그레이션 시작: {filename} ({month})")
            
            try:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    # CSV 파일 전체를 읽어서 파싱 (여러 줄 데이터 자동 처리)
                    reader = csv.reader(f)
                    all_rows = list(reader)
                    
                    if len(all_rows) < 3:
                        results['returns']['error'] += 1
                        results['returns']['errors'].append(f"{filename}: 파일이 너무 짧습니다")
                        print(f"   ❌ {filename}: 파일이 너무 짧습니다")
                        continue
                    
                    # 헤더 찾기
                    # CSV 구조: 
                    # 0: 빈 행
                    # 1: 설명 행
                    # 2: 헤더 첫 번째 부분 (반품 접수일,화주명,제품,고객명,송장번호,반품/교환/오배송,"재고상태)
                    # 3: 헤더 두 번째 부분 ((불량/정상)",검품유무,처리완료,비고,사진,QR코드,금액,화주사요청,화주사확인완료)
                    # 4: 데이터 시작 (예시 데이터 포함)
                    
                    # 헤더를 찾기 위해 "반품 접수일" 또는 "화주명"이 포함된 행 찾기
                    header_row_idx = None
                    for i, row in enumerate(all_rows):
                        if row and len(row) > 0:
                            first_cell = str(row[0]).strip()
                            # 헤더 찾기: "반품 접수일" 또는 첫 번째 셀에 접수일이 포함된 경우
                            if '접수일' in first_cell or (i == 2 and len(row) > 1 and '화주명' in str(row[1])):
                                header_row_idx = i
                                break
                    
                    if header_row_idx is None:
                        # 기본값: 3번째 행 (인덱스 2)
                        header_row_idx = 2
                    
                    if header_row_idx >= len(all_rows):
                        results['returns']['error'] += 1
                        results['returns']['errors'].append(f"{filename}: 헤더를 찾을 수 없습니다")
                        continue
                    
                    # 헤더 행 가져오기
                    header_row = all_rows[header_row_idx]
                    
                    # 다음 행도 헤더일 수 있음 (재고상태가 2줄에 걸쳐 있음)
                    if header_row_idx + 1 < len(all_rows):
                        next_row = all_rows[header_row_idx + 1]
                        # 다음 행의 첫 번째 셀이 비어있거나 "("로 시작하면 헤더의 연속
                        if next_row and len(next_row) > 0:
                            first_cell_next = str(next_row[0]).strip()
                            if not first_cell_next or first_cell_next.startswith('(') or '불량/정상' in first_cell_next:
                                # 두 번째 행의 헤더를 첫 번째 행에 병합
                                # 첫 번째 행의 마지막 셀과 두 번째 행의 첫 번째 셀을 병합
                                if header_row and next_row:
                                    # 마지막 셀과 첫 번째 셀 병합
                                    if header_row and len(header_row) > 0:
                                        last_header = header_row[-1] if header_row else ''
                                        if next_row and len(next_row) > 0:
                                            first_next = next_row[0] if next_row else ''
                                            # 병합
                                            merged = (last_header + first_next).strip()
                                            header_row = header_row[:-1] + [merged] + next_row[1:]
                                            header_row_idx += 1  # 데이터 시작 인덱스 조정
                    
                    # 헤더 정규화 (줄바꿈 제거, 공백 정리)
                    normalized_headers = []
                    for h in header_row:
                        if h:
                            normalized = str(h).strip().replace('\n', ' ').replace('\r', ' ')
                            normalized = ' '.join(normalized.split())  # 여러 공백을 하나로
                            normalized_headers.append(normalized)
                        else:
                            normalized_headers.append('')
                    
                    # 컬럼 인덱스 찾기
                    col_indices = {}
                    for i, header in enumerate(normalized_headers):
                        header_lower = header.lower()
                        if '접수일' in header or '반품 접수일' in header:
                            col_indices['return_date'] = i
                        elif '화주명' in header or '화주' in header:
                            col_indices['company_name'] = i
                        elif '제품' in header:
                            col_indices['product'] = i
                        elif '고객명' in header or '고객' in header:
                            col_indices['customer_name'] = i
                        elif '송장번호' in header or '송장' in header:
                            col_indices['tracking_number'] = i
                        elif '반품/교환' in header or '반품' in header:
                            col_indices['return_type'] = i
                        elif '재고상태' in header:
                            col_indices['stock_status'] = i
                        elif '검품유무' in header or '검품' in header:
                            col_indices['inspection'] = i
                        elif '처리완료' in header:
                            col_indices['completed'] = i
                        elif '비고' in header:
                            col_indices['memo'] = i
                        elif '사진' in header:
                            col_indices['photo_links'] = i
                        elif '금액' in header or '배송비' in header:
                            col_indices['shipping_fee'] = i
                        elif '화주사요청' in header or '요청' in header:
                            col_indices['client_request'] = i
                        elif '화주사확인' in header or '확인완료' in header:
                            col_indices['client_confirmed'] = i
                    
                    print(f"   헤더 발견: {len(normalized_headers)}개 컬럼")
                    print(f"   컬럼 인덱스: {col_indices}")
                    
                    # 데이터 읽기 (헤더 다음 행부터, 인덱스 3부터)
                    data_start_idx = header_row_idx + 1
                    processed_count = 0
                    skipped_count = 0
                    
                    for row_idx in range(data_start_idx, len(all_rows)):
                        row = all_rows[row_idx]
                        
                        # 빈 행 건너뛰기
                        if not row or all(not cell.strip() for cell in row):
                            continue
                        
                        try:
                            # 행 길이 확장 (컬럼 개수 맞추기)
                            while len(row) < len(normalized_headers):
                                row.append('')
                            
                            # 데이터 추출
                            def get_col(idx, default=''):
                                if idx is not None and idx < len(row):
                                    return row[idx].strip()
                                return default
                            
                            customer_name = get_col(col_indices.get('customer_name'))
                            tracking_number = get_col(col_indices.get('tracking_number'))
                            company_name = get_col(col_indices.get('company_name'))
                            
                            # 필수 필드 검증
                            if not customer_name or not tracking_number:
                                skipped_count += 1
                                continue
                            
                            # 화주명이 없으면 건너뛰기
                            if not company_name:
                                skipped_count += 1
                                continue
                            
                            # 설명/예시 행 건너뛰기
                            if '예시' in customer_name or '댓글' in customer_name or '제품에' in customer_name:
                                skipped_count += 1
                                continue
                            
                            # 숫자만 있는 행 건너뛰기
                            if customer_name.isdigit() and tracking_number.isdigit():
                                skipped_count += 1
                                continue
                            
                            # 반품 데이터 생성
                            return_data = {
                                'return_date': get_col(col_indices.get('return_date')) or None,
                                'company_name': company_name,
                                'product': get_col(col_indices.get('product')) or None,
                                'customer_name': customer_name,
                                'tracking_number': tracking_number,
                                'return_type': get_col(col_indices.get('return_type')) or None,
                                'stock_status': get_col(col_indices.get('stock_status')) or None,
                                'inspection': get_col(col_indices.get('inspection')) or None,
                                'completed': get_col(col_indices.get('completed')) or None,
                                'memo': get_col(col_indices.get('memo')) or None,
                                'photo_links': get_col(col_indices.get('photo_links')) or None,
                                'other_courier': None,
                                'shipping_fee': get_col(col_indices.get('shipping_fee')) or None,
                                'client_request': get_col(col_indices.get('client_request')) or None,
                                'client_confirmed': get_col(col_indices.get('client_confirmed')) or None,
                                'month': month
                            }
                            
                            # 데이터베이스에 저장
                            return_id = create_return(return_data)
                            if return_id:
                                results['returns']['success'] += 1
                                processed_count += 1
                            else:
                                results['returns']['skip'] += 1
                                skipped_count += 1
                            
                            # 진행 상황 출력
                            if results['returns']['success'] % 50 == 0 and results['returns']['success'] > 0:
                                print(f"   진행 중: {results['returns']['success']}개 성공")
                                
                        except Exception as e:
                            results['returns']['error'] += 1
                            error_msg = f"줄 {row_idx+1}: {str(e)[:50]}"
                            if len(results['returns']['errors']) < 20:
                                results['returns']['errors'].append(error_msg)
                            if results['returns']['error'] <= 10:
                                print(f"   ⚠️ 오류 (줄 {row_idx+1}): {str(e)[:100]}")
                    
                    print(f"   ✅ {filename} 완료: {results['returns']['success']}개 성공, {results['returns']['skip']}개 건너뜀, {results['returns']['error']}개 오류")
                    print(f"   처리된 행: {processed_count}개, 건너뛴 행: {skipped_count}개")
                        
            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                results['returns']['error'] += 1
                error_msg = f"{filename}: {str(e)}"
                results['returns']['errors'].append(error_msg[:200])
                print(f"   ❌ {filename} 파일 읽기 오류: {str(e)}")
                print(f"   상세: {error_detail[:500]}")
        
        # 결과 요약
        total_companies = results['companies']['success'] + results['companies']['skip'] + results['companies']['error']
        total_returns = results['returns']['success'] + results['returns']['skip'] + results['returns']['error']
        
        return jsonify({
            'success': True,
            'message': '마이그레이션 완료',
            'results': {
                'companies': {
                    'total': total_companies,
                    'success': results['companies']['success'],
                    'skip': results['companies']['skip'],
                    'error': results['companies']['error'],
                    'errors': results['companies']['errors'][:10]  # 최대 10개만 표시
                },
                'returns': {
                    'total': total_returns,
                    'success': results['returns']['success'],
                    'skip': results['returns']['skip'],
                    'error': results['returns']['error'],
                    'errors': results['returns']['errors'][:10]  # 최대 10개만 표시
                }
            }
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'마이그레이션 중 오류 발생: {str(e)}'
        }), 500


@admin_bp.route('/migrate-status', methods=['GET'])
def migrate_status():
    """
    마이그레이션 상태 확인 (데이터베이스 통계)
    """
    try:
        from api.database.models import get_companies_statistics, get_available_months, get_returns_by_company
        
        # 통계 정보
        stats = get_companies_statistics()
        months = get_available_months()
        
        # 각 월별 데이터 개수
        month_counts = {}
        for month in months:
            try:
                returns = get_returns_by_company('', month, role='관리자')
                month_counts[month] = len(returns)
            except:
                month_counts[month] = 0
        
        return jsonify({
            'success': True,
            'statistics': {
                'companies': {
                    'total': stats.get('total_count', 0),
                    'admin': stats.get('admin_count', 0),
                    'shipper': stats.get('company_count', 0)
                },
                'returns': {
                    'months': month_counts,
                    'total': sum(month_counts.values())
                }
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'통계 조회 중 오류 발생: {str(e)}'
        }), 500

