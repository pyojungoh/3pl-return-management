# 로고 Cloudinary 업로드 가이드

## Cloudinary에 로고 업로드하기

### 방법 1: Cloudinary 대시보드에서 직접 업로드 (권장)

1. **Cloudinary 대시보드 접속**
   - https://console.cloudinary.com 접속
   - 로그인

2. **Media Library로 이동**
   - 좌측 메뉴에서 "Media Library" 클릭

3. **폴더 생성 (선택사항)**
   - "logo" 폴더 생성 (관리 편의)

4. **로고 업로드**
   - "Upload" 버튼 클릭
   - 로고 파일 선택 (PNG 또는 SVG, 투명 배경)
   - 파일명: `logo.png` 또는 `logo.svg`
   - Public ID: `logo/logo` (폴더/파일명 형식)

5. **업로드 완료 후 URL 복사**
   - 업로드된 이미지 클릭
   - "URL" 또는 "Secure URL" 복사
   - 예: `https://res.cloudinary.com/dokk81rjh/image/upload/v1234567890/logo/logo.png`

### 방법 2: 코드에서 자동 업로드

로고 파일을 `static/logo.png`에 넣고 다음 스크립트 실행:

```python
# upload_logo_to_cloudinary.py
from api.uploads.cloudinary_upload import upload_single_file_to_cloudinary
import base64

# 로고 파일 읽기
with open('static/logo.png', 'rb') as f:
    file_data = f.read()
    base64_data = base64.b64encode(file_data).decode('utf-8')

# Cloudinary에 업로드
url = upload_single_file_to_cloudinary(
    base64_data=f'data:image/png;base64,{base64_data}',
    filename='logo.png',
    folder='logo'
)

print(f"✅ 로고 업로드 완료!")
print(f"🔗 URL: {url}")
print(f"\n이 URL을 dashboard_server.html의 logoUrl 변수에 설정하세요.")
```

## 로고 URL 설정

### 1. Cloudinary URL 사용 (권장)

`dashboard_server.html` 파일에서 로고 URL 설정:

```javascript
// 로고 URL 설정 (Cloudinary)
const logoUrl = 'https://res.cloudinary.com/dokk81rjh/image/upload/v1/logo/logo.png';
```

### 2. 로컬 파일 사용

```javascript
// 로고 URL 설정 (로컬)
const logoUrl = '/static/logo.png';
```

### 3. 환경 변수 사용 (배포 시)

환경 변수로 관리하려면:

```javascript
// 환경 변수에서 가져오기 (서버에서 설정 필요)
const logoUrl = window.LOGO_URL || 'https://res.cloudinary.com/dokk81rjh/image/upload/v1/logo/logo.png';
```

## 로고 파일 요구사항

### 파일 형식
- **권장**: PNG (투명 배경)
- **대안**: SVG (벡터 형식)
- **비권장**: JPG (투명 배경 불가)

### 파일 크기
- **권장**: 200x200px ~ 400x400px (정사각형)
- **최소**: 120x120px
- **최대**: 800x800px

### 배경
- **투명 배경 필수** (PNG with alpha channel)

### 색상 권장사항
- 흰색 또는 밝은 색상 (오렌지 배경과 대비)
- 또는 오렌지 계열 색상 (그라데이션과 조화)

## Cloudinary URL 형식

업로드 후 받은 URL 형식:
```
https://res.cloudinary.com/{cloud_name}/image/upload/{version}/{folder}/{filename}.{ext}
```

예시:
```
https://res.cloudinary.com/dokk81rjh/image/upload/v1234567890/logo/logo.png
```

## 이미지 최적화 옵션

Cloudinary URL에 변환 옵션 추가 가능:

### 크기 조정
```
https://res.cloudinary.com/dokk81rjh/image/upload/w_200,h_200,c_fit/logo/logo.png
```

### 자동 포맷
```
https://res.cloudinary.com/dokk81rjh/image/upload/f_auto/logo/logo.png
```

### 품질 조정
```
https://res.cloudinary.com/dokk81rjh/image/upload/q_auto/logo/logo.png
```

## 확인 방법

1. Cloudinary에 로고 업로드
2. URL 복사
3. `dashboard_server.html`의 `logoUrl` 변수에 설정
4. 브라우저에서 로그인 페이지 확인
5. 로고가 표시되는지 확인

## 문제 해결

### 로고가 표시되지 않을 때
1. URL이 올바른지 확인
2. Cloudinary에서 이미지가 공개 설정인지 확인
3. 브라우저 콘솔에서 에러 확인
4. 로고가 없으면 자동으로 "JJ" 텍스트 표시

### CORS 오류
- Cloudinary는 기본적으로 CORS를 지원하므로 문제 없음
- 만약 문제가 있다면 Cloudinary 설정에서 CORS 활성화 확인

