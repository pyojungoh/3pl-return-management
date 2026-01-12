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
        from urllib.parse import unquote, urlparse
        pdf_url = unquote(pdf_url)
        
        print(f'[PDF 프록시] 시작 - URL: {pdf_url[:150]}...')
        
        # Cloudinary SDK를 사용하여 PDF 가져오기 시도
        try:
            import cloudinary
            import cloudinary.api
            from api.uploads.cloudinary_upload import CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET
            
            # Cloudinary URL에서 public_id 추출
            parsed_url = urlparse(pdf_url)
            path_parts = parsed_url.path.split('/')
            
            # upload 이후의 경로 찾기
            upload_index = -1
            for i, part in enumerate(path_parts):
                if part == 'upload':
                    upload_index = i
                    break
            
            if upload_index != -1:
                # public_id 추출 (upload 다음부터 마지막까지, 버전 제외)
                public_id_parts = []
                for part in path_parts[upload_index + 1:]:
                    if part.startswith('v') and len(part) > 1 and part[1:].isdigit():
                        continue  # 버전 스킵
                    if part:
                        public_id_parts.append(part)
                
                if public_id_parts:
                    public_id = '/'.join(public_id_parts)
                    # 확장자 제거 (Cloudinary가 자동으로 추가)
                    if public_id.endswith('.pdf'):
                        public_id = public_id[:-4]
                    
                    print(f'[PDF 프록시] 추출된 public_id: {public_id}')
                    
                    # Cloudinary API를 사용하여 리소스 정보 가져오기
                    try:
                        resource = cloudinary.api.resource(
                            public_id,
                            resource_type='raw',  # PDF는 raw 타입
                            type='upload'
                        )
                        
                        # secure_url 가져오기
                        secure_url = resource.get('secure_url', pdf_url)
                        print(f'[PDF 프록시] Cloudinary secure_url 사용: {secure_url[:150]}...')
                        pdf_url = secure_url
                    except Exception as api_error:
                        print(f'[PDF 프록시] Cloudinary API 오류 (직접 URL 사용): {api_error}')
        except Exception as sdk_error:
            print(f'[PDF 프록시] Cloudinary SDK 오류 (직접 URL 사용): {sdk_error}')
        
        # PDF 파일 다운로드 (urllib 사용)
        import urllib.request
        import urllib.error
        
        try:
            req = urllib.request.Request(pdf_url)
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            req.add_header('Accept', 'application/pdf,application/octet-stream,*/*')
            req.add_header('Accept-Language', 'ko-KR,ko;q=0.9,en;q=0.8')
            
            print(f'[PDF 프록시] PDF 다운로드 요청 중...')
            
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


@uploads_bp.route('/test/upload-excel', methods=['POST'])
def test_upload_excel():
    """
    엑셀 파일 업로드 테스트 API (구글 드라이브)
    
    Request Body:
        FormData with 'file' field (엑셀 파일)
    
    Returns:
        {
            "success": bool,
            "file_id": str,
            "file_url": str,
            "web_view_link": str,
            "message": str
        }
    """
    try:
        print(f"[정보] 엑셀 파일 업로드 테스트 API 호출됨")
        
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
        
        # 파일명 확인
        filename = file.filename
        if not filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({
                'success': False,
                'message': '엑셀 파일만 업로드 가능합니다. (.xlsx, .xls)'
            }), 400
        
        print(f"   파일명: {filename}")
        
        # 파일 데이터 읽기
        file_data = file.read()
        file_size = len(file_data)
        print(f"   파일 크기: {file_size} bytes ({file_size / 1024 / 1024:.2f} MB)")
        
        # 구글 드라이브에 업로드
        try:
            # OAuth 2.0 사용 (서비스 계정 제한 우회)
            from api.uploads.oauth_drive import upload_excel_to_drive
            
            result = upload_excel_to_drive(
                file_data=file_data,
                filename=filename,
                folder_name='정산파일'  # 테스트용 폴더명
            )
            
            if result.get('success'):
                return jsonify({
                    'success': True,
                    'file_id': result.get('file_id'),
                    'file_url': result.get('file_url'),
                    'web_view_link': result.get('web_view_link'),
                    'message': result.get('message', '파일 업로드 성공')
                })
            else:
                return jsonify({
                    'success': False,
                    'message': result.get('message', '파일 업로드 실패')
                }), 500
                
        except ImportError as import_error:
            print(f"[오류] 구글 드라이브 모듈 import 실패: {import_error}")
            return jsonify({
                'success': False,
                'message': f'구글 드라이브 모듈을 찾을 수 없습니다: {str(import_error)}'
            }), 500
        except Exception as upload_error:
            print(f"[오류] 구글 드라이브 업로드 오류: {upload_error}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'파일 업로드 중 오류가 발생했습니다: {str(upload_error)}'
            }), 500
        
    except Exception as e:
        print(f'[오류] 엑셀 파일 업로드 테스트 API 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'엑셀 파일 업로드 테스트 중 오류: {str(e)}'
        }), 500


