# 텔레그램 채팅방 ID 확인 가이드

## 봇 토큰
```
8518398236:AAEoGt4D_hwDa26cghbd3n4Lxcyra4xzgrg
```

## 방법 1: 웹 브라우저로 확인 (가장 쉬움)

### 단계별 안내

1. **텔레그램에서 그룹 생성 및 봇 추가**
   - 텔레그램 앱에서 새 그룹 생성
   - 그룹 이름: "스케쥴 알림" (원하는 이름)
   - 봇을 그룹에 추가 (멤버 추가 → 봇 사용자명 검색)

2. **봇에게 메시지 전송**
   - 그룹 채팅에서 봇에게 아무 메시지나 전송
   - 예: "테스트", "안녕", "/start" 등

3. **브라우저에서 URL 열기**
   ```
   https://api.telegram.org/bot8518398236:AAEoGt4D_hwDa26cghbd3n4Lxcyra4xzgrg/getUpdates
   ```

4. **JSON 응답에서 채팅방 ID 찾기**
   - 브라우저에 JSON 데이터가 표시됨
   - `"chat"` 객체 안의 `"id"` 값 확인
   - 예: `"id": -1001234567890`

## 방법 2: Python 스크립트로 확인

아래 스크립트를 실행하면 채팅방 ID를 찾을 수 있습니다:

```python
import requests

BOT_TOKEN = "8518398236:AAEoGt4D_hwDa26cghbd3n4Lxcyra4xzgrg"

# getUpdates 호출
url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
response = requests.get(url)
data = response.json()

print("=== 채팅방 ID 찾기 ===\n")

if data.get('ok'):
    results = data.get('result', [])
    if results:
        print("발견된 채팅방:")
        for update in results:
            if 'message' in update:
                chat = update['message'].get('chat', {})
                chat_id = chat.get('id')
                chat_type = chat.get('type')
                chat_title = chat.get('title', chat.get('first_name', '개인 채팅'))
                
                print(f"  - 채팅방 ID: {chat_id}")
                print(f"    타입: {chat_type}")
                print(f"    이름: {chat_title}")
                print()
    else:
        print("아직 메시지가 없습니다.")
        print("\n다음 단계:")
        print("1. 텔레그램 그룹에서 봇에게 메시지를 보내세요")
        print("2. 그 다음 이 스크립트를 다시 실행하세요")
else:
    print(f"오류: {data.get('description', '알 수 없는 오류')}")
```

## 방법 3: 간단한 테스트 봇 사용

1. 텔레그램에서 `@userinfobot` 검색
2. 그룹에 `@userinfobot` 초대
3. 그룹에서 `/start` 입력
4. 봇이 그룹 정보 표시 (채팅방 ID 포함)

## 방법 4: 직접 API 호출 (curl)

터미널에서 실행:
```bash
curl https://api.telegram.org/bot8518398236:AAEoGt4D_hwDa26cghbd3n4Lxcyra4xzgrg/getUpdates
```

## 주의사항

- 그룹 채팅방 ID는 보통 음수입니다 (예: `-1001234567890`)
- 개인 채팅 ID는 양수입니다
- 봇에게 메시지를 보내지 않으면 `getUpdates`에 나타나지 않습니다
- 메시지를 보낸 후 `getUpdates`를 호출해야 합니다


