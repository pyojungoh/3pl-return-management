# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(__file__).resolve().parent / "pallets.html"
text = p.read_text(encoding="utf-8")

old_btn = """          <div class=\"pal-filter-group pal-admin-only\">
            <button class=\"pal-btn\" onclick=\"palDeleteSelectedPallets()\" style=\"height: 40px; background: #dc3545; color: white;\">���️ 선택��제</button>
          </div>
        </div>"""

new_btn = """          <div class=\"pal-filter-group pal-admin-only\">
            <button class=\"pal-btn\" onclick=\"palDeleteSelectedPallets()\" style=\"height: 40px; background: #dc3545; color: white;\">���️ 선택��제</button>
          </div>
          <div class=\"pal-filter-group pal-admin-only\">
            <button type=\"button\" class=\"pal-btn\" onclick=\"palPrintSelectedQrLabels()\" style=\"height: 40px; background: #17a2b8; color: white;\">���️ 선택 QR 인���</button>
          </div>
        </div>"""

if old_btn not in text:
    raise SystemExit("button block not found")

text = text.replace(old_btn, new_btn, 1)

helpers = r'''
    var PAL_GOOGLE_FORM_BASE = 'https://docs.google.com/forms/d/e/1FAIpQLSdDmnWcW27tfDptUvuSjEgN8K7nNNQWecdpeMMhwftTtbiyIQ/viewform';

    function palBuildPalletQrText(palletId, vendor, product) {
      var v = vendor || '';
      var p = product || '';
      return PAL_GOOGLE_FORM_BASE + '?usp=pp_url&entry.419411235=' + encodeURIComponent(palletId) +
        '&entry.427884801=' + encodeURIComponent('\ubcf4\uad00\uc885\ub8cc') +
        '&entry.2110345042=' + encodeURIComponent(v) +
        '&entry.306824944=' + encodeURIComponent(p);
    }

    async function palQrTextToDataUrl(qrText, pixelSize) {
      var size = pixelSize || 200;
      if (typeof QRCode !== 'undefined') {
        return new Promise(function (resolve, reject) {
          var wrap = document.createElement('div');
          wrap.style.position = 'fixed';
          wrap.style.left = '-9999px';
          wrap.style.top = '0';
          document.body.appendChild(wrap);
          try {
            var CL = QRCode.CorrectLevel || { M: 0 };
            new QRCode(wrap, {
              text: qrText,
              width: size,
              height: size,
              colorDark: '#000000',
              colorLight: '#ffffff',
              correctLevel: CL.M
            });
            requestAnimationFrame(function () {
              requestAnimationFrame(function () {
                try {
                  var canvas = wrap.querySelector('canvas');
                  if (canvas) {
                    var url = canvas.toDataURL('image/png');
                    document.body.removeChild(wrap);
                    resolve(url);
                  } else {
                    document.body.removeChild(wrap);
                    reject(new Error('QR canvas missing'));
                  }
                } catch (e) {
                  try { document.body.removeChild(wrap); } catch (e2) {}
                  reject(e);
                }
              });
            });
          } catch (e) {
            try { document.body.removeChild(wrap); } catch (e2) {}
            reject(e);
          }
        });
      }
      var chartUrl = 'https://quickchart.io/qr?text=' + encodeURIComponent(qrText) + '&size=' + size + '&margin=1';
      var res = await fetch(chartUrl);
      if (!res.ok) throw new Error('QR image fetch failed');
      var blob = await res.blob();
      return await new Promise(function (resolve, reject) {
        var reader = new FileReader();
        reader.onloadend = function () { resolve(reader.result); };
        reader.onerror = reject;
        reader.readAsDataURL(blob);
      });
    }

    async function palWaitPrintImages(root) {
      var imgs = root.querySelectorAll('img');
      await Promise.all(Array.from(imgs).map(function (img) {
        if (img.complete && img.naturalWidth > 0) return Promise.resolve();
        if (img.decode) {
          return img.decode().catch(function () {
            return new Promise(function (res) {
              img.onload = function () { res(); };
              img.onerror = function () { res(); };
            });
          });
        }
        return new Promise(function (res) {
          img.onload = img.onerror = function () { res(); };
        });
      }));
      await new Promise(function (r) { setTimeout(r, 80); });
    }

    function palFormatPalletInDateForLabel(inDateRaw) {
      if (!inDateRaw) return '-';
      try {
        var d = new Date(inDateRaw);
        if (!isNaN(d.getTime())) {
          return d.toLocaleDateString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit' }).replace(/\. /g, '-').replace(/\./g, '');
        }
      } catch (e) {}
      return String(inDateRaw);
    }

    async function palExecuteRollQrPrint(innerHtml) {
      var printArea = document.getElementById('palQRPrintArea');
      if (!printArea) return;
      printArea.innerHTML = innerHtml;

      var printStyle = document.createElement('style');
      printStyle.id = 'palQRPrintStyle';
      printStyle.textContent =
        '@media print {\n' +
        '  @page { size: 63.5mm 70mm; margin: 0; }\n' +
        '  * { margin: 0; padding: 0; }\n' +
        '  html, body { margin: 0 !important; padding: 0 !important; overflow: visible !important; }\n' +
        '  body > *:not(#palQRPrintArea) { display: none !important; }\n' +
        '  #palQRPrintArea {\n' +
        '    display: block !important; position: absolute !important; left: 0 !important; top: 0 !important;\n' +
        '    width: 63.5mm !important; height: auto !important; margin: 0 !important; padding: 0 !important;\n' +
        '    background: white !important;\n' +
        '  }\n' +
        '  .pal-qr-label-page {\n' +
        '    width: 63.5mm !important; height: 70mm !important; box-sizing: border-box !important;\n' +
        '    padding: 3mm !important; display: flex !important; flex-direction: column !important;\n' +
        '    align-items: center !important; justify-content: flex-start !important;\n' +
        '    background: white !important; page-break-inside: avoid !important;\n' +
        '    page-break-after: always !important;\n' +
        '  }\n' +
        '  .pal-qr-label-page:last-of-type { page-break-after: auto !important; }\n' +
        '  .pal-qr-label-page img {\n' +
        '    max-width: 100% !important; max-height: 100% !important; width: auto !important; height: auto !important;\n' +
        '    object-fit: contain !important;\n' +
        '  }\n' +
        '}\n';

      var existingStyle = document.getElementById('palQRPrintStyle');
      if (existingStyle) document.head.removeChild(existingStyle);
      document.head.appendChild(printStyle);

      var bodyChildren = Array.from(document.body.children);
      var hiddenElements = [];
      bodyChildren.forEach(function (child) {
        if (child.id !== 'palQRPrintArea') {
          child.setAttribute('data-pal-original-display', window.getComputedStyle(child).display);
          child.style.display = 'none';
          hiddenElements.push(child);
        }
      });

      printArea.style.display = 'block';
      printArea.style.position = 'absolute';
      printArea.style.left = '0';
      printArea.style.top = '0';
      printArea.style.width = '63.5mm';
      document.body.insertBefore(printArea, document.body.firstChild);

      try {
        await palWaitPrintImages(printArea);
        window.print();
      } finally {
        setTimeout(function () {
          hiddenElements.forEach(function (child) {
            var od = child.getAttribute('data-pal-original-display');
            child.style.display = od || '';
            child.removeAttribute('data-pal-original-display');
          });
          printArea.innerHTML = '';
          printArea.style.display = 'none';
          var st = document.getElementById('palQRPrintStyle');
          if (st) document.head.removeChild(st);
        }, 200);
      }
    }

    function palBuildSingleLabelHtml(palletId, product, vendor, inDateStr, qrDataUrl) {
      return (
        '<div class="pal-qr-label-page">' +
        '<div style="width:100%;text-align:center;flex-shrink:0;margin-bottom:3px;">' +
        '<div style="font-size:11px;font-weight:600;margin-bottom:2px;line-height:1.2;">\ud30c\ub808\ud2b8 ID: ' + palEscapeHtml(palletId) + '</div>' +
        '<div style="font-size:11px;font-weight:600;margin-bottom:3px;line-height:1.2;">' + palEscapeHtml(product || '-') + '</div>' +
        '</div>' +
        '<div style="display:flex;align-items:center;justify-content:center;margin-bottom:3px;width:100%;flex-shrink:0;">' +
        '<img src="' + qrDataUrl + '" alt="QR" style="width:150px;height:150px;object-fit:contain;">' +
        '</div>' +
        '<div style="width:100%;text-align:center;flex-shrink:0;">' +
        '<div style="font-size:11px;font-weight:600;margin-bottom:2px;line-height:1.2;">\ud654\uc8fc\uc0ac: ' + palEscapeHtml(vendor || '') + '</div>' +
        '<div style="font-size:11px;font-weight:600;line-height:1.2;">\uc785\uace0\uc77c: ' + palEscapeHtml(inDateStr) + '</div>' +
        '</div></div>'
      );
    }

 async function palPrintSelectedQrLabels() {
      if (palCurrentRole !== '\uad00\ub9ac\uc790') {
        alert('\uad00\ub9ac\uc790\ub9cc \uc0ac\uc6a9\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.');
        return;
      }
      var checked = Array.from(document.querySelectorAll('.pal-pallet-checkbox:checked'));
      var ids = checked.map(function (cb) { return cb.getAttribute('data-pallet-id'); }).filter(Boolean);
      if (ids.length === 0) {
        alert('QR\uc744 \ucd9c\ub825\ud560 \ud30c\ub808\ud2b8\ub97c \uccb4\ud06c\ud558\uc138\uc694.');
        return;
      }
      if (ids.length > 80) {
        if (!confirm(ids.length + '\uac74 \uc785\ub2c8\ub2e4. \uacc4\uc18d\ud558\uc2dc\uaca0\uc2b5\ub2c8\uae4c? (\uc2dc\uac04\uc774 \uac78\ub9b4 \uc218 \uc788\uc2b5\ub2c8\ub2e4)')) return;
      }
      var parts = [];
      try {
        for (var i = 0; i < ids.length; i++) {
          var pid = ids[i];
          var res = await fetch(PAL_API_BASE_URL + '/api/pallets/' + encodeURIComponent(pid), { headers: palGetUserHeaders() });
          var json = await res.json();
          if (!json.success || !json.data) continue;
          var row = json.data;
          var qrText = palBuildPalletQrText(row.pallet_id, row.company_name || '', row.product_name || '');
          var dataUrl = await palQrTextToDataUrl(qrText, 200);
          var inStr = palFormatPalletInDateForLabel(row.in_date || '');
          parts.push(palBuildSingleLabelHtml(row.pallet_id, row.product_name, row.company_name, inStr, dataUrl));
        }
        if (parts.length === 0) {
          alert('\ub370\uc774\ud130\ub97c \ubd88\ub7ec\uc62c \uc218 \uc5c6\uc2b5\ub2c8\ub2e4.');
          return;
        }
        await palExecuteRollQrPrint(parts.join(''));
      } catch (e) {
        console.error('palPrintSelectedQrLabels', e);
        alert('\uc77c\uad04 \uc778\uc1c4 \uc911 \uc624\ub958: ' + (e.message || e));
      }
    }
    window.palPrintSelectedQrLabels = palPrintSelectedQrLabels;
'''

