"""
OAuth 2.0을 사용한 Google Drive 이미지 업로드
사용자 계정으로 파일을 업로드하여 서비스 계정 제한을 우회합니다.
"""
import os
import json
import base64
from datetime import datetime
from typing import List, Optional
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError
import io
import pickle

# Google Drive 설정
DRIVE_FOLDER_NAME = '반품내역'
SETTLEMENT_MAIN_FOLDER_NAME = '제이제이솔루션'
SCOPES = ['https://www.googleapis.com/auth/drive']
MAIN_FOLDER_ID = os.environ.get('GOOGLE_DRIVE_MAIN_FOLDER_ID', '1KiirgG6NkMI0XsLL6P9N88OB9QCPucbn')
SETTLEMENT_MAIN_FOLDER_ID = os.environ.get('GOOGLE_DRIVE_SETTLEMENT_MAIN_FOLDER_ID', '16TdQlAqyOkYIrvSTvEPH9LByLzyamsAw')

# OAuth 2.0 토큰 파일 경로
TOKEN_FILE = os.path.join(os.path.dirname(__file__), '../../token.pickle')
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), '../../credentials.json')


def get_credentials():
    """
    OAuth 2.0을 사용하여 사용자 계정 인증 정보 가져오기
    Vercel 환경 변수에서 토큰을 읽거나, 로컬 파일에서 읽습니다.
    """
    creds = None
    
    # 1. 환경 변수에서 토큰 읽기 (Vercel 등 서버리스 환경 우선)
    oauth_token_json = os.environ.get('GOOGLE_OAUTH_TOKEN_JSON')
    oauth_credentials_json = os.environ.get('GOOGLE_OAUTH_CREDENTIALS_JSON')
    
    if oauth_token_json and oauth_credentials_json:
        try:
            # 환경 변수에서 credentials 읽기
            creds_info = json.loads(oauth_credentials_json)
            # installed 또는 web 형식 모두 지원
            if 'installed' in creds_info:
                client_id = creds_info['installed']['client_id']
                client_secret = creds_info['installed']['client_secret']
            elif 'web' in creds_info:
                client_id = creds_info['web']['client_id']
                client_secret = creds_info['web']['client_secret']
            else:
                client_id = creds_info.get('client_id')
                client_secret = creds_info.get('client_secret')
            
            # 환경 변수에서 토큰 읽기
            token_info = json.loads(oauth_token_json)
            
            # Credentials 객체 생성
            creds = Credentials(
                token=token_info.get('token'),
                refresh_token=token_info.get('refresh_token'),
                token_uri=token_info.get('token_uri', 'https://oauth2.googleapis.com/token'),
                client_id=client_id,
                client_secret=client_secret,
                scopes=token_info.get('scopes', SCOPES)
            )
            
            print("✅ 환경 변수에서 OAuth 토큰 로드 성공 (Vercel 배포 환경)")
            
            # 토큰이 만료되었으면 갱신
            if creds.expired and creds.refresh_token:
                try:
                    print("🔄 토큰 갱신 중...")
                    creds.refresh(Request())
                    print("✅ 토큰 갱신 성공")
                except Exception as e:
                    print(f"❌ 토큰 갱신 실패: {e}")
                    creds = None
            
            if creds and creds.valid:
                return creds
        except Exception as e:
            print(f"⚠️ 환경 변수에서 토큰 로드 실패: {e}")
            print(f"   GOOGLE_OAUTH_TOKEN_JSON 존재: {bool(oauth_token_json)}")
            print(f"   GOOGLE_OAUTH_CREDENTIALS_JSON 존재: {bool(oauth_credentials_json)}")
            if oauth_token_json:
                print(f"   GOOGLE_OAUTH_TOKEN_JSON 길이: {len(oauth_token_json)} 문자")
                print(f"   GOOGLE_OAUTH_TOKEN_JSON 처음 100자: {oauth_token_json[:100]}")
            if oauth_credentials_json:
                print(f"   GOOGLE_OAUTH_CREDENTIALS_JSON 길이: {len(oauth_credentials_json)} 문자")
                print(f"   GOOGLE_OAUTH_CREDENTIALS_JSON 처음 100자: {oauth_credentials_json[:100]}")
            import traceback
            traceback.print_exc()
            creds = None
    
    # 2. 로컬 파일에서 토큰 읽기 (로컬 환경)
    # 배포 환경에서는 환경 변수를 사용해야 하므로, 환경 변수가 없으면 명확한 오류 메시지
    is_vercel = os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV')
    
    if not oauth_token_json or not oauth_credentials_json:
        if is_vercel:
            print(f"❌ Vercel 배포 환경에서 OAuth 2.0 환경 변수가 설정되지 않았습니다.")
            print(f"   GOOGLE_OAUTH_TOKEN_JSON: {'✅' if oauth_token_json else '❌'}")
            print(f"   GOOGLE_OAUTH_CREDENTIALS_JSON: {'✅' if oauth_credentials_json else '❌'}")
            raise Exception(
                f"Vercel 배포 환경에서 OAuth 2.0 환경 변수가 설정되지 않았습니다.\n\n"
                f"필요한 환경 변수:\n"
                f"1. GOOGLE_OAUTH_CREDENTIALS_JSON: credentials.json 전체 내용\n"
                f"2. GOOGLE_OAUTH_TOKEN_JSON: 로컬에서 인증 받은 토큰 JSON\n\n"
                f"설정 방법:\n"
                f"1. Vercel 대시보드 → Settings → Environment Variables\n"
                f"2. 두 환경 변수 모두 추가 (Production, Preview, Development 모두 선택)\n"
                f"3. 재배포\n\n"
                f"자세한 내용은 Vercel_환경변수_설정_단계별_가이드.md 참고"
            )
        else:
            print(f"⚠️ 로컬 환경: 환경 변수가 없으므로 로컬 파일을 시도합니다.")
    
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'rb') as token:
                creds = pickle.load(token)
            print(f"✅ 기존 토큰 파일 로드 성공: {TOKEN_FILE}")
        except Exception as e:
            print(f"⚠️ 토큰 파일 로드 실패: {e}")
            creds = None
    
    # 토큰이 없거나 만료된 경우
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # 토큰 갱신
            try:
                print("🔄 토큰 갱신 중...")
                creds.refresh(Request())
                print("✅ 토큰 갱신 성공")
                # 갱신된 토큰 저장
                with open(TOKEN_FILE, 'wb') as token:
                    pickle.dump(creds, token)
            except Exception as e:
                print(f"❌ 토큰 갱신 실패: {e}")
                import traceback
                traceback.print_exc()
                creds = None
        
        # 토큰이 없으면 OAuth 2.0 플로우 시작
        if not creds:
            print(f"[디버깅] 토큰이 없음 - OAuth 2.0 플로우 시작 또는 오류 발생")
            if is_vercel:
                # Vercel 환경에서는 환경 변수만 사용 가능
                print(f"[디버깅] Vercel 환경에서 토큰 없음 - 예외 발생")
                raise Exception(
                    f"Vercel 배포 환경에서 OAuth 2.0 토큰을 가져올 수 없습니다.\n\n"
                    f"환경 변수 확인:\n"
                    f"- GOOGLE_OAUTH_TOKEN_JSON: {'✅ 설정됨' if oauth_token_json else '❌ 없음'}\n"
                    f"- GOOGLE_OAUTH_CREDENTIALS_JSON: {'✅ 설정됨' if oauth_credentials_json else '❌ 없음'}\n\n"
                    f"환경 변수가 설정되어 있다면 재배포가 필요할 수 있습니다.\n"
                    f"또는 토큰이 만료되었을 수 있으므로 로컬에서 다시 인증 받아주세요."
                )
            if not os.path.exists(CREDENTIALS_FILE):
                raise Exception(
                    f"OAuth 2.0 인증 파일이 없습니다: {CREDENTIALS_FILE}\n\n"
                    f"해결 방법:\n"
                    f"1. Google Cloud Console 접속: https://console.cloud.google.com/\n"
                    f"2. 프로젝트 선택: composite-dream-477907-c5\n"
                    f"3. APIs & Services → Credentials\n"
                    f"4. Create Credentials → OAuth client ID\n"
                    f"5. Application type: Desktop app 선택\n"
                    f"6. Create 클릭\n"
                    f"7. JSON 다운로드\n"
                    f"8. 다운로드한 파일을 credentials.json으로 이름 변경\n"
                    f"9. 프로젝트 루트 폴더에 저장"
                )
            
            print("🔐 OAuth 2.0 인증 시작...")
            print("브라우저가 열리면 Google 로그인을 진행하세요.")
            
            # credentials.json 형식 확인 (web 또는 installed)
            with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
                creds_data = json.load(f)
            
            # installed 형식 (Desktop app) 또는 web 형식 모두 지원
            if 'installed' in creds_data or 'web' in creds_data:
                # Desktop app 또는 Web application 타입 모두 InstalledAppFlow 사용 가능
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES)
            else:
                raise Exception(
                    f"credentials.json 형식이 올바르지 않습니다.\n"
                    f"'installed' 또는 'web' 키가 필요합니다.\n"
                    f"OAuth 클라이언트 ID를 'Desktop app' 타입으로 다시 생성하세요.\n"
                    f"(현재 '웹 애플리케이션' 타입은 redirect_uri_mismatch 오류가 발생할 수 있습니다)"
                )
            
            creds = flow.run_local_server(port=0, open_browser=True)
            print("✅ OAuth 2.0 인증 완료")
            
            # 토큰 저장
            with open(TOKEN_FILE, 'wb') as token:
                pickle.dump(creds, token)
            print(f"✅ 토큰 저장 완료: {TOKEN_FILE}")
    
    return creds


