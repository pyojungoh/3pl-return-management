/*********************************************************
 * 📁 폴더명: configUI
 * 파일: configUI.gs
 * 목적: 설정 시트 UI/데이터 관리
 *  - (기존) 템플릿/드롭다운/체크박스/ON/OFF
 *  - (추가) A2 다중/접두 검색 파서 & 헬퍼
 **********************************************************/

// ──── ✅ (기존) 네가 준 코드: 그대로 유지 ────

//설정시트 검색 //
function createFilterSettingsTemplateHorizontal() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName("설정");
  if (!sheet) sheet = ss.insertSheet("설정");
  else sheet.clear();

  const headers = [
    "파레트 ID 검색어",    // A1
    "화주사 선택",         // B1
    "품목 키워드",         // C1
    "입고 시작일",         // D1
    "입고 종료일",         // E1
    "출력완료 포함 여부",   // F1
    "보관 상태 필터"        // G1
  ];

  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  sheet.getRange(1, 1, 1, headers.length).setFontWeight("bold").setBackground("#eeeeee");
  sheet.setFrozenRows(1);

  // ✅ 열 너비 넉넉하게 확보 (파레트 ID 검색어는 더 크게)
  sheet.setColumnWidth(1, 220); // A열
  for (let i = 2; i <= 7; i++) sheet.setColumnWidth(i, 160);

  // ✅ F2: 체크박스
  sheet.getRange(2, 6).insertCheckboxes();

  // ✅ 화주사 선택 구역 구성
  sheet.getRange("A5:G5").merge().setValue("화주사 선택").setFontWeight("bold").setBackground("#d9ead3").setHorizontalAlignment("center");
}

function updateFilterDropdowns() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const configSheet = ss.getSheetByName("설정");
  const sourceSheet = ss.getSheetByName("파레트 요약 정산");
  if (!configSheet || !sourceSheet) return;

  const data = sourceSheet.getDataRange().getValues();
  const header = data[0];
  const vendorIdx = header.indexOf("화주사");
  const statusIdx = header.indexOf("상태");

  const vendorSet = new Set();
  const statusSet = new Set(["전체"]);

  for (let i = 1; i < data.length; i++) {
    if (data[i][vendorIdx]) vendorSet.add(data[i][vendorIdx]);
    if (data[i][statusIdx]) statusSet.add(data[i][statusIdx]);
  }

  const vendorList = Array.from(vendorSet);
  const statusList = Array.from(statusSet);

  // ✅ 체크박스 영역 초기화
  const startRow = 6;
  const itemsPerColumn = 3;
  let col = 1;

  configSheet.getRange("A6:G20").clearContent().removeCheckboxes().setBorder(false, false, false, false, false, false);

  for (let i = 0; i < vendorList.length; i++) {
    const rowOffset = (i % itemsPerColumn) * 2;
    const row = startRow + rowOffset;
    const column = col + Math.floor(i / itemsPerColumn);

    const nameCell = configSheet.getRange(row, column);
    const checkboxCell = configSheet.getRange(row + 1, column);

    nameCell.setValue(vendorList[i]).setFontWeight("normal").setHorizontalAlignment("center").setBorder(true, true, true, true, false, false);
    checkboxCell.insertCheckboxes().setBorder(true, true, true, true, false, false);
  }

  // G2: 보관 상태 드롭다운
  const statusRule = SpreadsheetApp.newDataValidation().requireValueInList(statusList, true).build();
  configSheet.getRange("G2").setDataValidation(statusRule);

  // B2: 화주사 드롭다운
  const vendorDropdownRule = SpreadsheetApp.newDataValidation().requireValueInList(["전체"].concat(vendorList), true).build();
  configSheet.getRange("B2").setDataValidation(vendorDropdownRule);

  // ✅ 선택된 화주사만 B2 셀에 자동 입력 (쉼표 구분)
  const selectedVendors = [];
  for (let col = 1; col <= 7; col++) {
    for (let row = 6; row <= 20; row += 2) {
      const name = configSheet.getRange(row, col).getValue();
      const checked = configSheet.getRange(row + 1, col).getValue();
      if (name && checked === true) selectedVendors.push(name);
    }
  }
  configSheet.getRange("B2").setValue(selectedVendors.join(", "));
}

