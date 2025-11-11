"""
Google Drive API를 사용한 이미지 업로드 기능
"""
import os
import base64
from datetime import datetime
from typing import List, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError
import io

# Google Drive 설정
DRIVE_FOLDER_NAME = '반품내역'
SCOPES = ['https://www.googleapis.com/auth/drive']

# 공유 폴더 ID (환경 변수 또는 직접 지정)
# 사용자의 Google Drive에서 폴더를 만들고 서비스 계정과 공유한 후,
# 폴더 URL에서 ID를 복사하여 여기에 입력하세요.
# 예: https://drive.google.com/drive/folders/1KiirgG6NkMI0XsLL6P9N88OB9QCPucbn
#     → 폴더 ID: 1KiirgG6NkMI0XsLL6P9N88OB9QCPucbn
# 로그에서 확인된 폴더 ID를 여기에 입력
# Google Drive에서 폴더 URL 확인 후 폴더 ID 복사
# 예: https://drive.google.com/drive/folders/1KiirgG6NkMI0XsLL6P9N88OB9QCPucbn
MAIN_FOLDER_ID = os.environ.get('GOOGLE_DRIVE_MAIN_FOLDER_ID', '1KiirgG6NkMI0XsLL6P9N88OB9QCPucbn')


def get_credentials():
    """Google Drive API 인증 정보 가져오기"""
    try:
        # 환경 변수에서 인증 정보 가져오기
        creds_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
        if creds_json:
            import json
            if isinstance(creds_json, str):
                creds_info = json.loads(creds_json)
            else:
                creds_info = creds_json
            
            credentials = service_account.Credentials.from_service_account_info(
                creds_info, scopes=SCOPES)
            return credentials
        
        # 로컬 파일에서 인증 정보 가져오기
        creds_path = os.path.join(os.path.dirname(__file__), '../../service_account.json')
        if os.path.exists(creds_path):
            credentials = service_account.Credentials.from_service_account_file(
                creds_path, scopes=SCOPES)
            return credentials
        
        print("❌ Google Drive API 인증 정보를 찾을 수 없습니다.")
        return None
    except Exception as e:
        print(f"인증 정보 로드 실패: {e}")
        import traceback
        traceback.print_exc()
        return None


