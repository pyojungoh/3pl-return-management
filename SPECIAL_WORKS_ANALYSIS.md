# 특수작업 메뉴 전체 구조 및 기능 분석

## 📋 파일 구조
- **프론트엔드**: `special_works.html` (3264줄)
- **백엔드 API**: `api/special_works/routes_db.py` (911줄)

---

## 🔑 핵심 전역 변수

```javascript
var swCurrentRole = '';           // 현재 사용자 역할 (관리자/화주사)
var swCurrentCompany = '';        // 현재 화주사명
var swCurrentUsername = '';       // 현재 사용자명
var swWorkTypes = [];             // 작업 종류 목록
var swSelectedWorkType = null;    // 선택된 작업 종류 필터
var swSelectedCompany = null;     // 선택된 화주사 필터 ⚠️ 사용됨
var swSelectedPhotos = [];        // 등록 폼 선택된 사진
var swEditSelectedPhotos = [];    // 수정 모달 선택된 사진
var swEditExistingPhotos = [];    // 수정 모달 기존 사진
var swInitialized = false;        // 초기화 여부
var swWorkEntryCounter = 0;       // 작업 항목 카운터 (등록 폼)
var swEditWorkEntryCounter = 0;   // 작업 항목 카운터 (수정 모달)
```

---

## 🏗️ 주요 HTML 구조

### 1. 관리자 전용 섹션 (`.sw-admin-only`)
- **작업 종류 관리** (`#swAdminWorkTypeSection`)
  - 작업 종류 목록 표시
  - 작업 종류 추가/수정/삭제
- **작업 등록** (`#swAdminWorkRegistrationSection`)
  - 화주사 선택 (검색 가능한 드롭다운)
  - 작업 일자 선택
  - 동적 작업 항목 추가/삭제
  - 사진 업로드
  - 메모 입력
- **필터 섹션** (`#swAdminFilterSection`)
  - 월 필터
  - 작업 종류 필터
  - 화주사 필터
- **화주사별 통계** (`#swAdminCompanyStatsSection`)
  - 화주사별 작업 건수 및 총액 표시
  - 클릭 시 필터링

### 2. 화주사 전용 섹션 (`.sw-consignor-only`)
- **필터 섹션** (`#swConsignorFilterSection`)
  - 월 필터만

### 3. 공통 섹션
- **작업 종류별 통계** (`#swCommonStatsSection`)
  - 작업 종류별 건수 및 총액
  - 클릭 시 필터링
- **작업 목록 테이블** (`#swCommonTableSection`)
  - 관리자: 화주사 컬럼 + 관리 컬럼 포함
  - 화주사: 화주사 컬럼 제외

### 4. 수정 모달 (`#swEditWorkModal`)
- 화주사 선택
- 작업 일자
- 동적 작업 항목 추가/삭제
- 사진 관리 (기존 + 신규)
- 메모

---

## 🔧 주요 JavaScript 함수 목록

### 공통 함수 (swCommon*)
1. **swCommonInit()** - 초기화 함수 (가장 중요!)
   - 역할 확인 (헤더 또는 전역 변수)
   - 가시성 제어
   - 모드별 초기화 함수 호출
2. **swApplyVisibility()** - 관리자/화주사 섹션 표시/숨김
3. **swGetUserHeaders()** - API 요청용 헤더 생성
4. **swEscapeHtml()** - XSS 방지
5. **swFormatNumber()** - 숫자 포맷팅
6. **swCommonLoadWorkTypes()** - 작업 종류 목록 로드
7. **swFilterByWorkType()** - 작업 종류 필터링
8. **swViewPhoto()** - 사진 보기

### 관리자 함수 (swAdmin*)

#### 초기화 및 로드
- **swAdminInit()** - 관리자 모드 초기화
- **swAdminLoadCompanies()** - 화주사 목록 로드
- **swAdminLoadWorks()** - 작업 목록 로드
- **swAdminRenderWorks()** - 작업 목록 렌더링

#### 작업 종류 관리
- **swAdminToggleWorkTypeManagement()** - 작업 종류 관리 토글
- **swAdminUpdateWorkTypeList()** - 작업 종류 목록 업데이트
- **swAdminUpdateWorkTypeSelects()** - 작업 종류 드롭다운 업데이트
- **swAdminShowAddWorkTypeModal()** - 작업 종류 추가 모달
- **swAdminShowAddWorkTypeModalFromForm()** - 폼에서 작업 종류 추가
- **swAdminEditWorkType()** - 작업 종류 수정
- **swAdminDeleteWorkType()** - 작업 종류 삭제

