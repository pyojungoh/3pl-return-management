/**
 * 📝 입력용 시트 관리 시스템
 * 
 * 주요 기능:
 * - 설문지 응답 시트1과 동일한 구조의 입력용 시트 생성
 * - 대량 데이터 입력 및 저장
 * - 데이터 검증 및 오류 처리
 * - 편의 기능 제공
 */

// ========================================
// 📋 입력용 시트 생성 및 관리
// ========================================

/**
 * 입력용 시트 생성
 */
function createInputSheet() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    let inputSheet = ss.getSheetByName("입력용");
    
    // 기존 시트가 있으면 삭제하고 새로 생성
    if (inputSheet) {
      ss.deleteSheet(inputSheet);
    }
    
    inputSheet = ss.insertSheet("입력용");
    
    // 헤더 설정
    const headers = [
      "타임스탬프", "파레트 ID", "작업 유형", "화주사", "품목명", "작업 수량", "보관 위치"
    ];
    
    inputSheet.getRange("A1:G1").setValues([headers]);
    inputSheet.getRange("A1:G1").setFontWeight("bold").setBackground("#e1f5fe");
    
    // 열 너비 설정
    inputSheet.setColumnWidth(1, 120); // 타임스탬프
    inputSheet.setColumnWidth(2, 120); // 파레트 ID
    inputSheet.setColumnWidth(3, 100); // 작업 유형
    inputSheet.setColumnWidth(4, 120); // 화주사
    inputSheet.setColumnWidth(5, 150); // 품목명
    inputSheet.setColumnWidth(6, 80);  // 작업 수량
    inputSheet.setColumnWidth(7, 100); // 보관 위치
    
    // 입력 영역 준비 (A2~G100)
    inputSheet.getRange("A2:G100").clearContent();
    
    // 동적 확장을 위한 헬퍼 함수 등록
    setupDynamicExpansion(inputSheet);
    
    // 기본값 설정
    setupInputSheetDefaults(inputSheet);
    
    // 데이터 검증 설정
    setupDataValidation(inputSheet);
    
    SpreadsheetApp.getUi().alert("✅ 입력용 시트가 생성되었습니다.\n\nA2부터 데이터를 입력하세요.");
    
  } catch (error) {
    console.error('입력용 시트 생성 실패:', error);
    SpreadsheetApp.getUi().alert('입력용 시트 생성 실패: ' + error.message);
  }
}

/**
 * 입력용 시트 기본값 설정 (필요한 행만)
 */
function setupInputSheetDefaults(inputSheet) {
  try {
    // A열(타임스탬프)에 오늘 날짜 기본값 설정 (A2~A10만)
    const today = new Date();
    const todayStr = Utilities.formatDate(today, Session.getScriptTimeZone(), "yyyy-MM-dd");
    
    // A2~A10에만 오늘 날짜 기본값 설정
    for (let i = 2; i <= 10; i++) {
      inputSheet.getRange(i, 1).setValue(todayStr);
    }
    
    // 날짜 형식 적용 (A2~A10만)
    inputSheet.getRange("A2:A10").setNumberFormat("yyyy-MM-dd");
    
  } catch (error) {
    console.error('기본값 설정 실패:', error);
  }
}

/**
 * 데이터 검증 설정 (필요한 행만)
 */
function setupDataValidation(inputSheet) {
  try {
    // C열(작업 유형) 드롭다운 설정 (C2~C10만)
    const workTypes = ["입고", "출고", "사용중", "보관종료", "서비스"];
    const workTypeRule = SpreadsheetApp.newDataValidation()
      .requireValueInList(workTypes, true)
      .setAllowInvalid(false)
      .build();
    inputSheet.getRange("C2:C10").setDataValidation(workTypeRule);
    
    // F열(작업 수량) 숫자 형식 설정 (F2~F10만)
    inputSheet.getRange("F2:F10").setNumberFormat("0");
    
  } catch (error) {
    console.error('데이터 검증 설정 실패:', error);
  }
}

// ========================================
// 💾 데이터 저장 및 처리
// ========================================

/**
 * 입력 데이터 저장
 */
function saveInputData() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const inputSheet = ss.getSheetByName("입력용");
    const responseSheet = ss.getSheetByName("설문지 응답 시트1");
    
    if (!inputSheet) {
      SpreadsheetApp.getUi().alert("입력용 시트가 없습니다. 먼저 입력용 시트를 생성하세요.");
      return;
    }
    
    if (!responseSheet) {
      SpreadsheetApp.getUi().alert("설문지 응답 시트1이 없습니다.");
      return;
    }
    
    // 입력용 시트에서 데이터 읽기
    const inputData = inputSheet.getRange("A2:G100").getValues();
    
    // 빈 행 제거 및 데이터 검증
    const validData = [];
    const errors = [];
    
    for (let i = 0; i < inputData.length; i++) {
      const row = inputData[i];
      const rowNum = i + 2; // 실제 행 번호
      
      // 파레트 ID가 있는 행만 처리
      if (row[1] && row[1].toString().trim()) {
        // 데이터 검증
        const validation = validateInputRow(row, rowNum);
        if (validation.isValid) {
          validData.push(row);
        } else {
          errors.push(...validation.errors);
        }
      }
    }
    
    if (validData.length === 0) {
      SpreadsheetApp.getUi().alert("저장할 데이터가 없습니다.");
      return;
    }
    
    // 오류가 있으면 사용자에게 알림
    if (errors.length > 0) {
      const errorMsg = "다음 오류가 있습니다:\n\n" + errors.join("\n") + 
                      "\n\n오류를 수정한 후 다시 시도하세요.";
      SpreadsheetApp.getUi().alert(errorMsg);
      return;
    }
    
    // 설문지 응답 시트1에 추가
    responseSheet.getRange(responseSheet.getLastRow() + 1, 1, validData.length, 7)
      .setValues(validData);
    
    // 입력용 시트 초기화
    clearInputSheet();
    
    // 성공 메시지
    SpreadsheetApp.getUi().alert(`✅ ${validData.length}개 데이터가 성공적으로 저장되었습니다.`);
    
    // 감사 로그 기록
    if (typeof logAuditEvent === 'function') {
      logAuditEvent('INFO', 'Input data saved', { count: validData.length });
    }
    
  } catch (error) {
    console.error('데이터 저장 실패:', error);
    SpreadsheetApp.getUi().alert('데이터 저장 실패: ' + error.message);
  }
}

/**
 * 입력 행 데이터 검증
 */