@uploads_bp.route('/test/check-auth', methods=['GET'])
def test_check_auth():
    """
    구글 드라이브 인증 정보 확인 테스트 API
    
    Returns:
        {
            "success": bool,
            "has_env_var": bool,
            "env_var_length": int,
            "has_credentials": bool,
            "service_account_email": str,
            "json_parse_error": str,
            "error_details": str,
            "message": str
        }
    """
    try:
        import os
        import json
        
        # 환경 변수 확인
        creds_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
        has_env_var = bool(creds_json)
        env_var_length = len(creds_json) if creds_json else 0
        
        # 인증 정보 확인
        has_credentials = False
        service_account_email = None
        json_parse_error = None
        error_details = None
        
        # 환경 변수 길이 확인 (일반적으로 2000자 이상)
        if has_env_var and env_var_length < 1000:
            error_details = f"⚠️ 환경 변수 길이가 너무 짧습니다 ({env_var_length}자). 일반적으로 서비스 계정 JSON은 2000자 이상입니다. 환경 변수가 잘못 설정되었을 수 있습니다."
        
        try:
            from api.uploads.google_drive import get_credentials
            credentials = get_credentials()
            if credentials:
                has_credentials = True
                # 서비스 계정 이메일 추출 시도
                try:
                    if creds_json:
                        creds_info = json.loads(creds_json.strip())
                        service_account_email = creds_info.get('client_email', '알 수 없음')
                except json.JSONDecodeError as json_err:
                    json_parse_error = f"JSON 파싱 오류: {json_err.msg} (라인 {json_err.lineno}, 컬럼 {json_err.colno})"
                    error_details = f"JSON 파싱 실패. 환경 변수 형식이 올바른지 확인하세요.\n오류 위치: {json_parse_error}\n처음 200자: {creds_json[:200] if creds_json else '없음'}"
                except Exception as parse_err:
                    json_parse_error = str(parse_err)
                    error_details = f"JSON 파싱 중 오류: {json_parse_error}"
        except Exception as cred_error:
            print(f"[오류] 인증 정보 확인 실패: {cred_error}")
            import traceback
            error_details = f"인증 정보 로드 실패: {str(cred_error)}\n{traceback.format_exc()}"
        
        # JSON 파싱 직접 시도 (디버깅용)
        if has_env_var and not has_credentials and not json_parse_error:
            try:
                creds_json_cleaned = creds_json.strip()
                test_parse = json.loads(creds_json_cleaned)
                # 파싱은 성공했지만 인증 객체 생성 실패
                if 'client_email' in test_parse:
                    service_account_email = test_parse.get('client_email')
                    error_details = "JSON 파싱은 성공했지만 인증 객체 생성에 실패했습니다. 필수 필드가 누락되었을 수 있습니다."
            except json.JSONDecodeError as json_err:
                json_parse_error = f"JSON 파싱 오류: {json_err.msg} (라인 {json_err.lineno}, 컬럼 {json_err.colno})"
                error_details = f"JSON 파싱 실패.\n오류: {json_parse_error}\n처음 300자: {creds_json[:300] if creds_json else '없음'}\n마지막 100자: {creds_json[-100:] if creds_json and len(creds_json) > 100 else '없음'}"
            except Exception as parse_err:
                json_parse_error = str(parse_err)
                error_details = f"JSON 파싱 중 오류: {json_parse_error}"
        
        return jsonify({
            'success': True,
            'has_env_var': has_env_var,
            'env_var_length': env_var_length,
            'has_credentials': has_credentials,
            'service_account_email': service_account_email,
            'json_parse_error': json_parse_error,
            'error_details': error_details,
            'message': '인증 정보 확인 완료'
        })
        
    except Exception as e:
        print(f'[오류] 인증 확인 테스트 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'has_env_var': False,
            'env_var_length': 0,
            'has_credentials': False,
            'service_account_email': None,
            'json_parse_error': None,
            'error_details': str(e),
            'message': f'인증 확인 중 오류: {str(e)}'
        }), 500


