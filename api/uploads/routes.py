"""
이미지 업로드 API 라우트
"""
from flask import Blueprint, request, jsonify
# Cloudinary 사용 (권장)
try:
    from api.uploads.cloudinary_upload import upload_images_to_cloudinary
    upload_images_to_drive = upload_images_to_cloudinary  # 호환성을 위한 별칭
    print("✅ Cloudinary 모듈 사용")
except ImportError:
    # Cloudinary 모듈이 없으면 OAuth 2.0 사용
    try:
        from api.uploads.oauth_drive import upload_images_to_drive
        print("⚠️ Cloudinary 모듈을 찾을 수 없습니다. OAuth 2.0 모듈 사용")
    except ImportError:
        # OAuth 2.0 모듈이 없으면 기존 서비스 계정 모듈 사용
        from api.uploads.google_drive import upload_images_to_drive
        print("⚠️ Cloudinary 및 OAuth 2.0 모듈을 찾을 수 없습니다. 서비스 계정 모듈 사용 (제한 있음)")

from api.database.models import (
    find_return_by_tracking_number,
    update_photo_links,
    get_available_months
)
from datetime import datetime
import base64

# Blueprint 생성
uploads_bp = Blueprint('uploads', __name__, url_prefix='/api/uploads')


@uploads_bp.route('/upload-images', methods=['POST'])
def upload_images():
    """
    이미지 업로드 API (Cloudinary)
    
    Request Body:
        {
            "images": List[str],      # Base64 인코딩된 이미지 데이터 리스트
            "trackingNumber": str      # 송장번호
        }
    
    Returns:
        {
            "success": bool,
            "photoLinks": str,         # "사진1: url\n사진2: url" 형식
            "message": str
        }
    """
    try:
        data = request.get_json()
        images = data.get('images', [])
        tracking_number = data.get('trackingNumber', '').strip()
        
        if not images or len(images) == 0:
            return jsonify({
                'success': False,
                'message': '이미지 데이터가 없습니다.'
            }), 400
        
        if not tracking_number:
            return jsonify({
                'success': False,
                'message': '송장번호가 없습니다.'
            }), 400
        
        # Cloudinary에 이미지 업로드
        photo_links = upload_images_to_drive(images, tracking_number)
        
        return jsonify({
            'success': True,
            'photoLinks': photo_links,
            'message': f'{len(images)}장의 이미지가 업로드되었습니다.'
        })
        
    except Exception as e:
        print(f'❌ 이미지 업로드 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'이미지 업로드 실패: {str(e)}'
        }), 500


@uploads_bp.route('/find-by-tracking', methods=['GET'])
@uploads_bp.route('/find-by-tracking/', methods=['GET'])  # trailing slash 지원
def find_by_tracking():
    """
    송장번호로 반품 데이터 찾기 (QR 코드 검색용)
    
    Query Parameters:
        - trackingNumber: 송장번호
        - month: 월 (예: "2025년11월")
    
    Returns:
        {
            "success": bool,
            "data": {
                "company": str,
                "product": str,
                "customer": str,
                "trackingNumber": str,
                "returnType": str,
                "stockStatus": str
            } or null,
            "message": str
        }
    """
    print(f"🔍 find_by_tracking 엔드포인트 호출됨!")
    print(f"   요청 URL: {request.url}")
    print(f"   요청 메서드: {request.method}")
    print(f"   쿼리 파라미터: {request.args}")
    try:
        tracking_number = request.args.get('trackingNumber', '').strip()
        month = request.args.get('month', '').strip()
        
        if not tracking_number:
            return jsonify({
                'success': False,
                'message': '송장번호가 없습니다.'
            }), 400
        
        # 데이터베이스에서 검색
        # month가 있으면 해당 월에서만 검색, 없으면 모든 월에서 검색
        print(f"🔍 송장번호 검색 요청:")
        print(f"   송장번호: {tracking_number}")
        print(f"   요청된 월: '{month}' (길이: {len(month) if month else 0})")
        
        return_data = None
        if month:
            # 지정된 월에서 먼저 검색
            print(f"   📅 지정된 월에서 검색 시도: '{month}'")
            return_data = find_return_by_tracking_number(tracking_number, month)
            if return_data:
                found_month = return_data.get('month', '알 수 없음')
                print(f"   ✅ 지정된 월에서 데이터 발견: {found_month}")
            else:
                print(f"   ❌ 지정된 월에서 데이터를 찾지 못함")
        
        # 월이 없거나 지정된 월에서 찾지 못한 경우 모든 월에서 검색
        if not return_data:
            print(f"🔍 모든 월에서 송장번호 검색: {tracking_number}")
            return_data = find_return_by_tracking_number(tracking_number, None)
            if return_data:
                found_month = return_data.get('month', '알 수 없음')
                print(f"   ✅ 모든 월에서 데이터 발견: {found_month}월")
                print(f"   ⚠️ 요청된 월 '{month}'와 저장된 월 '{found_month}'가 일치하지 않음!")
            else:
                print(f"   ❌ 모든 월에서도 데이터를 찾지 못함")
        
        if return_data:
            return jsonify({
                'success': True,
                'data': {
                    'company': return_data.get('company_name', ''),
                    'product': return_data.get('product', ''),
                    'customer': return_data.get('customer_name', ''),
                    'trackingNumber': return_data.get('tracking_number', ''),
                    'returnType': return_data.get('return_type', ''),
                    'stockStatus': return_data.get('stock_status', '')
                },
                'message': '데이터를 찾았습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'data': None,
                'message': '해당 송장번호의 데이터를 찾을 수 없습니다.'
            }), 404
        
    except Exception as e:
        print(f'❌ 송장번호 검색 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'data': None,
            'message': f'검색 중 오류: {str(e)}'
        }), 500