function validateInputRow(row, rowNum) {
  const errors = [];
  
  // 필수 항목 체크
  if (!row[0] || !row[0].toString().trim()) {
    errors.push(`행 ${rowNum}: 타임스탬프(입고일)는 필수입니다.`);
  }
  
  if (!row[1] || !row[1].toString().trim()) {
    errors.push(`행 ${rowNum}: 파레트 ID는 필수입니다.`);
  }
  
  if (!row[2] || !row[2].toString().trim()) {
    errors.push(`행 ${rowNum}: 작업 유형은 필수입니다.`);
  }
  
  if (!row[3] || !row[3].toString().trim()) {
    errors.push(`행 ${rowNum}: 화주사는 필수입니다.`);
  }
  
  if (!row[4] || !row[4].toString().trim()) {
    errors.push(`행 ${rowNum}: 품목명은 필수입니다.`);
  }
  
  // 날짜 형식 검증
  if (row[0]) {
    const dateStr = row[0].toString().trim();
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) {
      errors.push(`행 ${rowNum}: 타임스탬프 형식이 올바르지 않습니다. (예: 2024-01-15)`);
    } else {
      // 미래 날짜 체크
      const today = new Date();
      today.setHours(23, 59, 59, 999);
      if (date > today) {
        errors.push(`행 ${rowNum}: 미래 날짜는 입력할 수 없습니다.`);
      }
    }
  }
  
  // 작업 수량 검증
  if (row[5] && isNaN(Number(row[5]))) {
    errors.push(`행 ${rowNum}: 작업 수량은 숫자여야 합니다.`);
  }
  
  return {
    isValid: errors.length === 0,
    errors: errors
  };
}

// ========================================
// 🧹 시트 관리 및 편의 기능
// ========================================

/**
 * 동적 확장 설정
 */
function setupDynamicExpansion(inputSheet) {
  try {
    // onEdit 트리거를 사용하여 동적 확장
    // 사용자가 데이터를 입력하면 해당 행에 설정 적용
    const scriptId = ScriptApp.getScriptId();
    const triggers = ScriptApp.getProjectTriggers();
    
    // 기존 onEdit 트리거 제거
    triggers.forEach(trigger => {
      if (trigger.getHandlerFunction() === 'onInputSheetEdit') {
        ScriptApp.deleteTrigger(trigger);
      }
    });
    
    // 새 onEdit 트리거 생성
    ScriptApp.newTrigger('onInputSheetEdit')
      .for(inputSheet)
      .onEdit()
      .create();
    
  } catch (error) {
    console.error('동적 확장 설정 실패:', error);
  }
}

/**
 * 입력용 시트 편집 이벤트 처리
 */
function onInputSheetEdit(e) {
  try {
    const range = e.range;
    const sheet = e.source.getActiveSheet();
    
    // 입력용 시트가 아니면 무시
    if (sheet.getName() !== '입력용') return;
    
    const row = range.getRow();
    const col = range.getColumn();
    
    // A열(타임스탬프) 편집 시
    if (col === 1 && row >= 2) {
      setupRowDefaults(sheet, row);
    }
    
    // C열(작업 유형) 편집 시
    if (col === 3 && row >= 2) {
      setupRowValidation(sheet, row);
    }
    
  } catch (error) {
    console.error('편집 이벤트 처리 실패:', error);
  }
}

/**
 * 특정 행에 기본값 설정
 */
function setupRowDefaults(sheet, row) {
  try {
    const cell = sheet.getRange(row, 1);
    const value = cell.getValue();
    
    // 빈 셀이면 오늘 날짜 설정
    if (!value || value.toString().trim() === '') {
      const today = new Date();
      const todayStr = Utilities.formatDate(today, Session.getScriptTimeZone(), "yyyy-MM-dd");
      cell.setValue(todayStr);
      cell.setNumberFormat("yyyy-MM-dd");
    }
    
  } catch (error) {
    console.error('행 기본값 설정 실패:', error);
  }
}

/**
 * 특정 행에 검증 설정
 */
function setupRowValidation(sheet, row) {
  try {
    // C열(작업 유형) 드롭다운 설정
    const workTypes = ["입고", "출고", "사용중", "보관종료", "서비스"];
    const workTypeRule = SpreadsheetApp.newDataValidation()
      .requireValueInList(workTypes, true)
      .setAllowInvalid(false)
      .build();
    sheet.getRange(row, 3).setDataValidation(workTypeRule);
    
    // F열(작업 수량) 숫자 형식 설정
    sheet.getRange(row, 6).setNumberFormat("0");
    
  } catch (error) {
    console.error('행 검증 설정 실패:', error);
  }
}

/**
 * 입력용 시트 초기화 (스마트 초기화)
 */
function clearInputSheet() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const inputSheet = ss.getSheetByName("입력용");
    
    if (!inputSheet) {
      SpreadsheetApp.getUi().alert("입력용 시트가 없습니다.");
      return;
    }
    
    // 사용된 행만 찾아서 초기화
    const data = inputSheet.getRange("A2:G100").getValues();
    let clearedRows = 0;
    
    for (let i = 0; i < data.length; i++) {
      const row = data[i];
      // 파레트 ID가 있는 행만 초기화
      if (row[1] && row[1].toString().trim()) {
        inputSheet.getRange(i + 2, 1, 1, 7).clearContent();
        clearedRows++;
      }
    }
    
    // 기본값 다시 설정 (A2~A10만)
    setupInputSheetDefaults(inputSheet);
    
    SpreadsheetApp.getUi().alert(`✅ 입력용 시트가 초기화되었습니다.\n(초기화된 행: ${clearedRows}개)`);
    
  } catch (error) {
    console.error('시트 초기화 실패:', error);
    SpreadsheetApp.getUi().alert('시트 초기화 실패: ' + error.message);
  }
}

/**
 * 샘플 데이터 입력
 */
function insertSampleData() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const inputSheet = ss.getSheetByName("입력용");
    
    if (!inputSheet) {
      SpreadsheetApp.getUi().alert("입력용 시트가 없습니다. 먼저 입력용 시트를 생성하세요.");
      return;
    }
    
    const today = new Date();
    const todayStr = Utilities.formatDate(today, Session.getScriptTimeZone(), "yyyy-MM-dd");
    
    const sampleData = [
      [todayStr, "250930_001", "입고", "ABC회사", "상품A", 100, "A-01"],
      [todayStr, "250930_002", "입고", "XYZ회사", "상품B", 50, "A-02"],
      [todayStr, "250930_003", "입고", "DEF회사", "상품C", 200, "B-01"]
    ];
    
    inputSheet.getRange("A2:G4").setValues(sampleData);
    
    SpreadsheetApp.getUi().alert("✅ 샘플 데이터가 입력되었습니다.\n\nA2~G4 영역을 확인하세요.");
    
  } catch (error) {
    console.error('샘플 데이터 입력 실패:', error);
    SpreadsheetApp.getUi().alert('샘플 데이터 입력 실패: ' + error.message);
  }
}

/**
 * 입력 데이터 미리보기
 */
function previewInputData() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const inputSheet = ss.getSheetByName("입력용");
    
    if (!inputSheet) {
      SpreadsheetApp.getUi().alert("입력용 시트가 없습니다.");
      return;
    }
    
    const inputData = inputSheet.getRange("A2:G100").getValues();
    const validData = inputData.filter(row => row[1] && row[1].toString().trim());
    
    if (validData.length === 0) {
      SpreadsheetApp.getUi().alert("미리보기할 데이터가 없습니다.");
      return;
    }
    
    let previewText = `📋 입력 데이터 미리보기 (${validData.length}개)\n\n`;
    
    validData.slice(0, 10).forEach((row, index) => {
      previewText += `${index + 1}. ${row[0]} | ${row[1]} | ${row[2]} | ${row[3]} | ${row[4]} | ${row[5]} | ${row[6]}\n`;
    });
    
    if (validData.length > 10) {
      previewText += `\n... 외 ${validData.length - 10}개 더`;
    }
    
    SpreadsheetApp.getUi().alert(previewText);
    
  } catch (error) {
    console.error('미리보기 실패:', error);
    SpreadsheetApp.getUi().alert('미리보기 실패: ' + error.message);
  }
}

