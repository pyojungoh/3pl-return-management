"""
헤더 배너 API 직접 테스트
실제 Flask 앱을 실행하지 않고 함수만 테스트
"""
import sys
import os

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.database.models import create_header_banner, get_all_header_banners, get_active_header_banners

print("=" * 50)
print("헤더 배너 API 테스트")
print("=" * 50)

# 테스트 데이터
test_data = {
    'text': '테스트 테스트 테스트 테스트 테스트 테스트 테스트 테스트 테스트 테스트 테스트 테스트 테스트 테스트 테스트 테스트',
    'link_type': 'none',
    'board_post_id': None,
    'is_active': True,
    'display_order': 0,
    'text_color': '#2d3436',
    'bg_color': '#fff9e6'
}

print("\n1. 배너 생성 테스트")
print(f"입력 데이터: {test_data}")
try:
    banner_id = create_header_banner(test_data)
    if banner_id and banner_id > 0:
        print(f"✅ 배너 생성 성공! ID: {banner_id}")
    else:
        print(f"❌ 배너 생성 실패 (ID: {banner_id})")
except Exception as e:
    print(f"❌ 배너 생성 중 예외 발생: {e}")
    import traceback
    traceback.print_exc()

print("\n2. 모든 배너 조회 테스트")
try:
    banners = get_all_header_banners()
    print(f"✅ 배너 조회 성공! 총 {len(banners)}개")
    if banners:
        print(f"   첫 번째 배너: {banners[0]}")
except Exception as e:
    print(f"❌ 배너 조회 중 예외 발생: {e}")
    import traceback
    traceback.print_exc()

print("\n3. 활성 배너 조회 테스트")
try:
    active_banners = get_active_header_banners()
    print(f"✅ 활성 배너 조회 성공! 총 {len(active_banners)}개")
    if active_banners:
        print(f"   첫 번째 활성 배너: {active_banners[0]}")
except Exception as e:
    print(f"❌ 활성 배너 조회 중 예외 발생: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 50)

