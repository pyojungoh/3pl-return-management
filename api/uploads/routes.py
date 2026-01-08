"""
이미지 업로드 API 라우트
"""
from flask import Blueprint, request, jsonify
# Cloudinary 사용 (권장)
try:
    from api.uploads.cloudinary_upload import upload_images_to_cloudinary
    upload_images_to_drive = upload_images_to_cloudinary  # 호환성을 위한 별칭
    print("[성공] Cloudinary 모듈 사용")
except ImportError:
    # Cloudinary 모듈이 없으면 OAuth 2.0 사용
    try:
        from api.uploads.oauth_drive import upload_images_to_drive
        print("[경고] Cloudinary 모듈을 찾을 수 없습니다. OAuth 2.0 모듈 사용")
    except ImportError:
        # OAuth 2.0 모듈이 없으면 기존 서비스 계정 모듈 사용
        from api.uploads.google_drive import upload_images_to_drive
        print("[경고] Cloudinary 및 OAuth 2.0 모듈을 찾을 수 없습니다. 서비스 계정 모듈 사용 (제한 있음)")

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
        print(f"[정보] 이미지 업로드 API 호출됨")
        print(f"   요청 URL: {request.url}")
        print(f"   요청 메서드: {request.method}")
        print(f"   Content-Type: {request.content_type}")
        
        # JSON 데이터 확인
        if not request.is_json:
            print(f"[오류] JSON이 아닌 요청")
            return jsonify({
                'success': False,
                'message': 'JSON 형식의 데이터가 필요합니다.'
            }), 400
        
        data = request.get_json()
        if not data:
            print(f"[오류] 요청 데이터가 없음")
            return jsonify({
                'success': False,
                'message': '요청 데이터가 없습니다.'
            }), 400
        
        images = data.get('images', [])
        tracking_number = data.get('trackingNumber', '').strip()
        
        print(f"   이미지 개수: {len(images) if images else 0}")
        print(f"   송장번호: '{tracking_number}'")
        
        if not images or len(images) == 0:
            print(f"[오류] 이미지 데이터가 없음")
            return jsonify({
                'success': False,
                'message': '이미지 데이터가 없습니다.'
            }), 400
        
        if not tracking_number:
            print(f"[오류] 송장번호가 없음")
            return jsonify({
                'success': False,
                'message': '송장번호가 없습니다.'
            }), 400
        
        # Cloudinary에 이미지 업로드
        print(f"[정보] Cloudinary 업로드 시작: {len(images)}장")
        try:
            photo_links = upload_images_to_drive(images, tracking_number)
            print(f"[성공] Cloudinary 업로드 완료: {len(photo_links.split(chr(10))) if photo_links else 0}개 링크")
            
            if not photo_links:
                print(f"[경고] 업로드된 링크가 없음")
                return jsonify({
                    'success': False,
                    'message': '이미지 업로드는 완료되었지만 링크를 가져올 수 없습니다.'
                }), 500
            
            return jsonify({
                'success': True,
                'photoLinks': photo_links,
                'message': f'{len(images)}장의 이미지가 업로드되었습니다.'
            })
        except Exception as upload_error:
            print(f"[오류] Cloudinary 업로드 오류: {upload_error}")
            import traceback
            traceback.print_exc()
            
            # 에러 메시지 개선
            error_message = str(upload_error)
            if 'Cloudinary 설정' in error_message or '인증' in error_message:
                error_message = 'Cloudinary 설정 오류: 환경 변수를 확인해주세요.'
            elif 'unauthorized' in error_message.lower() or '401' in error_message:
                error_message = 'Cloudinary 인증 오류: API 키를 확인해주세요.'
            elif '403' in error_message:
                error_message = 'Cloudinary 권한 오류: API 키 권한을 확인해주세요.'
            
            return jsonify({
                'success': False,
                'message': f'이미지 업로드 실패: {error_message}'
            }), 500
        
    except Exception as e:
        print(f'[오류] 이미지 업로드 API 오류: {e}')
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
    print(f"[정보] find_by_tracking 엔드포인트 호출됨!")
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
        print(f"[정보] 송장번호 검색 요청:")
        print(f"   송장번호: {tracking_number}")
        print(f"   요청된 월: '{month}' (길이: {len(month) if month else 0})")
        
        return_data = None
        if month:
            # 지정된 월에서 먼저 검색
            print(f"   [정보] 지정된 월에서 검색 시도: '{month}'")
            return_data = find_return_by_tracking_number(tracking_number, month)
            if return_data:
                found_month = return_data.get('month', '알 수 없음')
                print(f"   [성공] 지정된 월에서 데이터 발견: {found_month}")
            else:
                print(f"   [오류] 지정된 월에서 데이터를 찾지 못함")
        
        # 월이 없거나 지정된 월에서 찾지 못한 경우 모든 월에서 검색
        if not return_data:
            print(f"[정보] 모든 월에서 송장번호 검색: {tracking_number}")
            return_data = find_return_by_tracking_number(tracking_number, None)
            if return_data:
                found_month = return_data.get('month', '알 수 없음')
                print(f"   [성공] 모든 월에서 데이터 발견: {found_month}월")
                print(f"   [경고] 요청된 월 '{month}'와 저장된 월 '{found_month}'가 일치하지 않음!")
            else:
                print(f"   [오류] 모든 월에서도 데이터를 찾지 못함")
        
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
        print(f'[오류] 송장번호 검색 오류: {e}')
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
        print(f'[오류] 사진 링크 업데이트 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'사진 링크 업데이트 중 오류: {str(e)}'
        }), 500