// ========================================
// 🔄 기존 메뉴에 통합
// ========================================

/**
 * 입력용 시트 메뉴 설정
 */
function setupInputSheetMenu(ui) {
  ui.createMenu("📝 데이터 입력")
    .addItem("📋 입력용 시트 생성", "createInputSheet")
    .addItem("⚡ 신규 파레트 저장 및 적용", "saveAndProcessNewPallets")
    .addItem("🧹 입력 시트 초기화", "clearInputSheet")
    .addSeparator()
    .addItem("📄 샘플 데이터 입력", "insertSampleData")
    .addItem("👁️ 데이터 미리보기", "previewInputData")
    .addSeparator()
    .addItem("🗑️ 보관종료 정리", "cleanupCompletedData")
    .addItem("👀 삭제 대상 미리보기", "previewDeletionTargets")
    .addItem("🔍 보관종료 데이터 상세 확인", "checkRemainingCompletedData")
    .addSeparator()
    .addItem("🎨 화주사 시트 서식 정리", "cleanupVendorSheetFormatting")
    .addToUi();
}

// ========================================
// ⚡ 신규 파레트 증분 정산 (빠른 업데이트)
// ========================================

/**
 * 신규 파레트 저장 및 적용 (통합 버튼)
 */
function saveAndProcessNewPallets() {
  try {
    // 1단계: 입력 데이터 저장
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const inputSheet = ss.getSheetByName("입력용");
    const responseSheet = ss.getSheetByName("설문지 응답 시트1");
    
    if (!inputSheet) {
      SpreadsheetApp.getUi().alert("입력용 시트가 없습니다.");
      return;
    }
    
    if (!responseSheet) {
      SpreadsheetApp.getUi().alert("설문지 응답 시트1이 없습니다.");
      return;
    }
    
    // 입력용 시트에서 데이터 읽기
    const inputData = inputSheet.getRange("A2:G100").getValues();
    
    // 빈 행 제거 및 데이터 검증
    const validData = [];
    const errors = [];
    const palletIds = [];
    
    for (let i = 0; i < inputData.length; i++) {
      const row = inputData[i];
      const rowNum = i + 2;
      
      // 파레트 ID가 있는 행만 처리
      if (row[1] && row[1].toString().trim()) {
        // 데이터 검증
        const validation = validateInputRow(row, rowNum);
        if (validation.isValid) {
          validData.push(row);
          palletIds.push(row[1].toString().trim());
        } else {
          errors.push(...validation.errors);
        }
      }
    }
    
    if (validData.length === 0) {
      SpreadsheetApp.getUi().alert("저장할 데이터가 없습니다.");
      return;
    }
    
    // 오류가 있으면 사용자에게 알림
    if (errors.length > 0) {
      const errorMsg = "다음 오류가 있습니다:\n\n" + errors.join("\n") + 
                      "\n\n오류를 수정한 후 다시 시도하세요.";
      SpreadsheetApp.getUi().alert(errorMsg);
      return;
    }
    
    // 설문지 응답 시트1에 추가
    responseSheet.getRange(responseSheet.getLastRow() + 1, 1, validData.length, 7)
      .setValues(validData);
    
    console.log(`${validData.length}개 데이터 저장 완료`);
    
    // 2단계: 신규 파레트 정산 실행
    const summarySheet = ss.getSheetByName("파레트 요약 정산");
    
    if (!summarySheet) {
      SpreadsheetApp.getUi().alert(`✅ ${validData.length}개 데이터가 저장되었습니다.\n\n⚠️ 파레트 요약 정산 시트가 없습니다.\n먼저 전체 정산을 실행하세요.`);
      return;
    }
    
    // 중복 제거
    const uniquePalletIds = [...new Set(palletIds)];
    
    console.log(`처리할 파레트 ID: ${uniquePalletIds.join(', ')}`);
    
    // 설문지 응답 시트1에서 해당 파레트들만 집계
    const palletSummaries = summarizeSpecificPallets(responseSheet, uniquePalletIds);
    
    console.log(`집계된 파레트 수: ${Object.keys(palletSummaries).length}`);
    console.log(`집계된 파레트: ${Object.keys(palletSummaries).join(', ')}`);
    
    if (Object.keys(palletSummaries).length === 0) {
      SpreadsheetApp.getUi().alert(`✅ ${validData.length}개 데이터가 저장되었습니다.\n\n⚠️ 해당 파레트 데이터를 찾을 수 없습니다.`);
      return;
    }
    
    // 파레트 요약 정산에 업데이트
    console.log("파레트 요약 정산 업데이트 시작...");
    updateSummarySheet(summarySheet, palletSummaries);
    console.log("파레트 요약 정산 업데이트 완료");
    
    // 화주사별 시트에 업데이트
    console.log("화주사별 시트 업데이트 시작...");
    updateVendorSheets(ss, palletSummaries);
    console.log("화주사별 시트 업데이트 완료");
    
    // 입력용 시트 초기화
    clearInputSheet();
    
    // 결과 알림
    SpreadsheetApp.getUi().alert(`⚡ 저장 및 정산 완료!\n\n` +
      `💾 저장된 데이터: ${validData.length}개\n` +
      `📦 처리된 파레트: ${uniquePalletIds.length}개\n` +
      `🏢 업데이트된 화주사: ${Object.keys(palletSummaries).map(id => palletSummaries[id]["화주사"]).filter((v, i, a) => a.indexOf(v) === i).length}개\n\n` +
      `✅ 입력용 시트가 초기화되었습니다.`);
    
  } catch (error) {
    console.error('저장 및 정산 실패:', error);
    SpreadsheetApp.getUi().alert('저장 및 정산 실패: ' + error.message);
  }
}

/**
 * 신규 파레트만 빠르게 정산 (저장 없이 정산만)
 */
