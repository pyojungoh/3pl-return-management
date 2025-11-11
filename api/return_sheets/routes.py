"""
반품 관리 API 라우트
"""
from flask import Blueprint, jsonify, request
from .read_google_sheets import read_return_data, filter_return_data, get_statistics

# Blueprint 생성
return_sheets_bp = Blueprint('return_sheets', __name__, url_prefix='/api/return_sheets')


@return_sheets_bp.route('/data', methods=['GET'])
def get_return_data():
    """
    반품 데이터 조회 API
    
    Query Parameters:
        - company_name: 화주명 필터
        - return_type: 반품/교환/오배송 필터
        - stock_status: 정상/불량 필터
        - completed: true/false (처리완료 여부)
    
    Returns:
        JSON: {
            'success': bool,
            'data': [...],
            'count': int,
            'message': str
        }
    """
    try:
        # 데이터 읽기
        result = read_return_data()
        
        if result['error']:
            return jsonify({
                'success': False,
                'error': result['error'],
                'data': [],
                'count': 0
            }), 500
        
        # 필터 적용
        filters = {}
        if request.args.get('company_name'):
            filters['company_name'] = request.args.get('company_name')
        if request.args.get('return_type'):
            filters['return_type'] = request.args.get('return_type')
        if request.args.get('stock_status'):
            filters['stock_status'] = request.args.get('stock_status')
        if request.args.get('completed'):
            completed_str = request.args.get('completed').lower()
            filters['completed'] = completed_str == 'true'
        
        filtered_data = filter_return_data(result['data'], filters)
        
        return jsonify({
            'success': True,
            'data': filtered_data,
            'count': len(filtered_data),
            'message': f'{len(filtered_data)}건의 데이터를 조회했습니다.'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'data': [],
            'count': 0
        }), 500


@return_sheets_bp.route('/statistics', methods=['GET'])
def get_return_statistics():
    """
    반품 데이터 통계 API
    
    Returns:
        JSON: {
            'success': bool,
            'statistics': {...},
            'message': str
        }
    """
    try:
        # 데이터 읽기
        result = read_return_data()
        
        if result['error']:
            return jsonify({
                'success': False,
                'error': result['error'],
                'statistics': {}
            }), 500
        
        # 통계 생성
        stats = get_statistics(result['data'])
        
        return jsonify({
            'success': True,
            'statistics': stats,
            'message': '통계 데이터를 생성했습니다.'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'statistics': {}
        }), 500


@return_sheets_bp.route('/companies', methods=['GET'])
def get_companies():
    """
    화주 목록 조회 API
    
    Returns:
        JSON: {
            'success': bool,
            'companies': [...],
            'count': int
        }
    """
    try:
        # 데이터 읽기
        result = read_return_data()
        
        if result['error']:
            return jsonify({
                'success': False,
                'error': result['error'],
                'companies': [],
                'count': 0
            }), 500
        
        # 화주 목록 추출 (중복 제거)
        companies = list(set([
            item['company_name'] 
            for item in result['data'] 
            if item['company_name']
        ]))
        companies.sort()
        
        return jsonify({
            'success': True,
            'companies': companies,
            'count': len(companies)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'companies': [],
            'count': 0
        }), 500


@return_sheets_bp.route('/health', methods=['GET'])
def health_check():
    """
    API 상태 확인
    """
    return jsonify({
        'status': 'ok',
        'service': 'return_sheets_api',
        'message': '반품 관리 API가 정상 작동 중입니다.'
    })





