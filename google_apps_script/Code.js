// 📦 통합 Apps Script 전체 코드 (필터 기반 라벨 불러오기 통합 포함)




// code.gs
function onOpen() {
  const ui = SpreadsheetApp.getUi();

  // 📦 라벨 도구 메뉴 (기존 유지)
  ui.createMenu("📦 라벨 도구")
    .addItem("🔄 전체 파레트 불러오기", "loadAllPalletsToLabelSheet")
    .addItem("🆕 신규 파레트 불러오기", "loadNewPalletsOnly")
    .addItem("🎯 조건 불러오기 (설정 기반)", "loadPalletsByFilter")
    .addItem("🛠 설정 시트 초기화", "setupFilterSettingsSheet") // 템플릿+드롭다운 래퍼(아래 신규)
    .addItem("📊 설정 템플릿 생성", "createFilterSettingsTemplateHorizontal") // (기존 함수)
    .addItem("📥 드롭다운 적용", "updateFilterDropdowns") // (기존 함수)
    .addItem("🏷️ 선택 라벨 출력 실행", "generatePalletLabels")
    .addSeparator()
    .addItem("✅ 전체 선택", "checkAllPallets")
    .addItem("❎ 전체 해제", "uncheckAllPallets")
    .addSeparator()
    .addItem("🧪 A2 검색어 정규식 미리보기", "showPalletIdRegexPreview") // ← ✅ 추가
    .addToUi();

  // ⚙️ 설정 도구 메뉴 (✅ 신규 추가: 화주사 갱신/필터 초기화 등)
  ui.createMenu("⚙️ 설정 도구")
    .addItem("📄 설정 시트 만들기/초기화", "createFilterSettingsTemplateHorizontal")
    .addItem("🔄 화주사/상태 목록 갱신", "updateFilterDropdowns")
    .addItem("🧹 필터 값 초기화(A2:G2·체크박스)", "resetFilterInputs")
    .addSeparator()
    .addItem("💰 보관료설정 시트 생성", "createVendorFeeSettingsSheet")
    .addItem("🔄 화주사 가져오기 (신규만)", "importNewVendorsToFeeSettings")
    .addItem("⚡ 보관료만 재계산 (빠름)", "recalculateVendorFeesOnly")
    .addSeparator()
    .addItem("🔔 자동화 ON/OFF 버튼 생성", "setupAutoSyncButton")
    .addItem("⏰ 매월 1일 자동 '중단' 트리거 설정", "setAutoDisableTrigger")
    .addItem("📅 전달 자동화 트리거 설정 (정산+백업)", "setPreviousMonthAutomationTrigger")
    .addSeparator()
    .addItem("🧪 전달 날짜 계산 테스트", "testPreviousMonthCalculation")
    .addItem("🧪 데이터 필터링 테스트", "testDataFiltering")
    .addItem("🧪 전달 정산 테스트", "testSummarizePreviousMonth")
    .addItem("🧪 전달 백업 테스트", "testExportPreviousMonth")
    .addItem("🧪 전체 자동화 테스트", "testFullAutomation")
    .addToUi();

  // 📬 이메일 도구 메뉴 (기존 유지)
  setupEmailSheetMenu(ui);

  // 📁 정산 백업 메뉴 (기존 유지)
  createBackupMenu(ui);

  // 📝 데이터 입력 메뉴 (신규 추가)
  setupInputSheetMenu(ui);

  // 🔄 신규 시스템 동기화 메뉴 (신규 추가)
  setupSyncMenu(ui);

  // 🔄 입력용 시트 자동 설정
  autoSetupInputSheet();
}

/* ───── 기존에 있던 함수들(이메일/백업 메뉴)은 그대로 유지 ───── */
function setupEmailSheetMenu(ui) {
  ui.createMenu("📬 이메일 도구")
    .addItem("📤 선택 이메일 발송", "sendAllVendorEmails")
    .addItem("🧪 선택 테스트 발송", "sendAllTestEmails")
    .addItem("🔄 화주사 목록 갱신", "refreshVendorListFromDropdown")
    .addToUi();
}

function createBackupMenu(ui) {
  ui.createMenu("📁 정산 백업")
    .addItem("📤 수동 백업 실행", "exportCurrentMonthSummaryToDrive")
    .addItem("📤 화주사별 분리 백업 실행", "exportVendorSheetsSeparately")
    .addItem("📅 전달 데이터 백업 트리거 설정", "createPreviousMonthBackupTrigger")
    .addToUi();
}

/* ───── ✅ 편의 버튼(신규) ───── */

// 설정 시트 셋업(템플릿 생성 후 드롭다운까지 한 번에)
function setupFilterSettingsSheet() {
  createFilterSettingsTemplateHorizontal(); // configUI.gs (기존)
  updateFilterDropdowns();                  // configUI.gs (기존)
  SpreadsheetApp.getUi().alert("설정 시트 초기화 + 드롭다운/체크박스 갱신 완료");
}

// A2 검색어 정규식 미리보기(콤마 다중/접두 매칭 확인)
function showPalletIdRegexPreview() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const cfg = ss.getSheetByName("설정");
  if (!cfg) {
    SpreadsheetApp.getUi().alert("‘설정’ 시트가 없습니다. 먼저 설정 시트를 생성하세요.");
    return;
  }
  if (typeof parsePalletIdQuery !== "function") {
    SpreadsheetApp.getUi().alert("parsePalletIdQuery()가 없습니다. configUI.gs 최신 추가 코드를 적용하세요.");
    return;
  }
  const raw = String(cfg.getRange("A2").getValue() || "").trim();
  const { terms, regex } = parsePalletIdQuery();
  if (!terms.length) {
    SpreadsheetApp.getUi().alert("A2에 검색어가 없습니다.\n예) 250930, 250930_001, ABC123");
    return;
  }
  SpreadsheetApp.getUi().alert(
    "입력값: " + raw +
    "\n\n파싱된 항목: " + terms.join(", ") +
    "\n\n정규식: " + regex
  );
}

// 필터 값 초기화(A2:G2 비움 + 체크박스 해제 + B2 갱신)
function resetFilterInputs() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const cfg = ss.getSheetByName("설정");
  if (!cfg) {
    SpreadsheetApp.getUi().alert("‘설정’ 시트가 없습니다.");
    return;
  }
  // 값 초기화
  cfg.getRange("A2:G2").clearContent();

  // 체크박스(A6:G20) 해제(체크 라인만 false로)
  const boxRange = cfg.getRange("A6:G20");
  const vals = boxRange.getValues();
  for (let r = 0; r < vals.length; r++) {
    // 짝수행(0-based r가 홀수)만 체크박스 줄
    if ((r % 2) === 1) {
      for (let c = 0; c < vals[r].length; c++) vals[r][c] = false;
    }
  }
  boxRange.setValues(vals);

  // B2 동기화(있으면 호출)
  if (typeof _syncSelectedVendorsToB2 === "function") {
    _syncSelectedVendorsToB2();
  } else {
    cfg.getRange("B2").clearContent();
  }
  SpreadsheetApp.getUi().alert("필터 값과 체크박스를 초기화했습니다.");
}


