// 정산시트 백업 함수(매월 말일 자동저장)//

function createBackupMenu(ui) { // ui 매개변수 추가
  ui.createMenu("📁 정산 백업")
    .addItem("📤 월별 정산 통합 백업", "exportCurrentMonthSummaryToDrive")
    .addItem("📤 화주사별 분리 백업 실행", "exportVendorSheetsSeparately")
    .addToUi();
}

// 📦 최종 백업 자동화 함수 (날짜열 제거 + 상단 제목 삽입)
function exportCurrentMonthSummaryToDrive() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sourceSheet = ss.getSheetByName("파레트 요약 정산");
  if (!sourceSheet) {
    SpreadsheetApp.getUi().alert("파레트 요약 정산 시트가 없습니다.");
    return;
  }

  const data = sourceSheet.getDataRange().getValues();
  const header = data[0];
  const statusIdx = header.indexOf("상태");
  const dateIdx = header.indexOf("갱신일");

  // ✅ 갱신일 기준 yyyy.MM 추출 (보관종료 제외)
  const monthCount = {};
  for (let i = 1; i < data.length; i++) {
    const status = data[i][statusIdx];
    const dateStr = data[i][dateIdx];

    if (status !== "보관종료" && typeof dateStr === "string" && dateStr.match(/^\d{4}\.\d{2}/)) {
      const yyyymm = dateStr.substr(0, 7).replace(".", "-"); // yyyy-MM 형식
      monthCount[yyyymm] = (monthCount[yyyymm] || 0) + 1;
    }
  }

  // 가장 많이 나온 yyyy-MM 값 선택
  const sortedMonths = Object.entries(monthCount).sort((a, b) => b[1] - a[1]);
  if (sortedMonths.length === 0) {
    SpreadsheetApp.getUi().alert("❌ '보관종료' 제외 기준으로 유효한 '갱신일' 값이 없습니다.");
    return;
  }
  const yyyymm = sortedMonths[0][0]; // 가장 많이 나온 월
  const titleFormatted = `${yyyymm.replace("-", "년 ")}월 파레트보관 상세내역`;

  // ✅ 드라이브 폴더 구조
  const rootFolder = getOrCreateFolderByName(DriveApp.getRootFolder(), "3pl자동화");
  const archiveFolder = getOrCreateFolderByName(rootFolder, "정산파일");
  const monthFolder = getOrCreateFolderByName(archiveFolder, yyyymm);

  // 📄 파일명 중복 방지
  let baseFileName = `${yyyymm} 화주사 정산`;
  let fileName = baseFileName;
  let suffix = 1;
  while (monthFolder.getFilesByName(fileName).hasNext()) {
    fileName = `${baseFileName} (${suffix++})`;
  }

  const newFile = SpreadsheetApp.create(fileName);
  Utilities.sleep(1000);
  const newSs = SpreadsheetApp.openById(newFile.getId());

  const sheetNames = ss.getSheets().map(s => s.getName());
  const targetSheets = sheetNames.filter(name =>
    name === "월별 화주사 요약" ||
    (name !== "설정" && name !== "라벨출력대상" && name !== "설문지 응답 시트1" && name !== "Sheet1" && name !== "Sheet1의 사본" && name !== "이메일발송")
  );

  targetSheets.forEach(name => {
    const sourceSheet = ss.getSheetByName(name);
    const newSheet = newSs.insertSheet(name);
    const data = sourceSheet.getDataRange().getValues();

    // 날짜열 제거 ("날짜"라는 헤더가 있을 경우 해당 열 제거)
    const dateColIndex = data[0].findIndex(col => col.toString().includes("날짜"));
    const filteredData = data.map(row => {
      return dateColIndex >= 0 ? row.filter((_, i) => i !== dateColIndex) : row;
    });

    // 제목 삽입
    newSheet.insertRows(1);
    newSheet.getRange("A1").setValue(titleFormatted)
      .setFontWeight("bold")
      .setFontSize(14)
      .setHorizontalAlignment("center");
    newSheet.getRange(1, 1, 1, filteredData[0].length).mergeAcross();

    newSheet.getRange(2, 1, filteredData.length, filteredData[0].length).setValues(filteredData);

    // 서식 적용
    const fullRange = newSheet.getRange(2, 1, filteredData.length, filteredData[0].length);
    fullRange.setFontFamily("Arial").setFontSize(10).setVerticalAlignment("middle");
    newSheet.getRange(2, 1, 1, filteredData[0].length).setFontWeight("bold").setBackground("#f1f3f4");
    fullRange.setBorder(true, true, true, true, true, true);

    const numericCols = findNumericColumns(filteredData);
    numericCols.forEach(col => {
      newSheet.getRange(3, col + 1, filteredData.length - 1).setNumberFormat("#,##0");
    });

    // 합계 행 서식 추가
    for (let r = 1; r < filteredData.length; r++) {
      if (typeof filteredData[r][0] === "string" && filteredData[r][0].includes("합계")) {
        newSheet.getRange(r + 2, 1, 1, filteredData[0].length)
          .setFontWeight("bold")
          .setBackground("#eeeeee")
          .setBorder(true, true, true, true, true, true);
      }
    }
  });

  const defaultSheet = newSs.getSheetByName("Sheet1");
  if (defaultSheet) newSs.deleteSheet(defaultSheet);

  const file = DriveApp.getFileById(newFile.getId());
  monthFolder.addFile(file);
  DriveApp.getRootFolder().removeFile(file);

  const email = Session.getActiveUser().getEmail();
  MailApp.sendEmail({
    to: email,
    subject: `✅ [${yyyymm}] 화주사 정산 백업 완료`,
    body: `Google Drive > 3pl자동화 > 정산파일 > ${yyyymm} 폴더에 "${fileName}" 문서가 백업되었습니다.`,
  });

  SpreadsheetApp.getUi().alert(`✅ ${fileName} 정산 문서가 백업되고 이메일 알림이 전송되었습니다.`);
}