@uploads_bp.route('/test/upload-excel-start', methods=['POST'])
def test_upload_excel_start():
    """
    엑셀 파일 청크 업로드 시작 API
    
    Request Body:
        {
            "filename": str,
            "file_size": int,
            "total_chunks": int
        }
    
    Returns:
        {
            "success": bool,
            "upload_id": str,
            "message": str
        }
    """
    try:
        data = request.get_json()
        filename = data.get('filename')
        file_size = data.get('file_size')
        total_chunks = data.get('total_chunks')
        
        if not filename or not file_size or not total_chunks:
            return jsonify({
                'success': False,
                'message': '필수 파라미터가 없습니다.'
            }), 400
        
        # 구글 드라이브 인증 확인 (사전 체크)
        try:
            from api.uploads.google_drive import get_credentials
            credentials = get_credentials()
            if not credentials:
                return jsonify({
                    'success': False,
                    'message': 'Google Drive API 인증 정보를 찾을 수 없습니다.\n\n환경 변수 GOOGLE_SERVICE_ACCOUNT_JSON을 확인하거나 service_account.json 파일이 있는지 확인해주세요.'
                }), 500
        except Exception as auth_error:
            print(f"[오류] 구글 드라이브 인증 확인 실패: {auth_error}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'Google Drive API 인증 확인 실패: {str(auth_error)}\n\n환경 변수 GOOGLE_SERVICE_ACCOUNT_JSON을 확인하거나 service_account.json 파일이 있는지 확인해주세요.'
            }), 500
        
        # 업로드 세션 생성 (간단한 메모리 저장, 실제로는 DB나 Redis 사용 권장)
        import uuid
        upload_id = str(uuid.uuid4())
        
        # 세션 저장 (임시로 전역 변수 사용, 실제로는 DB나 Redis 사용)
        if not hasattr(test_upload_excel_start, 'upload_sessions'):
            test_upload_excel_start.upload_sessions = {}
        
        test_upload_excel_start.upload_sessions[upload_id] = {
            'filename': filename,
            'file_size': file_size,
            'total_chunks': total_chunks,
            'chunks': {},
            'created_at': datetime.now()
        }
        
        print(f"[정보] 업로드 세션 시작: {upload_id}, 파일: {filename}, 크기: {file_size} bytes, 청크: {total_chunks}")
        
        return jsonify({
            'success': True,
            'upload_id': upload_id,
            'message': '업로드 세션이 생성되었습니다.'
        })
        
    except Exception as e:
        print(f'[오류] 업로드 시작 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'업로드 시작 중 오류: {str(e)}'
        }), 500


@uploads_bp.route('/test/upload-excel-chunk', methods=['POST'])
def test_upload_excel_chunk():
    """
    엑셀 파일 청크 업로드 API
    
    Request Body:
        {
            "upload_id": str,
            "chunk_index": int,
            "chunk_data": str (base64),
            "is_last_chunk": bool
        }
    
    Returns:
        {
            "success": bool,
            "message": str
        }
    """
    try:
        data = request.get_json()
        upload_id = data.get('upload_id')
        chunk_index = data.get('chunk_index')
        chunk_data = data.get('chunk_data')
        is_last_chunk = data.get('is_last_chunk', False)
        
        if not upload_id or chunk_index is None or not chunk_data:
            return jsonify({
                'success': False,
                'message': '필수 파라미터가 없습니다.'
            }), 400
        
        # 세션 확인
        if not hasattr(test_upload_excel_start, 'upload_sessions'):
            return jsonify({
                'success': False,
                'message': '업로드 세션을 찾을 수 없습니다.'
            }), 404
        
        session = test_upload_excel_start.upload_sessions.get(upload_id)
        if not session:
            return jsonify({
                'success': False,
                'message': '업로드 세션이 만료되었거나 존재하지 않습니다.'
            }), 404
        
        # 청크 저장
        session['chunks'][chunk_index] = chunk_data
        
        print(f"[정보] 청크 수신: {upload_id}, 청크 {chunk_index + 1}/{session['total_chunks']}")
        
        return jsonify({
            'success': True,
            'message': f'청크 {chunk_index + 1} 수신 완료'
        })
        
    except Exception as e:
        print(f'[오류] 청크 업로드 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'청크 업로드 중 오류: {str(e)}'
        }), 500