function processNewPalletsOnly() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const inputSheet = ss.getSheetByName("입력용");
    const responseSheet = ss.getSheetByName("설문지 응답 시트1");
    const summarySheet = ss.getSheetByName("파레트 요약 정산");
    
    if (!inputSheet) {
      SpreadsheetApp.getUi().alert("입력용 시트가 없습니다.");
      return;
    }
    
    if (!responseSheet) {
      SpreadsheetApp.getUi().alert("설문지 응답 시트1이 없습니다.");
      return;
    }
    
    if (!summarySheet) {
      SpreadsheetApp.getUi().alert("파레트 요약 정산 시트가 없습니다.\n먼저 전체 정산을 실행하세요.");
      return;
    }
    
    // 입력용 시트에서 파레트 ID 추출
    const inputData = inputSheet.getRange("A2:G100").getValues();
    const newPalletIds = [];
    
    for (let i = 0; i < inputData.length; i++) {
      const row = inputData[i];
      const palletId = row[1]; // B열: 파레트 ID
      if (palletId && palletId.toString().trim()) {
        newPalletIds.push(palletId.toString().trim());
      }
    }
    
    if (newPalletIds.length === 0) {
      SpreadsheetApp.getUi().alert("입력용 시트에 파레트 데이터가 없습니다.");
      return;
    }
    
    // 중복 제거
    const uniquePalletIds = [...new Set(newPalletIds)];
    
    console.log(`처리할 파레트 ID: ${uniquePalletIds.join(', ')}`);
    
    // 설문지 응답 시트1에서 해당 파레트들만 집계
    const palletSummaries = summarizeSpecificPallets(responseSheet, uniquePalletIds);
    
    if (Object.keys(palletSummaries).length === 0) {
      SpreadsheetApp.getUi().alert("해당 파레트 데이터를 찾을 수 없습니다.");
      return;
    }
    
    // 파레트 요약 정산에 업데이트
    updateSummarySheet(summarySheet, palletSummaries);
    
    // 화주사별 시트에 업데이트
    updateVendorSheets(ss, palletSummaries);
    
    // 결과 알림
    SpreadsheetApp.getUi().alert(`⚡ 신규 파레트 정산 완료!\n\n` +
      `📦 처리된 파레트: ${uniquePalletIds.length}개\n` +
      `🏢 업데이트된 화주사: ${Object.keys(palletSummaries).map(id => palletSummaries[id]["화주사"]).filter((v, i, a) => a.indexOf(v) === i).length}개\n\n` +
      `빠르게 처리되었습니다!`);
    
  } catch (error) {
    console.error('신규 파레트 정산 실패:', error);
    SpreadsheetApp.getUi().alert('신규 파레트 정산 실패: ' + error.message);
  }
}

/**
 * 특정 파레트들만 집계
 */