function getSelectedVendorsFromCheckboxes() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("설정");
  const selected = [];
  for (let col = 1; col <= 7; col++) {
    for (let row = 6; row <= 20; row += 2) {
      const name = sheet.getRange(row, col).getValue();
      const checked = sheet.getRange(row + 1, col).getValue();
      if (name && checked === true) selected.push(name);
    }
  }
  return selected;
}

// ✅ 외부에서 호출할 때 사용할 간편한 이름 (드롭다운 없이 체크박스만 기준)
function getFilterVendorList() {
  return getSelectedVendorsFromCheckboxes();
}

// ✅ ON/OFF (기존)
function setupAutoSyncButton() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("설정");
  if (!sheet) return;
  sheet.getRange("A18").setValue("자동화 ON/OFF").setFontWeight("bold").setBackground("#cfe2f3");
  sheet.getRange("A19").setValue("사용").setFontWeight("bold").setBackground("#d9ead3");
  const rule = SpreadsheetApp.newDataValidation().requireValueInList(["사용", "중단"], true).setAllowInvalid(false).build();
  sheet.getRange("A19").setDataValidation(rule);
}

function disableAutoSync() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("설정");
  if (!sheet) return;
  sheet.getRange("A19").setValue("중단");
  Logger.log("🔕 자동화 상태가 자동으로 '중단'으로 설정되었습니다.");
}

function setAutoDisableTrigger() {
  ScriptApp.newTrigger("disableAutoSync").timeBased().onMonthDay(1).atHour(0).create();
}

/**
 * 전달 자동화 트리거 설정 (매월 1일 0시에 전달 데이터 처리)
 * 기존 setAutoDisableTrigger() 함수는 그대로 유지
 * 
 * 실행 순서:
 * 1. 매월 1일 0시: runPreviousMonthAutomation() - 전달 데이터 정산 + 백업
 * 2. 매월 1일 0시 30분: disableAutoSync() - 자동화 중단 (별도 트리거)
 */
function setPreviousMonthAutomationTrigger() {
  // 기존 동일한 트리거 제거 (중복 방지)
  const triggers = ScriptApp.getProjectTriggers();
  for (let t of triggers) {
    if (t.getHandlerFunction() === "runPreviousMonthAutomation") {
      ScriptApp.deleteTrigger(t);
    }
  }

  // 매월 1일 0시에 전달 자동화 실행
  ScriptApp.newTrigger("runPreviousMonthAutomation")
    .timeBased()
    .onMonthDay(1) // 매월 1일
    .atHour(0)     // 오전 0시
    .create();
  
  // 자동화 중단 트리거는 0시 30분으로 변경
  // 기존 setAutoDisableTrigger()는 0시로 설정되어 있으므로 수동으로 변경 필요
  // 또는 별도 함수로 0시 30분 트리거 생성
  
  SpreadsheetApp.getUi().alert("✅ 전달 자동화 트리거가 설정되었습니다.\n\n" +
    "매월 1일 0시: 전달 데이터 정산 + 백업\n" +
    "매월 1일 0시 30분: 자동화 중단 (별도 설정 필요)");
  
  console.log("✅ 전달 자동화 트리거가 설정되었습니다. (매월 1일 0시)");
}

/**
 * 자동화 중단 트리거를 0시 30분으로 설정
 * 기존 setAutoDisableTrigger()는 0시로 설정되므로, 30분 버전 추가
 */
function setAutoDisableTriggerAt30Min() {
  // 기존 동일한 트리거 제거 (중복 방지)
  const triggers = ScriptApp.getProjectTriggers();
  for (let t of triggers) {
    if (t.getHandlerFunction() === "disableAutoSync") {
      ScriptApp.deleteTrigger(t);
    }
  }

  // 매월 1일 0시 30분에 자동화 중단
  // Apps Script는 분 단위 설정이 불가능하므로, 1시로 설정하고 함수 내부에서 30분 대기
  // 또는 별도 트리거로 0시에 실행되도록 하고 함수 내부에서 30분 대기
  
  // 대안: 0시에 실행되도록 설정하고, runPreviousMonthAutomation() 내부에서 30분 대기 후 실행
  // 하지만 이는 비효율적이므로, 0시 30분 대신 1시로 설정
  
  ScriptApp.newTrigger("disableAutoSync")
    .timeBased()
    .onMonthDay(1) // 매월 1일
    .atHour(0)     // 오전 0시 (Apps Script는 분 단위 설정 불가)
    .create();
  
  console.log("⚠️ Apps Script는 분 단위 설정이 불가능합니다. 0시에 실행되도록 설정되었습니다.");
  console.log("전달 자동화가 완료된 후 수동으로 자동화를 중단하거나, 별도 스크립트로 30분 대기 후 실행하세요.");
}

