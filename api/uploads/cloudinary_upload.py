"""
Cloudinary를 사용한 이미지 업로드 기능
"""
import os
import base64
from datetime import datetime
from typing import List
import cloudinary
import cloudinary.uploader
import cloudinary.api

# Cloudinary 설정
# 환경 변수에서 먼저 가져오고, 없으면 직접 설정된 값 사용
CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME', 'dokk81rjh')
CLOUDINARY_API_KEY = os.environ.get('CLOUDINARY_API_KEY', '447577332396678')
CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET', '_fh-dOMoaFvOvCRkFk_AzqjOFA8')

# Cloudinary 초기화
if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
        secure=True  # HTTPS 사용
    )
    print("[성공] Cloudinary 초기화 완료")
    print(f"   Cloud Name: {CLOUDINARY_CLOUD_NAME}")
else:
    print("[경고] Cloudinary 환경 변수가 설정되지 않았습니다.")
    print("   CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET 환경 변수를 설정하세요.")


def upload_images_to_cloudinary(image_data_list: List[str], tracking_number: str) -> str:
    """
    Cloudinary에 이미지 업로드
    
    Args:
        image_data_list: Base64 인코딩된 이미지 데이터 리스트
        tracking_number: 송장번호
    
    Returns:
        줄바꿈으로 구분된 사진 링크 문자열 (예: "사진1: url\n사진2: url")
    """
    try:
        if not image_data_list or len(image_data_list) == 0:
            print("[경고] 이미지 데이터가 없습니다.")
            return ''
        
        if not tracking_number:
            print("[경고] 송장번호가 없습니다.")
            return ''
        
        # Cloudinary 설정 확인
        if not CLOUDINARY_CLOUD_NAME or not CLOUDINARY_API_KEY or not CLOUDINARY_API_SECRET:
            raise Exception(
                "Cloudinary 설정이 완료되지 않았습니다.\n\n"
                "환경 변수를 설정하세요:\n"
                "- CLOUDINARY_CLOUD_NAME\n"
                "- CLOUDINARY_API_KEY\n"
                "- CLOUDINARY_API_SECRET\n\n"
                "또는 .env 파일에 추가하세요:\n"
                "CLOUDINARY_CLOUD_NAME=your_cloud_name\n"
                "CLOUDINARY_API_KEY=your_api_key\n"
                "CLOUDINARY_API_SECRET=your_api_secret"
            )
        
        print(f"[정보] Cloudinary 이미지 업로드 시작: {len(image_data_list)}개")
        
        # 타임스탬프 생성
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        photo_texts = []
        
        print("[정보] 개별 이미지 업로드 시작...")
        
        # 모든 이미지 업로드
        for i, image_data in enumerate(image_data_list, 1):
            try:
                if not image_data or not isinstance(image_data, str):
                    print(f"[경고] 이미지 {i} 데이터가 유효하지 않습니다.")
                    continue
                
                print(f"[정보] 이미지 {i} 업로드 중...")
                
                # Base64 데이터 디코딩
                if ',' in image_data:
                    # data:image/jpeg;base64,xxxxx 형식에서 실제 데이터만 추출
                    base64_data = image_data.split(',')[1]
                    # MIME 타입 추출 (선택사항)
                    mime_type = image_data.split(',')[0].split(':')[1].split(';')[0]
                else:
                    base64_data = image_data
                    mime_type = 'image/jpeg'  # 기본값
                
                # Base64 디코딩
                image_bytes = base64.b64decode(base64_data)
                
                # 파일명 생성 (폴더 구조: 반품내역/년월/송장번호_타임스탬프_번호)
                today = datetime.now()
                year_month = today.strftime('%Y년%m월')
                filename = f"{tracking_number}_{timestamp}_{i}"
                folder_path = f"반품내역/{year_month}"
                
                # Cloudinary 업로드
                # public_id: 폴더/파일명 형식
                # resource_type: 'image' (기본값)
                # format: 원본 형식 유지 또는 'jpg'로 변환
                upload_result = cloudinary.uploader.upload(
                    image_bytes,
                    public_id=f"{folder_path}/{filename}",
                    resource_type='image',
                    format='jpg',  # JPEG로 통일
                    overwrite=False,  # 같은 이름 파일이 있으면 오류 (고유성 보장)
                    use_filename=False,  # public_id 사용
                    unique_filename=True,  # 고유 파일명 생성 (타임스탬프 추가)
                    invalidate=True,  # CDN 캐시 무효화
                )
                
                # 업로드 결과에서 URL 가져오기
                image_url = upload_result.get('secure_url', upload_result.get('url', ''))
                
                if not image_url:
                    print(f"[경고] 이미지 {i} URL을 가져올 수 없습니다.")
                    continue
                
                link_text = f"사진{i}"
                photo_texts.append(f"{link_text}: {image_url}")
                
                print(f"[성공] 이미지 {i} 업로드 완료: {filename}")
                print(f"[정보] URL: {image_url}")
                
            except Exception as error:
                error_msg = str(error)
                error_type = type(error).__name__
                print(f"[오류] 이미지 {i} 업로드 오류 ({error_type}): {error_msg}")
                import traceback
                traceback.print_exc()
                
                # 인증 오류나 설정 오류인 경우 즉시 중단
                error_lower = error_msg.lower()
                if ('cloudinary 설정' in error_msg or 
                    '인증 오류' in error_msg or
                    'api key' in error_lower or
                    'unauthorized' in error_lower or
                    '401' in error_msg or
                    '403' in error_msg or
                    'invalid' in error_lower):
                    raise Exception(
                        f"Cloudinary 업로드 오류: {error_msg}\n\n"
                        "Cloudinary 설정을 확인하세요:\n"
                        "- CLOUDINARY_CLOUD_NAME\n"
                        "- CLOUDINARY_API_KEY\n"
                        "- CLOUDINARY_API_SECRET"
                    )
                
                # 개별 이미지 실패해도 계속 진행 (다른 오류인 경우)
                print(f"[경고] 이미지 {i} 업로드 실패했지만 계속 진행합니다.")
                continue
        
        print(f"[성공] 모든 이미지 업로드 완료: {len(photo_texts)}개")
        
        if len(photo_texts) == 0:
            raise Exception("업로드된 이미지가 없습니다.")
        
        # 줄바꿈으로 구분된 텍스트 반환
        return '\n'.join(photo_texts)
        
    except Exception as e:
        print(f"[오류] Cloudinary 이미지 업로드 전체 오류: {e}")
        import traceback
        traceback.print_exc()
        raise Exception(f"이미지 업로드 실패: {str(e)}")