#### 작업 등록
- **swAdminToggleWorkRegistration()** - 작업 등록 폼 토글
- **swAdminAddWorkEntry()** - 작업 항목 추가
- **swAdminRemoveWorkEntry()** - 작업 항목 제거
- **swAdminUpdateEntryPrice()** - 작업 종류 선택 시 단가 업데이트
- **swAdminUpdateEntryTotal()** - 작업 항목 총액 계산
- **swAdminUpdateAllTotal()** - 전체 총액 계산
- **swAdminHandlePhotoSelect()** - 사진 선택 처리
- **swAdminRenderPhotoPreviews()** - 사진 미리보기 렌더링
- **swAdminRemovePhoto()** - 사진 제거
- **swAdminResetWorkForm()** - 폼 초기화
- **swAdminHandleWorkSubmit()** - 작업 등록 처리 (배치)

#### 작업 수정
- **swAdminEditWorkGroup()** - 작업 그룹 수정 (첫 번째 작업만)
- **swAdminEditWorkGroupData()** - 작업 그룹 데이터 로드 (모든 작업 항목)
- **swAdminEditWork()** - 단일 작업 수정 (레거시 호환)
- **swAdminAddEditWorkEntry()** - 수정 모달 작업 항목 추가
- **swAdminRemoveEditWorkEntry()** - 수정 모달 작업 항목 제거
- **swAdminUpdateEditEntryPrice()** - 수정 모달 단가 업데이트
- **swAdminUpdateEditEntryTotal()** - 수정 모달 항목 총액 계산
- **swAdminUpdateEditAllTotal()** - 수정 모달 전체 총액 계산
- **swAdminHandleEditPhotoSelect()** - 수정 모달 사진 선택
- **swAdminRenderEditPhotoPreviews()** - 수정 모달 사진 미리보기
- **swAdminRemoveEditPhoto()** - 수정 모달 사진 제거
- **swAdminInitEditCompanyDropdown()** - 수정 모달 화주사 드롭다운 초기화
- **swAdminHandleEditWorkSubmit()** - 작업 수정 처리 (배치 업데이트)
- **swAdminCloseEditModal()** - 수정 모달 닫기

#### 작업 삭제
- **swAdminDeleteWorkGroup()** - 작업 그룹 삭제 (모든 작업)

#### 통계
- **swUpdateStats()** - 작업 종류별 통계 업데이트 (공통)
- **swUpdateCompanyStats()** - 화주사별 통계 업데이트 (관리자 전용)

### 화주사 함수 (swConsignor*)
- **swConsignorInit()** - 화주사 모드 초기화
- **swConsignorLoadWorks()** - 화주사 작업 목록 로드
- **swConsignorRenderWorks()** - 화주사 작업 목록 렌더링

---

## ⚠️ 발견된 문제점

### 1. 누락된 함수: `swFilterByCompany()`
- **위치**: 2255줄에서 호출되지만 정의되지 않음
- **기능**: 화주사별 통계 박스 클릭 시 필터링
- **영향**: 화주사별 통계 박스 클릭 시 오류 발생

### 2. 화주사별 통계 기능 부족
- "전체" 옵션이 없음
- 선택 시 다른 박스가 사라지지 않음 (현재는 문제 없을 수 있음)
- 박스 내용 정렬 확인 필요

### 3. 전체 데이터 로드 로직
- 화주사별 통계는 전체 데이터 기반으로 계산되어야 함
- 현재는 필터된 데이터만 사용 중

---

## 🔗 API 엔드포인트

### 작업 종류 관련
- `GET /api/special-works/types` - 작업 종류 목록 조회
- `POST /api/special-works/types` - 작업 종류 생성
- `PUT /api/special-works/types/<id>` - 작업 종류 수정
- `DELETE /api/special-works/types/<id>` - 작업 종류 삭제

### 작업 관련
- `GET /api/special-works/works` - 작업 목록 조회
- `POST /api/special-works/works` - 작업 등록 (단일)
- `POST /api/special-works/works/batch` - 작업 배치 등록 ⭐
- `GET /api/special-works/works/<id>` - 작업 상세 조회
- `PUT /api/special-works/works/<id>` - 작업 수정
- `DELETE /api/special-works/works/<id>` - 작업 삭제

---

## 📊 데이터 흐름

### 작업 등록 흐름
1. `swAdminHandleWorkSubmit()` 호출
2. 작업 항목 수집 (여러 개 가능)
3. 사진 업로드 (`/api/uploads/upload-images`)
4. 배치 등록 (`POST /api/special-works/works/batch`)
5. 성공 시 폼 초기화 및 목록 새로고침

### 작업 수정 흐름
1. `swAdminEditWorkGroup()` 호출
2. `swAdminEditWorkGroupData()` - 모든 작업 항목 로드
3. 수정 모달에 데이터 채우기
4. `swAdminHandleEditWorkSubmit()` 호출
5. 기존 작업 삭제
6. 새로운 작업 배치 등록

