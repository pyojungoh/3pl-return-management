# 🔄 Google Apps Script → Flask 서버 마이그레이션 가이드

## 📌 변경 사항

### 이전 (Google Apps Script)
- `clasp push` 필요
- `Code.js` 파일 사용
- `dashboard.html` 파일 사용
- Google Apps Script 웹앱으로 배포

### 현재 (Flask 서버)
- `clasp push` **불필요**
- `server_new.py` 파일 사용
- `dashboard_server.html` 파일 사용
- Vercel/Railway로 배포

## 🚫 더 이상 하지 않아야 할 것

1. ❌ `clasp push` 실행
2. ❌ Google Apps Script 편집기에서 코드 수정
3. ❌ Google Apps Script 웹앱 버전 관리

## ✅ 새로운 작업 흐름

1. ✅ 로컬에서 `server_new.py` 수정
2. ✅ GitHub에 푸시
3. ✅ Vercel/Railway 자동 배포

## 📁 파일 구조

```
프로젝트/
├── server_new.py          # Flask 서버 (새로 사용)
├── dashboard_server.html  # 프론트엔드 (새로 사용)
├── api/                   # API 엔드포인트
│   ├── auth/             # 로그인 API
│   └── returns/          # 반품 데이터 API
├── Code.js               # 기존 파일 (백업용)
├── dashboard.html        # 기존 파일 (백업용)
└── .clasp.json          # 더 이상 사용 안 함
```

## 🔄 마이그레이션 체크리스트

- [ ] Google 서비스 계정 설정
- [ ] Google Sheets에 서비스 계정 공유
- [ ] Flask 서버 로컬 테스트
- [ ] GitHub에 코드 푸시
- [ ] Vercel/Railway 배포
- [ ] 환경 변수 설정
- [ ] 배포된 서버 테스트
- [ ] 기존 Google Apps Script 백업 (선택)

## 💡 기존 코드 보관

기존 Google Apps Script 코드는 백업으로 보관하세요:
- `Code.js`: 백업 보관
- `dashboard.html`: 백업 보관
- 필요시 다시 사용 가능

## 🎯 다음 단계

1. **Google 서비스 계정 설정** (위의 DEPLOYMENT_GUIDE.md 참조)
2. **로컬 테스트** 실행
3. **GitHub에 푸시**
4. **Vercel/Railway 배포**

## ❓ 질문

**Q: 기존 Google Apps Script는 삭제해도 되나요?**
A: 아니요, 백업으로 보관하세요. 새로운 서버가 안정적으로 작동하는지 확인한 후에 삭제하세요.

**Q: `clasp push`를 실행하면 어떻게 되나요?**
A: Google Apps Script에 코드가 업데이트되지만, 새로운 Flask 서버와는 무관합니다. 실행하지 않아도 됩니다.

**Q: 두 시스템을 동시에 사용할 수 있나요?**
A: 가능하지만 권장하지 않습니다. 하나의 시스템만 사용하는 것이 좋습니다.