function summarizeSpecificPallets(responseSheet, palletIds) {
  try {
    const data = responseSheet.getDataRange().getValues();
    const header = data[0];
    
    const idIdx = header.indexOf("파레트 ID");
    const typeIdx = header.indexOf("작업 유형");
    const qtyIdx = header.indexOf("작업 수량");
    const timeIdx = header.indexOf("타임스탬프");
    const productIdx = header.indexOf("품목명");
    const vendorIdx = header.indexOf("화주사");
    
    if (idIdx === -1 || typeIdx === -1 || qtyIdx === -1 || timeIdx === -1) {
      throw new Error("필수 컬럼을 찾을 수 없습니다.");
    }
    
    const summary = {};
    const today = new Date();
    
    // 해당 파레트 ID만 집계
    for (let i = 1; i < data.length; i++) {
      const id = data[i][idIdx];
      
      // 지정된 파레트 ID만 처리
      if (!id || !palletIds.includes(id.toString().trim())) {
        continue;
      }
      
      const type = data[i][typeIdx];
      const qty = Number(data[i][qtyIdx]) || 0;
      const time = new Date(data[i][timeIdx]);
      const product = (data[i][productIdx] || "무기입").toString().trim();
      const vendor = data[i][vendorIdx];
      
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
      
      // 작업 유형별 처리 (기존 로직 그대로)
      if (type === "입고") {
        summary[id]["입고 수량"] += qty;
        summary[id]["입고일후보"].push(time);
      } else if (type === "사용중") {
        summary[id]["사용중 여부"] = true;
        summary[id]["입고일후보"].push(time);
      } else if (type === "보관종료") {
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
    
    return summary;
    
  } catch (error) {
    console.error('특정 파레트 집계 실패:', error);
    return {};
  }
}

/**
 * 파레트 요약 정산 시트 업데이트
 */
function updateSummarySheet(summarySheet, palletSummaries) {
  try {
    const existingData = summarySheet.getDataRange().getValues();
    const header = existingData[0];
    const today = new Date();
    
    // 설정 시트에서 보관료 정보 가져오기
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const configSheet = ss.getSheetByName("설정") || ss.insertSheet("설정");
    const configData = configSheet.getDataRange().getValues();
    
    // getDailyFee 함수 재정의 (로컬)
    function getDailyFee(date, vendor) {
      if (vendor && typeof getVendorMonthlyFee === 'function') {
        const vendorFee = getVendorMonthlyFee(vendor);
        if (vendorFee > 0) {
          return Math.round(vendorFee / 30.44);
        }
      }
      
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
    
    // calculateFee 함수 재정의 (로컬)
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
      const roundedFee = Math.ceil(totalFee / 100) * 100;
      return { days: totalDays, fee: roundedFee };
    }
    
    // 각 파레트 처리
    for (const id in palletSummaries) {
      const e = palletSummaries[id];
      const 남은 = e["입고 수량"] - e["출고 수량"];
      let 상태 = "";
      let 갱신일 = "";
      let 보관일수 = 0;
      let 보관료 = 0;
      let 입고일 = e["입고일후보"].length > 0
        ? new Date(Math.min(...e["입고일후보"].map(d => d.getTime())))
        : null;
      
      // 상태 판단 (기존 로직 그대로)
      if (e["서비스 여부"]) {
        상태 = "서비스";
      } else if (e["보관종료 여부"]) {
        상태 = "보관종료";
      } else if (e["사용중 여부"]) {
        상태 = "사용중";
      } else {
        상태 = "입고됨";
      }
      
      // 보관료 계산 (기존 로직 그대로)
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
          
          // 보관종료가 이번달이 아닌 경우 보관료 제외
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
      
      const newRow = [
        e["파레트 ID"], e["화주사"], e["품목명"], e["입고 수량"], e["출고 수량"], 남은,
        입고일, e["출고일"], e["보관종료일"], 상태, 갱신일,
        e["서비스 여부"] ? 0 : 보관일수,
        e["서비스 여부"] ? 0 : 보관료
      ];
      
      // 기존 행 찾기
      let found = false;
      for (let i = 1; i < existingData.length; i++) {
        if (existingData[i][0] === id) {
          // 기존 행 업데이트
          summarySheet.getRange(i + 1, 1, 1, newRow.length).setValues([newRow]);
          found = true;
          console.log(`파레트 ${id} 업데이트됨`);
          break;
        }
      }
      
      // 신규 행 추가
      if (!found) {
        summarySheet.appendRow(newRow);
        console.log(`파레트 ${id} 신규 추가됨`);
      }
    }
    
    // 날짜 포맷 적용
    const lastRow = summarySheet.getLastRow();
    summarySheet.getRange(2, 7, lastRow - 1, 1).setNumberFormat("yyyy.MM.dd");
    summarySheet.getRange(2, 8, lastRow - 1, 1).setNumberFormat("yyyy.MM.dd");
    summarySheet.getRange(2, 9, lastRow - 1, 1).setNumberFormat("yyyy.MM.dd");
    summarySheet.getRange(2, 11, lastRow - 1, 1).setNumberFormat("yyyy.MM.dd");
    
  } catch (error) {
    console.error('파레트 요약 정산 업데이트 실패:', error);
    throw error;
  }
}

/**
 * 화주사별 시트 업데이트 (Code.js의 splitByVendor 로직 그대로 사용)
 */
function updateVendorSheets(ss, palletSummaries) {
  try {
    const summarySheet = ss.getSheetByName("파레트 요약 정산");
    const data = summarySheet.getDataRange().getValues();
    const header = data[0];
    const vendorIdx = header.indexOf("화주사");
    const remarkIdx = header.length; // 비고 추가 예정
    const feeColIdx = header.indexOf("보관료(원)"); // 보관료 열 인덱스 추가

    // 화주사별로 그룹화 (Code.js와 동일한 로직)
    const vendorMap = {};
    const vendorNameMap = {}; // 원본 이름 → 정규화된 이름 매핑
    
    for (let i = 1; i < data.length; i++) {
      const row = data[i];
      const originalVendor = row[vendorIdx] || "미지정";
      const normalizedVendor = normalizeVendorName(originalVendor);
      
      // 정규화된 이름으로 그룹화
      if (!vendorMap[normalizedVendor]) {
        vendorMap[normalizedVendor] = [];
        vendorNameMap[normalizedVendor] = originalVendor; // 원본 이름 저장
      }
      vendorMap[normalizedVendor].push(row);
    }

    // 각 화주사별 시트 생성 (Code.js의 splitByVendor 로직 그대로)
    for (const normalizedVendor in vendorMap) {
      const originalVendor = vendorNameMap[normalizedVendor];
      const sheetName = originalVendor.length > 0 ? sanitizeSheetName(originalVendor) : "미지정";
      let sheet = ss.getSheetByName(sheetName) || ss.insertSheet(sheetName);
      
      console.log(`처리 중인 화주사: ${originalVendor} (시트명: ${sheetName})`);
      
      const lastRow = sheet.getLastRow();
      const oldRemarks = lastRow >= 2
        ? sheet.getRange(2, remarkIdx + 1, lastRow - 1).getValues()
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
      if (feeColIdx !== -1) {
        const feeRange = sheet.getRange(2, feeColIdx + 1, cleanedRows.length, 1);
        feeRange.setNumberFormat("#,##0");
        feeRange.setHorizontalAlignment("right");  // 보관료 열만 우측 정렬
        feeRange.setFontWeight("normal");
        feeRange.setFontColor("#000000");
        feeRange.setFontStyle("normal");
        feeRange.setFontSize(10);
      }

      // ⭐ 보관료 총계 추가 로직 시작 (Code.js와 동일)
      if (feeColIdx !== -1 && cleanedRows.length > 0) { // 보관료 열이 있고 데이터가 있을 경우에만
        const totalLabelCol = 1; // '총 보관료 합계'를 A열에 표시
        const totalValueCol = feeColIdx + 1; // 보관료 값은 해당 열에 표시

        const lastDataRow = sheet.getLastRow();
        const totalRowIndex = lastDataRow + 2; // 데이터 마지막 행 + 1 (빈 칸) + 1 (총계 행)

        // '총 보관료 합계' 라벨
        sheet.getRange(totalRowIndex, totalLabelCol).setValue("총 보관료 합계")
          .setFontWeight("bold")
          .setFontSize(12)
          .setHorizontalAlignment("right")
          .setBackground("#e6e6e6");

        // 보관료 합계 계산 수식 (데이터가 2행부터 시작하므로)
        const formulaRange = `${String.fromCharCode(65 + feeColIdx)}2:${String.fromCharCode(65 + feeColIdx)}${lastDataRow}`;
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
      
      console.log(`화주사 시트 ${sheetName} 업데이트 완료`);
    }
    
  } catch (error) {
    console.error('화주사별 시트 업데이트 실패:', error);
    throw error;
  }
}


/**
 * 화주사별 시트 총계 업데이트 (기존 함수 유지)
 */
function updateVendorSheetTotal(vendorSheet) {
  try {
    const data = vendorSheet.getDataRange().getValues();
    const header = data[0];
    const feeIdx = header.indexOf("보관료(원)");
    
    if (feeIdx === -1) return;
    
    // 총계 행 찾기
    for (let i = data.length - 1; i >= 0; i--) {
      const cellValue = data[i][0];
      if (cellValue && cellValue.toString().includes("총 보관료 합계")) {
        const totalRowNum = i + 1;
        const feeColLetter = String.fromCharCode(65 + feeIdx);
        const formulaRange = `${feeColLetter}2:${feeColLetter}${totalRowNum - 2}`;
        vendorSheet.getRange(totalRowNum, feeIdx + 1).setFormula(`=SUM(${formulaRange})`);
        console.log(`총계 업데이트: ${vendorSheet.getName()}`);
        break;
      }
    }
    
  } catch (error) {
    console.error('총계 업데이트 실패:', error);
  }
}

// ========================================
// 🗑️ 보관종료 데이터 정리 기능
// ========================================

/**
 * 삭제 대상 미리보기
 */
function previewDeletionTargets() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const responseSheet = ss.getSheetByName("설문지 응답 시트1");
    
    if (!responseSheet) {
      SpreadsheetApp.getUi().alert("설문지 응답 시트1이 없습니다.");
      return;
    }
    
    const deletionTargets = getDeletionTargets(responseSheet);
    
    if (deletionTargets.length === 0) {
      SpreadsheetApp.getUi().alert("삭제할 보관종료 데이터가 없습니다.");
      return;
    }
    
    // 삭제 대상 정보 수집
    const stats = analyzeDeletionTargets(deletionTargets);
    
    // 미리보기 메시지 생성
    let previewMessage = `🗑️ 삭제 대상 미리보기\n\n`;
    previewMessage += `📊 총 삭제 개수: ${stats.totalCount}개\n`;
    previewMessage += `📅 삭제 기준: ${stats.cutoffDate} 이전\n`;
    previewMessage += `🏢 화주사별 개수:\n`;
    
    Object.entries(stats.vendorCount).forEach(([vendor, count]) => {
      previewMessage += `  • ${vendor}: ${count}개\n`;
    });
    
    previewMessage += `\n⚠️ 주의: 이 작업은 되돌릴 수 없습니다.\n`;
    previewMessage += `백업을 권장합니다.`;
    
    SpreadsheetApp.getUi().alert(previewMessage);
    
  } catch (error) {
    console.error('삭제 대상 미리보기 실패:', error);
    SpreadsheetApp.getUi().alert('미리보기 실패: ' + error.message);
  }
}

/**
 * 보관종료 데이터 상세 확인
 */
function checkRemainingCompletedData() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const responseSheet = ss.getSheetByName("설문지 응답 시트1");
    
    if (!responseSheet) {
      SpreadsheetApp.getUi().alert("설문지 응답 시트1이 없습니다.");
      return;
    }
    
    const data = responseSheet.getDataRange().getValues();
    const header = data[0];
    
    // 컬럼 인덱스 찾기 (설문지 응답 시트1 구조)
    const timestampIdx = header.indexOf("타임스탬프");
    const workTypeIdx = header.indexOf("작업 유형");
    const palletIdIdx = header.indexOf("파레트 ID");
    const vendorIdx = header.indexOf("화주사");
    
    if (timestampIdx === -1 || workTypeIdx === -1) {
      SpreadsheetApp.getUi().alert("필수 컬럼을 찾을 수 없습니다.");
      return;
    }
    
    // 현재 월에서 2개월 전 계산
    const now = new Date();
    const cutoffDate = new Date(now.getFullYear(), now.getMonth() - 2, 1);
    
    console.log(`현재 날짜: ${Utilities.formatDate(now, Session.getScriptTimeZone(), "yyyy.MM.dd")}`);
    console.log(`삭제 기준 날짜: ${Utilities.formatDate(cutoffDate, Session.getScriptTimeZone(), "yyyy.MM.dd")}`);
    
    // 모든 보관종료 데이터 찾기
    const allCompletedData = [];
    const oldCompletedData = [];
    
    for (let i = 1; i < data.length; i++) {
      const row = data[i];
      const workType = row[workTypeIdx];
      const timestamp = row[timestampIdx];
      
      if (workType === "보관종료") {
        const dataInfo = {
          rowIndex: i + 1,
          palletId: row[palletIdIdx] || "미지정",
          vendor: row[vendorIdx] || "미지정",
          timestamp: timestamp,
          dateStr: timestamp instanceof Date ? 
            Utilities.formatDate(timestamp, Session.getScriptTimeZone(), "yyyy.MM.dd") : 
            timestamp.toString()
        };
        
        allCompletedData.push(dataInfo);
        console.log(`보관종료 데이터: ${dataInfo.palletId} (${dataInfo.vendor}) - ${dataInfo.dateStr}, 타입: ${typeof timestamp}`);
        
        // 전전달 이전 데이터인지 확인
        let isOldData = false;
        
        if (timestamp instanceof Date && timestamp < cutoffDate) {
          isOldData = true;
        } else if (typeof timestamp === 'string') {
          // 문자열로 된 날짜 처리 (7월 10일 등)
          const dateStr = timestamp.toString();
          if (dateStr.includes('2025.07.10')) {
            isOldData = true;
            console.log(`7월 10일 데이터 발견: ${dataInfo.palletId} - ${dateStr}`);
          }
        }
        
        if (isOldData) {
          oldCompletedData.push(dataInfo);
          console.log(`삭제 대상: ${dataInfo.palletId} (${dataInfo.vendor}) - ${dataInfo.dateStr}`);
        }
      }
    }
    
    // 결과 메시지 생성
    let message = `🔍 보관종료 데이터 상세 확인\n\n`;
    message += `전체 보관종료 데이터: ${allCompletedData.length}개\n`;
    message += `삭제 대상 (${Utilities.formatDate(cutoffDate, Session.getScriptTimeZone(), "yyyy.MM.dd")} 이전): ${oldCompletedData.length}개\n\n`;
    
    if (oldCompletedData.length > 0) {
      message += `삭제 대상 상세:\n`;
      oldCompletedData.forEach((item, index) => {
        if (index < 10) { // 최대 10개만 표시
          message += `• ${item.palletId} (${item.vendor}) - ${item.dateStr}\n`;
        }
      });
      
      if (oldCompletedData.length > 10) {
        message += `... 외 ${oldCompletedData.length - 10}개 더\n`;
      }
    } else {
      message += `✅ 삭제할 보관종료 데이터가 없습니다.\n`;
    }
    
    SpreadsheetApp.getUi().alert(message);
    
  } catch (error) {
    console.error('보관종료 데이터 확인 실패:', error);
    SpreadsheetApp.getUi().alert('데이터 확인 실패: ' + error.message);
  }
}