anchor = """    function palEscapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }

    /**
     * ��신일 계산 (보관이 1달 이상이면 매월 1일)"""

if anchor not in text:
    raise SystemExit("palEscapeHtml anchor not found")

text = text.replace(anchor, """    function palEscapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }
""" + helpers + """
    /**
     * ��신일 계산 (보관이 1달 이상이면 매월 1일)""", 1)

# Globals for QR print cache
g_anchor = """    if (typeof palCurrentQRInDate === 'undefined') {
      var palCurrentQRInDate = null;
    }
    
    // QR 코드 보기 모달 ��기"""
if g_anchor not in text:
    raise SystemExit("QR globals anchor not found")

text = text.replace(
    g_anchor,
    """    if (typeof palCurrentQRInDate === 'undefined') {
      var palCurrentQRInDate = null;
    }
    if (typeof palCurrentQRDataUrl === 'undefined') {
      var palCurrentQRDataUrl = null;
    }
    if (typeof palCurrentQRMeta === 'undefined') {
      var palCurrentQRMeta = null;
    }
    
    // QR 코드 보�기""",
    1,
)

# palViewQRCode replacement
v_old = """    async function palViewQRCode(palletId, inDate) {
      try {
        // 파레트 상세 정보 가져오기
        const response = await fetch(`${PAL_API_BASE_URL}/api/pallets/${palletId}`, {
          headers: palGetUserHeaders()
        });
        
        const result = await response.json();
        const palletInfo = result.success && result.data ? result.data : null;
        
        palCurrentQRPalletId = palletId;
        palCurrentQRInDate = palletInfo?.in_date || inDate || '';
        
        const modal = document.getElementById('palQRModal');
        const titleEl = document.getElementById('palQRTitle');
        const inDateEl = document.getElementById('palQRInDate');
        const qrContainer = document.getElementById('palQRCodeContainer');
        
        if (modal && titleEl && inDateEl && qrContainer) {
          titleEl.textContent = `파레트 ID: ${palletId}`;
          inDateEl.textContent = `입고일: ${palCurrentQRInDate || '-'}`;
          
          // QR 코드 생성 (quickchart.io 사용)
          // Google Apps Script와 동일한 형식: 파레트ID, 작업유형(보관종료), ��주�목명 포함
          const formUrl = "https://docs.google.com/forms/d/e/1FAIpQLSdDmnWcW27tfDptUvuSjEgN8K7nNNQWecdpeMMhwftTtbiyIQ/viewform";
          const vendor = palletInfo?.company_name || '';
          const product = palletInfo?.product_name || '';
          // entry.419411235 = 파레트 ID
          // entry.427884801 = 작업 유형 (보관종료)
          // entry.2110345042 = ��주사
          // entry.306824�목명
          const qrText = `${formUrl}?usp=pp_url&entry.419411235=${encodeURIComponent(palletId)}&entry.427884801=보관종료&entry.2110345042=${encodeURIComponent(vendor)}&entry.306824944=${encodeURIComponent(product)}`;
          const qrImageUrl = `https://quickchart.io/qr?text=${encodeURIComponent(qrText)}&size=300`;
          
          qrContainer.innerHTML = `<img src="${qrImageUrl}" alt="QR Code" style="max-width: 300px; width: 100%; height: auto;">`;
          
          modal.style.display = 'block';
        }
      } catch (error) {
        console.error('QR�기 오류:', error);
        alert('QR 코드를 불러오는 중 오류가 발생했습니다.');
      }
    }"""