@uploads_bp.route('/update-photo-links', methods=['POST'])
def update_photo_links_route():
    """
    사진 링크 업데이트 API
    
    Request Body:
        {
            "returnId": int,           # 반품 ID
            "photoLinks": str          # "사진1: url\n사진2: url" 형식
        }
    
    Returns:
        {
            "success": bool,
            "message": str
        }
    """
    try:
        data = request.get_json()
        return_id = data.get('returnId')
        photo_links = data.get('photoLinks', '').strip()
        
        if not return_id:
            return jsonify({
                'success': False,
                'message': '반품 ID가 없습니다.'
            }), 400
        
        # 데이터베이스에 사진 링크 업데이트
        if update_photo_links(return_id, photo_links):
            return jsonify({
                'success': True,
                'message': '사진 링크가 업데이트되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': '사진 링크 업데이트에 실패했습니다.'
            }), 500
        
    except Exception as e:
        print(f'❌ 사진 링크 업데이트 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'사진 링크 업데이트 중 오류: {str(e)}'
        }), 500


@uploads_bp.route('/certificate', methods=['POST'])
def upload_certificate():
    """
    사업자 등록증 업로드 API (Cloudinary)
    
    Request Body:
        FormData with 'file' field
    
    Returns:
        {
            "success": bool,
            "url": str,
            "message": str
        }
    """
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': '파일이 제공되지 않았습니다.'
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': '파일이 선택되지 않았습니다.'
            }), 400
        
        # 파일을 읽어서 Base64로 변환
        file_data = file.read()
        base64_data = base64.b64encode(file_data).decode('utf-8')
        
        # Cloudinary에 업로드
        try:
            from api.uploads.cloudinary_upload import upload_single_file_to_cloudinary
            url = upload_single_file_to_cloudinary(base64_data, file.filename, 'business_certificates')
            
            if url:
                return jsonify({
                    'success': True,
                    'url': url,
                    'message': '사업자 등록증이 업로드되었습니다.'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '사업자 등록증 업로드에 실패했습니다.'
                }), 500
                
        except ImportError:
            # Cloudinary 모듈이 없으면 직접 업로드
            import cloudinary
            import cloudinary.uploader
            
            # 파일을 Cloudinary에 업로드
            result = cloudinary.uploader.upload(
                file_data,
                folder='business_certificates',
                resource_type='auto'
            )
            
            return jsonify({
                'success': True,
                'url': result.get('secure_url', result.get('url', '')),
                'message': '사업자 등록증이 업로드되었습니다.'
            })
        
    except Exception as e:
        print(f"❌ 사업자 등록증 업로드 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'사업자 등록증 업로드 중 오류가 발생했습니다: {str(e)}'
        }), 500

