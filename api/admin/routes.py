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
                    reader = csv.DictReader(f)
                    for row in reader:
                        try:
                            customer_name = row.get('고객명', row.get('customer_name', '')).strip()
                            tracking_number = row.get('송장번호', row.get('tracking_number', '')).strip()
                            
                            # 빈 행 건너뛰기
                            if not customer_name or not tracking_number:
                                continue
                            
                            # 숫자만 있는 행 건너뛰기 (예: "3", "4" 등)
                            if customer_name.isdigit() and tracking_number.isdigit():
                                continue
                            
                            # 설명 행 건너뛰기
                            if '예시' in customer_name or '댓글' in customer_name:
                                continue
                            
                            # 반품 데이터 생성
                            # CSV 컬럼명: 반품 접수일,화주명,제품,고객명,송장번호,반품/교환/오배송,재고상태(불량/정상),검품유무,처리완료,비고,사진,QR코드,금액,화주사요청,화주사확인완료
                            return_data = {
                                'return_date': row.get('반품 접수일', row.get('접수일', row.get('return_date', ''))).strip() or None,
                                'company_name': row.get('화주명', row.get('company_name', '')).strip() or '',
                                'product': row.get('제품', row.get('product', '')).strip() or None,
                                'customer_name': customer_name,
                                'tracking_number': tracking_number,
                                'return_type': row.get('반품/교환/오배송', row.get('반품/교환', row.get('return_type', ''))).strip() or None,
                                'stock_status': row.get('재고상태\n(불량/정상)', row.get('재고상태(불량/정상)', row.get('재고상태', row.get('stock_status', '')))).strip() or None,
                                'inspection': row.get('검품유무', row.get('inspection', '')).strip() or None,
                                'completed': row.get('처리완료', row.get('completed', '')).strip() or None,
                                'memo': row.get('비고', row.get('memo', '')).strip() or None,
                                'photo_links': row.get('사진', row.get('photo_links', '')).strip() or None,
                                'other_courier': None,  # CSV에 타택배 컬럼이 없을 수 있음
                                'shipping_fee': row.get('금액', row.get('배송비', row.get('shipping_fee', ''))).strip() or None,
                                'client_request': row.get('화주사요청', row.get('화주사요청사항', row.get('client_request', ''))).strip() or None,
                                'client_confirmed': row.get('화주사확인완료', row.get('화주사확인', row.get('client_confirmed', ''))).strip() or None,
                                'month': month
                            }
                            
                            return_id = create_return(return_data)
                            if return_id:
                                results['returns']['success'] += 1
                            else:
                                results['returns']['skip'] += 1
                                
                            if results['returns']['success'] % 100 == 0:
                                print(f"   진행 중: {results['returns']['success']}개")
                        except Exception as e:
                            results['returns']['error'] += 1
                            error_msg = f"{customer_name}/{tracking_number}: {str(e)}"
                            results['returns']['errors'].append(error_msg[:100])  # 오류 메시지 길이 제한
            except Exception as e:
                results['returns']['error'] += 1
                results['returns']['errors'].append(f"{filename}: {str(e)}")
        
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

