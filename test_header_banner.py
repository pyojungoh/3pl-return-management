"""
헤더 배너 생성 테스트 스크립트
"""
from api.database.models import create_header_banner, get_all_header_banners

# 테스트 데이터
test_banner = {
    'text': '테스트 배너입니다',
    'link_type': 'none',
    'board_post_id': None,
    'is_active': True,
    'display_order': 0,
    'text_color': '#2d3436',
    'bg_color': '#fff9e6'
}

print("배너 생성 테스트 시작...")
try:
    banner_id = create_header_banner(test_banner)
    if banner_id:
        print(f"✅ 배너 생성 성공! ID: {banner_id}")
        
        # 조회 테스트
        banners = get_all_header_banners()
        print(f"✅ 배너 조회 성공! 총 {len(banners)}개")
        if banners:
            print(f"   첫 번째 배너: {banners[0]}")
    else:
        print("❌ 배너 생성 실패 (ID가 0 반환)")
except Exception as e:
    print(f"❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()

