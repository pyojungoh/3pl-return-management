"""
헤더 배너 관리 API 라우트
"""
from flask import Blueprint, request, jsonify

# 함수 import 시도 및 오류 처리
try:
    from api.database.models import (
        create_header_banner,
        get_all_header_banners,
        get_active_header_banners,
        get_header_banner_by_id,
        update_header_banner,
        delete_header_banner
    )
    print("[헤더 배너 API] 함수 import 성공")
except ImportError as e:
    print(f"[헤더 배너 API] ❌ 함수 import 실패: {e}")
    import traceback
    traceback.print_exc()
    # 빈 함수로 대체하여 서버가 시작되도록 함
    def create_header_banner(*args, **kwargs):
        raise Exception(f"create_header_banner 함수를 import할 수 없습니다: {e}")
    def get_all_header_banners(*args, **kwargs):
        raise Exception(f"get_all_header_banners 함수를 import할 수 없습니다: {e}")
    def get_active_header_banners(*args, **kwargs):
        raise Exception(f"get_active_header_banners 함수를 import할 수 없습니다: {e}")
    def get_header_banner_by_id(*args, **kwargs):
        raise Exception(f"get_header_banner_by_id 함수를 import할 수 없습니다: {e}")
    def update_header_banner(*args, **kwargs):
        raise Exception(f"update_header_banner 함수를 import할 수 없습니다: {e}")
    def delete_header_banner(*args, **kwargs):
        raise Exception(f"delete_header_banner 함수를 import할 수 없습니다: {e}")

# Blueprint 생성
header_banners_bp = Blueprint('header_banners', __name__, url_prefix='/api/header-banners')


@header_banners_bp.route('/init-table', methods=['POST'])
def init_table():
    """헤더 배너 테이블 생성 (수동 초기화용)"""
    try:
        from api.database.models import get_db_connection, USE_POSTGRESQL
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            if USE_POSTGRESQL:
                # PostgreSQL 테이블 생성
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS header_banners (
                        id SERIAL PRIMARY KEY,
                        text TEXT NOT NULL,
                        link_type TEXT DEFAULT 'none',
                        board_post_id INTEGER,
                        is_active BOOLEAN DEFAULT TRUE,
                        display_order INTEGER DEFAULT 0,
                        text_color TEXT DEFAULT '#2d3436',
                        bg_color TEXT DEFAULT '#fff9e6',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_header_banners_active_order 
                    ON header_banners(is_active, display_order)
                ''')
            else:
                # SQLite 테이블 생성
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS header_banners (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        text TEXT NOT NULL,
                        link_type TEXT DEFAULT 'none',
                        board_post_id INTEGER,
                        is_active INTEGER DEFAULT 1,
                        display_order INTEGER DEFAULT 0,
                        text_color TEXT DEFAULT '#2d3436',
                        bg_color TEXT DEFAULT '#fff9e6',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_header_banners_active_order 
                    ON header_banners(is_active, display_order)
                ''')
            
            conn.commit()
            return jsonify({
                'success': True,
                'message': 'header_banners 테이블이 생성되었습니다.'
            })
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        print(f'❌ 테이블 생성 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'테이블 생성 중 오류: {str(e)}'
        }), 500


@header_banners_bp.route('/', methods=['GET'])
def get_banners():
    """모든 헤더 배너 조회 (관리자용)"""
    try:
        print('[헤더 배너 조회] GET /api/header-banners/ 요청 수신')
        print(f'[헤더 배너 조회] get_all_header_banners 함수 타입: {type(get_all_header_banners)}')
        
        # 함수가 제대로 import되었는지 확인
        if not callable(get_all_header_banners):
            raise Exception(f"get_all_header_banners가 호출 가능한 함수가 아닙니다: {type(get_all_header_banners)}")
        
        banners = get_all_header_banners()
        print(f'[헤더 배너 조회] 조회 성공: {len(banners)}개')
        return jsonify({
            'success': True,
            'data': banners,
            'count': len(banners)
        })
    except Exception as e:
        print(f'❌ 헤더 배너 조회 오류: {e}')
        import traceback
        error_trace = traceback.format_exc()
        print(f'상세 오류:\n{error_trace}')
        return jsonify({
            'success': False,
            'data': [],
            'count': 0,
            'message': f'헤더 배너 조회 중 오류: {str(e)}',
            'error_trace': error_trace
        }), 500


