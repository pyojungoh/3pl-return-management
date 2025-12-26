/**
 * 📅 전달 데이터 자동화 시스템
 * 
 * 매월 1일에 전달(이전 달) 데이터만 처리하는 함수들
 * 기존 함수는 절대 수정하지 않고, 새로운 함수로 추가
 */

/**
 * 전달 데이터만 정산하는 함수
 * 기존 summarizePalletData() 함수를 기반으로 하되, 전달 데이터만 처리
 */
function summarizePreviousMonthData() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const configSheet = ss.getSheetByName("설정") || ss.insertSheet("설정");
  const configData = configSheet.getDataRange().getValues();
  const rawSheet = ss.getSheetByName("설문지 응답 시트1");
  
  if (!rawSheet) {
    console.error("설문지 응답 시트1이 없습니다.");
    return;
  }
  
  const data = rawSheet.getDataRange().getValues();
  const header = data[0];

  const idIdx = header.indexOf("파레트 ID");
  const typeIdx = header.indexOf("작업 유형");
  const qtyIdx = header.indexOf("작업 수량");
  const timeIdx = header.indexOf("타임스탬프");
  const productIdx = header.indexOf("품목명");
  const vendorIdx = header.indexOf("화주사");

  // ✅ 전달 마지막 날 계산
  const today = new Date();
  const previousMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1);
  const previousMonthLastDay = new Date(today.getFullYear(), today.getMonth(), 0);
  const previousMonthStr = Utilities.formatDate(previousMonth, Session.getScriptTimeZone(), "yyyy.MM");
  
  console.log(`전달 데이터 처리: ${previousMonthStr} (${previousMonthLastDay.getDate()}일까지)`);

  const summary = {};
  // ✅ 전달 마지막 날을 기준일로 사용 (이번달이 아닌 전달)
  const targetDate = previousMonthLastDay;

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

  // ✅ 전달 데이터만 처리 (전달 마지막 날까지만)
  for (let i = 1; i < data.length; i++) {
    const id = data[i][idIdx];
    const type = data[i][typeIdx];
    const qty = Number(data[i][qtyIdx]) || 0;
    const time = new Date(data[i][timeIdx]);
    const product = (data[i][productIdx] || "무기입").toString().trim();
    const vendor = data[i][vendorIdx];
    
    if (!id) continue;
    
    // ✅ 전달 마지막 날 이후 데이터는 제외
    if (time > targetDate) {
      continue;
    }

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
        // ✅ 전달 월의 1일부터 보관종료일까지 계산
        const 전달월초 = new Date(previousMonth.getFullYear(), previousMonth.getMonth(), 1);
        const 종료월초 = new Date(e["보관종료일"].getFullYear(), e["보관종료일"].getMonth(), 1);
        const 시작일 = 입고일 > 전달월초 ? 입고일 : 전달월초;
        const 종료일 = e["보관종료일"] > targetDate ? targetDate : e["보관종료일"];
        갱신일 = Utilities.formatDate(시작일, Session.getScriptTimeZone(), "yyyy.MM.dd");
        const resultObj = calculateFee(시작일, 종료일, e["화주사"]);
        보관일수 = resultObj.days;
        보관료 = resultObj.fee;
        
        // ✅ 보관종료가 전달이 아닌 경우 보관료 제외
        const 종료월 = Utilities.formatDate(e["보관종료일"], Session.getScriptTimeZone(), "yyyy.MM");
        if (종료월 !== previousMonthStr) {
          보관일수 = "";
          보관료 = "";
        }
      } else {
        // ✅ 전달 월의 1일부터 전달 마지막 날까지 계산
        const 전달월초 = new Date(previousMonth.getFullYear(), previousMonth.getMonth(), 1);
        const 시작일 = 입고일 > 전달월초 ? 입고일 : 전달월초;
        갱신일 = Utilities.formatDate(시작일, Session.getScriptTimeZone(), "yyyy.MM.dd");
        const resultObj = calculateFee(시작일, targetDate, e["화주사"]);
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

  // ✅ 화주사별 시트 분리 (기존 함수 사용)
  splitByVendor();
  
  // ✅ 전달 월별 요약 생성
  generatePreviousMonthVendorSummary(previousMonthStr);
}

/**
 * 전달 월별 화주사 요약 생성
 * 기존 generateMonthlyVendorSummary() 함수를 기반으로 하되, 전달 데이터만 처리
 */