@uploads_bp.route('/test/upload-excel-complete', methods=['POST'])
def test_upload_excel_complete():
    """
    엑셀 파일 청크 업로드 완료 API
    
    Request Body:
        {
            "upload_id": str
        }
    
    Returns:
        {
            "success": bool,
            "file_id": str,
            "file_url": str,
            "web_view_link": str,
            "message": str
        }
    """
    try:
        data = request.get_json()
        upload_id = data.get('upload_id')
        
        if not upload_id:
            return jsonify({
                'success': False,
                'message': '업로드 ID가 없습니다.'
            }), 400
        
        # 세션 확인
        if not hasattr(test_upload_excel_start, 'upload_sessions'):
            return jsonify({
                'success': False,
                'message': '업로드 세션을 찾을 수 없습니다.'
            }), 404
        
        session = test_upload_excel_start.upload_sessions.get(upload_id)
        if not session:
            return jsonify({
                'success': False,
                'message': '업로드 세션이 만료되었거나 존재하지 않습니다.'
            }), 404
        
        # 모든 청크 확인
        total_chunks = session['total_chunks']
        chunks = session['chunks']
        
        if len(chunks) != total_chunks:
            return jsonify({
                'success': False,
                'message': f'모든 청크를 받지 못했습니다. ({len(chunks)}/{total_chunks})'
            }), 400
        
        # 청크 조립
        print(f"[정보] 청크 조립 시작: {upload_id}, 총 {total_chunks}개 청크")
        chunks_list = [chunks[i] for i in range(total_chunks)]
        base64_data = ''.join(chunks_list)
        
        # Base64 디코딩
        import base64
        file_data = base64.b64decode(base64_data)
        
        print(f"[정보] 파일 조립 완료: {len(file_data)} bytes")
        
        # 구글 드라이브에 업로드
        try:
            print(f"[디버깅] 엑셀 파일 업로드 시작: {session['filename']}")
            print(f"[디버깅] OAuth 2.0 모듈 import 시도...")
            
            # OAuth 2.0 사용 (서비스 계정 제한 우회)
            from api.uploads.oauth_drive import upload_excel_to_drive
            
            print(f"[디버깅] OAuth 2.0 모듈 import 성공")
            print(f"[디버깅] upload_excel_to_drive 함수 호출 시작...")
            
            result = upload_excel_to_drive(
                file_data=file_data,
                filename=session['filename'],
                folder_name='정산파일'
            )
            
            print(f"[디버깅] upload_excel_to_drive 함수 호출 완료: {result.get('success')}")
            
            # 세션 삭제
            del test_upload_excel_start.upload_sessions[upload_id]
            
            if result.get('success'):
                return jsonify({
                    'success': True,
                    'file_id': result.get('file_id'),
                    'file_url': result.get('file_url'),
                    'web_view_link': result.get('web_view_link'),
                    'message': result.get('message', '파일 업로드 성공')
                })
            else:
                return jsonify({
                    'success': False,
                    'message': result.get('message', '파일 업로드 실패')
                }), 500
                
        except ImportError as import_error:
            print(f"[오류] 구글 드라이브 모듈 import 실패: {import_error}")
            return jsonify({
                'success': False,
                'message': f'구글 드라이브 모듈을 찾을 수 없습니다: {str(import_error)}'
            }), 500
        except Exception as upload_error:
            print(f"[오류] 구글 드라이브 업로드 오류: {upload_error}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'파일 업로드 중 오류가 발생했습니다: {str(upload_error)}'
            }), 500
        
    except Exception as e:
        print(f'[오류] 업로드 완료 처리 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'업로드 완료 처리 중 오류: {str(e)}'
        }), 500