function setupFilterSettingsSheet() {
  createFilterSettingsTemplateHorizontal();
  updateFilterDropdowns();
  applyDatePickersToSettings(); // ← 달력 적용 추가됨
}




function loadPalletsByFilter() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const config = ss.getSheetByName("설정");
  const source = ss.getSheetByName("파레트 요약 정산");
  const labelSheet = ss.getSheetByName("라벨출력대상") || ss.insertSheet("라벨출력대상");


  const data = source.getDataRange().getValues();
  const header = data[0];


  const idIdx = header.indexOf("파레트 ID");
  const vendorIdx = header.indexOf("화주사");
  const productIdx = header.indexOf("품목명");
  const inDateIdx = header.indexOf("입고일");
  const statusIdx = header.indexOf("상태");


  // ✅ 설정값 가져오기 (B2는 무시)
  const [idFilter, , productKeyword, startDateRaw, endDateRaw, includePrinted, statusFilterRaw] =
    config.getRange("A2:G2").getValues()[0];


  const idText = (idFilter + "").trim();
  const vendorList = getFilterVendorList();  // ✅ 체크박스 기반
  const productText = (productKeyword + "").trim();
  const startDate = tryParseDate(startDateRaw);
  const endDate = tryParseDate(endDateRaw);
  const allowPrinted = includePrinted === true;
  const statusText = (statusFilterRaw + "").trim();


  // ✅ 초기화
  const maxRows = labelSheet.getMaxRows();
  if (maxRows > 3) {
    labelSheet.getRange(3, 2, maxRows - 2).removeCheckboxes();
    labelSheet.getRange(3, 1, maxRows - 2, 8).clearContent();
    labelSheet.getRange(3, 7, maxRows - 2, 2).setBackground(null);
  }


  labelSheet.getRange("A1:H1").setValues([[
    "파레트 ID", "출력 여부", "화주사 필터", "입고일", "보관 상태", "품목명", "출력일자", "출력여부"
  ]]);


  let rowIndex = 2;
  let added = 0;


  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    const id = (row[idIdx] + "").trim();
    const vendor = (row[vendorIdx] + "").trim();
    const product = (row[productIdx] + "").trim();
    const status = (row[statusIdx] + "").trim();
    const inDate = row[inDateIdx] instanceof Date ? row[inDateIdx] : tryParseDate(row[inDateIdx]);


    if (idText && !id.includes(idText)) continue;
    if (vendorList.length > 0 && !vendorList.includes(vendor)) continue;
    if (productText && !product.includes(productText)) continue;
    if (!allowPrinted && status === "출력완료") continue;
    if (startDate && isValidDate(inDate) && inDate < startDate) continue;
    if (endDate && isValidDate(inDate) && inDate > endDate) continue;
    if (statusText && statusText !== "전체" && status !== statusText) continue;


    labelSheet.getRange(rowIndex, 1).setValue(id);
    labelSheet.getRange(rowIndex, 2).insertCheckboxes();
    labelSheet.getRange(rowIndex, 3).setValue(vendor || "");
    labelSheet.getRange(rowIndex, 4).setValue(isValidDate(inDate) ? inDate : "");
    labelSheet.getRange(rowIndex, 5).setValue(status || "");
    labelSheet.getRange(rowIndex, 6).setValue(product || "");
    labelSheet.getRange(rowIndex, 7).setValue(""); // 출력일자
    labelSheet.getRange(rowIndex, 8).setValue("미출력"); // 출력여부


    rowIndex++;
    added++;
  }


  const ui = SpreadsheetApp.getUi();
  if (added === 0) ui.alert("🔍 조건에 맞는 파레트가 없습니다.");
  else ui.alert(`🎯 조건에 맞는 파레트 ${added}건이 불러와졌습니다.`);
}






function applyDatePickersToSettings() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("설정");
  if (!sheet) return;


  const startCell = sheet.getRange("D2");
  const endCell = sheet.getRange("E2");


  // ✅ 날짜 형식으로 초기화 → Google Sheets가 "날짜 셀"로 인식함
  startCell.setValue(new Date());  // 기본값 넣고
  endCell.setValue(new Date());


  startCell.setNumberFormat("yyyy-mm-dd");  // 보기 형식 지정
  endCell.setNumberFormat("yyyy-mm-dd");


  // ❗️선택사항: 다시 비우고 싶다면 아래 줄 주석 제거
  // startCell.clearContent();
  // endCell.clearContent();
}










function checkAllPallets() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("라벨출력대상");
  if (!sheet) return;
  const lastRow = sheet.getLastRow();
  for (let row = 2; row <= lastRow; row++) {
    if (!sheet.isRowHiddenByFilter(row)) {
      sheet.getRange(row, 2).setValue(true); // B열 체크박스
    }
  }
  SpreadsheetApp.getUi().alert("✅ 화면에 보이는 파레트만 선택되었습니다.");
}


function uncheckAllPallets() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("라벨출력대상");
  if (!sheet) return;
  const lastRow = sheet.getLastRow();
  const checkRange = sheet.getRange(2, 2, lastRow - 1);
  checkRange.setValue(false);
  SpreadsheetApp.getUi().alert("❎ 모든 체크박스를 해제했습니다.");
}


function fmt(d) {
  return d instanceof Date ? Utilities.formatDate(d, Session.getScriptTimeZone(), "yyyy.MM.dd") : "";
}


// 기존 코드에서 이 부분을 교체하세요

// 기존 코드에서 이 부분을 교체하세요