function generatePreviousMonthVendorSummary(targetMonthStr) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sourceSheet = ss.getSheetByName("파레트 요약 정산");
  if (!sourceSheet) return;

  const data = sourceSheet.getDataRange().getValues();
  const header = data[0];
  const vendorIdx = header.indexOf("화주사");
  const dateIdx = header.indexOf("갱신일");
  const feeIdx = header.indexOf("보관료(원)");
  const statusIdx = header.indexOf("상태");

  // ✅ 전달 월 기준으로 필터링
  const targetMonth = targetMonthStr; // "yyyy.MM" 형식

  const summaryMap = {};

  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    const vendor = row[vendorIdx] || "미지정";
    const status = row[statusIdx];
    const fee = Number(row[feeIdx]);
    const date = row[dateIdx];

    // ✅ 전달 월 데이터만 처리
    if (!vendor || !date || typeof date !== "string" || !date.startsWith(targetMonth)) continue;
    const key = vendor + "|" + targetMonth;

    if (!summaryMap[key]) {
      summaryMap[key] = {
        vendor,
        yyyymm: targetMonth,
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
      summaryMap[key].보관중 += 1;
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

/**
 * 전달 데이터만 백업하는 함수
 * 기존 exportVendorSheetsSeparately() 함수를 기반으로 하되, 전달 데이터만 백업
 */
function exportPreviousMonthBackup() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sourceSheet = ss.getSheetByName("파레트 요약 정산");
  if (!sourceSheet) {
    console.error("파레트 요약 정산 시트가 없습니다.");
    return;
  }

  const data = sourceSheet.getDataRange().getValues();
  const header = data[0];
  const vendorIdx = header.indexOf("화주사");
  const feeIdx = header.indexOf("보관료(원)");
  const statusIdx = header.indexOf("상태");
  const dateIdx = header.indexOf("갱신일");

  // ✅ 전달 월 계산
  const today = new Date();
  const previousMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1);
  const previousMonthStr = Utilities.formatDate(previousMonth, Session.getScriptTimeZone(), "yyyy.MM");
  const yyyymm = previousMonthStr.replace(".", "-"); // yyyy-MM 형식
  
  console.log(`전달 백업 실행: ${yyyymm}`);

  const titleFormatted = `${yyyymm.replace("-", "년 ")}월 파레트보관 상세내역`;

  // ✅ 드라이브 폴더 구조
  const rootFolder = getOrCreateFolderByName(DriveApp.getRootFolder(), "3pl자동화");
  const archiveFolder = getOrCreateFolderByName(rootFolder, "정산파일");
  const monthFolder = getOrCreateFolderByName(archiveFolder, yyyymm);

  // ✅ 전달 월 데이터만 필터링
  const vendorMap = {};
  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    const dateStr = row[dateIdx];
    
    // ✅ 전달 월 데이터만 처리
    if (typeof dateStr === "string" && dateStr.startsWith(previousMonthStr)) {
      const vendor = row[vendorIdx] || "미지정";
      if (!vendorMap[vendor]) vendorMap[vendor] = [];
      vendorMap[vendor].push(row);
    }
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

  console.log(`✅ 전달 데이터 백업 완료: ${yyyymm}`);
}

/**
 * 전달 자동화 통합 실행 함수
 * 매월 1일 0시 트리거에서 호출
 * 실행 순서: 정산 → 백업 → 자동화 중단
 */
