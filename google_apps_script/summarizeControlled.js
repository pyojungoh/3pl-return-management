// 📁 summarizeControlled.gs

// ✅ 설정 시트의 자동화 ON/OFF 값에 따라 정산 갱신 실행
function summarizePalletData_FormControlled() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName("설정");
  if (!sheet) return;

  const status = sheet.getRange("A19").getValue();
  if (status !== "사용") {
    SpreadsheetApp.getUi().alert("⛔️ 현재 자동화 상태는 '중단'입니다.\n\n정산 갱신이 차단되었습니다.");
    return;
  }

  // ✅ 정상 실행 허용 시 원본 함수 호출
  summarizePalletData();
}

// 📌 기존 summarizePalletData() 함수는 별도 파일에 있음
// 이 함수는 트리거 또는 수동 실행에 대응하는 조건 필터 역할만 함