def find_folder_in_shared(service, folder_name: str, parent_folder_id: Optional[str] = None) -> Optional[str]:
    """
    공유된 폴더에서 폴더 찾기 (서비스 계정용)
    서비스 계정은 폴더를 생성할 수 없으므로, 사용자가 미리 만든 폴더를 찾기만 합니다.
    """
    try:
        # 폴더 이름에서 특수문자 이스케이프
        folder_name_escaped = folder_name.replace("'", "\\'")
        
        # 공유된 폴더에서 검색 (서비스 계정이 접근 가능한 폴더)
        if parent_folder_id:
            # 부모 폴더 ID로 직접 접근 시도 (가장 확실한 방법)
            try:
                # 부모 폴더의 자식 폴더 목록 가져오기
                query = f"'{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
                results = service.files().list(
                    q=query,
                    fields="files(id, name, parents)",
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True,
                    corpora='allDrives'
                ).execute()
                
                folders = results.get('files', [])
                for folder in folders:
                    if folder.get('name') == folder_name:
                        print(f"✅ 폴더 찾기 성공 (부모 폴더 내 검색): {folder_name} (ID: {folder['id']}, 부모: {parent_folder_id})")
                        return folder['id']
            except HttpError as e:
                print(f"⚠️ 부모 폴더 내 검색 실패: {e}")
            
            # 부모 폴더 내 검색 실패 시 이름으로 검색
            query = f"name='{folder_name_escaped}' and mimeType='application/vnd.google-apps.folder' and '{parent_folder_id}' in parents and trashed=false"
        else:
            # 모든 공유된 폴더에서 검색
            query = f"name='{folder_name_escaped}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        
        # 서비스 계정이 접근 가능한 폴더만 검색 (공유된 폴더 포함)
        # 여러 방법 시도
        methods = [
            # 방법 1: allDrives 사용
            {
                'includeItemsFromAllDrives': True,
                'supportsAllDrives': True,
                'corpora': 'allDrives'
            },
            # 방법 2: 기본 방식
            {
                'includeItemsFromAllDrives': True,
                'supportsAllDrives': True
            },
            # 방법 3: sharedWithMe 사용
            {
                'q': query + " and sharedWithMe=true",
                'fields': "files(id, name, parents)"
            }
        ]
        
        for method_idx, method_params in enumerate(methods):
            try:
                if 'q' in method_params:
                    # 방법 3: sharedWithMe 사용
                    list_params = {
                        'q': method_params['q'],
                        'fields': method_params['fields']
                    }
                else:
                    # 방법 1, 2: 기본 방식
                    list_params = {
                        'q': query,
                        'fields': "files(id, name, parents)",
                        **method_params
                    }
                
                results = service.files().list(**list_params).execute()
                folders = results.get('files', [])
                
                if folders:
                    # 부모 폴더 ID가 일치하는 폴더 찾기
                    if parent_folder_id:
                        for folder in folders:
                            folder_parents = folder.get('parents', [])
                            if parent_folder_id in folder_parents and folder.get('name') == folder_name:
                                print(f"✅ 폴더 찾기 성공 (방법 {method_idx + 1}): {folder_name} (ID: {folder['id']}, 부모: {parent_folder_id})")
                                return folder['id']
                    else:
                        # 부모 폴더가 없으면 이름이 정확히 일치하는 첫 번째 결과 반환
                        for folder in folders:
                            if folder.get('name') == folder_name:
                                print(f"✅ 폴더 찾기 성공 (방법 {method_idx + 1}): {folder_name} (ID: {folder['id']})")
                                return folder['id']
                
            except HttpError as e:
                print(f"⚠️ 검색 방법 {method_idx + 1} 실패: {e}")
                continue
            except Exception as e:
                print(f"⚠️ 검색 방법 {method_idx + 1} 오류: {e}")
                continue
        
        print(f"⚠️ 폴더를 찾을 수 없음: {folder_name}")
        if parent_folder_id:
            print(f"⚠️ 부모 폴더 ID: {parent_folder_id}")
        return None
        
    except HttpError as error:
        print(f"❌ 폴더 찾기 오류: {error}")
        import traceback
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"❌ 폴더 찾기 오류: {e}")
        import traceback
        traceback.print_exc()
        return None