function runPreviousMonthAutomation() {
  try {
    const startTime = new Date();
    console.log(`전달 자동화 시작: ${startTime.toLocaleString()}`);
    
    // 1단계: 전달 데이터 정산
    console.log("1단계: 전달 데이터 정산 실행");
    summarizePreviousMonthData();
    console.log("✅ 전달 데이터 정산 완료");
    
    // 2단계: 전달 데이터 백업
    console.log("2단계: 전달 데이터 백업 실행");
    exportPreviousMonthBackup();
    console.log("✅ 전달 데이터 백업 완료");
    
    // 3단계: 자동화 중단 (전달 자동화 완료 후 실행)
    // 전달 데이터 처리가 완료된 후 자동화를 중단하여 다음 달 데이터가 섞이지 않도록 함
    console.log("3단계: 자동화 중단 실행");
    if (typeof disableAutoSync === 'function') {
      disableAutoSync();
      console.log("✅ 자동화 중단 완료");
    } else {
      console.warn("⚠️ disableAutoSync 함수를 찾을 수 없습니다.");
    }
    
    const endTime = new Date();
    const duration = (endTime - startTime) / 1000;
    console.log(`✅ 전달 자동화 완료 (소요 시간: ${duration}초)`);
    
    // 성공 알림 이메일 (선택사항)
    const email = Session.getActiveUser().getEmail();
    const today = new Date();
    const previousMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1);
    const previousMonthStr = Utilities.formatDate(previousMonth, Session.getScriptTimeZone(), "yyyy년 MM월");
    
    MailApp.sendEmail({
      to: email,
      subject: `✅ ${previousMonthStr} 전달 자동화 완료`,
      body: `${previousMonthStr} 전달 데이터 자동화가 성공적으로 완료되었습니다.\n\n` +
            `실행 시간: ${startTime.toLocaleString()}\n` +
            `소요 시간: ${duration}초\n\n` +
            `Google Drive > 3pl자동화 > 정산파일 폴더에서 백업 파일을 확인하세요.`
    });
    
  } catch (error) {
    console.error("전달 자동화 실패:", error);
    
    // 에러 발생 시 이메일 알림
    const email = Session.getActiveUser().getEmail();
    MailApp.sendEmail({
      to: email,
      subject: "❌ 전달 자동화 실행 실패",
      body: `전달 자동화 실행 중 오류가 발생했습니다.\n\n` +
            `오류 내용: ${error.message}\n` +
            `스택 트레이스: ${error.stack}\n\n` +
            `시간: ${new Date().toLocaleString()}\n\n` +
            `수동으로 확인해주세요.`
    });
    
    // 에러를 다시 던져서 트리거 시스템에 알림
    throw error;
  }
}

// ========================================
// 🧪 테스트 함수들
// ========================================

/**
 * 전달 날짜 계산 확인 테스트
 */
function testPreviousMonthCalculation() {
  const today = new Date();
  const previousMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1);
  const previousMonthLastDay = new Date(today.getFullYear(), today.getMonth(), 0);
  const previousMonthStr = Utilities.formatDate(previousMonth, Session.getScriptTimeZone(), "yyyy.MM");
  
  console.log("현재 날짜:", today);
  console.log("전달 첫날:", previousMonth);
  console.log("전달 마지막날:", previousMonthLastDay);
  console.log("전달 월:", previousMonthStr);
  
  SpreadsheetApp.getUi().alert(
    `📅 전달 날짜 계산 확인\n\n` +
    `현재: ${Utilities.formatDate(today, Session.getScriptTimeZone(), "yyyy-MM-dd")}\n` +
    `전달: ${previousMonthStr} (${previousMonthLastDay.getDate()}일까지)\n\n` +
    `✅ 계산이 올바른지 확인하세요.`
  );
}

/**
 * 전달 데이터 정산만 테스트
 */
function testSummarizePreviousMonth() {
  console.log("전달 데이터 정산 테스트 시작...");
  
  try {
    summarizePreviousMonthData();
    console.log("✅ 전달 데이터 정산 완료");
    
    // 결과 확인
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = ss.getSheetByName("파레트 요약 정산");
    if (sheet) {
      const data = sheet.getDataRange().getValues();
      const dateIdx = data[0].indexOf("갱신일");
      
      if (dateIdx !== -1) {
        const today = new Date();
        const previousMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1);
        const previousMonthStr = Utilities.formatDate(previousMonth, Session.getScriptTimeZone(), "yyyy.MM");
        
        let previousMonthCount = 0;
        let otherMonthCount = 0;
        
        for (let i = 1; i < data.length; i++) {
          const dateStr = data[i][dateIdx];
          if (typeof dateStr === "string" && dateStr.startsWith(previousMonthStr)) {
            previousMonthCount++;
          } else if (dateStr) {
            otherMonthCount++;
          }
        }
        
        SpreadsheetApp.getUi().alert(
          `✅ 전달 데이터 정산 테스트 완료\n\n` +
          `전달 월: ${previousMonthStr}\n` +
          `전달 데이터: ${previousMonthCount}개 ✅\n` +
          `다른 월 데이터: ${otherMonthCount}개\n` +
          `전체 데이터: ${data.length - 1}개\n\n` +
          `전달 데이터만 정산되었는지 확인하세요.`
        );
      } else {
        SpreadsheetApp.getUi().alert("✅ 전달 데이터 정산 완료\n\n갱신일 컬럼을 찾을 수 없습니다.");
      }
    }
  } catch (error) {
    console.error("테스트 실패:", error);
    SpreadsheetApp.getUi().alert("❌ 테스트 실패\n\n오류: " + error.message);
  }
}

/**
 * 전달 데이터 백업만 테스트
 */