function tryParseDate(input) {
  if (!input) return null;
  
  // 이미 Date 객체인 경우
  if (input instanceof Date) {
    return isValidDate(input) ? input : null;
  }
  
  // 문자열이 아닌 경우 문자열로 변환
  const dateStr = input.toString().trim();
  if (!dateStr) return null;
  
  // 1. 기본 Date 생성자로 시도
  let parsed = new Date(dateStr);
  if (isValidDate(parsed)) return parsed;
  
  // 2. 한국어 날짜 형식 처리: "2025. 6. 17오전 10:54:00" 또는 "2025. 6. 17 오전 10:54:00"
  const koreanPattern = /^(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\s*(오전|오후)?\s*(\d{1,2}):(\d{1,2}):(\d{1,2})$/;
  const koreanMatch = dateStr.match(koreanPattern);
  if (koreanMatch) {
    const [, year, month, day, ampm, hour, minute, second] = koreanMatch;
    let hour24 = parseInt(hour);
    
    // 오후인 경우 12시간 추가 (12시는 제외)
    if (ampm === "오후" && hour24 !== 12) {
      hour24 += 12;
    }
    // 오전 12시는 0시로 변환
    else if (ampm === "오전" && hour24 === 12) {
      hour24 = 0;
    }
    
    parsed = new Date(parseInt(year), parseInt(month) - 1, parseInt(day), hour24, parseInt(minute), parseInt(second));
    if (isValidDate(parsed)) return parsed;
  }
  
  // 3. 한국어 날짜만 있는 형식: "2025. 6. 17" 또는 "2025.06.17"
  const koreanDatePatterns = [
    /^(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})$/,  // "2025. 6. 17" (공백 있음)
    /^(\d{4})\.(\d{1,2})\.(\d{1,2})$/         // "2025.06.17" (공백 없음)
  ];
  
  for (const pattern of koreanDatePatterns) {
    const match = dateStr.match(pattern);
    if (match) {
      const [, year, month, day] = match;
      parsed = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
      if (isValidDate(parsed)) return parsed;
    }
  }
  
  // 4. 다양한 구분자로 시도: "2025-06-17", "2025/06/17" 등
  const formats = [
    /^(\d{4})-(\d{1,2})-(\d{1,2})/, // YYYY-MM-DD
    /^(\d{4})\/(\d{1,2})\/(\d{1,2})/, // YYYY/MM/DD
    /^(\d{1,2})\/(\d{1,2})\/(\d{4})/, // MM/DD/YYYY
    /^(\d{1,2})-(\d{1,2})-(\d{4})/, // MM-DD-YYYY
  ];
  
  for (const format of formats) {
    const match = dateStr.match(format);
    if (match) {
      const [, first, second, third] = match;
      
      // YYYY-MM-DD 또는 YYYY/MM/DD 형식
      if (format.toString().includes('4')) {
        parsed = new Date(parseInt(first), parseInt(second) - 1, parseInt(third));
      }
      // MM/DD/YYYY 또는 MM-DD-YYYY 형식
      else {
        parsed = new Date(parseInt(third), parseInt(first) - 1, parseInt(second));
      }
      
      if (isValidDate(parsed)) return parsed;
    }
  }
  
  // 5. ISO 형식 직접 처리: "2025-05-01T14:59:08.000Z"
  if (dateStr.includes('T') && dateStr.includes('Z')) {
    parsed = new Date(dateStr);
    if (isValidDate(parsed)) return parsed;
  }
  
  // 모든 시도 실패
  return null;
}

function isValidDate(d) {
  return d instanceof Date && !isNaN(d.getTime());
}
// 파레트 요약 정산 시트 //
function summarizePalletData() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const configSheet = ss.getSheetByName("설정") || ss.insertSheet("설정");
  const configData = configSheet.getDataRange().getValues();
  const rawSheet = ss.getSheetByName("설문지 응답 시트1");
  const data = rawSheet.getDataRange().getValues();
  const header = data[0];


  const idIdx = header.indexOf("파레트 ID");
  const typeIdx = header.indexOf("작업 유형");
  const qtyIdx = header.indexOf("작업 수량");
  const timeIdx = header.indexOf("타임스탬프");
  const productIdx = header.indexOf("품목명");
  const vendorIdx = header.indexOf("화주사");


  const summary = {};
  const today = new Date();


  function getDailyFee(date, vendor) {
    // ✅ 신규: 화주사별 보관료 조회 (보관료설정 시트)
    if (vendor && typeof getVendorMonthlyFee === 'function') {
      const vendorFee = getVendorMonthlyFee(vendor);
      if (vendorFee > 0) {
        return Math.round(vendorFee / 30.44);
      }
    }
    
    // ✅ 기존 로직 유지 (fallback)
    const yyyymm = Utilities.formatDate(date, Session.getScriptTimeZone(), "yyyy.MM");
    for (let i = 1; i < configData.length; i++) {
      const configMonth = (configData[i][0] + "").trim();
      const configRate = Number(configData[i][1]);
      if (configMonth === yyyymm && configRate > 0) {
        return Math.round(configRate / 30.44);
      }
    }
    return 533;
  }


  function calculateFee(start, end, vendor) {
    let totalFee = 0;
    let totalDays = 0;
    let current = new Date(start.getFullYear(), start.getMonth(), 1);
    while (current <= end) {
      const nextMonth = new Date(current.getFullYear(), current.getMonth() + 1, 1);
      const rangeStart = current < start ? start : current;
      const rangeEnd = nextMonth > end ? end : new Date(nextMonth - 1);
      const days = Math.ceil((rangeEnd - rangeStart) / (1000 * 60 * 60 * 24));
      const fee = getDailyFee(current, vendor) * days;
      totalDays += days;
      totalFee += fee;
      current = nextMonth;
    }
    
    // ✅ 백원 단위 올림
    const roundedFee = Math.ceil(totalFee / 100) * 100;
    
    return { days: totalDays, fee: roundedFee };
  }


  for (let i = 1; i < data.length; i++) {
    const id = data[i][idIdx];
    const type = data[i][typeIdx];
    const qty = Number(data[i][qtyIdx]) || 0;  // undefined나 NaN일 때 0으로 처리
    const time = new Date(data[i][timeIdx]);
    const product = (data[i][productIdx] || "무기입").toString().trim();
    const vendor = data[i][vendorIdx];
    if (!id) continue;  // 날짜 유효성 검사 제거


    if (!summary[id]) {
      summary[id] = {
        "파레트 ID": id,
        "화주사": vendor,
        "품목명": product,
        "입고일후보": [],
        "입고 수량": 0,
        "출고 수량": 0,
        "출고일": null,
        "보관종료일": null,
        "보관종료 여부": false,
        "서비스 여부": false,
        "사용중 여부": false,
        "마지막 타임스탬프": time
      };
    }


    if (time > summary[id]["마지막 타임스탬프"]) {
      summary[id]["마지막 타임스탬프"] = time;
      summary[id]["품목명"] = product;
    }


    if (type === "입고") {
      summary[id]["입고 수량"] += qty;
      summary[id]["입고일후보"].push(time);
    } else if (type === "사용중") {
      summary[id]["사용중 여부"] = true;
      summary[id]["입고일후보"].push(time); // 입고일 없을 경우 대체용
    } else if (type === "보관종료") {
  // 수량이 0이거나 없으면 입고수량으로 대체 (전체 출고로 간주)
  const exitQty = qty > 0 ? qty : summary[id]["입고 수량"];
  summary[id]["출고 수량"] += exitQty;
  summary[id]["출고일"] = summary[id]["출고일"]
    ? new Date(Math.max(summary[id]["출고일"].getTime(), time.getTime()))
    : time;
  summary[id]["보관종료일"] = summary[id]["보관종료일"]
    ? new Date(Math.max(summary[id]["보관종료일"].getTime(), time.getTime()))
    : time;
  summary[id]["보관종료 여부"] = true;
    } else if (type === "서비스") {
      summary[id]["서비스 여부"] = true;
      summary[id]["입고일후보"].push(time);
    }
  }


  const sheet = ss.getSheetByName("파레트 요약 정산") || ss.insertSheet("파레트 요약 정산");
  sheet.clearContents();


  const result = [[
    "파레트 ID", "화주사", "품목명", "입고 수량", "출고 수량", "남은 수량",
    "입고일", "출고일", "보관종료일", "상태", "갱신일", "보관일수", "보관료(원)"
  ]];


  for (const id in summary) {
    const e = summary[id];
    const 남은 = e["입고 수량"] - e["출고 수량"];
    let 상태 = "";
    let 갱신일 = "";
    let 보관일수 = 0;
    let 보관료 = 0;
    let 입고일 = e["입고일후보"].length > 0
      ? new Date(Math.min(...e["입고일후보"].map(d => d.getTime())))
      : null;


    if (e["서비스 여부"]) {
      상태 = "서비스";
    } else if (e["보관종료 여부"]) {
      상태 = "보관종료";
    } else if (e["사용중 여부"]) {
      상태 = "사용중";
    } else {
      상태 = "입고됨";
    }


    if (입고일 instanceof Date) {
      if (상태 === "서비스") {
        갱신일 = Utilities.formatDate(입고일, Session.getScriptTimeZone(), "yyyy.MM.dd");
      } else if (상태 === "보관종료" && e["보관종료일"] instanceof Date) {
        const 종료월초 = new Date(e["보관종료일"].getFullYear(), e["보관종료일"].getMonth(), 1);
        const 시작일 = 입고일 > 종료월초 ? 입고일 : 종료월초;
        갱신일 = Utilities.formatDate(시작일, Session.getScriptTimeZone(), "yyyy.MM.dd");
        const resultObj = calculateFee(시작일, e["보관종료일"], e["화주사"]);
        보관일수 = resultObj.days;
        보관료 = resultObj.fee;
        // 🔒 보관종료가 '이번달이 아닌 경우' 보관료 제외
if (e["보관종료 여부"]) {
  const 종료월 = Utilities.formatDate(e["보관종료일"], Session.getScriptTimeZone(), "yyyy.MM");
  const 이번달 = Utilities.formatDate(today, Session.getScriptTimeZone(), "yyyy.MM");

  if (종료월 !== 이번달) {
    보관일수 = "";
    보관료 = "";
  }
}
      } else {
        const 이번달1일 = new Date(today.getFullYear(), today.getMonth(), 1);
        const 시작일 = 입고일 > 이번달1일 ? 입고일 : 이번달1일;
        갱신일 = Utilities.formatDate(시작일, Session.getScriptTimeZone(), "yyyy.MM.dd");
        const resultObj = calculateFee(시작일, today, e["화주사"]);
        보관일수 = resultObj.days;
        보관료 = resultObj.fee;
      }
    }


    result.push([
      e["파레트 ID"], e["화주사"], e["품목명"], e["입고 수량"], e["출고 수량"], 남은,
      입고일, e["출고일"], e["보관종료일"], 상태, 갱신일,
      e["서비스 여부"] ? 0 : 보관일수,
      e["서비스 여부"] ? 0 : 보관료
    ]);
  }


  sheet.getRange(1, 1, result.length, result[0].length).setValues(result);
  sheet.setFrozenRows(1);
  sheet.getRange(1, 1, 1, result[0].length).setFontWeight("bold");
  sheet.getRange(1, 1, result.length, result[0].length).setBorder(true, true, true, true, true, true);


  sheet.getRange(2, 7, result.length - 1, 1).setNumberFormat("yyyy.MM.dd");
  sheet.getRange(2, 8, result.length - 1, 1).setNumberFormat("yyyy.MM.dd");
  sheet.getRange(2, 9, result.length - 1, 1).setNumberFormat("yyyy.MM.dd");
  sheet.getRange(2, 11, result.length - 1, 1).setNumberFormat("yyyy.MM.dd");


  splitByVendor();
  generateMonthlyVendorSummary();
 
}