### 작업 목록 로드 흐름
1. `swAdminLoadWorks()` 또는 `swConsignorLoadWorks()` 호출
2. 필터 파라미터 수집 (월, 작업 종류, 화주사)
3. API 호출 (`GET /api/special-works/works`)
4. 데이터 그룹화 (같은 날짜/화주사/메모/사진)
5. 렌더링 (`swAdminRenderWorks()` 또는 `swConsignorRenderWorks()`)
6. 통계 업데이트 (`swUpdateStats()`, `swUpdateCompanyStats()`)

---

## 🎯 수정 시 주의사항

### 절대 수정 금지 영역
1. **초기화 함수들**
   - `swCommonInit()` - 전체 초기화 로직
   - `swAdminInit()` - 관리자 초기화
   - `swConsignorInit()` - 화주사 초기화
   - `swApplyVisibility()` - 가시성 제어

2. **API 통신 함수들**
   - `swGetUserHeaders()` - 헤더 생성
   - `swCommonLoadWorkTypes()` - 작업 종류 로드
   - `swAdminLoadWorks()` - 작업 목록 로드
   - `swConsignorLoadWorks()` - 화주사 작업 목록 로드

3. **렌더링 함수들**
   - `swAdminRenderWorks()` - 관리자 작업 목록 렌더링
   - `swConsignorRenderWorks()` - 화주사 작업 목록 렌더링
   - `swUpdateStats()` - 작업 종류별 통계
   - `swUpdateCompanyStats()` - 화주사별 통계

4. **작업 등록/수정 핵심 함수들**
   - `swAdminHandleWorkSubmit()` - 작업 등록 처리
   - `swAdminHandleEditWorkSubmit()` - 작업 수정 처리
   - `swAdminEditWorkGroupData()` - 작업 그룹 데이터 로드

### 수정 가능 영역 (신중하게)
1. UI 스타일 (CSS)
2. 새로운 기능 추가 (기존 함수 수정 금지)
3. 버그 수정 (기존 로직 유지)

---

## 🔍 주요 의존성

### 전역 변수 의존성
- `swWorkTypes` - 작업 종류 목록 (여러 함수에서 사용)
- `swSelectedWorkType` - 작업 종류 필터 (필터링에 사용)
- `swSelectedCompany` - 화주사 필터 (필터링에 사용) ⚠️
- `swCurrentRole` - 현재 역할 (가시성 제어에 사용)

### 함수 호출 체인
```
swCommonInit()
  ├─ swApplyVisibility()
  ├─ swAdminInit() (관리자일 때)
  │   ├─ swAdminLoadCompanies()
  │   ├─ swCommonLoadWorkTypes()
  │   └─ swAdminLoadWorks()
  │       └─ swAdminRenderWorks()
  │           ├─ swUpdateStats()
  │           └─ swUpdateCompanyStats()
  └─ swConsignorInit() (화주사일 때)
      ├─ swCommonLoadWorkTypes()
      └─ swConsignorLoadWorks()
          └─ swConsignorRenderWorks()
              └─ swUpdateStats()
```

---

## ✅ 수정 전 체크리스트

- [ ] 수정하려는 함수가 다른 함수에서 호출되는지 확인
- [ ] 전역 변수 사용 여부 확인
- [ ] API 엔드포인트 변경 여부 확인
- [ ] 초기화 함수 영향 여부 확인
- [ ] 렌더링 함수 영향 여부 확인
- [ ] 관리자/화주사 모드 구분 확인
- [ ] 테스트 시나리오 작성

---

## 📝 추가 구현 필요 사항

1. **swFilterByCompany() 함수 추가**
   - 화주사별 통계 박스 클릭 시 필터링
   - swSelectedCompany 변수 업데이트
   - swAdminLoadWorks() 호출

2. **화주사별 통계 개선**
   - "전체" 옵션 추가
   - 전체 데이터 로드 로직 추가
   - 박스 내용 왼쪽 정렬

---

## 🎨 UI 컴포넌트 구조

### 작업 항목 (`.sw-work-entry`)
- 작업 종류 선택
- 수량 입력
- 단가 입력
- 총액 계산 (자동)
- 삭제 버튼

### 통계 박스 (`.sw-stat-box`)
- 작업 종류별 통계
- 화주사별 통계 (관리자 전용)
- 클릭 시 필터링

### 테이블 구조
- 관리자: 10개 컬럼 (관리 컬럼 포함)
- 화주사: 9개 컬럼 (관리 컬럼 제외)
- 작업 그룹화 (같은 날짜/화주사/메모/사진)

---

이 문서는 특수작업 메뉴 수정 시 참고용으로 작성되었습니다.





