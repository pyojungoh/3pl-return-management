// 📁 emailSender.gs

/**
 * ✅ 이메일 발송 시트를 초기화합니다.
 */
function setupEmailSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName("이메일발송") || ss.insertSheet("이메일발송");
  sheet.clear();

  const headers = [
    "화주사", "이메일", "메일발송여부", "발송 대상 월", "발송 체크", "비고"
  ];
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]).setFontWeight("bold");
  sheet.setColumnWidths(1, 6, 140);

  // 전체 발송 대상 월 입력칸
  const thisYear = new Date().getFullYear();
  const monthOptions = Array.from({ length: 12 }, (_, i) => [`${thisYear}-${String(i + 1).padStart(2, "0")}`]);
  const dropdownRange = sheet.getRange("J2");
  const thisMonth = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "yyyy-MM");
  sheet.getRange("J1").setValue("전체 발송 대상 월 (yyyy-MM)").setFontWeight("bold").setBackground("#fce5cd");
  dropdownRange.setValue(thisMonth);
  dropdownRange.setDataValidation(SpreadsheetApp.newDataValidation().requireValueInList(monthOptions.flat()).setAllowInvalid(false).build());
  sheet.getRange("K1").setValue("버튼 클릭 시 자동 실행됨 (onEdit 사용)");

  // 📌 화주사 자동 불러오기
  updateVendorListInEmailSheet(thisMonth);

  // 여기에서 setupEmailSheet() 함수가 끝납니다.
  // 이메일 메뉴는 onOpen()에서 직접 호출되거나, setupEmailSheetMenu를 onOpen()에서 호출해야 합니다.
}

// 이 함수는 setupEmailSheet() 함수 밖에 별도로 정의되어야 합니다.
// 그리고 onOpen() 함수에서 ui 객체를 매개변수로 받아 호출되어야 합니다.
function setupEmailSheetMenu(ui) { // 이 함수는 이제 최상위 레벨에 있습니다.
  ui.createMenu("📬 이메일 도구")
    .addItem("📤 선택 이메일 발송", "sendAllVendorEmails")
    .addItem("🧪 선택 테스트 발송", "sendAllTestEmails")
    .addItem("🔄 화주사 목록 갱신", "refreshVendorListFromDropdown")
    .addToUi();
}


/**
 * ✅ 화주사 리스트 업데이트
 */
function updateVendorListInEmailSheet(month) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sourceSheet = ss.getSheetByName("파레트 요약 정산");
  const emailSheet = ss.getSheetByName("이메일발송");
  if (!sourceSheet || !emailSheet) return;

  const data = sourceSheet.getDataRange().getValues();
  const vendorIdx = data[0].indexOf("화주사");
  if (vendorIdx === -1) return;

  const vendors = [...new Set(data.slice(1).map(row => row[vendorIdx]).filter(v => v))];

  // A~E열 클리어
  emailSheet.getRange(2, 1, emailSheet.getMaxRows() - 1, 5).clearContent();

  // 화주사, 이메일빈칸, 발송여부빈칸, 월, 체크박스
  const rows = vendors.map(v => [v, "", "", month, false]);
  emailSheet.getRange(2, 1, rows.length, 5).setValues(rows);
  emailSheet.getRange(2, 5, rows.length).insertCheckboxes();

  // 드롭다운 설정: 발송 대상 월 (D열)
  const thisYear = new Date().getFullYear();
  const monthOptions = Array.from({ length: 12 }, (_, i) => `${thisYear}-${String(i + 1).padStart(2, "0")}`);
  const rule = SpreadsheetApp.newDataValidation().requireValueInList(monthOptions).setAllowInvalid(false).build();
  emailSheet.getRange(2, 4, rows.length).setDataValidation(rule);
}

/**
 * ✅ 드롭다운에서 선택된 월로 갱신
 */
function refreshVendorListFromDropdown() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName("이메일발송");
  if (!sheet) return;
  const month = sheet.getRange("J2").getValue();
  if (!month) return;
  updateVendorListInEmailSheet(month);
}