/**
 * 화주사 이름 정규화 (대소문자, 띄어쓰기, 특수문자 무시)
 */
function normalizeVendorName(name) {
  if (typeof name !== 'string') return "미지정";
  
  // 정규화: 소문자 변환, 띄어쓰기 제거, 특수문자 제거
  let normalized = name
    .toLowerCase() // 소문자 변환
    .replace(/\s+/g, '') // 모든 띄어쓰기 제거
    .replace(/[^\w가-힣]/g, '') // 영문, 숫자, 한글만 남기기
    .trim();
  
  // 빈 문자열 처리
  if (!normalized || normalized.length === 0) {
    normalized = "미지정";
  }
  
  return normalized;
}

function sanitizeSheetName(name) {
  return name.replace(/[\\/\[\]\*\?]/g, '_').substring(0, 99);
}


function splitByVendor() {
  const maxRetries = 3;
  let retryCount = 0;
  
  while (retryCount < maxRetries) {
    try {
      const ss = SpreadsheetApp.getActiveSpreadsheet();
      const sourceSheet = ss.getSheetByName("파레트 요약 정산");
      
      if (!sourceSheet) {
        console.error("파레트 요약 정산 시트를 찾을 수 없습니다.");
        return;
      }
      
      const data = sourceSheet.getDataRange().getValues();
      const header = data[0];

  const vendorIndex = header.indexOf("화주사");
  const remarkIndex = header.length; // 비고 추가 예정
  const feeColIndex = header.indexOf("보관료(원)"); // 보관료 열 인덱스 추가

  const vendorMap = {};
  const vendorNameMap = {}; // 원본 이름 → 정규화된 이름 매핑
  
  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    const originalVendor = row[vendorIndex] || "미지정";
    const normalizedVendor = normalizeVendorName(originalVendor);
    
    // 정규화된 이름으로 그룹화
    if (!vendorMap[normalizedVendor]) {
      vendorMap[normalizedVendor] = [];
      vendorNameMap[normalizedVendor] = originalVendor; // 원본 이름 저장
    }
    vendorMap[normalizedVendor].push(row);
  }

  for (const normalizedVendor in vendorMap) {
    const originalVendor = vendorNameMap[normalizedVendor];
    const sheetName = originalVendor.length > 0 ? sanitizeSheetName(originalVendor) : "미지정"; // 시트 이름 유효성 검사 적용
    let sheet = ss.getSheetByName(sheetName) || ss.insertSheet(sheetName);
    const lastRow = sheet.getLastRow();
    const oldRemarks = lastRow >= 2
      ? sheet.getRange(2, remarkIndex + 1, lastRow - 1).getValues()
      : [];

    // ✅ 수정된 부분: 내용만 지우고 배경색도 초기화
    sheet.clearContents();
    if (sheet.getMaxRows() > 1) {
      sheet.getRange(1, 1, sheet.getMaxRows(), sheet.getMaxColumns()).setBackground(null);
    }
    
    // ✅ 빈 셀들 배경색 완전 초기화
    sheet.getRange(1, 1, sheet.getMaxRows(), sheet.getMaxColumns()).setBackground(null);

    const newHeader = header.concat(["비고"]);
    sheet.getRange(1, 1, 1, newHeader.length).setValues([newHeader]);

    const cleanedRows = vendorMap[normalizedVendor].map((row, i) => {
      const newRow = [...row];
      newRow.push(oldRemarks[i] ? oldRemarks[i][0] : "");
      return newRow;
    });

    const range = sheet.getRange(2, 1, cleanedRows.length, newHeader.length);
    range.setValues(cleanedRows);
    
    // ✅ 데이터 범위 서식 통일
    range.setFontWeight("normal");  // 글씨 굵기 통일
    range.setHorizontalAlignment("center");  // 중앙 정렬 통일
    range.setVerticalAlignment("middle");  // 세로 중앙 정렬
    range.setFontSize(10);  // 글씨 크기 통일
    range.setFontColor("#000000");  // 글씨 색상 검정으로 통일
    range.setFontStyle("normal");  // 기울임 제거
    range.setBorder(true, true, true, true, true, true);
    
    sheet.setFrozenRows(1);
    if (sheet.getFilter()) sheet.getFilter().remove();
    sheet.getRange(1, 1, cleanedRows.length + 1, newHeader.length).createFilter();

    // 날짜 포맷 적용
    sheet.getRange(2, 7, cleanedRows.length, 1).setNumberFormat("yyyy.MM.dd"); // 입고일
    sheet.getRange(2, 8, cleanedRows.length, 1).setNumberFormat("yyyy.MM.dd"); // 출고일
    sheet.getRange(2, 9, cleanedRows.length, 1).setNumberFormat("yyyy.MM.dd"); // 보관종료일
    sheet.getRange(2, 11, cleanedRows.length, 1).setNumberFormat("yyyy.MM.dd"); // 갱신일
    
    // ⭐ 보관료(원) 열의 숫자 포맷 및 우측 정렬 적용
    if (feeColIndex !== -1) {
      const feeRange = sheet.getRange(2, feeColIndex + 1, cleanedRows.length, 1);
      feeRange.setNumberFormat("#,##0");
      feeRange.setHorizontalAlignment("right");  // 보관료 열만 우측 정렬
      feeRange.setFontWeight("normal");
      feeRange.setFontColor("#000000");
      feeRange.setFontStyle("normal");
      feeRange.setFontSize(10);
    }

    // ⭐ 보관료 총계 추가 로직 시작
    if (feeColIndex !== -1 && cleanedRows.length > 0) { // 보관료 열이 있고 데이터가 있을 경우에만
      const totalLabelCol = 1; // '총 보관료 합계'를 A열에 표시
      const totalValueCol = feeColIndex + 1; // 보관료 값은 해당 열에 표시

      const lastDataRow = sheet.getLastRow();
      const totalRowIndex = lastDataRow + 2; // 데이터 마지막 행 + 1 (빈 칸) + 1 (총계 행)

      // '총 보관료 합계' 라벨
      sheet.getRange(totalRowIndex, totalLabelCol).setValue("총 보관료 합계")
        .setFontWeight("bold")
        .setFontSize(12)
        .setHorizontalAlignment("right")
        .setBackground("#e6e6e6");

      // 보관료 합계 계산 수식 (데이터가 2행부터 시작하므로)
      const formulaRange = `${String.fromCharCode(65 + feeColIndex)}2:${String.fromCharCode(65 + feeColIndex)}${lastDataRow}`;
      sheet.getRange(totalRowIndex, totalValueCol).setFormula(`=SUM(${formulaRange})`)
        .setFontWeight("bold")
        .setFontSize(12)
        .setNumberFormat("#,##0")
        .setHorizontalAlignment("center")
        .setBackground("#e6e6e6");

      // 총계 행 전체에 테두리 적용
      sheet.getRange(totalRowIndex, 1, 1, newHeader.length).setBorder(true, true, true, true, true, true);

      // '※ 부가세 별도' 문구 추가
      const vatNoteRowIndex = totalRowIndex + 1;
      sheet.getRange(vatNoteRowIndex, totalValueCol).setValue("※ 부가세 별도")
        .setFontSize(9)
        .setFontStyle("italic")
        .setFontColor("#666")
        .setHorizontalAlignment("center");
        
      // ✅ 총계 아래 빈 셀들 배경색 초기화
      const maxRows = sheet.getMaxRows();
      if (vatNoteRowIndex + 1 <= maxRows) {
        sheet.getRange(vatNoteRowIndex + 1, 1, maxRows - vatNoteRowIndex, sheet.getMaxColumns())
          .setBackground(null);
      }
    }
    // ⭐ 보관료 총계 추가 로직 끝
  }
  
      // 성공 시 루프 종료
      break;
      
    } catch (error) {
      retryCount++;
      console.error(`splitByVendor 실행 중 오류 (시도 ${retryCount}/${maxRetries}):`, error);
      
      if (retryCount >= maxRetries) {
        SpreadsheetApp.getUi().alert('화주사별 시트 생성 중 오류가 발생했습니다: ' + error.message);
        return;
      }
      
      // 재시도 전 대기
      Utilities.sleep(1000 * retryCount);
    }
  }
}