v_new = """    async function palViewQRCode(palletId, inDate) {
      try {
        const response = await fetch(`${PAL_API_BASE_URL}/api/pallets/${palletId}`, {
          headers: palGetUserHeaders()
        });
        
        const result = await response.json();
        const palletInfo = result.success && result.data ? result.data : null;
        
        palCurrentQRPalletId = palletId;
        palCurrentQRInDate = palletInfo?.in_date || inDate || '';
        palCurrentQRDataUrl = null;
        palCurrentQRMeta = null;
        
        const modal = document.getElementById('palQRModal');
        const titleEl = document.getElementById('palQRTitle');
        const inDateEl = document.getElementById('palQRInDate');
        const qrContainer = document.getElementById('palQRCodeContainer');
        
        if (modal && titleEl && inDateEl && qrContainer) {
          titleEl.textContent = `파레트 ID: ${palletId}`;
          inDateEl.textContent = `입고일: ${palCurrentQRInDate || '-'}`;
          qrContainer.innerHTML = '<div style="padding:24px;color:#636e72;">QR 생성 중...</div>';
          modal.style.display = 'block';
          
          const vendor = palletInfo?.company_name || '';
          const product = palletInfo?.product_name || '';
          const qrText = palBuildPalletQrText(palletId, vendor, product);
          const dataUrl = await palQrTextToDataUrl(qrText, 280);
          palCurrentQRDataUrl = dataUrl;
          palCurrentQRMeta = { vendor: vendor, product: product };
          
          qrContainer.innerHTML = `<img src="${dataUrl}" alt="QR Code" style="max-width: 300px; width: 100%; height: auto;">`;
        }
      } catch (error) {
        console.error('QR 코드 모달 ��기 오류:', error);
        alert('QR 코드를 불러오는 중 오류가 발생했습니다.');
      }
    }"""

