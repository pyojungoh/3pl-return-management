"""
게시판 관리 API 라우트
"""
from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
from api.database.models import (
    create_board_category,
    get_all_board_categories,
    update_board_category,
    delete_board_category,
    create_board,
    get_boards_by_category,
    get_all_boards,
    get_board_by_id,
    update_board,
    delete_board,
    increment_board_view_count,
    create_board_file,
    get_board_files,
    delete_board_file
)
from api.uploads.cloudinary_upload import upload_to_cloudinary

# Blueprint 생성
board_bp = Blueprint('board', __name__, url_prefix='/api/board')


# ========== 카테고리 관련 API ==========

@board_bp.route('/categories', methods=['GET'])
def get_categories():
    """모든 카테고리 조회"""
    try:
        categories = get_all_board_categories()
        return jsonify({
            'success': True,
            'data': categories,
            'count': len(categories)
        })
    except Exception as e:
        print(f'❌ 카테고리 조회 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'data': [],
            'count': 0,
            'message': f'카테고리 조회 중 오류: {str(e)}'
        }), 500


@board_bp.route('/categories', methods=['POST'])
def create_category():
    """카테고리 생성"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        display_order = data.get('display_order', 0)
        
        if not name:
            return jsonify({
                'success': False,
                'message': '카테고리명은 필수입니다.'
            }), 400
        
        category_id = create_board_category(name, display_order)
        if category_id:
            return jsonify({
                'success': True,
                'message': '카테고리가 생성되었습니다.',
                'id': category_id
            })
        else:
            return jsonify({
                'success': False,
                'message': '카테고리 생성에 실패했습니다.'
            }), 500
        
    except Exception as e:
        print(f'❌ 카테고리 생성 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'카테고리 생성 중 오류: {str(e)}'
        }), 500


@board_bp.route('/categories/<int:category_id>', methods=['PUT'])
def update_category(category_id):
    """카테고리 수정"""
    try:
        data = request.get_json()
        name = data.get('name')
        display_order = data.get('display_order')
        
        success = update_board_category(category_id, name, display_order)
        if success:
            return jsonify({
                'success': True,
                'message': '카테고리가 수정되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': '카테고리 수정에 실패했습니다.'
            }), 500
        
    except Exception as e:
        print(f'❌ 카테고리 수정 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'카테고리 수정 중 오류: {str(e)}'
        }), 500


@board_bp.route('/categories/<int:category_id>', methods=['DELETE'])
def delete_category(category_id):
    """카테고리 삭제"""
    try:
        success = delete_board_category(category_id)
        if success:
            return jsonify({
                'success': True,
                'message': '카테고리가 삭제되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': '카테고리 삭제에 실패했습니다.'
            }), 500
        
    except Exception as e:
        print(f'❌ 카테고리 삭제 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'카테고리 삭제 중 오류: {str(e)}'
        }), 500


# ========== 게시글 관련 API ==========

@board_bp.route('/posts', methods=['GET'])
def get_posts():
    """게시글 목록 조회"""
    try:
        category_id = request.args.get('category_id', type=int)
        
        if category_id:
            posts = get_boards_by_category(category_id)
        else:
            posts = get_all_boards()
        
        # 디버깅: 첫 번째 게시글의 키 확인
        if posts and len(posts) > 0:
            first_post = posts[0]
            print(f"🔍 API 응답 - 첫 번째 게시글 키: {list(first_post.keys()) if isinstance(first_post, dict) else 'not dict'}")
            print(f"🔍 API 응답 - 첫 번째 게시글 id: {first_post.get('id') if isinstance(first_post, dict) else 'N/A'}")
        
        return jsonify({
            'success': True,
            'data': posts,
            'count': len(posts)
        })
    except Exception as e:
        print(f'❌ 게시글 조회 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'data': [],
            'count': 0,
            'message': f'게시글 조회 중 오류: {str(e)}'
        }), 500


@board_bp.route('/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    """게시글 상세 조회"""
    try:
        post = get_board_by_id(post_id)
        if post:
            # 조회수 증가
            increment_board_view_count(post_id)
            # 첨부파일 조회
            files = get_board_files(post_id)
            post['files'] = files
            return jsonify({
                'success': True,
                'data': post
            })
        else:
            return jsonify({
                'success': False,
                'data': None,
                'message': '게시글을 찾을 수 없습니다.'
            }), 404
        
    except Exception as e:
        print(f'❌ 게시글 조회 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'data': None,
            'message': f'게시글 조회 중 오류: {str(e)}'
        }), 500


@board_bp.route('/posts', methods=['POST'])
def create_post():
    """게시글 생성"""
    try:
        data = request.get_json()
        
        if not data.get('category_id') or not data.get('title') or not data.get('content'):
            return jsonify({
                'success': False,
                'message': '카테고리, 제목, 내용은 필수입니다.'
            }), 400
        
        board_id = create_board(data)
        print(f"🔍 create_board 반환값: {board_id}, 타입: {type(board_id)}")
        if board_id:
            # 첨부파일이 있으면 저장
            files = data.get('files', [])
            for file_data in files:
                create_board_file({
                    'board_id': board_id,
                    'file_name': file_data.get('file_name'),
                    'file_url': file_data.get('file_url'),
                    'file_size': file_data.get('file_size')
                })
            
            # 생성된 게시글 확인
            from api.database.models import get_board_by_id
            created_post = get_board_by_id(board_id)
            print(f"🔍 생성된 게시글 확인 - ID: {board_id}, 실제 데이터: {created_post.get('id') if created_post else 'None'}")
            
            return jsonify({
                'success': True,
                'message': '게시글이 등록되었습니다.',
                'id': board_id
            })
        else:
            return jsonify({
                'success': False,
                'message': '게시글 등록에 실패했습니다.'
            }), 500
        
    except Exception as e:
        print(f'❌ 게시글 생성 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'게시글 생성 중 오류: {str(e)}'
        }), 500


@board_bp.route('/posts/<int:post_id>', methods=['PUT'])
def update_post(post_id):
    """게시글 수정"""
    try:
        data = request.get_json()
        
        success = update_board(post_id, data)
        if success:
            # 첨부파일 업데이트 (기존 파일 삭제 후 새로 추가)
            if 'files' in data:
                # 기존 파일 삭제
                existing_files = get_board_files(post_id)
                for file in existing_files:
                    delete_board_file(file['id'])
                
                # 새 파일 추가
                for file_data in data.get('files', []):
                    create_board_file({
                        'board_id': post_id,
                        'file_name': file_data.get('file_name'),
                        'file_url': file_data.get('file_url'),
                        'file_size': file_data.get('file_size')
                    })
            
            return jsonify({
                'success': True,
                'message': '게시글이 수정되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': '게시글 수정에 실패했습니다.'
            }), 500
        
    except Exception as e:
        print(f'❌ 게시글 수정 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'게시글 수정 중 오류: {str(e)}'
        }), 500


@board_bp.route('/posts/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    """게시글 삭제"""
    try:
        success = delete_board(post_id)
        if success:
            return jsonify({
                'success': True,
                'message': '게시글이 삭제되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': '게시글 삭제에 실패했습니다.'
            }), 500
        
    except Exception as e:
        print(f'❌ 게시글 삭제 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'게시글 삭제 중 오류: {str(e)}'
        }), 500


# ========== 파일 업로드 API ==========

@board_bp.route('/upload', methods=['POST'])
def upload_file():
    """게시글 첨부파일 업로드"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': '파일이 없습니다.'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': '파일명이 없습니다.'
            }), 400
        
        # Cloudinary에 업로드
        upload_result = upload_to_cloudinary(file, folder='board_files')
        
        if upload_result and upload_result.get('secure_url'):
            return jsonify({
                'success': True,
                'data': {
                    'file_name': file.filename,
                    'file_url': upload_result['secure_url'],
                    'file_size': upload_result.get('bytes', 0)
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': '파일 업로드에 실패했습니다.'
            }), 500
        
    except Exception as e:
        print(f'❌ 파일 업로드 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'파일 업로드 중 오류: {str(e)}'
        }), 500