//월별 화주사 요약 시트 //
// ✅ 월별 요약: 보관료 10원 단위 올림 + VAT + 총합
function generateMonthlyVendorSummary() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sourceSheet = ss.getSheetByName("파레트 요약 정산");
  if (!sourceSheet) return;


  const data = sourceSheet.getDataRange().getValues();
  const header = data[0];
  const vendorIdx = header.indexOf("화주사");
  const dateIdx = header.indexOf("갱신일");
  const feeIdx = header.indexOf("보관료(원)");
  const statusIdx = header.indexOf("상태");


  const today = new Date();
  const currentMonth = Utilities.formatDate(today, Session.getScriptTimeZone(), "yyyy.MM");


  const summaryMap = {};


  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    const vendor = row[vendorIdx] || "미지정";
    const status = row[statusIdx];
    const fee = Number(row[feeIdx]);
    const date = row[dateIdx];


    if (!vendor || !date || typeof date !== "string" || !date.startsWith(currentMonth)) continue;
    const key = vendor + "|" + currentMonth;


    if (!summaryMap[key]) {
      summaryMap[key] = {
        vendor,
        yyyymm: currentMonth,
        보관료합계: 0,
        보관중: 0,
        보관종료: 0,
        서비스: 0
      };
    }


    if (status === "서비스") {
      summaryMap[key].서비스 += 1;
    } else if (status === "보관종료") {
      summaryMap[key].보관종료 += 1;
      summaryMap[key].보관료합계 += fee;
    } else {
      summaryMap[key].보관중 += 1; // 입고됨, 사용중 포함
      summaryMap[key].보관료합계 += fee;
    }
  }


  const summarySheet = ss.getSheetByName("월별 화주사 요약") || ss.insertSheet("월별 화주사 요약");
  summarySheet.clearContents();


  const output = [
    ["날짜", "화주사", "보관 파레트 수", "종료 파레트 수", "서비스 수", "보관료", "비고"]
  ];


  for (const key in summaryMap) {
    const e = summaryMap[key];
    output.push([
      e.yyyymm,
      e.vendor,
      e.보관중,
      e.보관종료,
      e.서비스,
      e.보관료합계,
      ""
    ]);
  }


  const totalRow = ["전체 합계", "", 0, 0, 0, 0, ""];
  for (let i = 1; i < output.length; i++) {
    totalRow[2] += output[i][2];
    totalRow[3] += output[i][3];
    totalRow[4] += output[i][4];
    totalRow[5] += output[i][5];
  }
  output.push(totalRow);


  summarySheet.getRange(1, 1, output.length, output[0].length).setValues(output);
  summarySheet.getRange(1, 1, 1, output[0].length).setFontWeight("bold");
  summarySheet.getRange(2, 6, output.length - 1, 1).setNumberFormat("#,##0");


  const borderRange = summarySheet.getRange(2, 1, output.length - 2, output[0].length);
  borderRange.setBorder(true, true, true, true, true, true);


  summarySheet.getRange(output.length, 1, 1, 7)
    .setFontWeight("bold")
    .setBackground("#eeeeee");








  // ✅ 빈행 제외하고 테두리 설정
  const rangeToBorder = summarySheet.getRange(2, 1, output.length - 2, output[0].length)
    .getValues()
    .filter(row => row.some(cell => cell !== ""));
  if (rangeToBorder.length > 0) {
    const borderRange = summarySheet.getRange(2, 1, rangeToBorder.length, output[0].length);
    borderRange.setBorder(true, true, true, true, true, true);
  }


  summarySheet.getRange(output.length, 1, 1, 7).setFontWeight("bold").setBackground("#eeeeee");


  // ✅ 자동 차트 생성
  const charts = summarySheet.getCharts();
  charts.forEach(c => summarySheet.removeChart(c));


  const chartRange = summarySheet.getRange("A1:F" + (output.length - 1));
  const chart = summarySheet.newChart()
    .asColumnChart()
    .addRange(chartRange)
    .setPosition(2, 9, 0, 0)
    .setOption("title", "월별 화주사 보관료 비교")
    .setOption("seriesType", "bars")
    .setOption("hAxis", { title: "보관료" })
    .setOption("vAxis", { title: "화주사" })
    .setOption("legend", { position: "right" })
    .build();


  summarySheet.insertChart(chart);
}








function ensureConfigSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName("설정");
  if (!sheet) {
    sheet = ss.insertSheet("설정");
  } else {
    sheet.clearContents();
  }


  sheet.getRange("A1").setValue("년월 (YYYY.MM)");
  sheet.getRange("B1").setValue("월 보관료");
  sheet.getRange("A1:B1").setFontWeight("bold").setBackground("#f1f1f1");


  // 📌 드롭다운용: 현재 입고된 파레트의 년월 목록 추출
  const rawSheet = ss.getSheetByName("설문지 응답 시트1");
  if (!rawSheet) return;
  const data = rawSheet.getDataRange().getValues();
  const header = data[0];
  const timeIdx = header.indexOf("타임스탬프");


  const monthSet = new Set();
  for (let i = 1; i < data.length; i++) {
    const date = new Date(data[i][timeIdx]);
    if (isValidDate(date)) {
      const yyyymm = Utilities.formatDate(date, Session.getScriptTimeZone(), "yyyy.MM");
      monthSet.add(yyyymm);
    }
  }


  const months = Array.from(monthSet).sort();
  for (let i = 0; i < months.length; i++) {
    sheet.getRange(i + 2, 1).setValue(months[i]);
  }


  sheet.autoResizeColumns(1, 2);
}


function autoSelectPalletsByFilter() {}
// ❌ 오류 수정: setAttributes 메서드는 DocumentApp.Table에는 존재하지 않음
// 📌 해결: setAttributes 제거 또는 각 셀에 직접 스타일 적용


// 전체 파레트 불러오기 (보관종료는 안불러옴) //
function loadAllPalletsToLabelSheet() {
  backupPrintStatus();


  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const mainSheet = ss.getSheetByName("파레트 요약 정산");
  const data = mainSheet.getDataRange().getValues();
  let labelSheet = ss.getSheetByName("라벨출력대상");


  // 시트가 없다면 새로 생성
  if (!labelSheet) {
    labelSheet = ss.insertSheet("라벨출력대상");
  } else {
    const maxRows = labelSheet.getMaxRows();


    // ✅ 기존 체크박스(B열 전체) 제거
    labelSheet.getRange(2, 2, maxRows - 1).removeCheckboxes();


    // ✅ 기존 내용 A~H 열만 초기화 (출력기록 열 제외)
    labelSheet.getRange(2, 1, maxRows - 1, 8).clearContent();
      // ✅ 출력기록 열 배경색 초기화 (출력일자, 출력여부)
  labelSheet.getRange(2, 7, maxRows - 1, 2).setBackground(null);  // G, H열
  }


  // ✅ 헤더 다시 작성 (혹시라도 변경되었을 경우 대비)
  labelSheet.getRange("A1:H1").setValues([[
    "파레트 ID", "출력 여부", "화주사 필터", "입고일", "보관 상태", "품목명", "출력일자", "출력여부"
  ]]);


  const header = data[0];
  const palletColIndex = header.indexOf("파레트 ID");
  const vendorColIndex = header.indexOf("화주사");
  const inDateColIndex = header.indexOf("입고일");
  const statusColIndex = header.indexOf("상태");
  const productColIndex = header.indexOf("품목명");


  let rowIndex = 2;
  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    const palletId = row[palletColIndex];
    const vendor = row[vendorColIndex];
    const inDateRaw = row[inDateColIndex];
    const status = row[statusColIndex];
    const productRaw = row[productColIndex];


    if (status === "보관종료") continue;


    const product = typeof productRaw === 'string' ? productRaw.split(/\r?\n/)[0] : productRaw;


    if (palletId) {
      labelSheet.getRange(rowIndex, 1).setValue(palletId);                       // A: 파레트 ID
      labelSheet.getRange(rowIndex, 2).insertCheckboxes();                      // B: 체크박스
      labelSheet.getRange(rowIndex, 3).setValue(vendor || "");                  // C: 화주사
      labelSheet.getRange(rowIndex, 4).setValue(inDateRaw instanceof Date ? inDateRaw : "");  // D: 입고일
      labelSheet.getRange(rowIndex, 5).setValue(status || "");                  // E: 보관 상태
      labelSheet.getRange(rowIndex, 6).setValue(product || "");                 // F: 품목명
      labelSheet.getRange(rowIndex, 7).setValue("");                            // G: 출력일자
      labelSheet.getRange(rowIndex, 8).setValue("");                            // H: 출력여부
      rowIndex++;
    }
  }


  restorePrintStatus();


  SpreadsheetApp.getUi().alert("✅ 전체 파레트가 불러와졌고, 출력 기록이 복원되었습니다.");
}




