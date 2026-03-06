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
                    # CSV 구조상 헤더가 2줄에 걸쳐 있는 경우가 있음
                    merged_header_row = list(header_row)  # 복사
                    
                    if header_row_idx + 1 < len(all_rows):
                        next_row = all_rows[header_row_idx + 1]
                        # 다음 행의 첫 번째 셀이 비어있거나 "("로 시작하거나 "불량/정상"이 포함되면 헤더의 연속
                        if next_row and len(next_row) > 0:
                            first_cell_next = str(next_row[0]).strip() if next_row[0] else ''
                            # 헤더 연속 판단
                            is_header_continuation = (
                                not first_cell_next or 
                                first_cell_next.startswith('(') or 
                                '불량/정상' in first_cell_next or
                                first_cell_next.startswith('(불량') or
                                (len(merged_header_row) > 0 and merged_header_row[-1] and '재고상태' in str(merged_header_row[-1]))
                            )
                            
                            if is_header_continuation:
                                # 마지막 헤더 셀과 첫 번째 다음 셀 병합
                                if merged_header_row and len(merged_header_row) > 0:
                                    last_header_cell = str(merged_header_row[-1]) if merged_header_row[-1] else ''
                                    first_next_cell = str(next_row[0]) if next_row and next_row[0] else ''
                                    # 병합 (예: "재고상태\n(불량/정상)" -> "재고상태 (불량/정상)")
                                    merged_cell = (last_header_cell + ' ' + first_next_cell).strip()
                                    # 병합된 헤더 생성
                                    merged_header_row = merged_header_row[:-1] + [merged_cell] + list(next_row[1:])
                                    header_row_idx += 1  # 데이터 시작 인덱스 조정
                                    print(f"   헤더 병합 완료: {len(merged_header_row)}개 컬럼")
                    
                    # 헤더 정규화 (줄바꿈 제거, 공백 정리)
                    normalized_headers = []
                    for h in merged_header_row:
                        if h:
                            normalized = str(h).strip().replace('\n', ' ').replace('\r', ' ')
                            normalized = ' '.join(normalized.split())  # 여러 공백을 하나로
                            normalized_headers.append(normalized)
                        else:
                            normalized_headers.append('')
                    
                    print(f"   정규화된 헤더 ({len(normalized_headers)}개): {normalized_headers[:12]}")
                    
                    # 컬럼 인덱스 찾기 (정확한 순서대로 매칭)
                    col_indices = {}
                    
                    # 헤더를 순서대로 확인하고 정확한 컬럼 찾기
                    for i, header in enumerate(normalized_headers):
                        header_clean = header.strip().lower()
                        
                        # 정확한 매칭 우선
                        if '반품 접수일' in header or ('접수일' in header and '반품' in header):
                            if 'return_date' not in col_indices:
                                col_indices['return_date'] = i
                        elif header_clean == '화주명' or ('화주명' in header and '화주' in header):
                            if 'company_name' not in col_indices:
                                col_indices['company_name'] = i
                        elif header_clean == '제품':
                            if 'product' not in col_indices:
                                col_indices['product'] = i
                        elif header_clean == '고객명' or ('고객명' in header and '고객' in header):
                            if 'customer_name' not in col_indices:
                                col_indices['customer_name'] = i
                        elif '송장번호' in header or ('송장' in header and '번호' in header):
                            if 'tracking_number' not in col_indices:
                                col_indices['tracking_number'] = i
                        elif '반품/교환/오배송' in header or '반품/교환' in header:
                            if 'return_type' not in col_indices:
                                col_indices['return_type'] = i
                        elif '재고상태' in header and ('불량' in header or '정상' in header):
                            if 'stock_status' not in col_indices:
                                col_indices['stock_status'] = i
                        elif header_clean == '검품유무' or '검품유무' in header:
                            if 'inspection' not in col_indices:
                                col_indices['inspection'] = i
                        elif header_clean == '처리완료' or '처리완료' in header:
                            if 'completed' not in col_indices:
                                col_indices['completed'] = i
                        elif header_clean == '비고':
                            if 'memo' not in col_indices:
                                col_indices['memo'] = i
                        elif header_clean == '사진':
                            if 'photo_links' not in col_indices:
                                col_indices['photo_links'] = i
                        elif header_clean == 'qr코드' or 'qr' in header_clean:
                            # QR코드는 사용하지 않지만 인덱스 추적용
                            pass
                        elif header_clean == '금액':
                            if 'shipping_fee' not in col_indices:
                                col_indices['shipping_fee'] = i
                        elif '화주사요청' in header or ('화주사' in header and '요청' in header):
                            if 'client_request' not in col_indices:
                                col_indices['client_request'] = i
                        elif '화주사확인완료' in header or ('화주사' in header and '확인' in header):
                            if 'client_confirmed' not in col_indices:
                                col_indices['client_confirmed'] = i
                    
                    # 디버깅: 헤더와 매핑 결과 출력
                    print(f"   헤더 발견: {len(normalized_headers)}개 컬럼")
                    print(f"   헤더 목록: {normalized_headers[:15]}")  # 처음 15개만
                    print(f"   컬럼 인덱스 매핑: {col_indices}")
                    
                    # 필수 컬럼 확인
                    required_cols = ['customer_name', 'tracking_number', 'company_name']
                    missing_cols = [col for col in required_cols if col not in col_indices]
                    if missing_cols:
                        print(f"   ⚠️ 필수 컬럼 누락: {missing_cols}")
                        # 기본 인덱스 시도 (일반적인 CSV 구조 기준)
                        if 'company_name' not in col_indices and len(normalized_headers) > 1:
                            col_indices['company_name'] = 1
                        if 'customer_name' not in col_indices and len(normalized_headers) > 3:
                            col_indices['customer_name'] = 3
                        if 'tracking_number' not in col_indices and len(normalized_headers) > 4:
                            col_indices['tracking_number'] = 4
                        if 'completed' not in col_indices and len(normalized_headers) > 8:
                            col_indices['completed'] = 8
                        if 'inspection' not in col_indices and len(normalized_headers) > 7:
                            col_indices['inspection'] = 7
                        if 'stock_status' not in col_indices and len(normalized_headers) > 6:
                            col_indices['stock_status'] = 6
                        if 'return_type' not in col_indices and len(normalized_headers) > 5:
                            col_indices['return_type'] = 5
                        if 'product' not in col_indices and len(normalized_headers) > 2:
                            col_indices['product'] = 2
                        if 'return_date' not in col_indices and len(normalized_headers) > 0:
                            col_indices['return_date'] = 0
                        if 'memo' not in col_indices and len(normalized_headers) > 9:
                            col_indices['memo'] = 9
                        print(f"   기본 인덱스 적용 후: {col_indices}")
                    
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
                            completed_value = get_col(col_indices.get('completed'))
                            inspection_value = get_col(col_indices.get('inspection'))
                            stock_status_value = get_col(col_indices.get('stock_status'))
                            return_type_value = get_col(col_indices.get('return_type'))
                            return_date_value = get_col(col_indices.get('return_date'))
                            product_value = get_col(col_indices.get('product'))
                            memo_value = get_col(col_indices.get('memo'))
                            photo_links_value = get_col(col_indices.get('photo_links'))
                            shipping_fee_value = get_col(col_indices.get('shipping_fee'))
                            client_request_value = get_col(col_indices.get('client_request'))
                            client_confirmed_value = get_col(col_indices.get('client_confirmed'))
                            
                            # 디버깅: 처음 몇 개 데이터만 상세 로그
                            if processed_count < 3:
                                print(f"   데이터 샘플 #{processed_count + 1}:")
                                print(f"     고객명: {customer_name}, 송장번호: {tracking_number}")
                                print(f"     처리완료 컬럼 인덱스: {col_indices.get('completed')}, 값: '{completed_value}'")
                                print(f"     검품유무: '{inspection_value}', 재고상태: '{stock_status_value}'")
                                print(f"     사진 컬럼 인덱스: {col_indices.get('photo_links')}, 값: '{photo_links_value}'")
                                print(f"     전체 행: {row[:12]}")  # 처음 12개 컬럼만 (사진 포함)
                            
                            return_data = {
                                'return_date': return_date_value or None,
                                'company_name': company_name,
                                'product': product_value or None,
                                'customer_name': customer_name,
                                'tracking_number': tracking_number,
                                'return_type': return_type_value or None,
                                'stock_status': stock_status_value or None,
                                'inspection': inspection_value or None,
                                'completed': completed_value or None,  # 처리완료 값 (예: "강", "표", "표정오" 등)
                                'memo': memo_value or None,
                                'photo_links': photo_links_value or None,
                                'other_courier': None,
                                'shipping_fee': shipping_fee_value or None,
                                'client_request': client_request_value or None,
                                'client_confirmed': client_confirmed_value or None,
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
        from api.database.models import get_companies_statistics, get_available_months, get_returns_by_company, is_company_deactivated
        
        # 통계 정보
        stats = get_companies_statistics()
        months = get_available_months()
        
        # 각 월별 데이터 개수 (이전/비활성 화주사 데이터 제외)
        month_counts = {}
        for month in months:
            try:
                returns = get_returns_by_company('', month, role='관리자')
                returns = [r for r in returns if not is_company_deactivated(r.get('company_name', '') or '')]
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

