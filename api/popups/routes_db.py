"""
팝업 관리 API 라우트
"""
from flask import Blueprint, request, jsonify
from api.database.models import (
    create_popup,
    get_all_popups,
    get_active_popup,
    get_popup_by_id,
    update_popup,
    delete_popup
)

# Blueprint 생성
popups_bp = Blueprint('popups', __name__, url_prefix='/api/popups')


@popups_bp.route('/', methods=['GET'])
def get_popups():
    """모든 팝업 조회 (관리자용)"""
    try:
        popups = get_all_popups()
        return jsonify({
            'success': True,
            'data': popups,
            'count': len(popups)
        })
    except Exception as e:
        print(f'❌ 팝업 조회 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'data': [],
            'count': 0,
            'message': f'팝업 조회 중 오류: {str(e)}'
        }), 500


@popups_bp.route('/active', methods=['GET'])
def get_active():
    """현재 활성화된 팝업 조회 (사용자용)"""
    try:
        popup = get_active_popup()
        return jsonify({
            'success': True,
            'data': popup
        })
    except Exception as e:
        print(f'❌ 활성 팝업 조회 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'data': None,
            'message': f'활성 팝업 조회 중 오류: {str(e)}'
        }), 500


@popups_bp.route('/', methods=['POST'])
def create():
    """팝업 생성"""
    try:
        data = request.get_json()
        title = data.get('title', '').strip()
        content = data.get('content', '').strip()
        start_date = data.get('start_date', '').strip()
        end_date = data.get('end_date', '').strip()
        image_url = data.get('image_url', '').strip()
        width = data.get('width', 600)
        height = data.get('height', 400)
        is_active = data.get('is_active', True)
        
        if not title or not content or not start_date or not end_date:
            return jsonify({
                'success': False,
                'message': '제목, 내용, 시작일, 종료일은 필수입니다.'
            }), 400
        
        popup_id = create_popup({
            'title': title,
            'content': content,
            'image_url': image_url if image_url else None,
            'width': int(width) if width else 600,
            'height': int(height) if height else 400,
            'start_date': start_date,
            'end_date': end_date,
            'is_active': is_active
        })
        
        if popup_id:
            return jsonify({
                'success': True,
                'message': '팝업이 생성되었습니다.',
                'id': popup_id
            })
        else:
            return jsonify({
                'success': False,
                'message': '팝업 생성에 실패했습니다.'
            }), 500
        
    except Exception as e:
        print(f'❌ 팝업 생성 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'팝업 생성 중 오류: {str(e)}'
        }), 500


@popups_bp.route('/<int:popup_id>', methods=['GET'])
def get_popup(popup_id):
    """팝업 상세 조회"""
    try:
        popup = get_popup_by_id(popup_id)
        if popup:
            return jsonify({
                'success': True,
                'data': popup
            })
        else:
            return jsonify({
                'success': False,
                'data': None,
                'message': '팝업을 찾을 수 없습니다.'
            }), 404
        
    except Exception as e:
        print(f'❌ 팝업 조회 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'data': None,
            'message': f'팝업 조회 중 오류: {str(e)}'
        }), 500


@popups_bp.route('/<int:popup_id>', methods=['PUT'])
def update(popup_id):
    """팝업 수정"""
    try:
        data = request.get_json()
        
        success = update_popup(popup_id, data)
        if success:
            return jsonify({
                'success': True,
                'message': '팝업이 수정되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': '팝업 수정에 실패했습니다.'
            }), 500
        
    except Exception as e:
        print(f'❌ 팝업 수정 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'팝업 수정 중 오류: {str(e)}'
        }), 500


@popups_bp.route('/<int:popup_id>', methods=['DELETE'])
def delete(popup_id):
    """팝업 삭제"""
    try:
        success = delete_popup(popup_id)
        if success:
            return jsonify({
                'success': True,
                'message': '팝업이 삭제되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': '팝업 삭제에 실패했습니다.'
            }), 500
        
    except Exception as e:
        print(f'❌ 팝업 삭제 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'팝업 삭제 중 오류: {str(e)}'
        }), 500

