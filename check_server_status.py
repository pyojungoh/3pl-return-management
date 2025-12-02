"""
서버 상태 확인 및 헤더 배너 API 테스트
"""
import requests
import json

base_url = "http://localhost:5000"

print("=" * 50)
print("서버 상태 확인 및 헤더 배너 API 테스트")
print("=" * 50)

# 1. 서버 연결 확인
print("\n1. 서버 연결 확인")
try:
    response = requests.get(f"{base_url}/", timeout=5)
    print(f"✅ 서버 연결 성공 (상태 코드: {response.status_code})")
except requests.exceptions.ConnectionError:
    print("❌ 서버가 실행 중이지 않습니다!")
    print("   서버를 시작해주세요: python app.py")
    exit(1)
except Exception as e:
    print(f"❌ 서버 연결 오류: {e}")
    exit(1)

# 2. 헤더 배너 조회 테스트
print("\n2. 헤더 배너 조회 테스트 (GET /api/header-banners/)")
try:
    response = requests.get(f"{base_url}/api/header-banners/", timeout=5)
    print(f"   상태 코드: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 조회 성공: {data.get('count', 0)}개")
        if data.get('data'):
            print(f"   첫 번째 배너: {data['data'][0]}")
    else:
        print(f"❌ 조회 실패: {response.text}")
except Exception as e:
    print(f"❌ 조회 오류: {e}")

# 3. 활성 배너 조회 테스트
print("\n3. 활성 배너 조회 테스트 (GET /api/header-banners/active)")
try:
    response = requests.get(f"{base_url}/api/header-banners/active", timeout=5)
    print(f"   상태 코드: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 조회 성공: {data.get('count', 0)}개")
    else:
        print(f"❌ 조회 실패: {response.text}")
except Exception as e:
    print(f"❌ 조회 오류: {e}")

# 4. 배너 생성 테스트
print("\n4. 배너 생성 테스트 (POST /api/header-banners/)")
test_data = {
    'text': 'API 테스트 배너',
    'link_type': 'none',
    'board_post_id': None,
    'is_active': True,
    'display_order': 0,
    'text_color': '#2d3436',
    'bg_color': '#fff9e6'
}
try:
    response = requests.post(
        f"{base_url}/api/header-banners/",
        json=test_data,
        headers={'Content-Type': 'application/json'},
        timeout=5
    )
    print(f"   상태 코드: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 생성 성공: {data.get('message', '')}")
        if data.get('id'):
            print(f"   생성된 ID: {data['id']}")
    else:
        print(f"❌ 생성 실패: {response.text}")
except Exception as e:
    print(f"❌ 생성 오류: {e}")

print("\n" + "=" * 50)

