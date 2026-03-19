# C/S 알림 반복 실패 - 정밀 원인 분석

## 증상
- **취소건**: 1분마다 알림 예정 → **1번만 오고 중단**
- **일반건**: 5분마다 알림 예정 → **1번만 오고 중단**
- cron-job.org는 1분마다 정상 호출됨 (History 확인)

---

## 1. 데이터 흐름

```
cron-job.org (1분마다)
    → GET/POST /api/cs/check-notifications
    → send_cs_notifications()
    → get_pending_cs_requests_by_issue_type('취소') / get_pending_cs_requests()
    → last_notification_at 비교
    → 조건 만족 시 send_telegram_notification() + update_cs_last_notification()
```

---

## 2. 의심 원인 (우선순위순)

### 2-1. PostgreSQL 타임존 변환 오류 (가장 유력)

**문제**: `current_time`(KST)을 DB에 저장할 때 psycopg2가 UTC로 변환하여 저장

**동작**:
1. `current_time = datetime.now(kst)` → 11:13 KST (02:13 UTC)
2. `update_cs_last_notification(cs_id, current_time)` 호출
3. psycopg2가 timezone-aware datetime을 TIMESTAMP WITHOUT TIME ZONE에 저장 시 **UTC로 변환**
4. DB에 **02:13** (UTC) 저장
5. 다음 요청 시 `SELECT *` → **02:13** (naive) 반환
6. `parse_datetime_for_compare(02:13)` → **02:13 KST**로 해석 (replace tzinfo=kst)
7. `current_time` = 11:14 KST
8. `time_diff = (11:14 KST - 02:13 KST).total_seconds()` = **약 32,400초 (9시간)**

**결과**: time_diff가 9시간이므로 **매번 알림 전송**되어야 함

→ 이 경우 "1번만 온다"와 **모순**됨. 따라서 **반대 시나리오** 가능성:

**반대 시나리오 (시간이 미래로 해석되는 경우)**:
1. 저장: 02:13 UTC
2. 조회 시 connection timezone이 Asia/Seoul이면 → 11:13 반환
3. 또는 **서버 시간이 9시간 앞서** 있으면 → 11:13 KST 저장 시 20:13 UTC로 저장됨
4. 다음 요청 시 20:13 조회 → 20:13 KST로 해석
5. current_time = 11:14 KST
6. `last_time(20:13 KST) > current_time(11:14 KST)` → **time_diff 음수**
7. `time_diff < 60` → **True** (음수는 60 미만)
8. **continue** → 알림 스킵!

**결론**: 타임존/서버 시간 불일치로 `last_time`이 `current_time`보다 **미래**로 해석되면, 매번 스킵되어 "1번만 온다"와 일치함.

---

### 2-2. RealDictCursor 컬럼명 대소문자

PostgreSQL은 기본적으로 컬럼명을 **소문자**로 반환.
- `cs.get('last_notification_at')` → 정상
- `cs.get('Last_Notification_At')` → None (대소문자 다르면)

→ 확인 필요: `get_pending_cs_requests`가 `last_notification_at`을 제대로 반환하는지

---

### 2-3. update_cs_last_notification 실패

- UPDATE 실패 시 `last_notification_at`이 갱신되지 않음
- 다음 요청 시 `last_notification_at` = None → **매번 첫 알림 로직** → 매번 전송
- "1번만 온다"와 **불일치**

→ UPDATE 실패 시나리오는 배제

---

### 2-4. cs_id 타입 불일치

- `cs_id = cs.get('id', '')` → `''`가 될 수 있음
- `update_cs_last_notification('', current_time)` → `WHERE id = ''` → **0 rows updated**
- 다음 요청 시 `last_notification_at` = None → 매번 전송

→ 취소건 루프에서 `cs_id = cs.get('id', '')`로 **덮어쓰기**함 (139행)
```python
cs_id = cs.get('id', '')  # 메시지용 - 하지만 update에도 전달됨!
update_cs_last_notification(cs_id, current_time)  # cs_id가 ''일 수 있음
```

- `cs.get('id', '')`에서 id가 0이면 `0` 반환 (정상)
- id가 None이면 `''` 반환 → **UPDATE 실패** (id가 빈 문자열)

**확인**: 117행에서 `if not cs_id: continue`로 이미 필터링됨. `cs_id`가 0이면 `continue`되지만, 0은 유효한 id가 아님. 일반적으로 id는 1 이상.

---

### 2-5. DB 컬럼 부재

- `last_notification_at`이 테이블에 없으면 SELECT 시 None
- ALTER TABLE은 init_db에서 실행됨
- 배포 DB에 init_db가 아직 안 돌았을 수 있음

→ `init_db`는 lazy loading으로 첫 요청 시 실행. 첫 알림이 1번 온다면 DB는 정상 동작 중.

---

## 3. 수정 방안

### 3-1. 타임존 저장 방식 통일 (핵심)

**저장 시**: KST 기준 **naive datetime**으로 저장

```python
# 저장 전 naive로 변환 (KST 시간값만 유지)
naive_time = current_time.replace(tzinfo=None) if current_time.tzinfo else current_time
update_cs_last_notification(cs_id, naive_time)
```

- psycopg2가 UTC로 변환하지 않음
- 11:13 KST → 11:13으로 저장
- 조회 시 11:13 반환 → KST로 해석 → 비교 정확

### 3-2. 상세 디버그 로그

- `last_notification_at` 원시값
- `parse_datetime_for_compare` 결과
- `time_diff` 값
- 스킵/전송 결정 사유

### 3-3. cs_id 전달 검증

- `update_cs_last_notification` 호출 직전에 `cs_id`가 정수인지 확인
- 메시지용 `cs_id`와 UPDATE용 `cs_id` 변수 분리

---

## 4. 결론

**가장 유력한 원인**: PostgreSQL/psycopg2의 timezone-aware datetime 저장 시 UTC 변환으로 인해, `last_notification_at`이 **비교 기준보다 미래**로 해석되어 매번 스킵되는 경우.

**권장 조치**: 저장 시 **naive datetime (KST)** 사용 + 상세 디버그 로그 추가.