def upload_images_to_drive(image_data_list: List[str], tracking_number: str) -> str:
    """
    OAuth 2.0을 사용하여 Google Drive에 이미지 업로드
    
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
        
        # OAuth 2.0 인증 정보 가져오기
        credentials = get_credentials()
        if not credentials:
            raise Exception("OAuth 2.0 인증 실패")
        
        service = build('drive', 'v3', credentials=credentials)
        
        # 메인 폴더 ID 사용
        main_folder_id = MAIN_FOLDER_ID
        print(f"✅ 메인 폴더 ID 사용: {DRIVE_FOLDER_NAME} (ID: {main_folder_id})")
        
        # 현재 월 폴더 찾기
        today = datetime.now()
        year_month = today.strftime('%Y년%m월')
        print(f"🔍 월 폴더 검색 중: {year_month} (부모 폴더 ID: {main_folder_id})")
        
        # 월별 폴더 찾기
        query = f"'{main_folder_id}' in parents and name='{year_month}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = service.files().list(
            q=query,
            fields="files(id, name)",
            spaces='drive'
        ).execute()
        
        folders = results.get('files', [])
        if not folders:
            raise Exception(
                f"월 폴더 '{year_month}'를 찾을 수 없습니다. "
                f"Google Drive의 '{DRIVE_FOLDER_NAME}' 폴더 안에 '{year_month}' 폴더를 만들어주세요."
            )
        
        month_folder_id = folders[0]['id']
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
                
                # 파일 업로드
                file = service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id, webViewLink'
                ).execute()
                
                file_id = file.get('id')
                link_url = file.get('webViewLink', '')
                
                # 공유 설정 (누구나 링크로 볼 수 있도록)
                try:
                    permission = {
                        'type': 'anyone',
                        'role': 'reader'
                    }
                    service.permissions().create(
                        fileId=file_id,
                        body=permission
                    ).execute()
                except Exception as e:
                    print(f"⚠️ 공유 설정 실패 (무시): {e}")
                
                link_text = f"사진{i}"
                photo_texts.append(f"{link_text}: {link_url}")
                
                print(f"✅ 이미지 {i} 업로드 완료: {filename}")
                print(f"🔗 링크: {link_url}")
                
            except Exception as error:
                print(f"❌ 이미지 {i} 업로드 오류: {error}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"🎉 모든 이미지 업로드 완료: {len(photo_texts)}개")
        
        if len(photo_texts) == 0:
            raise Exception("업로드된 이미지가 없습니다.")
        
        return '\n'.join(photo_texts)
        
    except Exception as e:
        print(f"💥 이미지 업로드 전체 오류: {e}")
        import traceback
        traceback.print_exc()
        raise Exception(f"이미지 업로드 실패: {str(e)}")


def find_folder_in_oauth(service, folder_name: str, parent_folder_id: Optional[str] = None) -> Optional[str]:
    """
    OAuth 2.0을 사용하여 폴더 찾기
    """
    try:
        if parent_folder_id:
            # 부모 폴더의 자식 폴더 목록 가져오기
            query = f"'{parent_folder_id}' in parents and name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = service.files().list(
                q=query,
                fields="files(id, name)",
                spaces='drive'
            ).execute()
            
            folders = results.get('files', [])
            if folders:
                folder_id = folders[0]['id']
                print(f"✅ 폴더 찾기 성공: {folder_name} (ID: {folder_id}, 부모: {parent_folder_id})")
                return folder_id
        else:
            # 이름으로 직접 검색
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = service.files().list(
                q=query,
                fields="files(id, name)",
                spaces='drive'
            ).execute()
            
            folders = results.get('files', [])
            if folders:
                folder_id = folders[0]['id']
                print(f"✅ 폴더 찾기 성공: {folder_name} (ID: {folder_id})")
                return folder_id
        
        print(f"⚠️ 폴더를 찾을 수 없음: {folder_name}")
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


def upload_excel_to_drive(file_data: bytes, filename: str, folder_name: str = '정산파일') -> dict:
    """
    OAuth 2.0을 사용하여 Google Drive에 엑셀 파일 업로드
    
    Args:
        file_data: 파일 데이터 (bytes)
        filename: 파일명
        folder_name: 대상 폴더명 (기본값: '정산파일')
    
    Returns:
        {
            'success': bool,
            'file_id': str,
            'file_url': str,
            'web_view_link': str,
            'message': str
        }
    """
    try:
        if not file_data:
            raise Exception("파일 데이터가 없습니다.")
        
        if not filename:
            raise Exception("파일명이 없습니다.")
        
        print(f"📄 엑셀 파일 업로드 시작: {filename}")
        print(f"🔍 OAuth 2.0 인증 정보 확인 중...")
        
        # 환경 변수 확인 (디버깅)
        oauth_token_json = os.environ.get('GOOGLE_OAUTH_TOKEN_JSON')
        oauth_credentials_json = os.environ.get('GOOGLE_OAUTH_CREDENTIALS_JSON')
        is_vercel = os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV')
        
        print(f"   Vercel 환경: {bool(is_vercel)}")
        print(f"   GOOGLE_OAUTH_TOKEN_JSON 존재: {bool(oauth_token_json)}")
        print(f"   GOOGLE_OAUTH_CREDENTIALS_JSON 존재: {bool(oauth_credentials_json)}")
        if oauth_token_json:
            print(f"   GOOGLE_OAUTH_TOKEN_JSON 길이: {len(oauth_token_json)} 문자")
        if oauth_credentials_json:
            print(f"   GOOGLE_OAUTH_CREDENTIALS_JSON 길이: {len(oauth_credentials_json)} 문자")
        
        # OAuth 2.0 인증 정보 가져오기
        credentials = get_credentials()
        if not credentials:
            error_msg = "OAuth 2.0 인증 실패"
            if is_vercel and (not oauth_token_json or not oauth_credentials_json):
                error_msg += f"\n\nVercel 배포 환경에서 환경 변수가 설정되지 않았습니다.\n"
                error_msg += f"필요한 환경 변수:\n"
                error_msg += f"- GOOGLE_OAUTH_CREDENTIALS_JSON: {'✅ 설정됨' if oauth_credentials_json else '❌ 없음'}\n"
                error_msg += f"- GOOGLE_OAUTH_TOKEN_JSON: {'✅ 설정됨' if oauth_token_json else '❌ 없음'}\n"
                error_msg += f"\nVercel 대시보드 → Settings → Environment Variables에서 설정하세요."
            raise Exception(error_msg)
        
        service = build('drive', 'v3', credentials=credentials)
        print(f"✅ Google Drive API 서비스 생성 완료 (OAuth 2.0)")
        
        # 메인 폴더 ID 사용
        main_folder_id = SETTLEMENT_MAIN_FOLDER_ID
        print(f"✅ 메인 폴더 ID 사용: {SETTLEMENT_MAIN_FOLDER_NAME} (ID: {main_folder_id})")
        
        # 대상 폴더 찾기
        target_folder_id = find_folder_in_oauth(service, folder_name, main_folder_id)
        
        if not target_folder_id:
            raise Exception(
                f"'{folder_name}' 폴더를 찾을 수 없습니다.\n"
                f"Google Drive에서 '{SETTLEMENT_MAIN_FOLDER_NAME}' 폴더 안에 '{folder_name}' 폴더를 만들어주세요."
            )
        
        print(f"✅ 대상 폴더 찾기 성공: {folder_name} (ID: {target_folder_id})")
        
        # 파일 메타데이터
        file_metadata = {
            'name': filename,
            'parents': [target_folder_id]
        }
        
        # 미디어 업로드 (엑셀 파일)
        # 파일 확장자에 따라 MIME 타입 결정
        if filename.endswith('.xlsx'):
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif filename.endswith('.xls'):
            mimetype = 'application/vnd.ms-excel'
        else:
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
        media = MediaIoBaseUpload(
            io.BytesIO(file_data),
            mimetype=mimetype,
            resumable=True
        )
        
        # 파일 업로드
        try:
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink, webContentLink'
            ).execute()
            
            file_id = file.get('id')
            web_view_link = file.get('webViewLink', '')
            web_content_link = file.get('webContentLink', '')
            
            print(f"✅ 파일 업로드 성공: {filename} (ID: {file_id})")
            print(f"🔗 웹 보기 링크: {web_view_link}")
            
            # 공유 설정 (누구나 링크로 볼 수 있도록)
            try:
                permission = {
                    'type': 'anyone',
                    'role': 'reader'
                }
                service.permissions().create(
                    fileId=file_id,
                    body=permission
                ).execute()
                print(f"✅ 공유 설정 완료: {filename}")
            except HttpError as perm_error:
                print(f"⚠️ 공유 설정 실패 (무시, 파일은 업로드됨): {perm_error}")
            
            return {
                'success': True,
                'file_id': file_id,
                'file_url': web_content_link,
                'web_view_link': web_view_link,
                'message': f'파일 업로드 성공: {filename}'
            }
            
        except HttpError as upload_error:
            error_msg = str(upload_error)
            error_status = upload_error.resp.status if hasattr(upload_error, 'resp') else '알 수 없음'
            
            print(f"❌ 파일 업로드 실패: {error_msg} (상태 코드: {error_status})")
            raise Exception(f"파일 업로드 실패 ({error_status}): {error_msg}")
    
    except HttpError as error:
        print(f"💥 Google Drive API 오류: {error}")
        return {
            'success': False,
            'file_id': None,
            'file_url': None,
            'web_view_link': None,
            'message': f'Google Drive API 오류: {error}'
        }
    except Exception as e:
        print(f"💥 엑셀 파일 업로드 전체 오류: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'file_id': None,
            'file_url': None,
            'web_view_link': None,
            'message': f'엑셀 파일 업로드 실패: {str(e)}'
        }


# ========== 정산 파일 업로드 관련 함수 ==========

def find_or_create_year_folder(service, parent_folder_id: str, year: str) -> str:
    """
    년도 폴더 찾기 또는 생성
    
    Args:
        service: Google Drive API 서비스 객체
        parent_folder_id: 부모 폴더 ID (정산파일 폴더)
        year: 년도 (예: "2025")
    
    Returns:
        폴더 ID
    """
    folder_name = f"{year}년"
    
    # 기존 폴더 찾기
    folder_id = find_folder_in_oauth(service, folder_name, parent_folder_id)
    
    if folder_id:
        return folder_id
    
    # 폴더가 없으면 생성
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_folder_id]
    }
    
    folder = service.files().create(
        body=file_metadata,
        fields='id'
    ).execute()
    
    print(f"✅ 년도 폴더 생성: {folder_name} (ID: {folder.get('id')})")
    return folder.get('id')


def find_or_create_month_folder(service, parent_folder_id: str, month: str) -> str:
    """
    월 폴더 찾기 또는 생성
    
    Args:
        service: Google Drive API 서비스 객체
        parent_folder_id: 부모 폴더 ID (년도 폴더)
        month: 월 (예: "01" 또는 "1")
    
    Returns:
        폴더 ID
    """
    # 월을 2자리로 변환 (예: "1" -> "01")
    month_padded = month.zfill(2)
    folder_name = f"{month_padded}월"
    
    # 기존 폴더 찾기
    folder_id = find_folder_in_oauth(service, folder_name, parent_folder_id)
    
    if folder_id:
        return folder_id
    
    # 폴더가 없으면 생성
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_folder_id]
    }
    
    folder = service.files().create(
        body=file_metadata,
        fields='id'
    ).execute()
    
    print(f"✅ 월 폴더 생성: {folder_name} (ID: {folder.get('id')})")
    return folder.get('id')


def find_or_create_company_folder(service, parent_folder_id: str, company_name: str) -> str:
    """
    화주사 폴더 찾기 또는 생성
    
    Args:
        service: Google Drive API 서비스 객체
        parent_folder_id: 부모 폴더 ID (월 폴더)
        company_name: 화주사명
    
    Returns:
        폴더 ID
    """
    # 기존 폴더 찾기
    folder_id = find_folder_in_oauth(service, company_name, parent_folder_id)
    
    if folder_id:
        return folder_id
    
    # 폴더가 없으면 생성
    file_metadata = {
        'name': company_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_folder_id]
    }
    
    folder = service.files().create(
        body=file_metadata,
        fields='id'
    ).execute()
    
    print(f"✅ 화주사 폴더 생성: {company_name} (ID: {folder.get('id')})")
    return folder.get('id')


def upload_settlement_excel_to_drive(
    file_data: bytes, 
    filename: str, 
    company_name: str, 
    settlement_year_month: str
) -> dict:
    """
    정산용 엑셀 파일을 Google Drive에 업로드
    폴더 구조: 제이제이솔루션 > 정산파일 > 년도 > 월 > 화주사명
    
    Args:
        file_data: 파일 데이터 (bytes)
        filename: 파일명 (예: "작업비정산서.xlsx")
        company_name: 화주사명
        settlement_year_month: 정산년월 (예: "2025-01")
    
    Returns:
        {
            'success': bool,
            'file_id': str,
            'file_url': str,
            'web_view_link': str,
            'message': str
        }
    """
    try:
        if not file_data:
            raise Exception("파일 데이터가 없습니다.")
        
        if not filename:
            raise Exception("파일명이 없습니다.")
        
        if not company_name:
            raise Exception("화주사명이 없습니다.")
        
        if not settlement_year_month:
            raise Exception("정산년월이 없습니다.")
        
        print(f"📄 정산 엑셀 파일 업로드 시작: {filename}")
        print(f"   화주사: {company_name}")
        print(f"   정산년월: {settlement_year_month}")
        
        # OAuth 2.0 인증 정보 가져오기
        credentials = get_credentials()
        if not credentials:
            raise Exception("OAuth 2.0 인증 실패")
        
        service = build('drive', 'v3', credentials=credentials)
        
        # 1. 메인 폴더 ID 사용
        main_folder_id = SETTLEMENT_MAIN_FOLDER_ID
        print(f"✅ 메인 폴더 ID 사용: {SETTLEMENT_MAIN_FOLDER_NAME} (ID: {main_folder_id})")
        
        # 2. 정산파일 폴더 찾기
        settlement_folder_id = find_folder_in_oauth(service, "정산파일", main_folder_id)
        if not settlement_folder_id:
            raise Exception(
                f"'정산파일' 폴더를 찾을 수 없습니다.\n"
                f"Google Drive에서 '{SETTLEMENT_MAIN_FOLDER_NAME}' 폴더 안에 '정산파일' 폴더를 만들어주세요."
            )
        print(f"✅ 정산파일 폴더 찾기 성공 (ID: {settlement_folder_id})")
        
        # 3. 정산년월에서 년도와 월 추출
        # settlement_year_month 형식: "2025-01"
        year, month = settlement_year_month.split('-')
        print(f"   년도: {year}, 월: {month}")
        
        # 4. 년도 폴더 찾기/생성
        year_folder_id = find_or_create_year_folder(service, settlement_folder_id, year)
        print(f"✅ 년도 폴더: {year}년 (ID: {year_folder_id})")
        
        # 5. 월 폴더 찾기/생성
        month_folder_id = find_or_create_month_folder(service, year_folder_id, month)
        print(f"✅ 월 폴더: {month}월 (ID: {month_folder_id})")
        
        # 6. 화주사 폴더 찾기/생성
        company_folder_id = find_or_create_company_folder(service, month_folder_id, company_name)
        print(f"✅ 화주사 폴더: {company_name} (ID: {company_folder_id})")
        
        # 7. 파일 메타데이터
        file_metadata = {
            'name': filename,
            'parents': [company_folder_id]
        }
        
        # 8. 미디어 업로드 (엑셀 파일)
        if filename.endswith('.xlsx'):
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif filename.endswith('.xls'):
            mimetype = 'application/vnd.ms-excel'
        elif filename.endswith('.csv'):
            mimetype = 'text/csv'
        elif filename.endswith('.pdf'):
            mimetype = 'application/pdf'
        else:
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
        media = MediaIoBaseUpload(
            io.BytesIO(file_data),
            mimetype=mimetype,
            resumable=True
        )
        
        # 9. 파일 업로드
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink, webContentLink'
        ).execute()
        
        file_id = file.get('id')
        web_view_link = file.get('webViewLink', '')
        web_content_link = file.get('webContentLink', '')
        
        print(f"✅ 파일 업로드 성공: {filename} (ID: {file_id})")
        print(f"🔗 웹 보기 링크: {web_view_link}")
        
        # 10. 공유 설정 (누구나 링크로 볼 수 있도록)
        try:
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            service.permissions().create(
                fileId=file_id,
                body=permission
            ).execute()
            print(f"✅ 공유 설정 완료: {filename}")
        except HttpError as perm_error:
            print(f"⚠️ 공유 설정 실패 (무시, 파일은 업로드됨): {perm_error}")
        
        return {
            'success': True,
            'file_id': file_id,
            'file_url': web_content_link,
            'web_view_link': web_view_link,
            'message': f'파일 업로드 성공: {filename}'
        }
        
    except HttpError as error:
        print(f"💥 Google Drive API 오류: {error}")
        return {
            'success': False,
            'file_id': None,
            'file_url': None,
            'web_view_link': None,
            'message': f'Google Drive API 오류: {error}'
        }
    except Exception as e:
        print(f"💥 정산 엑셀 파일 업로드 전체 오류: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'file_id': None,
            'file_url': None,
            'web_view_link': None,
            'message': f'정산 엑셀 파일 업로드 실패: {str(e)}'
        }