if v_old not in text:
    raise SystemExit("palViewQRCode block not found")
text = text.replace(v_old, v_new, 1)

# palCloseQRModal
c_old = """      palCurrentQRPalletId = null;
      palCurrentQRInDate = null;
    }
    
    // QR� (63.5mm * 70mm 라��)"""
if c_old not in text:
    raise SystemExit("palCloseQRModal anchor not found")
text = text.replace(
    c_old,
    """      palCurrentQRPalletId = null;
      palCurrentQRInDate = null;
      palCurrentQRDataUrl = null;
      palCurrentQRMeta = null;
    }
    
    //�� (63.5mm * 70mm 라��)""",
    1,
)

# palPrintQRCode - find and replace whole function
p_start = text.find("    async function palPrintQRCode() {")
if p_start < 0:
    raise SystemExit("palPrintQRCode not found")
p_end = text.find("    // 모달��� 시 ��기", p_start)
if p_end < 0:
    raise SystemExit("palPrintQRCode end not found")
p_new_fn = """    async function palPrintQRCode() {
      if (!palCurrentQRPalletId) return;
      
      try {
        var palletId = palCurrentQRPalletId;
        var inDateStr = palFormatPalletInDateForLabel(palCurrentQRInDate);
        var vendor = '';
        var product = '';
        if (palCurrentQRMeta) {
          vendor = palCurrentQRMeta.vendor || '';
          product = palCurrentQRMeta.product || '';
        }
        var dataUrl = palCurrentQRDataUrl;
        if (!dataUrl) {
          const response = await fetch(`${PAL_API_BASE_URL}/api/pallets/${palletId}`, {
            headers: palGetUserHeaders()
          });
          const result = await response.json();
          const palletInfo = result.success && result.data ? result.data : null;
          vendor = palletInfo?.company_name || '';
          product = palletInfo?.product_name || '';
          var qrText = palBuildPalletQrText(palletId, vendor, product);
          dataUrl = await palQrTextToDataUrl(qrText, 200);
          palCurrentQRDataUrl = dataUrl;
          palCurrentQRMeta = { vendor: vendor, product: product };
        }
        var html = palBuildSingleLabelHtml(palletId, product, vendor, inDateStr, dataUrl);
        await palExecuteRollQrPrint(html);
      } catch (error) {
        console.error('QR 코드 인��� 오류:', error);
        alert('�� 중 오류가 발생했습니다.');
      }
    }
    
"""
text = text[:p_start] + p_new_fn + text[p_end:]

p.write_text(text, encoding="utf-8")
print("patched OK")