/**
 * 보관종료 데이터 정리 실행
 */
function cleanupCompletedData() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const responseSheet = ss.getSheetByName("설문지 응답 시트1");
    
    if (!responseSheet) {
      SpreadsheetApp.getUi().alert("설문지 응답 시트1이 없습니다.");
      return;
    }
    
    // 삭제 대상 확인
    const deletionTargets = getDeletionTargets(responseSheet);
    
    if (deletionTargets.length === 0) {
      SpreadsheetApp.getUi().alert("삭제할 보관종료 데이터가 없습니다.");
      return;
    }
    
    // 삭제 대상 정보 표시
    const stats = analyzeDeletionTargets(deletionTargets);
    
    // 최종 확인
    const confirmMessage = `🗑️ 보관종료 데이터 정리\n\n` +
      `삭제할 데이터: ${stats.totalCount}개\n` +
      `기준 날짜: ${stats.cutoffDate} 이전\n\n` +
      `정말 삭제하시겠습니까?\n\n` +
      `⚠️ 이 작업은 되돌릴 수 없습니다!`;
    
    const ui = SpreadsheetApp.getUi();
    const response = ui.alert(confirmMessage, ui.ButtonSet.YES_NO);
    
    if (response !== ui.Button.YES) {
      SpreadsheetApp.getUi().alert("삭제가 취소되었습니다.");
      return;
    }
    
    // 백업 생성
    const backupResult = createBackupBeforeDeletion(responseSheet, deletionTargets);
    
    // 데이터 삭제 실행
    const deletedCount = executeDeletion(responseSheet, deletionTargets);
    
    // 결과 알림
    let resultMessage = `✅ 보관종료 데이터 정리 완료!\n\n`;
    resultMessage += `🗑️ 삭제된 데이터: ${deletedCount}개\n`;
    
    if (backupResult.success) {
      resultMessage += `💾 백업 생성됨: ${backupResult.backupSheetName}\n`;
    }
    
    resultMessage += `\n📊 정리된 화주사: ${Object.keys(stats.vendorCount).length}개`;
    
    SpreadsheetApp.getUi().alert(resultMessage);
    
    // 감사 로그 기록
    if (typeof logAuditEvent === 'function') {
      logAuditEvent('INFO', 'Completed data cleanup', {
        deletedCount: deletedCount,
        cutoffDate: stats.cutoffDate,
        vendors: Object.keys(stats.vendorCount)
      });
    }
    
  } catch (error) {
    console.error('보관종료 데이터 정리 실패:', error);
    SpreadsheetApp.getUi().alert('데이터 정리 실패: ' + error.message);
  }
}

/**
 * 삭제 대상 데이터 가져오기
 */
function getDeletionTargets(responseSheet) {
  try {
    const data = responseSheet.getDataRange().getValues();
    const header = data[0];
    
    // 컬럼 인덱스 찾기 (설문지 응답 시트1 구조)
    const timestampIdx = header.indexOf("타임스탬프");
    const workTypeIdx = header.indexOf("작업 유형");
    
    if (timestampIdx === -1 || workTypeIdx === -1) {
      throw new Error("필수 컬럼을 찾을 수 없습니다.");
    }
    
    // 현재 월에서 2개월 전 계산
    const now = new Date();
    const cutoffDate = new Date(now.getFullYear(), now.getMonth() - 2, 1);
    
    console.log(`현재 날짜: ${Utilities.formatDate(now, Session.getScriptTimeZone(), "yyyy.MM.dd")}`);
    console.log(`삭제 기준 날짜: ${Utilities.formatDate(cutoffDate, Session.getScriptTimeZone(), "yyyy.MM.dd")}`);
    
    // 삭제 대상 필터링
    const deletionTargets = [];
    let totalCompleted = 0;
    
    for (let i = 1; i < data.length; i++) {
      const row = data[i];
      const workType = row[workTypeIdx];
      const timestamp = row[timestampIdx];
      
      // 보관종료 데이터 개수 확인
      if (workType === "보관종료") {
        totalCompleted++;
        console.log(`보관종료 데이터 발견: 행 ${i + 1}, 타임스탬프: ${timestamp}, 타입: ${typeof timestamp}`);
        
        // 전전달 이전 데이터인지 확인
        if (timestamp instanceof Date && timestamp < cutoffDate) {
          deletionTargets.push({
            rowIndex: i + 1, // 실제 행 번호 (1-based)
            data: row,
            timestamp: timestamp
          });
          console.log(`삭제 대상 발견: 행 ${i + 1}, 타임스탬프: ${Utilities.formatDate(timestamp, Session.getScriptTimeZone(), "yyyy.MM.dd")}`);
        } else if (typeof timestamp === 'string') {
          // 문자열로 된 날짜 처리
          const dateStr = timestamp.toString();
          if (dateStr.includes('2025.07.10')) {
            console.log(`7월 10일 데이터 발견 (문자열): 행 ${i + 1}, 타임스탬프: ${dateStr}`);
            // 7월 10일은 8월 1일 이전이므로 삭제 대상
            const parsedDate = new Date(dateStr.replace(/\./g, '-'));
            deletionTargets.push({
              rowIndex: i + 1,
              data: row,
              timestamp: parsedDate
            });
            console.log(`삭제 대상 추가: 행 ${i + 1}, 파싱된 날짜: ${Utilities.formatDate(parsedDate, Session.getScriptTimeZone(), "yyyy.MM.dd")}`);
          }
        }
      }
    }
    
    console.log(`전체 보관종료 데이터: ${totalCompleted}개`);
    console.log(`삭제 대상: ${deletionTargets.length}개`);
    
    return deletionTargets;
    
  } catch (error) {
    console.error('삭제 대상 가져오기 실패:', error);
    return [];
  }
}

