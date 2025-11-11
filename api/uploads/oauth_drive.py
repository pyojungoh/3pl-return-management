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
SCOPES = ['https://www.googleapis.com/auth/drive']
MAIN_FOLDER_ID = os.environ.get('GOOGLE_DRIVE_MAIN_FOLDER_ID', '1KiirgG6NkMI0XsLL6P9N88OB9QCPucbn')

# OAuth 2.0 토큰 파일 경로
TOKEN_FILE = os.path.join(os.path.dirname(__file__), '../../token.pickle')
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), '../../credentials.json')


def get_credentials():
    """
    OAuth 2.0을 사용하여 사용자 계정 인증 정보 가져오기
    """
    creds = None
    
    # 기존 토큰 파일이 있으면 로드
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
                creds = None
        
        # 토큰이 없으면 OAuth 2.0 플로우 시작
        if not creds:
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
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
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