@uploads_bp.route('/certificate-proxy', methods=['GET'])
def proxy_certificate():
    """
    사업자 등록증 PDF 프록시 (CORS 및 401 오류 해결)
    
    Query Parameters:
        url: Cloudinary PDF URL
    
    Returns:
        PDF 파일 스트림
    """
    from flask import Response
    
    try:
        pdf_url = request.args.get('url')
        if not pdf_url:
            error_html = '''
            <!DOCTYPE html>
            <html>
            <head><title>오류</title></head>
            <body style="font-family: Arial; padding: 40px; text-align: center;">
                <h2 style="color: #e74c3c;">❌ PDF를 불러올 수 없습니다</h2>
                <p>URL 파라미터가 필요합니다.</p>
            </body>
            </html>
            '''
            return Response(error_html, mimetype='text/html'), 400
        
        # URL 디코딩
        from urllib.parse import unquote
        pdf_url = unquote(pdf_url)
        
        print(f'[PDF 프록시] 시작 - URL: {pdf_url[:150]}...')
        
        # PDF 파일 다운로드 (urllib 사용 - requests 의존성 없이)
        import urllib.request
        import urllib.error
        import io
        
        try:
            req = urllib.request.Request(pdf_url)
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            req.add_header('Accept', 'application/pdf,application/octet-stream,*/*')
            req.add_header('Accept-Language', 'ko-KR,ko;q=0.9,en;q=0.8')
            
            print(f'[PDF 프록시] Cloudinary에 요청 중...')
            
            # 타임아웃을 더 길게 설정하고 청크 단위로 읽기
            with urllib.request.urlopen(req, timeout=60) as response:
                # Content-Type 확인
                content_type = response.headers.get('Content-Type', '')
                print(f'[PDF 프록시] 응답 받음 - Content-Type: {content_type}, Status: {response.status}')
                
                # 청크 단위로 읽기 (메모리 효율성)
                chunk_size = 8192
                pdf_chunks = []
                total_size = 0
                max_size = 50 * 1024 * 1024  # 50MB 제한
                
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    pdf_chunks.append(chunk)
                    total_size += len(chunk)
                    
                    if total_size > max_size:
                        raise Exception(f'PDF 파일이 너무 큽니다. (최대 {max_size // 1024 // 1024}MB)')
                
                pdf_data = b''.join(pdf_chunks)
                
                print(f'[PDF 프록시] PDF 다운로드 성공: {len(pdf_data)} bytes')
                
                # PDF 파일을 스트림으로 반환
                return Response(
                    pdf_data,
                    mimetype='application/pdf',
                    headers={
                        'Content-Disposition': 'inline; filename="certificate.pdf"',
                        'Access-Control-Allow-Origin': '*',
                        'Cache-Control': 'public, max-age=3600',
                        'Content-Length': str(len(pdf_data)),
                        'Content-Type': 'application/pdf'
                    }
                )
                
        except urllib.error.HTTPError as e:
            error_msg = f'HTTP {e.code}'
            if e.code == 401:
                error_msg += ' (인증 오류 - Cloudinary 접근 권한이 없습니다)'
            elif e.code == 403:
                error_msg += ' (접근 거부)'
            elif e.code == 404:
                error_msg += ' (파일을 찾을 수 없습니다)'
            
            print(f'[PDF 프록시] HTTP 오류: {e.code} - {e.reason}')
            print(f'[PDF 프록시] 오류 URL: {pdf_url[:150]}...')
            
            # 에러 응답 본문 읽기 (있는 경우)
            try:
                error_body = e.read().decode('utf-8', errors='ignore')[:500]
                print(f'[PDF 프록시] 오류 응답 본문: {error_body}')
            except:
                pass
            
            error_html = f'''
            <!DOCTYPE html>
            <html>
            <head><title>오류</title></head>
            <body style="font-family: Arial; padding: 40px; text-align: center;">
                <h2 style="color: #e74c3c;">❌ PDF를 불러올 수 없습니다</h2>
                <p style="font-size: 16px; margin: 20px 0;">{error_msg}</p>
                <p style="color: #95a5a6; font-size: 14px; margin-top: 30px;">아래 버튼을 사용하여 PDF를 확인하세요.</p>
            </body>
            </html>
            '''
            return Response(error_html, mimetype='text/html'), e.code
            
        except urllib.error.URLError as e:
            error_reason = str(e.reason) if e.reason else '알 수 없는 오류'
            print(f'[PDF 프록시] URL 오류: {error_reason}')
            print(f'[PDF 프록시] 오류 URL: {pdf_url[:150]}...')
            
            error_html = f'''
            <!DOCTYPE html>
            <html>
            <head><title>오류</title></head>
            <body style="font-family: Arial; padding: 40px; text-align: center;">
                <h2 style="color: #e74c3c;">❌ PDF를 불러올 수 없습니다</h2>
                <p style="font-size: 16px; margin: 20px 0;">연결 오류: {error_reason}</p>
                <p style="color: #95a5a6; font-size: 14px; margin-top: 30px;">아래 버튼을 사용하여 PDF를 확인하세요.</p>
            </body>
            </html>
            '''
            return Response(error_html, mimetype='text/html'), 500
        
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        print(f'[오류] PDF 프록시 오류 ({error_type}): {error_msg}')
        import traceback
        traceback.print_exc()
        
        error_html = f'''
        <!DOCTYPE html>
        <html>
        <head><title>오류</title></head>
        <body style="font-family: Arial; padding: 40px; text-align: center;">
            <h2 style="color: #e74c3c;">❌ PDF 프록시 중 오류가 발생했습니다</h2>
            <p style="font-size: 16px; margin: 20px 0;">오류 유형: {error_type}</p>
            <p style="color: #95a5a6; font-size: 14px; margin-top: 30px;">아래 버튼을 사용하여 PDF를 확인하세요.</p>
        </body>
        </html>
        '''
        return Response(error_html, mimetype='text/html'), 500


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
        print(f"[오류] 사업자 등록증 업로드 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'사업자 등록증 업로드 중 오류가 발생했습니다: {str(e)}'
        }), 500