def upload_single_file_to_cloudinary(base64_data: str, filename: str, folder: str = 'business_certificates') -> str:
    """
    Cloudinary에 단일 파일 업로드 (사업자 등록증 등)
    
    Args:
        base64_data: Base64 인코딩된 파일 데이터 (data:xxx;base64,xxx 형식 또는 순수 base64)
        filename: 파일명
        folder: 업로드할 폴더명
    
    Returns:
        업로드된 파일의 URL
    """
    try:
        # Base64 데이터에서 실제 데이터 부분만 추출
        if ',' in base64_data:
            base64_data = base64_data.split(',')[1]
        
        # Base64 디코딩
        file_data = base64.b64decode(base64_data)
        
        # 파일 확장자 추출
        file_extension = filename.split('.')[-1] if '.' in filename else 'pdf'
        
        # 타임스탬프 생성
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 파일명에서 확장자 제거하고 타임스탬프 추가
        file_name_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
        public_id = f"{folder}/{file_name_without_ext}_{timestamp}"
        
        # Cloudinary에 업로드
        result = cloudinary.uploader.upload(
            file_data,
            public_id=public_id,
            folder=folder,
            resource_type='auto',  # 자동으로 이미지/비디오/원시 파일 감지
            overwrite=False,
            use_filename=False,
            unique_filename=True
        )
        
        url = result.get('secure_url', result.get('url', ''))
        print(f"[성공] 파일 업로드 완료: {url}")
        return url
        
    except Exception as e:
        print(f"[오류] 파일 업로드 오류: {e}")
        import traceback
        traceback.print_exc()
        raise


def upload_to_cloudinary(file, folder: str = 'uploads') -> dict:
    """
    Cloudinary에 파일 업로드 (Werkzeug FileStorage 객체 사용)
    
    Args:
        file: Werkzeug FileStorage 객체
        folder: 업로드할 폴더명
    
    Returns:
        업로드 결과 딕셔너리 (secure_url, bytes 등 포함)
    """
    try:
        # 파일 데이터 읽기
        file_data = file.read()
        
        # 파일명에서 확장자 추출
        filename = file.filename or 'file'
        file_extension = filename.split('.')[-1] if '.' in filename else ''
        
        # 타임스탬프 생성
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 파일명에서 확장자 제거하고 타임스탬프 추가
        file_name_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
        public_id = f"{folder}/{file_name_without_ext}_{timestamp}"
        
        # Cloudinary에 업로드
        result = cloudinary.uploader.upload(
            file_data,
            public_id=public_id,
            folder=folder,
            resource_type='auto',  # 자동으로 이미지/비디오/원시 파일 감지
            overwrite=False,
            use_filename=False,
            unique_filename=True
        )
        
        url = result.get('secure_url', result.get('url', ''))
        file_size = result.get('bytes', len(file_data))
        
        print(f"[성공] 파일 업로드 완료: {url}")
        return {
            'secure_url': url,
            'url': url,
            'bytes': file_size,
            'public_id': result.get('public_id', ''),
            'format': result.get('format', file_extension)
        }
        
    except Exception as e:
        print(f"[오류] 파일 업로드 오류: {e}")
        import traceback
        traceback.print_exc()
        raise