function getOrCreateFolderByName(parent, name) {
  const folders = parent.getFoldersByName(name);
  return folders.hasNext() ? folders.next() : parent.createFolder(name);
}


function findNumericColumns(data) {
  const header = data[0];
  const numericCols = [];
  for (let col = 0; col < header.length; col++) {
    for (let row = 1; row < data.length; row++) {
      if (typeof data[row][col] === "number") {
        numericCols.push(col);
        break;
      }
    }
  }
  return numericCols;
}



function exportVendorSheetsSeparately() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sourceSheet = ss.getSheetByName("파레트 요약 정산");
  if (!sourceSheet) {
    SpreadsheetApp.getUi().alert("파레트 요약 정산 시트가 없습니다.");
    return;
  }

  const data = sourceSheet.getDataRange().getValues();
  const header = data[0];
  const vendorIdx = header.indexOf("화주사");
  const feeIdx = header.indexOf("보관료(원)");
  const statusIdx = header.indexOf("상태");
  const dateIdx = header.indexOf("갱신일");

  // ✅ 갱신일 기준 yyyy.MM 추출 (보관종료 제외)
  const monthCount = {};
  for (let i = 1; i < data.length; i++) {
    const status = data[i][statusIdx];
    const dateStr = data[i][dateIdx];

    if (status !== "보관종료" && typeof dateStr === "string" && dateStr.match(/^\d{4}\.\d{2}/)) {
      const yyyymm = dateStr.substr(0, 7).replace(".", "-"); // yyyy-MM 형식
      monthCount[yyyymm] = (monthCount[yyyymm] || 0) + 1;
    }
  }

  // 가장 많이 나온 yyyy-MM 값 선택
  const sortedMonths = Object.entries(monthCount).sort((a, b) => b[1] - a[1]);
  if (sortedMonths.length === 0) {
    SpreadsheetApp.getUi().alert("❌ '보관종료' 제외 기준으로 유효한 '갱신일' 값이 없습니다.");
    return;
  }
  const yyyymm = sortedMonths[0][0]; // 가장 많이 나온 월
  const titleFormatted = `${yyyymm.replace("-", "년 ")}월 파레트보관 상세내역`;

  // ✅ 드라이브 폴더 구조
  const rootFolder = getOrCreateFolderByName(DriveApp.getRootFolder(), "3pl자동화");
  const archiveFolder = getOrCreateFolderByName(rootFolder, "정산파일");
  const monthFolder = getOrCreateFolderByName(archiveFolder, yyyymm);

  // ✅ 화주사별 데이터 분리
  const vendorMap = {};
  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    const vendor = row[vendorIdx] || "미지정";
    if (!vendorMap[vendor]) vendorMap[vendor] = [];
    vendorMap[vendor].push(row);
  }

  // ✅ 화주사별 파일 생성
  for (const vendor in vendorMap) {
    let fileName = `${vendor} (${yyyymm}) 파레트보관 상세내역`;
    let suffix = 1;
    while (monthFolder.getFilesByName(fileName).hasNext()) {
      fileName = `${vendor} (${yyyymm}) 파레트보관 상세내역 (${suffix++})`;
    }

    const newFile = SpreadsheetApp.create(fileName);
    Utilities.sleep(1000);
    const newSs = SpreadsheetApp.openById(newFile.getId());
    const sheet = newSs.getActiveSheet();
    sheet.setName("정산");

    // 🟨 제목 (1행)
    sheet.insertRows(1);
    sheet.getRange("A1").setValue(titleFormatted)
      .setFontWeight("bold")
      .setFontSize(14)
      .setHorizontalAlignment("center");
    sheet.getRange(1, 1, 1, header.length).mergeAcross();

    // 🟨 본문
    sheet.getRange(2, 1, 1, header.length).setValues([header]);
    sheet.getRange(3, 1, vendorMap[vendor].length, header.length).setValues(vendorMap[vendor]);

    // 🟨 서식
    const fullRange = sheet.getRange(2, 1, vendorMap[vendor].length + 1, header.length);
    fullRange.setFontFamily("Arial").setFontSize(10).setVerticalAlignment("middle");
    sheet.getRange(2, 1, 1, header.length).setFontWeight("bold").setBackground("#f1f3f4");
    fullRange.setBorder(true, true, true, true, true, true);

    // 🟨 보관료 열 숫자 포맷 (천단위 쉼표)
    if (feeIdx !== -1) {
      const feeCol = feeIdx + 1;
      sheet.getRange(3, feeCol, vendorMap[vendor].length).setNumberFormat("#,##0");

      // 🟨 총계 행
      const lastRow = vendorMap[vendor].length + 3;
      const totalLabelCell = sheet.getRange(lastRow, 1);
      totalLabelCell.setValue("총 보관료 합계")
        .setFontWeight("bold")
        .setFontSize(12)
        .setHorizontalAlignment("right")
        .setBackground("#e6e6e6");

      const totalCell = sheet.getRange(lastRow, feeCol);
      totalCell.setFormula(`=SUM(${sheet.getRange(3, feeCol, vendorMap[vendor].length).getA1Notation()})`)
        .setFontWeight("bold")
        .setFontSize(12)
        .setNumberFormat("#,##0")
        .setHorizontalAlignment("center")
        .setBackground("#e6e6e6");

      // 🟨 총계 테두리
      sheet.getRange(lastRow, 1, 1, header.length).setBorder(true, true, true, true, true, true);

      // 🟨 부가세 별도 문구 추가
      const noteRow = lastRow + 1;
      sheet.getRange(noteRow, feeCol).setValue("※ 부가세 별도")
        .setFontSize(9)
        .setFontStyle("italic")
        .setFontColor("#666")
        .setHorizontalAlignment("center");
    }

    // 🟨 드라이브 이동
    const file = DriveApp.getFileById(newFile.getId());
    monthFolder.addFile(file);
    DriveApp.getRootFolder().removeFile(file);
  }

  SpreadsheetApp.getUi().alert("✅ 화주사별 개별 정산 문서 백업이 완료되었습니다.");
}