def upload_images_to_drive(image_data_list: List[str], tracking_number: str) -> str:
    """
    Google Drive에 이미지 업로드
    
    Args:
        image_data_list: Base64 인코딩된 이미지 데이터 리스트
        tracking_number: 송장번호
    
    Returns:
        줄바꿈으로 구분된 사진 링크 문자열 (예: "사진1: url\n사진2: url")
    """
    try:
        if not image_data_list or len(image_data_list) == 0:
            print("⚠️ 이미지 데이터가 없습니다.")
            return ''
        
        if not tracking_number:
            print("⚠️ 송장번호가 없습니다.")
            return ''
        
        print(f"📸 이미지 업로드 시작: {len(image_data_list)}개")
        
        # Google Drive API 서비스 생성
        credentials = get_credentials()
        if not credentials:
            raise Exception("Google Drive API 인증 실패")
        
        # 서비스 계정 이메일 가져오기 (오류 메시지에 사용)
        def get_service_account_email():
            """서비스 계정 이메일 가져오기"""
            try:
                # service_account.json 파일에서 직접 읽기
                import json
                creds_path = os.path.join(os.path.dirname(__file__), '../../service_account.json')
                if os.path.exists(creds_path):
                    with open(creds_path, 'r', encoding='utf-8') as f:
                        creds_info = json.load(f)
                    return creds_info.get('client_email', '확인 필요')
                
                # 환경 변수에서 읽기
                creds_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
                if creds_json:
                    if isinstance(creds_json, str):
                        creds_info = json.loads(creds_json)
                    else:
                        creds_info = creds_json
                    return creds_info.get('client_email', '확인 필요')
                
                return '확인 필요'
            except:
                return 'id-pl-return-service@composite-dream-477907-c5.iam.gserviceaccount.com'
        
        service = build('drive', 'v3', credentials=credentials)
        
        # 메인 폴더 ID 가져오기
        if MAIN_FOLDER_ID:
            # 환경 변수나 설정에서 폴더 ID 직접 사용
            main_folder_id = MAIN_FOLDER_ID
            print(f"✅ 메인 폴더 ID 사용: {DRIVE_FOLDER_NAME} (ID: {main_folder_id})")
            
            # 폴더 접근 가능 여부 확인
            try:
                folder_info = service.files().get(
                    fileId=main_folder_id,
                    fields='id, name, permissions, shared, owners',
                    supportsAllDrives=True
                ).execute()
                folder_name = folder_info.get('name', '알 수 없음')
                folder_shared = folder_info.get('shared', False)
                permissions = folder_info.get('permissions', [])
                
                print(f"✅ 폴더 접근 확인: {folder_name}")
                print(f"   폴더 ID: {main_folder_id}")
                print(f"   공유됨: {folder_shared}")
                print(f"   권한 수: {len(permissions)}")
                
                # 서비스 계정 이메일 확인
                sa_email = get_service_account_email()
                has_service_account = False
                for perm in permissions:
                    email = perm.get('emailAddress', '')
                    role = perm.get('role', '')
                    if email == sa_email:
                        has_service_account = True
                        print(f"   ✅ 서비스 계정 발견: {email} (권한: {role})")
                        break
                
                if not has_service_account:
                    print(f"   ⚠️ 서비스 계정이 권한 목록에 없지만, 폴더 접근은 가능합니다.")
                    
            except HttpError as e:
                error_status = e.resp.status if hasattr(e, 'resp') else '알 수 없음'
                error_msg = str(e)
                
                # 오류 세부 정보
                error_details_str = ''
                try:
                    if hasattr(e, 'error_details'):
                        error_details = e.error_details
                        error_details_str = str(error_details)
                except:
                    pass
                
                print(f"❌ 폴더 접근 오류: {error_msg}")
                print(f"   오류 코드: {error_status}")
                if error_details_str:
                    print(f"   오류 세부 정보: {error_details_str}")
                
                if error_status == 404:
                    raise Exception(
                        f"폴더를 찾을 수 없습니다. (ID: {main_folder_id})\n"
                        f"폴더가 존재하지 않거나 삭제되었습니다."
                    )
                elif error_status == 403:
                    # 서비스 계정 이메일 가져오기
                    sa_email = get_service_account_email()
                    
                    raise Exception(
                        f"❌ 폴더에 접근할 수 없습니다! (403 Forbidden)\n\n"
                        f"서비스 계정이 폴더에 접근할 수 없습니다.\n\n"
                        f"가능한 원인:\n"
                        f"1. 폴더가 서비스 계정과 공유되지 않았음\n"
                        f"2. 권한이 부족함 (읽기만 가능)\n"
                        f"3. 폴더 ID가 잘못됨\n\n"
                        f"해결 방법:\n"
                        f"1. Google Drive 접속: https://drive.google.com/\n"
                        f"2. '{DRIVE_FOLDER_NAME}' 폴더 우클릭 → '공유' 클릭\n"
                        f"3. 서비스 계정 이메일 추가: {sa_email}\n"
                        f"4. 권한: '편집자' 선택 (중요!)\n"
                        f"5. '전송' 클릭\n"
                        f"6. 몇 분 기다린 후 다시 시도 (공유 반영 시간)\n\n"
                        f"폴더 ID: {main_folder_id}\n"
                        f"서비스 계정: {sa_email}"
                    )
                else:
                    raise Exception(f"폴더 접근 오류 ({error_status}): {error_msg}\n{error_details_str}")
        else:
            # 공유된 폴더에서 찾기
            main_folder_id = find_folder_in_shared(service, DRIVE_FOLDER_NAME)
            if not main_folder_id:
                raise Exception(
                    f"메인 폴더 '{DRIVE_FOLDER_NAME}'를 찾을 수 없습니다. "
                    "Google Drive에서 폴더를 만들고 서비스 계정과 공유한 후, "
                    "폴더 ID를 환경 변수 GOOGLE_DRIVE_MAIN_FOLDER_ID에 설정하거나 "
                    "코드의 MAIN_FOLDER_ID에 직접 입력하세요."
                )
            print(f"✅ 메인 폴더 찾기 성공: {DRIVE_FOLDER_NAME} (ID: {main_folder_id})")
        
        # 현재 월 폴더 찾기
        today = datetime.now()
        year_month = today.strftime('%Y년%m월')
        print(f"🔍 월 폴더 검색 중: {year_month} (부모 폴더 ID: {main_folder_id})")
        
        month_folder_id = find_folder_in_shared(service, year_month, main_folder_id)
        if not month_folder_id:
            # 서비스 계정 이메일 가져오기
            sa_email = get_service_account_email()
            
            # 디버깅: 부모 폴더의 자식 폴더 목록 확인
            try:
                query = f"'{main_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
                debug_results = service.files().list(
                    q=query,
                    fields="files(id, name)",
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True,
                    corpora='allDrives'
                ).execute()
                debug_folders = debug_results.get('files', [])
                folder_names = [f.get('name', '') for f in debug_folders]
                print(f"⚠️ 부모 폴더 내 폴더 목록: {folder_names}")
            except Exception as debug_error:
                print(f"⚠️ 폴더 목록 확인 실패: {debug_error}")
            
            raise Exception(
                f"월 폴더 '{year_month}'를 찾을 수 없습니다.\n\n"
                f"해결 방법:\n"
                f"1. Google Drive 접속: https://drive.google.com/\n"
                f"2. '{DRIVE_FOLDER_NAME}' 폴더 열기 (폴더 ID: {main_folder_id})\n"
                f"3. '{year_month}' 폴더가 있는지 확인\n"
                f"4. 없으면 폴더 생성: '새로 만들기' → '폴더' → 이름: '{year_month}'\n"
                f"5. '{DRIVE_FOLDER_NAME}' 폴더가 서비스 계정과 공유되어 있는지 확인\n"
                f"6. 서비스 계정 이메일: {sa_email}\n"
                f"7. 권한: '편집자' (중요!)\n\n"
                f"상위 폴더를 공유하면 하위 폴더도 자동으로 공유됩니다."
            )
        
        print(f"✅ 월 폴더 찾기 성공: {year_month} (ID: {month_folder_id})")
        
        # 타임스탬프 생성
        timestamp = today.strftime('%Y%m%d_%H%M%S')
        photo_texts = []
        
        print("🖼️ 개별 이미지 업로드 시작...")
        
        # 모든 이미지 업로드
        for i, image_data in enumerate(image_data_list, 1):
            try:
                if not image_data or not isinstance(image_data, str):
                    print(f"⚠️ 이미지 {i} 데이터가 유효하지 않습니다.")
                    continue
                
                print(f"📤 이미지 {i} 업로드 중...")
                
                # Base64 데이터 디코딩
                if ',' in image_data:
                    base64_data = image_data.split(',')[1]
                else:
                    base64_data = image_data
                
                image_bytes = base64.b64decode(base64_data)
                
                # 파일명 생성
                filename = f"{tracking_number}_{timestamp}_{i}.jpg"
                
                # 파일 메타데이터
                file_metadata = {
                    'name': filename,
                    'parents': [month_folder_id]
                }
                
                # 미디어 업로드
                media = MediaIoBaseUpload(
                    io.BytesIO(image_bytes),
                    mimetype='image/jpeg',
                    resumable=True
                )
                
                # 파일 업로드 (공유된 폴더에 업로드)
                # 중요: 서비스 계정은 저장 공간이 없으므로 공유된 폴더에만 업로드 가능
                try:
                    file = service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields='id, webViewLink, webContentLink',
                        supportsAllDrives=True,  # 공유 드라이브 지원 (필수)
                        ignoreDefaultVisibility=True  # 기본 공개 설정 무시
                    ).execute()
                    
                    file_id = file.get('id')
                    print(f"✅ 파일 생성 성공: {filename} (ID: {file_id})")
                except HttpError as upload_error:
                    error_msg = str(upload_error)
                    
                    # 오류 내용 추출 (다양한 방법 시도)
                    error_content = ''
                    try:
                        if hasattr(upload_error, 'content'):
                            error_content = upload_error.content.decode('utf-8') if isinstance(upload_error.content, bytes) else str(upload_error.content)
                        elif hasattr(upload_error, 'resp'):
                            error_resp = upload_error.resp
                            if hasattr(error_resp, 'data'):
                                error_content = error_resp.data.decode('utf-8') if isinstance(error_resp.data, bytes) else str(error_resp.data)
                    except Exception as e:
                        print(f"⚠️ 오류 내용 추출 실패: {e}")
                    
                    # 오류 세부 정보 가져오기
                    error_reason = ''
                    error_details_str = ''
                    try:
                        if hasattr(upload_error, 'error_details'):
                            error_details = upload_error.error_details
                            if isinstance(error_details, list) and len(error_details) > 0:
                                error_reason = error_details[0].get('reason', '') if isinstance(error_details[0], dict) else str(error_details[0])
                                error_details_str = str(error_details)
                    except:
                        pass
                    
                    # 오류 상태 코드 확인
                    error_status = upload_error.resp.status if hasattr(upload_error, 'resp') else '알 수 없음'
                    
                    print(f"❌ 파일 업로드 HttpError: {error_msg}")
                    print(f"   오류 상태 코드: {error_status}")
                    print(f"   파일명: {filename}")
                    print(f"   대상 폴더 ID: {month_folder_id}")
                    if error_content:
                        print(f"   오류 내용: {error_content}")
                    if error_reason:
                        print(f"   오류 이유: {error_reason}")
                    if error_details_str:
                        print(f"   오류 세부 정보: {error_details_str}")
                    
                    # 전체 오류 정보를 하나의 문자열로 만들기
                    full_error_text = f"{error_msg} {error_content} {error_reason} {error_details_str}".lower()
                    
                    # 저장 공간 오류인 경우
                    if 'storagequotaexceeded' in full_error_text or 'storage quota' in full_error_text:
                        # 서비스 계정 이메일 가져오기
                        sa_email = get_service_account_email()
                        
                        error_detail = (
                            f"서비스 계정이 파일을 업로드할 수 없습니다.\n\n"
                            f"원인: 서비스 계정은 저장 공간이 없어서 공유된 폴더에만 파일을 업로드할 수 있습니다.\n\n"
                            f"해결 방법:\n"
                            f"1. Google Drive 접속: https://drive.google.com/\n"
                            f"2. '{DRIVE_FOLDER_NAME}' 폴더 열기 (폴더 ID: {main_folder_id})\n"
                            f"3. 폴더 우클릭 → '공유' 클릭\n"
                            f"4. 서비스 계정 이메일 추가: {sa_email}\n"
                            f"5. 권한: '편집자' 선택 (중요!)\n"
                            f"6. '전송' 클릭\n"
                            f"7. '{year_month}' 폴더도 확인 (상위 폴더 공유 시 자동 공유)\n\n"
                            f"현재 폴더 ID: {month_folder_id}\n"
                            f"서비스 계정 이메일: {sa_email}"
                        )
                        
                        print(f"❌ {error_detail}")
                        raise Exception(error_detail)
                    elif error_status == 403:
                        # 권한 오류
                        sa_email = get_service_account_email()
                        raise Exception(
                            f"파일 업로드 권한이 없습니다. (403 Forbidden)\n\n"
                            f"서비스 계정이 폴더에 파일을 업로드할 권한이 없습니다.\n\n"
                            f"해결 방법:\n"
                            f"1. Google Drive에서 '{DRIVE_FOLDER_NAME}' 폴더 확인\n"
                            f"2. 폴더 우클릭 → '공유' 클릭\n"
                            f"3. 서비스 계정 이메일 확인: {sa_email}\n"
                            f"4. 권한이 '편집자'인지 확인 (읽기만으로는 업로드 불가)\n"
                            f"5. 권한이 '읽기'면 '편집자'로 변경\n\n"
                            f"폴더 ID: {month_folder_id}"
                        )
                    else:
                        # 다른 오류인 경우 - 자세한 정보와 함께
                        error_info = f"파일 업로드 실패 (상태 코드: {error_status})\n"
                        error_info += f"오류 메시지: {error_msg}\n"
                        if error_reason:
                            error_info += f"오류 이유: {error_reason}\n"
                        if error_content:
                            error_info += f"오류 내용: {error_content[:1000]}\n"  # 처음 1000자
                        if error_details_str:
                            error_info += f"오류 세부 정보: {error_details_str[:500]}\n"
                        error_info += f"\n대상 폴더 ID: {month_folder_id}\n"
                        error_info += f"파일명: {filename}"
                        raise Exception(error_info)
                
                # 공유 설정 (누구나 링크로 볼 수 있도록)
                try:
                    permission = {
                        'type': 'anyone',
                        'role': 'reader'
                    }
                    service.permissions().create(
                        fileId=file.get('id'),
                        body=permission,
                        supportsAllDrives=True  # 공유 드라이브 지원
                    ).execute()
                    print(f"✅ 공유 설정 완료: {filename}")
                except HttpError as perm_error:
                    # 공유 설정 실패해도 계속 진행 (이미 공유된 폴더에 있을 수 있음)
                    print(f"⚠️ 공유 설정 실패 (무시, 파일은 업로드됨): {perm_error}")
                
                # 공개 링크 가져오기
                try:
                    file_info = service.files().get(
                        fileId=file.get('id'),
                        fields='webViewLink',
                        supportsAllDrives=True  # 공유 드라이브 지원
                    ).execute()
                    link_url = file_info.get('webViewLink', '')
                except HttpError:
                    # 링크 가져오기 실패 시 파일 ID로 링크 생성
                    file_id = file.get('id')
                    link_url = f"https://drive.google.com/file/d/{file_id}/view"
                    print(f"⚠️ 링크 가져오기 실패, ID로 링크 생성: {link_url}")
                
                link_text = f"사진{i}"
                photo_texts.append(f"{link_text}: {link_url}")
                
                print(f"✅ 이미지 {i} 업로드 완료: {filename}")
                print(f"🔗 링크: {link_url}")
                
            except Exception as error:
                error_msg = str(error)
                print(f"❌ 이미지 {i} 업로드 오류: {error_msg}")
                import traceback
                traceback.print_exc()
                
                # 저장 공간 오류나 폴더 접근 오류인 경우 즉시 중단
                error_lower = error_msg.lower()
                if ('storagequotaexceeded' in error_lower or 
                    'storage quota' in error_lower or 
                    '서비스 계정이 파일을 업로드할 수 없습니다' in error_msg or
                    '폴더에 접근할 수 없습니다' in error_msg or
                    '접근할 수 없습니다' in error_msg):
                    raise error  # 상위로 전파하여 전체 프로세스 중단
                
                # 개별 이미지 실패해도 계속 진행 (다른 오류인 경우)
                print(f"⚠️ 이미지 {i} 업로드 실패했지만 계속 진행합니다.")
                continue
        
        print(f"🎉 모든 이미지 업로드 완료: {len(photo_texts)}개")
        
        if len(photo_texts) == 0:
            raise Exception("업로드된 이미지가 없습니다.")
        
        # 줄바꿈으로 구분된 텍스트 반환
        return '\n'.join(photo_texts)
        
    except HttpError as error:
        print(f"💥 Google Drive API 오류: {error}")
        raise Exception(f"이미지 업로드 실패: {error}")
    except Exception as e:
        print(f"💥 이미지 업로드 전체 오류: {e}")
        import traceback
        traceback.print_exc()
        raise Exception(f"이미지 업로드 실패: {str(e)}")