// ✅ 선택 발송/테스트 발송 함수와 개별 발송 함수들은 아래 그대로 유지됩니다.

function sendAllVendorEmails() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName("이메일발송");
  const data = sheet.getDataRange().getValues();
  for (let row = 1; row < data.length; row++) {
    const rowData = data[row];
    const checked = rowData[4]; // E열 = 발송 체크
    if (checked === true) {
      sendVendorEmail(row + 1);
    }
  }
  SpreadsheetApp.getUi().alert("✅ 선택된 화주사에 이메일을 발송했습니다.");
}

function sendAllTestEmails() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName("이메일발송");
  const data = sheet.getDataRange().getValues();
  for (let row = 1; row < data.length; row++) {
    const rowData = data[row];
    const checked = rowData[4]; // E열 = 발송 체크
    if (checked === true) {
      sendTestVendorEmail(row + 1);
    }
  }
  SpreadsheetApp.getUi().alert("🧪 선택된 화주사 테스트 메일이 발송되었습니다.");
}

function sendVendorEmail(row) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName("이메일발송");
  const values = sheet.getRange(row, 1, 1, 6).getValues()[0];
  const [vendor, email, status, rawMonth] = values;

  const month = typeof rawMonth === "string"
    ? rawMonth
    : Utilities.formatDate(new Date(rawMonth), Session.getScriptTimeZone(), "yyyy-MM"); // 📌 문자열로 변환

  const fileName = `${vendor} (${month}) 정산`;
  const file = DriveApp.getFilesByName(fileName).hasNext()
    ? DriveApp.getFilesByName(fileName).next()
    : null;

  if (!file) {
    SpreadsheetApp.getUi().alert(`${vendor}의 ${month} 정산서를 찾을 수 없습니다.`);
    return;
  }

  const body = `${vendor}님, 안녕하세요.

제이제이 3PL물류입니다.
첨부된 PDF는 ${month} 파레트 보관 정산서입니다. 확인 부탁드립니다.

📌 담당자: 표정오 이사
📞 연락처: 010-8684-8692
📍 주소: 경기도 김포시 통진읍 월하로 352-18

감사합니다.`;

  MailApp.sendEmail({
    to: email,
    subject: `[정산서] ${vendor}님의 ${month} 파레트 보관 정산서 전달드립니다`,
    body,
    attachments: [file.getAs(MimeType.PDF)]
  });

  sheet.getRange(row, 3).setValue("발송완료");
  SpreadsheetApp.getUi().alert(`${vendor}에게 정산서를 발송했습니다.`);
}


function sendTestVendorEmail(row) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName("이메일발송");
  const values = sheet.getRange(row, 1, 1, 6).getValues()[0];
  const [vendor, , , rawMonth] = values;
  const testEmail = Session.getActiveUser().getEmail();

  const month = typeof rawMonth === "string"
    ? rawMonth
    : Utilities.formatDate(new Date(rawMonth), Session.getScriptTimeZone(), "yyyy-MM"); // 📌 문자열로 변환

  const fileName = `${vendor} (${month}) 정산`;
  const file = DriveApp.getFilesByName(fileName).hasNext()
    ? DriveApp.getFilesByName(fileName).next()
    : null;

  if (!file) {
    SpreadsheetApp.getUi().alert(`${vendor}의 ${month} 정산서를 찾을 수 없습니다.`);
    return;
  }

  const body = `[테스트 발송]

제이제이 3PL물류입니다.
아래는 테스트용 정산서 미리보기입니다.

📌 화주사: ${vendor}
📅 정산월: ${month}
📞 010-8684-8692
📍 경기도 김포시 통진읍 월하로 352-18`;

  MailApp.sendEmail({
    to: testEmail,
    subject: `[테스트] ${vendor} ${month} 파레트 보관 정산서 미리보기`,
    body,
    attachments: [file.getAs(MimeType.PDF)]
  });

  SpreadsheetApp.getUi().alert(`[테스트] ${vendor} 정산서가 본인 메일로 전송되었습니다.`);
}