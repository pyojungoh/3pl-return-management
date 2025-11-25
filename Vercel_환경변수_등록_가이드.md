# Vercel 환경 변수 등록 가이드

## 현재 상황
- **새로운 봇 토큰**: `8518398236:AAEoGt4D_hwDa26cghbd3n4Lxcyra4xzgrg`
- **채팅방 ID**: `-5004696157`
- **채팅방 이름**: "jjay 스케줄"

## Vercel에 등록할 환경 변수

### 옵션 1: 같은 봇 사용 (기존 봇 토큰 유지)
기존 C/S 알림과 같은 봇을 사용하는 경우:

1. **TELEGRAM_BOT_TOKEN** (기존 유지)
   - Value: 기존 봇 토큰
   - Environment: Production, Preview, Development

2. **TELEGRAM_SCHEDULE_CHAT_ID** (신규 추가)
   - Value: `-5004696157`
   - Environment: Production, Preview, Development

### 옵션 2: 별도 봇 사용 (새로운 봇 토큰)
스케쥴 전용 봇을 사용하는 경우:

1. **TELEGRAM_SCHEDULE_BOT_TOKEN** (신규 추가)
   - Value: `8518398236:AAEoGt4D_hwDa26cghbd3n4Lxcyra4xzgrg`
   - Environment: Production, Preview, Development

2. **TELEGRAM_SCHEDULE_CHAT_ID** (신규 추가)
   - Value: `-5004696157`
   - Environment: Production, Preview, Development

3. **TELEGRAM_BOT_TOKEN** (기존 유지 - C/S 알림용)
   - Value: 기존 C/S 알림용 봇 토큰
   - Environment: Production, Preview, Development

## Vercel 등록 단계

### 1. Vercel 대시보드 접속
1. https://vercel.com 접속
2. 로그인
3. 프로젝트 선택

### 2. 환경 변수 추가
1. **Settings** 탭 클릭
2. 왼쪽 메뉴에서 **"Environment Variables"** 클릭
3. 환경 변수 추가:

#### 옵션 1인 경우:
- Key: `TELEGRAM_SCHEDULE_CHAT_ID`
- Value: `-5004696157`
- Environment: ✅ Production, ✅ Preview, ✅ Development
- **Add** 클릭

#### 옵션 2인 경우:
- Key: `TELEGRAM_SCHEDULE_BOT_TOKEN`
- Value: `8518398236:AAEoGt4D_hwDa26cghbd3n4Lxcyra4xzgrg`
- Environment: ✅ Production, ✅ Preview, ✅ Development
- **Add** 클릭

- Key: `TELEGRAM_SCHEDULE_CHAT_ID`
- Value: `-5004696157`
- Environment: ✅ Production, ✅ Preview, ✅ Development
- **Add** 클릭

### 3. 배포
환경 변수 저장 후 자동으로 재배포되거나, 수동으로 재배포:
- **Deployments** 탭 → 최신 배포의 **"..."** 메뉴 → **"Redeploy"**

## 확인 방법

배포 완료 후 테스트:
1. API 테스트 엔드포인트 호출:
   ```
   POST https://your-domain.vercel.app/api/schedule-notifications/test
   ```
2. 텔레그램 그룹 "jjay 스케줄"에서 메시지 확인

## 권장사항

**옵션 2 (별도 봇 사용)를 권장합니다:**
- C/S 알림과 스케쥴 알림을 완전히 분리
- 각각 독립적으로 관리 가능
- 하나의 봇에 문제가 생겨도 다른 봇은 정상 작동