// ──── ✅ (여기까지 ‘기존 코드’ 유지) ────



/* =======================================================
 * ✅ (추가) A2 콤마 다중검색 + 접두 매칭 파서 & 헬퍼
 *  - parsePalletIdQuery(): A2 값을 파싱해 정규식 반환
 *  - filterRowsByPalletId(data, idColIndex): 데이터 필터링
 *  - getFilterParams(): 설정 값 패키징(라벨/정산에서 사용)
 *  - _syncSelectedVendorsToB2(): 체크박스 → B2 합산(옵션)
 *  - refreshVendorStatusDropdowns(): 안전한 갱신 래퍼
 * ======================================================= */

// A2의 “파레트 ID 검색어” 파싱
// - "250930, 250930_001, ABC" 형태 지원(콤마 구분)
// - 언더바가 없는 '250930' → 접두 매칭: ^250930(?:_|$)
// - 언더바 포함 '250930_001' → 정확 매칭: ^250930_001$
function parsePalletIdQuery() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("설정");
  if (!sheet) return { terms: [], regex: null };
  const raw = String(sheet.getRange("A2").getValue() || "");
  const terms = raw.split(",").map(s => s.trim()).filter(Boolean);
  if (!terms.length) return { terms: [], regex: null };

  const patterns = terms.map(t => {
    if (t.includes("_")) {
      // 정확 매칭
      return "(?:" + "^" + _esc_(t) + "$" + ")";
    } else {
      // 접두 매칭(언더바 또는 문자열 종료)
      return "(?:" + "^" + _esc_(t) + "(?:_|$)" + ")";
    }
  });

  const regex = new RegExp(patterns.join("|"));
  return { terms, regex };
}

// 데이터 배열에서 파레트ID 컬럼 기준 필터링(헤더는 통과)
function filterRowsByPalletId(data, idColIndex) {
  const { regex } = parsePalletIdQuery();
  if (!regex) return data; // 검색어 없으면 그대로 반환
  const out = [];
  for (let i = 0; i < data.length; i++) {
    const id = String(data[i][idColIndex] || "");
    if (i === 0 || regex.test(id)) out.push(data[i]); // 헤더 or 매칭행
  }
  return out;
}

// 라벨/정산 쪽에서 한 번에 읽을 수 있는 설정 파라미터
function getFilterParams() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const cfg = ss.getSheetByName("설정");
  const vendors = (function(){
    const checked = getSelectedVendorsFromCheckboxes();
    if (checked.length) return checked;
    const b2 = String(cfg.getRange("B2").getValue() || "");
    return b2.split(",").map(s=>s.trim()).filter(Boolean);
  })();
  return {
    palletQuery: parsePalletIdQuery(), // {terms, regex}
    vendors,
    itemKeyword: String(cfg.getRange("C2").getValue() || "").trim(),
    startDate: cfg.getRange("D2").getValue(),
    endDate: cfg.getRange("E2").getValue(),
    includePrinted: cfg.getRange("F2").getValue() === true,
    status: String(cfg.getRange("G2").getValue() || "전체").trim()
  };
}

// (옵션) 체크박스 선택 → B2 자동 반영에 쓸 수 있는 내부 헬퍼
function _syncSelectedVendorsToB2() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("설정");
  if (!sheet) return;
  const selected = getSelectedVendorsFromCheckboxes();
  sheet.getRange("B2").setValue(selected.length ? selected.join(", ") : "");
}

// updateFilterDropdowns가 에러일 때도 안전하게 호출하는 래퍼(선택 사용)
function refreshVendorStatusDropdowns() {
  try {
    if (typeof updateFilterDropdowns === "function") updateFilterDropdowns();
  } catch (e) {
    SpreadsheetApp.getUi().alert("화주사/상태 목록 갱신 중 오류: " + e);
  }
}

// 정규식 이스케이프 유틸
function _esc_(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
