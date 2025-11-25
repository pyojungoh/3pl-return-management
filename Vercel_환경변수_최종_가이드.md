# Vercel 환경 변수 등록 최종 가이드

## ✅ 완전 분리된 봇 사용

C/S 알림과 스케쥴 알림은 **완전히 별도의 봇과 채팅방**을 사용합니다.

## 📋 등록할 환경 변수

### C/S 알림용 (기존)
- `TELEGRAM_BOT_TOKEN`: C/S 알림 봇 토큰
- `TELEGRAM_CHAT_ID`: C/S 알림 채팅방 ID

### 스케쥴 알림용 (신규 추가)
- `TELEGRAM_SCHEDULE_BOT_TOKEN`: `8518398236:AAEoGt4D_hwDa26cghbd3n4Lxcyra4xzgrg`
- `TELEGRAM_SCHEDULE_CHAT_ID`: `-5004696157`

## 🔧 Vercel 등록 단계

### 1. Vercel 대시보드 접속
1. https://vercel.com 접속
2. 로그인
3. 프로젝트 선택

### 2. 스케쥴 전용 봇 토큰 추가
1. **Settings** 탭 클릭
2. 왼쪽 메뉴에서 **"Environment Variables"** 클릭
3. 새 환경 변수 추가:
   - **Key**: `TELEGRAM_SCHEDULE_BOT_TOKEN`
   - **Value**: `8518398236:AAEoGt4D_hwDa26cghbd3n4Lxcyra4xzgrg`
   - **Environment**: ✅ Production, ✅ Preview, ✅ Development
   - **Add** 클릭

### 3. 스케쥴 전용 채팅방 ID 추가
1. 같은 페이지에서 계속
2. 새 환경 변수 추가:
   - **Key**: `TELEGRAM_SCHEDULE_CHAT_ID`
   - **Value**: `-5004696157`
   - **Environment**: ✅ Production, ✅ Preview, ✅ Development
   - **Add** 클릭

### 4. 배포
환경 변수 저장 후 자동으로 재배포되거나, 수동으로 재배포:
- **Deployments** 탭 → 최신 배포의 **"..."** 메뉴 → **"Redeploy"**

## ✅ 최종 환경 변수 목록

```
# C/S 알림용 (기존)
TELEGRAM_BOT_TOKEN = [C/S 알림 봇 토큰]
TELEGRAM_CHAT_ID = [C/S 알림 채팅방 ID]

# 스케쥴 알림용 (신규)
TELEGRAM_SCHEDULE_BOT_TOKEN = 8518398236:AAEoGt4D_hwDa26cghbd3n4Lxcyra4xzgrg
TELEGRAM_SCHEDULE_CHAT_ID = -5004696157
```

## 🧪 테스트

배포 완료 후:
1. API 테스트 엔드포인트 호출:
   ```
   POST https://your-domain.vercel.app/api/schedule-notifications/test
   ```
2. 텔레그램 그룹 "jjay 스케줄"에서 메시지 확인

## ⚠️ 중요 사항

- **C/S 알림 봇**과 **스케쥴 알림 봇**은 완전히 분리되어 있습니다
- 각각 다른 그룹에 메시지를 보냅니다
- 하나의 봇에 문제가 생겨도 다른 봇은 정상 작동합니다