function testExportPreviousMonth() {
  console.log("전달 데이터 백업 테스트 시작...");
  
  try {
    exportPreviousMonthBackup();
    console.log("✅ 전달 데이터 백업 완료");
    
    SpreadsheetApp.getUi().alert(
      "✅ 전달 데이터 백업 테스트 완료\n\n" +
      "Google Drive > 3pl자동화 > 정산파일 폴더에서\n" +
      "전달 월 폴더를 확인하세요."
    );
  } catch (error) {
    console.error("테스트 실패:", error);
    SpreadsheetApp.getUi().alert("❌ 테스트 실패\n\n오류: " + error.message);
  }
}

/**
 * 데이터 필터링 확인 테스트 (시뮬레이션)
 */
function testDataFiltering() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const rawSheet = ss.getSheetByName("설문지 응답 시트1");
  
  if (!rawSheet) {
    SpreadsheetApp.getUi().alert("설문지 응답 시트1이 없습니다.");
    return;
  }
  
  const data = rawSheet.getDataRange().getValues();
  const header = data[0];
  const timeIdx = header.indexOf("타임스탬프");
  const idIdx = header.indexOf("파레트 ID");
  
  if (timeIdx === -1) {
    SpreadsheetApp.getUi().alert("타임스탬프 컬럼을 찾을 수 없습니다.");
    return;
  }
  
  // 전달 마지막 날 계산
  const today = new Date();
  const previousMonthLastDay = new Date(today.getFullYear(), today.getMonth(), 0);
  const previousMonthStr = Utilities.formatDate(
    new Date(today.getFullYear(), today.getMonth() - 1, 1),
    Session.getScriptTimeZone(),
    "yyyy.MM"
  );
  
  let totalRows = 0;
  let previousMonthRows = 0;
  let currentMonthRows = 0;
  let futureRows = 0;
  const sampleData = [];
  
  for (let i = 1; i < data.length; i++) {
    const time = new Date(data[i][timeIdx]);
    totalRows++;
    
    if (time <= previousMonthLastDay) {
      previousMonthRows++;
      if (sampleData.length < 5) {
        sampleData.push({
          row: i + 1,
          id: data[i][idIdx] || "미지정",
          time: Utilities.formatDate(time, Session.getScriptTimeZone(), "yyyy-MM-dd")
        });
      }
    } else if (time > today) {
      futureRows++;
    } else {
      currentMonthRows++;
    }
  }
  
  let message = `📊 데이터 필터링 분석 결과\n\n`;
  message += `전체 데이터: ${totalRows}개\n`;
  message += `전달 데이터 (${previousMonthStr}): ${previousMonthRows}개 ✅\n`;
  message += `이번달 데이터: ${currentMonthRows}개\n`;
  message += `미래 데이터: ${futureRows}개\n\n`;
  
  if (sampleData.length > 0) {
    message += `전달 데이터 샘플:\n`;
    sampleData.forEach(item => {
      message += `- 행 ${item.row}: ${item.id} (${item.time})\n`;
    });
    if (previousMonthRows > 5) {
      message += `... 외 ${previousMonthRows - 5}개 더\n`;
    }
  }
  
  message += `\n✅ 전달 데이터만 정산될 예정입니다.`;
  
  SpreadsheetApp.getUi().alert(message);
}

/**
 * 전체 자동화 테스트 (실제 실행 - 주의!)
 */
function testFullAutomation() {
  const ui = SpreadsheetApp.getUi();
  const response = ui.alert(
    "⚠️ 전체 자동화 테스트",
    "이 함수는 실제로 데이터를 정산하고 백업합니다.\n\n" +
    "실행하시겠습니까?\n\n" +
    "권장: 먼저 testDataFiltering()을 실행하세요.",
    ui.ButtonSet.YES_NO
  );
  
  if (response !== ui.Button.YES) {
    ui.alert("테스트가 취소되었습니다.");
    return;
  }
  
  try {
    console.log("전체 자동화 테스트 시작...");
    runPreviousMonthAutomation();
    
    ui.alert(
      "✅ 전체 자동화 테스트 완료\n\n" +
      "확인 사항:\n" +
      "1. 파레트 요약 정산 시트 확인\n" +
      "2. Google Drive 백업 파일 확인\n" +
      "3. 설정 시트 A19 셀이 '중단'인지 확인\n" +
      "4. 이메일 알림 확인"
    );
  } catch (error) {
    ui.alert(
      "❌ 테스트 실패\n\n" +
      "오류: " + error.message + "\n\n" +
      "콘솔 로그를 확인하세요."
    );
    console.error("테스트 실패:", error);
  }
}