// 라벨 출력 함수//
// 📦 통합 Apps Script 전체 코드 (generatePalletLabels 함수만 Google Slides로 수정)


// ✅ 신규 파레트만 불러오는 함수
function loadNewPalletsOnly() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sourceSheet = ss.getSheetByName("파레트 요약 정산");
  const labelSheet = ss.getSheetByName("라벨출력대상") || ss.insertSheet("라벨출력대상");
  const data = sourceSheet.getDataRange().getValues();
  const header = data[0];


  const idIdx = header.indexOf("파레트 ID");
  const vendorIdx = header.indexOf("화주사");
  const inDateIdx = header.indexOf("입고일");
  const statusIdx = header.indexOf("상태");
  const productIdx = header.indexOf("품목명");


  const now = new Date();
  const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);


  // ✅ 기존 내용 및 서식 초기화
  const maxRows = labelSheet.getMaxRows();
  if (maxRows > 1) {
    labelSheet.getRange(2, 2, maxRows - 1).removeCheckboxes();  // B열 체크박스 제거
    labelSheet.getRange(2, 1, maxRows - 1, 8).clearContent();   // A~H 열 초기화
    labelSheet.getRange(2, 7, maxRows - 1, 2).setBackground(null); // G, H열 배경색 초기화
  }


  // ✅ 헤더 다시 삽입
  labelSheet.getRange("A1:H1").setValues([[
    "파레트 ID", "출력 여부", "화주사 필터", "입고일", "보관 상태", "품목명", "출력일자", "출력여부"
  ]]);


  const existingIds = new Set();


  // 출력대상 시트에 이미 있는 ID 목록 확보 (보호 목적이지만, 초기화 후라 의미 없음)
  // 하지만 출력완료된 것 제외하는 데 사용할 수도 있음
  const backupSheet = ss.getSheetByName("출력기록백업");
  if (backupSheet) {
    const backupData = backupSheet.getDataRange().getValues();
    for (let i = 1; i < backupData.length; i++) {
      const id = (backupData[i][0] + "").trim();
      const status = backupData[i][2];
      if (status === "출력완료") {
        existingIds.add(id);
      }
    }
  }


  let rowIndex = 2;
  let addedCount = 0;


  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    const id = (row[idIdx] + "").trim();
    const vendor = row[vendorIdx];
    const inDate = row[inDateIdx] instanceof Date ? row[inDateIdx] : tryParseDate(row[inDateIdx]);
    const status = row[statusIdx];
    const product = row[productIdx];


    if (!id || !isValidDate(inDate)) continue;
    if (inDate < sevenDaysAgo) continue;
    if (status === "보관종료") continue;
    if (existingIds.has(id)) continue;


    labelSheet.getRange(rowIndex, 1).setValue(id);
    labelSheet.getRange(rowIndex, 2).insertCheckboxes();
    labelSheet.getRange(rowIndex, 3).setValue(vendor || "");
    labelSheet.getRange(rowIndex, 4).setValue(fmt(inDate));
    labelSheet.getRange(rowIndex, 5).setValue(status || "");
    labelSheet.getRange(rowIndex, 6).setValue(product || "");
    labelSheet.getRange(rowIndex, 7).setValue(""); // 출력일자
    labelSheet.getRange(rowIndex, 8).setValue("미출력"); // 출력여부
    rowIndex++;
    addedCount++;
  }


  // ✅ 조건에 맞는 데이터가 없다면 안내
  if (addedCount === 0) {
    SpreadsheetApp.getUi().alert("🆕 신규 파레트나 라벨 미출력 파레트가 없습니다.");
  } else {
    SpreadsheetApp.getUi().alert(`🆕 최근 7일 이내 미출력 파레트 ${addedCount}건이 불러와졌습니다.`);
  }
}




function generatePalletLabels() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const labelSheet = ss.getSheetByName("라벨출력대상");
  const lastRow = labelSheet.getLastRow();
  const data = labelSheet.getRange(1, 1, lastRow, labelSheet.getLastColumn()).getValues();
  let header = data[0];


  const requiredHeaders = ["출력일자", "출력여부"];
  requiredHeaders.forEach(h => {
    if (!header.includes(h)) {
      labelSheet.getRange(1, header.length + 1).setValue(h);
      header.push(h);
    }
  });


  const palletIdIdx = header.indexOf("파레트 ID");
  const printIdx = header.indexOf("출력 여부");
  const vendorIdx = header.indexOf("화주사 필터");
  const productIdx = header.indexOf("품목명");


  const selected = [];
  for (let i = 1; i < data.length; i++) {
    if (data[i][printIdx] === true) {
      selected.push({
        id: data[i][palletIdIdx],
        vendor: data[i][vendorIdx],
        product: data[i][productIdx]
      });
    }
  }


  if (selected.length === 0) {
    SpreadsheetApp.getUi().alert("선택된 라벨이 없습니다.");
    return;
  }


  const folder = (() => {
    const folders = DriveApp.getFoldersByName("라벨");
    return folders.hasNext() ? folders.next() : DriveApp.createFolder("라벨");
  })();


  const LABELS_PER_PAGE = 12;
  const LABELS_PER_ROW = 3;
  const LABEL_WIDTH_PT = 180;


  let docCount = 1;
  let count = 0;
  let doc = DocumentApp.create(`📦 파레트 라벨_${docCount}`);
  let body = doc.getBody();
  body.setMarginTop(22.4);
  body.setMarginBottom(0);
  body.setMarginLeft(17);
  body.setMarginRight(22.6);
  let table = body.appendTable();
  table.setBorderWidth(0);


  const docUrls = [];


  selected.forEach((row, i) => {
    if (count > 0 && count % LABELS_PER_PAGE === 0) {
      doc.saveAndClose();
      const file = DriveApp.getFileById(doc.getId());
      folder.addFile(file);
      DriveApp.getRootFolder().removeFile(file);
      docUrls.push(doc.getUrl());


      docCount++;
      doc = DocumentApp.create(`📦 파레트 라벨_${docCount}`);
      body = doc.getBody();
      body.setMarginTop(22.4);
      body.setMarginBottom(0);
      body.setMarginLeft(17);
      body.setMarginRight(22.6);
      table = body.appendTable();
      table.setBorderWidth(0);
    }


    if (count % LABELS_PER_ROW === 0) table.appendTableRow();
    const cell = table.getRow(table.getNumRows() - 1).appendTableCell();
    cell.setWidth(LABEL_WIDTH_PT);
    cell.appendParagraph(`📦 파레트 ID: ${row.id}`).setAlignment(DocumentApp.HorizontalAlignment.CENTER);
    cell.appendParagraph(`화주사: ${row.vendor}`).setAlignment(DocumentApp.HorizontalAlignment.CENTER);


    const fullUrl = `https://docs.google.com/forms/d/e/1FAIpQLSdDmnWcW27tfDptUvuSjEgN8K7nNNQWecdpeMMhwftTtbiyIQ/viewform?usp=pp_url` +
      `&entry.419411235=${encodeURIComponent(row.id)}&entry.427884801=보관종료` +
      `&entry.2110345042=${encodeURIComponent(row.vendor)}&entry.306824944=${encodeURIComponent(row.product)}`;
    const qrUrl = `https://quickchart.io/qr?text=${encodeURIComponent(fullUrl)}&size=200`;
    const blob = UrlFetchApp.fetch(qrUrl).getBlob();
    const para = cell.appendParagraph(" ").setAlignment(DocumentApp.HorizontalAlignment.CENTER);
    para.appendInlineImage(blob).setWidth(120).setHeight(120);
    cell.appendParagraph(row.product).setAlignment(DocumentApp.HorizontalAlignment.CENTER);
    cell.appendParagraph((count % LABELS_PER_PAGE < 9) ? "\n" : "\n\n");
    count++;
  });


  doc.saveAndClose();
  const file = DriveApp.getFileById(doc.getId());
  folder.addFile(file);
  DriveApp.getRootFolder().removeFile(file);
  docUrls.push(doc.getUrl());


  const cache = CacheService.getUserCache();
  cache.put("printedPalletIds", JSON.stringify(selected.map(r => (r.id + "").trim())), 600);


  const template = HtmlService.createTemplateFromFile("PrintConfirmationTemplate");
  template.docUrls = docUrls;
  const htmlOutput = template.evaluate().setWidth(400).setHeight(250);
  SpreadsheetApp.getUi().showModalDialog(htmlOutput, "📄 라벨 출력 완료");
}