function createMonthlyExportTrigger() {
  // 기존 동일한 트리거 제거 (중복 방지)
  const triggers = ScriptApp.getProjectTriggers();
  for (let t of triggers) {
    if (t.getHandlerFunction() === "exportVendorSheetsSeparately") {
      ScriptApp.deleteTrigger(t);
    }
  }

  // 매월 1일 오전 1시 ~ 2시 사이 실행 트리거 생성
  ScriptApp.newTrigger("exportVendorSheetsSeparately")
    .timeBased()
    .onMonthDay(1) // 매월 1일
    .atHour(1)     // 오전 1시
    .create();
}

/**
 * 전달 데이터 백업 트리거 설정 (매월 1일 1시에 전달 데이터 백업)
 * 기존 createMonthlyExportTrigger() 함수는 그대로 유지
 */
function createPreviousMonthBackupTrigger() {
  // 기존 동일한 트리거 제거 (중복 방지)
  const triggers = ScriptApp.getProjectTriggers();
  for (let t of triggers) {
    if (t.getHandlerFunction() === "exportPreviousMonthBackup") {
      ScriptApp.deleteTrigger(t);
    }
  }

  // 매월 1일 오전 1시에 전달 데이터 백업 실행
  ScriptApp.newTrigger("exportPreviousMonthBackup")
    .timeBased()
    .onMonthDay(1) // 매월 1일
    .atHour(1)     // 오전 1시
    .create();
  
  console.log("✅ 전달 데이터 백업 트리거가 설정되었습니다. (매월 1일 1시)");
}
