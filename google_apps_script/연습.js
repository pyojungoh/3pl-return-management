// Apps Script에 이 함수를 추가하고 실행하세요
function forceBivid0006Update() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const summarySheet = ss.getSheetByName("파레트 요약 정산");
  const data = summarySheet.getDataRange().getValues();
  const header = data[0];
  
  const idIdx = header.indexOf("파레트 ID");
  const statusIdx = header.indexOf("상태");
  
  // bivid0006 찾아서 강제로 "보관종료"로 변경
  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    const id = (row[idIdx] + "").trim().toLowerCase();
    
    if (id === "bivid0006") {
      summarySheet.getRange(i + 1, statusIdx + 1).setValue("보관종료");
      console.log(`bivid0006 상태를 "보관종료"로 강제 변경했습니다. (행 ${i + 1})`);
      break;
    }
  }
  
  // 화주사별 시트 갱신
  splitByVendor();
  
  SpreadsheetApp.getUi().alert("✅ bivid0006 상태가 강제로 업데이트되었습니다.");
}