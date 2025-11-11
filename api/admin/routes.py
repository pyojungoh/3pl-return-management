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
                    lines = f.readlines()
                    
                    # 헤더 찾기 (3번째 줄이 실제 헤더)
                    header_line_index = 2  # 0-based index, 3번째 줄
                    if len(lines) > header_line_index:
                        # 헤더 줄 읽기
                        header_line = lines[header_line_index].strip()
                        # 헤더 정규화 (줄바꿈 제거, 공백 정리)
                        header_line = header_line.replace('\n', ' ').replace('\r', ' ')
                        header_line = ' '.join(header_line.split())  # 여러 공백을 하나로
                        
                        # CSV 파서로 헤더 파싱
                        import io
                        header_reader = csv.reader(io.StringIO(header_line))
                        headers = next(header_reader)
                        
                        # 컬럼명 정규화 (공백 제거, 소문자 변환 없이 유지)
                        normalized_headers = []
                        header_map = {}
                        for i, h in enumerate(headers):
                            normalized = h.strip().replace('\n', ' ').replace('\r', ' ')
                            normalized = ' '.join(normalized.split())
                            normalized_headers.append(normalized)
                            # 다양한 변형으로 매핑
                            header_map[normalized] = i
                            header_map[h.strip()] = i
                            header_map[h.strip().replace('\n', ' ')] = i
                            header_map[h.strip().replace('\r\n', ' ')] = i
                        
                        print(f"   헤더 발견: {len(headers)}개 컬럼")
                        print(f"   컬럼명: {normalized_headers[:5]}...")
                        
                        # 데이터 읽기 (헤더 다음 줄부터)
                        data_start_index = header_line_index + 1
                        row_count = 0
                        
                        for line_idx in range(data_start_index, len(lines)):
                            line = lines[line_idx].strip()
                            if not line:
                                continue
                            
                            try:
                                # CSV 파서로 데이터 행 파싱
                                row_reader = csv.reader(io.StringIO(line))
                                row_values = next(row_reader)
                                
                                # 컬럼 개수가 헤더보다 적으면 패딩
                                while len(row_values) < len(headers):
                                    row_values.append('')
                                
                                # 딕셔너리로 변환
                                row_dict = {}
                                for i, value in enumerate(row_values):
                                    if i < len(normalized_headers):
                                        row_dict[normalized_headers[i]] = value
                                        # 원본 헤더명도 저장
                                        if i < len(headers):
                                            row_dict[headers[i]] = value
                                
                                # 데이터 추출 (다양한 컬럼명 시도)
                                customer_name = (
                                    row_dict.get('고객명') or 
                                    row_dict.get('customer_name') or 
                                    ''
                                ).strip()
                                
                                tracking_number = (
                                    row_dict.get('송장번호') or 
                                    row_dict.get('tracking_number') or 
                                    ''
                                ).strip()
                                
                                company_name = (
                                    row_dict.get('화주명') or 
                                    row_dict.get('company_name') or 
                                    ''
                                ).strip()
                                
                                # 빈 행 건너뛰기
                                if not customer_name or not tracking_number:
                                    continue
                                
                                # 화주명이 없으면 건너뛰기
                                if not company_name:
                                    continue
                                
                                # 숫자만 있는 행 건너뛰기 (예: "3", "4" 등)
                                if customer_name.isdigit() and tracking_number.isdigit():
                                    continue
                                
                                # 설명 행 건너뛰기
                                if '예시' in customer_name or '댓글' in customer_name or '제품에' in customer_name:
                                    continue
                                
                                # 재고상태 컬럼명 정규화
                                stock_status_key = None
                                for key in row_dict.keys():
                                    if '재고상태' in key:
                                        stock_status_key = key
                                        break
                                
                                # 반품 데이터 생성
                                return_data = {
                                    'return_date': (row_dict.get('반품 접수일') or row_dict.get('접수일') or '').strip() or None,
                                    'company_name': company_name,
                                    'product': (row_dict.get('제품') or '').strip() or None,
                                    'customer_name': customer_name,
                                    'tracking_number': tracking_number,
                                    'return_type': (row_dict.get('반품/교환/오배송') or row_dict.get('반품/교환') or '').strip() or None,
                                    'stock_status': (row_dict.get(stock_status_key) if stock_status_key else '').strip() or None,
                                    'inspection': (row_dict.get('검품유무') or '').strip() or None,
                                    'completed': (row_dict.get('처리완료') or '').strip() or None,
                                    'memo': (row_dict.get('비고') or '').strip() or None,
                                    'photo_links': (row_dict.get('사진') or '').strip() or None,
                                    'other_courier': None,
                                    'shipping_fee': (row_dict.get('금액') or row_dict.get('배송비') or '').strip() or None,
                                    'client_request': (row_dict.get('화주사요청') or row_dict.get('화주사요청사항') or '').strip() or None,
                                    'client_confirmed': (row_dict.get('화주사확인완료') or row_dict.get('화주사확인') or '').strip() or None,
                                    'month': month
                                }
                                
                                # 데이터 검증
                                if not return_data['company_name']:
                                    continue
                                
                                return_id = create_return(return_data)
                                if return_id:
                                    results['returns']['success'] += 1
                                    row_count += 1
                                else:
                                    results['returns']['skip'] += 1
                                    
                                if results['returns']['success'] % 50 == 0 and results['returns']['success'] > 0:
                                    print(f"   진행 중: {results['returns']['success']}개 성공")
                                    
                            except Exception as e:
                                results['returns']['error'] += 1
                                error_msg = f"줄 {line_idx+1}: {str(e)[:50]}"
                                if len(results['returns']['errors']) < 20:  # 최대 20개 오류만 저장
                                    results['returns']['errors'].append(error_msg)
                                if results['returns']['error'] <= 5:  # 처음 5개만 출력
                                    print(f"   ⚠️ 오류 (줄 {line_idx+1}): {str(e)[:100]}")
                        
                        print(f"   ✅ {filename} 완료: {results['returns']['success']}개 성공, {results['returns']['skip']}개 건너뜀, {results['returns']['error']}개 오류")
                    else:
                        results['returns']['error'] += 1
                        results['returns']['errors'].append(f"{filename}: 헤더를 찾을 수 없습니다")
                        print(f"   ❌ {filename}: 파일이 너무 짧습니다 (헤더 없음)")
                        
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