@header_banners_bp.route('/active', methods=['GET'])
def get_active():
    """활성화된 헤더 배너만 조회 (사용자용)"""
    try:
        print('[헤더 배너 조회] GET /api/header-banners/active 요청 수신')
        banners = get_active_header_banners()
        print(f'[헤더 배너 조회] 활성 배너 조회 성공: {len(banners)}개')
        return jsonify({
            'success': True,
            'data': banners,
            'count': len(banners)
        })
    except Exception as e:
        print(f'❌ 활성 헤더 배너 조회 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'data': [],
            'count': 0,
            'message': f'활성 헤더 배너 조회 중 오류: {str(e)}'
        }), 500


@header_banners_bp.route('/', methods=['POST'])
def create():
    """헤더 배너 생성"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '요청 데이터가 없습니다.'
            }), 400
            
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({
                'success': False,
                'message': '배너 텍스트는 필수입니다.'
            }), 400
        
        # board_post_id가 빈 문자열이면 None으로 변환
        board_post_id = data.get('board_post_id')
        if board_post_id == '' or board_post_id == 'null':
            board_post_id = None
        elif board_post_id:
            try:
                board_post_id = int(board_post_id)
            except (ValueError, TypeError):
                board_post_id = None
        
        banner_data = {
            'text': text,
            'link_type': data.get('link_type', 'none'),
            'board_post_id': board_post_id,
            'is_active': data.get('is_active', True),
            'display_order': int(data.get('display_order', 0)) if data.get('display_order') else 0,
            'text_color': data.get('text_color', '#2d3436'),
            'bg_color': data.get('bg_color', '#fff9e6')
        }
        
        print(f'[헤더 배너 생성] 요청 데이터: {banner_data}')
        print(f'[헤더 배너 생성] create_header_banner 함수 타입: {type(create_header_banner)}')
        
        # 함수가 제대로 import되었는지 확인
        if not callable(create_header_banner):
            raise Exception(f"create_header_banner가 호출 가능한 함수가 아닙니다: {type(create_header_banner)}")
        
        banner_id = create_header_banner(banner_data)
        print(f'[헤더 배너 생성] 함수 호출 결과 ID: {banner_id}')
        
        if banner_id and banner_id > 0:
            return jsonify({
                'success': True,
                'message': '헤더 배너가 생성되었습니다.',
                'id': banner_id
            })
        else:
            return jsonify({
                'success': False,
                'message': '헤더 배너 생성에 실패했습니다. (ID: 0)'
            }), 500
        
    except Exception as e:
        print(f'❌ 헤더 배너 생성 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'헤더 배너 생성 중 오류: {str(e)}'
        }), 500


@header_banners_bp.route('/<int:banner_id>', methods=['GET'])
def get_banner(banner_id):
    """헤더 배너 상세 조회"""
    try:
        banner = get_header_banner_by_id(banner_id)
        if banner:
            return jsonify({
                'success': True,
                'data': banner
            })
        else:
            return jsonify({
                'success': False,
                'data': None,
                'message': '헤더 배너를 찾을 수 없습니다.'
            }), 404
        
    except Exception as e:
        print(f'❌ 헤더 배너 조회 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'data': None,
            'message': f'헤더 배너 조회 중 오류: {str(e)}'
        }), 500


@header_banners_bp.route('/<int:banner_id>', methods=['PUT'])
def update(banner_id):
    """헤더 배너 수정"""
    try:
        data = request.get_json()
        
        success = update_header_banner(banner_id, data)
        if success:
            return jsonify({
                'success': True,
                'message': '헤더 배너가 수정되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': '헤더 배너 수정에 실패했습니다.'
            }), 500
        
    except Exception as e:
        print(f'❌ 헤더 배너 수정 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'헤더 배너 수정 중 오류: {str(e)}'
        }), 500


@header_banners_bp.route('/<int:banner_id>', methods=['DELETE'])
def delete(banner_id):
    """헤더 배너 삭제"""
    try:
        success = delete_header_banner(banner_id)
        if success:
            return jsonify({
                'success': True,
                'message': '헤더 배너가 삭제되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': '헤더 배너 삭제에 실패했습니다.'
            }), 500
        
    except Exception as e:
        print(f'❌ 헤더 배너 삭제 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'헤더 배너 삭제 중 오류: {str(e)}'
        }), 500