function backupPrintStatus() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const labelSheet = ss.getSheetByName("라벨출력대상");
  const backupSheet = ss.getSheetByName("출력기록백업") || ss.insertSheet("출력기록백업");


  const labelData = labelSheet.getDataRange().getValues();
  const header = labelData[0];
  const idIdx = header.indexOf("파레트 ID");
  const dateIdx = header.indexOf("출력일자");
  const statusIdx = header.indexOf("출력여부");


  // ✅ 기존 백업을 Map 형태로 불러오기
  const backupMap = {};
  const backupData = backupSheet.getDataRange().getValues();
  for (let i = 1; i < backupData.length; i++) {
    const [id, date, status] = backupData[i];
    if (id) {
      backupMap[id] = { date, status };
    }
  }


  // ✅ 현재 라벨 시트에서 "출력완료"인 항목만 반영
  for (let i = 1; i < labelData.length; i++) {
    const id = (labelData[i][idIdx] + "").trim();
    const date = labelData[i][dateIdx];
    const status = (labelData[i][statusIdx] + "").trim();


    if (id && status === "출력완료") {
      backupMap[id] = { date, status };
    }
  }


  // ✅ 백업 시트 덮어쓰기 (하지만 누적된 내용 기준)
  const newData = [["파레트 ID", "출력일자", "출력여부"]];
  for (const id in backupMap) {
    const entry = backupMap[id];
    newData.push([id, entry.date, entry.status]);
  }


  backupSheet.clear();
  backupSheet.getRange(1, 1, newData.length, 3).setValues(newData);
}




function restorePrintStatus() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const labelSheet = ss.getSheetByName("라벨출력대상");
  const backupSheet = ss.getSheetByName("출력기록백업");
  if (!labelSheet || !backupSheet) return;


  const labelData = labelSheet.getDataRange().getValues();
  const backupData = backupSheet.getDataRange().getValues();


  const header = labelData[0];
  const idIdx = header.indexOf("파레트 ID");
  const dateIdx = header.indexOf("출력일자");
  const statusIdx = header.indexOf("출력여부");


  // ✅ 백업 데이터를 맵으로 만들어서 빠르게 접근
  const backupMap = {};
  for (let i = 1; i < backupData.length; i++) {
    const id = (backupData[i][0] + "").trim();  // ← 공백 제거!
    const date = backupData[i][1];
    const status = backupData[i][2];
    backupMap[id] = { date, status };
  }


  // ✅ 라벨 시트에서 ID 기준으로 복원
  for (let i = 1; i < labelData.length; i++) {
    const id = (labelData[i][idIdx] + "").trim();  // ← 공백 제거!
    if (backupMap[id]) {
      if (dateIdx !== -1) labelSheet.getRange(i + 1, dateIdx + 1).setValue(backupMap[id].date);
      if (statusIdx !== -1) labelSheet.getRange(i + 1, statusIdx + 1).setValue(backupMap[id].status);
    }
  }
}






// ✅ 출력확인 버튼 → 상태 기록
function confirmPrintStatus() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName("라벨출력대상");
  const data = sheet.getDataRange().getValues();
  const header = data[0];
  const idIdx = header.indexOf("파레트 ID");
  const dateIdx = header.indexOf("출력일자");
  const statusIdx = header.indexOf("출력여부");
  const cache = CacheService.getUserCache();

  // ✅ Cache 에 저장된 ID 로드 + 안전하게 trim 처리
  const idsRaw = JSON.parse(cache.get("printedPalletIds") || "[]");
  const ids = idsRaw.map(id => (id + "").trim());

  const today = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "yyyy.MM.dd");

  let updateCount = 0; // 몇 건 업데이트 되었는지 확인용

  for (let i = 1; i < data.length; i++) {
    const id = (data[i][idIdx] + "").trim(); // 여기도 반드시 trim 처리!
    if (ids.includes(id)) {
      if (dateIdx !== -1) sheet.getRange(i + 1, dateIdx + 1).setValue(today);
      if (statusIdx !== -1) {
        const cell = sheet.getRange(i + 1, statusIdx + 1);
        cell.setValue("출력완료").setBackground("#fff2cc");
      }
      updateCount++;
    }
  }

  // ✅ 출력 완료 후 자동 백업 실행
  backupPrintStatus();

  // ✅ Cache 삭제
  cache.remove("printedPalletIds");

  // ✅ 사용자에게 안내
  SpreadsheetApp.getUi().alert(`✅ ${updateCount}건의 라벨이 '출력완료'로 표시되었습니다.`);
}



// ✅ 팝업에서 문서 링크 호출용
function getLastLabelDocUrl() {
  const cache = CacheService.getUserCache();
  return cache.get("lastLabelDocUrl") || "";
}





