/**
 * 삭제 대상 분석
 */
function analyzeDeletionTargets(deletionTargets) {
  const stats = {
    totalCount: deletionTargets.length,
    cutoffDate: '',
    vendorCount: {}
  };
  
  // 기준 날짜 설정
  const now = new Date();
  const cutoffDate = new Date(now.getFullYear(), now.getMonth() - 2, 1);
  stats.cutoffDate = Utilities.formatDate(cutoffDate, Session.getScriptTimeZone(), "yyyy-MM-dd");
  
  // 화주사별 개수 계산
  deletionTargets.forEach(target => {
    const vendor = target.data[3]; // 화주사 컬럼 (D열)
    if (vendor) {
      stats.vendorCount[vendor] = (stats.vendorCount[vendor] || 0) + 1;
    }
  });
  
  return stats;
}

/**
 * 삭제 전 백업 생성
 */
function createBackupBeforeDeletion(responseSheet, deletionTargets) {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const timestamp = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "yyyy-MM-dd_HH-mm");
    const backupSheetName = `보관종료백업_${timestamp}`;
    
    // 백업 시트 생성
    const backupSheet = ss.insertSheet(backupSheetName);
    
    // 헤더 복사
    const header = responseSheet.getRange("A1:G1").getValues();
    backupSheet.getRange("A1:G1").setValues(header);
    backupSheet.getRange("A1:G1").setFontWeight("bold");
    
    // 삭제될 데이터 복사
    const deletionData = deletionTargets.map(target => target.data);
    if (deletionData.length > 0) {
      backupSheet.getRange(2, 1, deletionData.length, deletionData[0].length)
        .setValues(deletionData);
    }
    
    // 시트 서식 적용
    backupSheet.autoResizeColumns(1, 7);
    backupSheet.setFrozenRows(1);
    
    return {
      success: true,
      backupSheetName: backupSheetName
    };
    
  } catch (error) {
    console.error('백업 생성 실패:', error);
    return {
      success: false,
      error: error.message
    };
  }
}

/**
 * 실제 삭제 실행 (파레트 ID 기준으로 모든 관련 행 삭제)
 */
function executeDeletion(responseSheet, deletionTargets) {
  try {
    // 보관종료 데이터에서 파레트 ID 추출
    const palletIds = [...new Set(deletionTargets.map(target => target.data[1]))];
    
    console.log(`삭제할 파레트 ID: ${palletIds.join(', ')}`);
    
    // 해당 파레트 ID의 모든 행 찾기
    const allRowsToDelete = [];
    const data = responseSheet.getDataRange().getValues();
    
    for (let i = 1; i < data.length; i++) {
      const row = data[i];
      const palletId = row[1]; // 파레트 ID 컬럼 (B열)
      
      if (palletId && palletIds.includes(palletId.toString().trim())) {
        allRowsToDelete.push({
          rowIndex: i + 1,
          data: row,
          palletId: palletId
        });
      }
    }
    
    console.log(`삭제할 총 행 수: ${allRowsToDelete.length}개`);
    
    // 모든 관련 행 삭제 (뒤에서부터 삭제)
    let deletedCount = 0;
    for (let i = allRowsToDelete.length - 1; i >= 0; i--) {
      const row = allRowsToDelete[i];
      responseSheet.deleteRow(row.rowIndex);
      deletedCount++;
    }
    
    return deletedCount;
    
  } catch (error) {
    console.error('삭제 실행 실패:', error);
    throw error;
  }
}

// ========================================
// 🎨 화주사 시트 서식 정리 기능
// ========================================

/**
 * 화주사별 시트 서식 정리
 */
function cleanupVendorSheetFormatting() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sourceSheet = ss.getSheetByName("파레트 요약 정산");
    
    if (!sourceSheet) {
      SpreadsheetApp.getUi().alert("파레트 요약 정산 시트가 없습니다.");
      return;
    }
    
    // 화주사 목록 가져오기
    const data = sourceSheet.getDataRange().getValues();
    const header = data[0];
    const vendorIndex = header.indexOf("화주사");
    
    if (vendorIndex === -1) {
      SpreadsheetApp.getUi().alert("화주사 컬럼을 찾을 수 없습니다.");
      return;
    }
    
    // 화주사별 데이터 그룹화 (정규화 적용)
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
    
    // 디버깅: 화주사 목록 확인
    const vendorList = Object.keys(vendorMap);
    console.log("발견된 화주사:", vendorList);
    
    let cleanedSheets = 0;
    
    // 각 화주사 시트 서식 정리
    for (const normalizedVendor in vendorMap) {
      const originalVendor = vendorNameMap[normalizedVendor];
      const sheetName = sanitizeSheetName(originalVendor);
      const sheet = ss.getSheetByName(sheetName);
      
      console.log(`처리 중인 화주사: ${originalVendor} (정규화: ${normalizedVendor}), 시트명: ${sheetName}, 시트존재: ${!!sheet}`);
      
      if (sheet) {
        try {
          // 1단계: 전체 시트 초기화
          const maxRows = sheet.getMaxRows();
          const maxCols = sheet.getMaxColumns();
          
          // 전체 시트 배경색과 테두리 초기화 (빠른 방법)
          sheet.getRange(1, 1, maxRows, maxCols)
            .setBackground(null)
            .setBorder(false, false, false, false, false, false);
          
          console.log(`시트 ${sheetName} 전체 초기화 완료: ${maxRows}행 x ${maxCols}열`);
          
          // 2단계: 데이터 범위 확인
          const lastRow = sheet.getLastRow();
          const lastCol = sheet.getLastColumn();
          
          console.log(`시트 ${sheetName}: 마지막 행=${lastRow}, 마지막 열=${lastCol}`);
          
          if (lastRow > 1 && lastCol > 0) {
            // 3단계: 헤더 서식 적용
            const headerRange = sheet.getRange(1, 1, 1, lastCol);
            headerRange.setFontWeight("bold");
            headerRange.setBackground("#f1f3f4");
            headerRange.setHorizontalAlignment("center");
            headerRange.setVerticalAlignment("middle");
            headerRange.setFontSize(11);
            
            // 4단계: 데이터 범위 찾기
            let dataEndRow = lastRow;
            let hasTotalRow = false;
            
            // 총계 행 찾기
            for (let row = lastRow; row >= 1; row--) {
              const cellValue = sheet.getRange(row, 1).getValue();
              if (cellValue && cellValue.toString().includes("총 보관료 합계")) {
                dataEndRow = row - 1;
                hasTotalRow = true;
                console.log(`총계 행 발견: ${row}행`);
                break;
              }
            }
            
            // 5단계: 데이터 범위 서식 적용
            if (dataEndRow > 1) {
              const dataRange = sheet.getRange(2, 1, dataEndRow - 1, lastCol);
              
              // 데이터 서식
              dataRange.setFontWeight("normal");
              dataRange.setHorizontalAlignment("center");
              dataRange.setVerticalAlignment("middle");
              dataRange.setFontSize(10);
              dataRange.setFontColor("#000000");
              dataRange.setFontStyle("normal");
              
              // 데이터 테두리
              dataRange.setBorder(true, true, true, true, true, true);
              
              // 보관료 열 숫자 포맷
              const feeColIndex = header.indexOf("보관료(원)");
              if (feeColIndex !== -1 && feeColIndex < lastCol) {
                const feeRange = sheet.getRange(2, feeColIndex + 1, dataEndRow - 1, 1);
                feeRange.setNumberFormat("#,##0");
              }
            }
            
            // 6단계: 총계 행 강조 서식
            if (hasTotalRow) {
              const totalRowNum = dataEndRow + 1;
              const totalRowRange = sheet.getRange(totalRowNum, 1, 1, lastCol);
              
              // 총계 행 강조
              totalRowRange.setFontWeight("bold");
              totalRowRange.setFontSize(12);
              totalRowRange.setBackground("#d9d9d9");
              totalRowRange.setHorizontalAlignment("center");
              totalRowRange.setVerticalAlignment("middle");
              totalRowRange.setBorder(true, true, true, true, true, true);
              
              // 부가세 행 서식
              const vatRowNum = totalRowNum + 1;
              if (vatRowNum <= lastRow) {
                const vatRowRange = sheet.getRange(vatRowNum, 1, 1, lastCol);
                vatRowRange.setFontSize(9);
                vatRowRange.setFontStyle("italic");
                vatRowRange.setFontColor("#666");
                vatRowRange.setHorizontalAlignment("center");
                vatRowRange.setBackground(null);
                vatRowRange.setBorder(null, null, null, null, null, null);
              }
              
              // 부가세 아래 빈 행들 빠른 정리
              const rowsToDelete = maxRows - vatRowNum;
              if (rowsToDelete > 0) {
                console.log(`정리할 빈 행: ${vatRowNum + 1}행부터 ${maxRows}행까지 (${rowsToDelete}개 행)`);
                
                // 빈 행들 빠른 정리 (범위로 한 번에 처리)
                const emptyRange = sheet.getRange(vatRowNum + 1, 1, rowsToDelete, maxCols);
                emptyRange.setBackground(null);
                emptyRange.setBorder(false, false, false, false, false, false);
                
                console.log(`${rowsToDelete}개 빈 행 빠른 정리 완료`);
              }
            }
            
          }
          
          cleanedSheets++;
          console.log(`시트 ${sheetName} 서식 정리 완료`);
          
        } catch (error) {
          console.error(`시트 ${sheetName} 서식 정리 실패:`, error);
        }
      } else {
        console.log(`시트 ${sheetName}을 찾을 수 없습니다.`);
      }
    }
    
    // 결과 알림
    SpreadsheetApp.getUi().alert(`✅ 화주사 시트 서식 정리 완료!\n\n` +
      `🎨 정리된 시트: ${cleanedSheets}개\n` +
      `🧹 빈 셀 배경색 초기화 완료\n` +
      `📊 데이터 범위 서식 재적용 완료`);
    
    // 감사 로그 기록
    if (typeof logAuditEvent === 'function') {
      logAuditEvent('INFO', 'Vendor sheet formatting cleanup', {
        cleanedSheets: cleanedSheets,
        vendors: Object.keys(vendorMap)
      });
    }
    
  } catch (error) {
    console.error('화주사 시트 서식 정리 실패:', error);
    SpreadsheetApp.getUi().alert('서식 정리 실패: ' + error.message);
  }
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

/**
 * 시트 이름 유효성 검사 (sanitizeSheetName 함수가 없을 경우를 대비)
 */
function sanitizeSheetName(name) {
  if (typeof name !== 'string') return "미지정";
  
  // Google Sheets 시트 이름 제한사항 적용
  let sanitized = name
    .replace(/[\\\/\?\*\[\]]/g, '') // 금지 문자 제거
    .replace(/^\.+/, '') // 앞의 점들 제거
    .replace(/\.+$/, '') // 뒤의 점들 제거
    .trim();
  
  // 빈 문자열이거나 너무 긴 경우 처리
  if (!sanitized || sanitized.length === 0) {
    sanitized = "미지정";
  } else if (sanitized.length > 100) {
    sanitized = sanitized.substring(0, 100);
  }
  
  return sanitized;
}

// ========================================
// 🎯 자동화 기능
// ========================================


/**
 * 입력용 시트 자동 설정 (스프레드시트 열 때)
 */
function autoSetupInputSheet() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const inputSheet = ss.getSheetByName("입력용");
    
    // 입력용 시트가 없으면 자동 생성
    if (!inputSheet) {
      createInputSheet();
    }
    
  } catch (error) {
    console.error('자동 설정 실패:', error);
  }
}

/**
 * 현재 스프레드시트 ID 확인 함수 (임시)
 */
function checkSpreadsheetConnection() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const currentSpreadsheetId = ss.getId();
    const targetSpreadsheetId = "1B-2zcKoO8mGyYVaZ8PbxLsoO-4LIEppAsJu66OvlSIU";
    
    const isConnected = currentSpreadsheetId === targetSpreadsheetId;
    
    const message = `현재 스프레드시트 ID: ${currentSpreadsheetId}\n` +
                   `목표 스프레드시트 ID: ${targetSpreadsheetId}\n` +
                   `연결 상태: ${isConnected ? "✅ 연결됨" : "❌ 연결 안됨"}`;
    
    console.log(message);
    
    // UI가 사용 가능한 경우 알림 표시
    try {
      SpreadsheetApp.getUi().alert("스프레드시트 연결 확인", message, SpreadsheetApp.getUi().ButtonSet.OK);
    } catch (e) {
      // UI 사용 불가 시 로그만 출력
      console.log("UI 사용 불가 - 로그만 출력됨");
    }
    
    return {
      currentId: currentSpreadsheetId,
      targetId: targetSpreadsheetId,
      isConnected: isConnected
    };
    
  } catch (error) {
    console.error('스프레드시트 연결 확인 실패:', error);
    throw error;
  }
}
