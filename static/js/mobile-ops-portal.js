/**
 * 모바일 작업 포털 — C/S 조회·관리, 특수작업 목록·등록(관리자) (mobile_ops.html)
 * API·localStorage 키는 대시보드와 동일. 특수작업 API는 X-User-Role / X-User-Name / X-Company-Name 헤더를 사용한다.
 */
(function (global) {
  'use strict';

  var LS = {
    company: 'client_company',
    username: 'client_username',
    role: 'client_role',
    loginTime: 'client_loginTime'
  };

  /** 모바일 ops 전용 — 자동 로그인(기기 로컬 저장, 공용 PC 비권장) */
  var LS_AUTO = {
    remember: 'mop_auto_login',
    savedUser: 'mop_saved_username',
    savedPass: 'mop_saved_password'
  };

  function clearAutoLoginStorage() {
    try {
      localStorage.removeItem(LS_AUTO.remember);
      localStorage.removeItem(LS_AUTO.savedUser);
      localStorage.removeItem(LS_AUTO.savedPass);
    } catch (e) { /* ignore */ }
  }

  function saveAutoLoginIfChecked(username, password) {
    var chk = $('mopRemember');
    try {
      if (chk && chk.checked) {
        localStorage.setItem(LS_AUTO.remember, '1');
        localStorage.setItem(LS_AUTO.savedUser, username);
        localStorage.setItem(LS_AUTO.savedPass, password);
      } else {
        clearAutoLoginStorage();
      }
    } catch (e) { /* ignore */ }
  }

  function syncRememberCheckbox() {
    var chk = $('mopRemember');
    if (!chk) return;
    try {
      chk.checked = localStorage.getItem(LS_AUTO.remember) === '1';
      var su = localStorage.getItem(LS_AUTO.savedUser);
      if (su && $('mopUser')) $('mopUser').value = su;
    } catch (e) { /* ignore */ }
  }

  function getSavedCredentials() {
    try {
      if (localStorage.getItem(LS_AUTO.remember) !== '1') return null;
      var u = localStorage.getItem(LS_AUTO.savedUser);
      var p = localStorage.getItem(LS_AUTO.savedPass);
      if (u && p) return { username: u, password: p };
    } catch (e) { /* ignore */ }
    return null;
  }

  function performLogin(username, password) {
    return fetch(state.apiBase + '/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: username, password: password })
    }).then(function (r) { return r.json(); });
  }

  function getApiBase() {
    var origin = global.location.origin || '';
    var protocol = global.location.protocol || '';
    var host = global.location.hostname || '';
    if (!origin || origin === 'null' || protocol === 'file:' || protocol === 'vscode-webview:') {
      return 'http://127.0.0.1:5000';
    }
    if (host === '127.0.0.1' || host === 'localhost' || /^\d+\.\d+\.\d+\.\d+$/.test(host)) {
      return origin;
    }
    return origin;
  }

  function escapeHtml(text) {
    if (text == null || text === '') return '';
    var div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
  }

  function formatCsDate(cs) {
    if (cs.created_at) {
      var s = String(cs.created_at);
      if (/^\d{4}-\d{2}-\d{2}/.test(s)) return s.slice(0, 16).replace('T', ' ');
      var d = new Date(s);
      if (!isNaN(d.getTime())) {
        var y = d.getFullYear();
        var m = String(d.getMonth() + 1).padStart(2, '0');
        var day = String(d.getDate()).padStart(2, '0');
        var h = String(d.getHours()).padStart(2, '0');
        var min = String(d.getMinutes()).padStart(2, '0');
        return y + '-' + m + '-' + day + ' ' + h + ':' + min;
      }
      return s.slice(0, 16);
    }
    return cs.date || '-';
  }

  function statusClass(st) {
    if (st === '처리완료') return 'mop-badge--완료';
    if (st === '처리불가') return 'mop-badge--불가';
    if (st === '보류') return 'mop-badge--보류';
    return 'mop-badge--접수';
  }

  /** 카드 우측 상태 라벨 (접수 → 대기중) */
  function statusLabel(st) {
    var s = (st || '').trim() || '접수';
    if (s === '접수') return '대기중';
    return s;
  }

  /** C/S 종류(누락·오배송 등) — 리스트·시트 배지용 클래스 */
  function issueTypeBadgeClass(issueType) {
    var t = (issueType || '').trim();
    var map = {
      누락: 'mop-type--missing',
      오배송: 'mop-type--wrong',
      교환: 'mop-type--exchange',
      반품: 'mop-type--return',
      취소: 'mop-type--cancel',
      기타: 'mop-type--other'
    };
    return 'mop-type ' + (map[t] || 'mop-type--default');
  }

  var state = {
    apiBase: getApiBase(),
    company: '',
    username: '',
    role: '',
    csList: [],
    filter: 'all',
    month: '',
    selectedId: null,
    mopPane: 'cs',
    swList: [],
    swWorkTypes: [],
    swModalPhotos: []
  };

  function $(id) {
    return document.getElementById(id);
  }

  function authHeaders() {
    function enc(v) {
      return encodeURIComponent((v == null ? '' : String(v)).trim());
    }
    return {
      'X-User-Role': enc(state.role || '화주사'),
      'X-User-Name': enc(state.username || ''),
      'X-Company-Name': enc(state.company || '')
    };
  }

  function monthKoreanToRange(label) {
    var m = /^(\d{4})년(\d{2})월$/.exec(String(label || '').trim());
    if (!m) return { start: '', end: '' };
    var y = m[1];
    var mo = m[2];
    var im = parseInt(mo, 10);
    var iy = parseInt(y, 10);
    var last = new Date(iy, im, 0).getDate();
    return {
      start: y + '-' + mo + '-01',
      end: y + '-' + mo + '-' + String(last).padStart(2, '0')
    };
  }

  function parseSwPhotoUrls(photoLinks) {
    var s = (photoLinks || '').trim();
    if (!s) return [];
    return s.split(',').map(function (x) { return x.trim(); }).filter(function (u) {
      return /^https?:\/\//i.test(u);
    });
  }

  function parseUploadPhotoLinksString(photoLinksRaw) {
    if (!photoLinksRaw) return '';
    var lines = String(photoLinksRaw).split('\n').filter(function (line) { return line.trim(); });
    var urls = lines.map(function (line) {
      var idx = line.indexOf(':');
      if (idx >= 0) return line.slice(idx + 1).trim();
      return '';
    }).filter(Boolean);
    return urls.join(',');
  }

  function setMopPane(pane) {
    state.mopPane = pane;
    var tCs = $('mopTabCs');
    var tSw = $('mopTabSw');
    var pCs = $('mopPaneCs');
    var pSw = $('mopPaneSw');
    var ht = $('mopHeaderTitle');
    if (tCs) {
      tCs.classList.toggle('mop-tab--active', pane === 'cs');
      tCs.setAttribute('aria-current', pane === 'cs' ? 'page' : 'false');
    }
    if (tSw) {
      tSw.classList.toggle('mop-tab--active', pane === 'sw');
      tSw.setAttribute('aria-current', pane === 'sw' ? 'page' : 'false');
    }
    if (pCs) pCs.classList.toggle('mop-hidden', pane !== 'cs');
    if (pSw) pSw.classList.toggle('mop-hidden', pane !== 'sw');
    if (ht) ht.textContent = pane === 'sw' ? '특수작업' : 'C/S';
    if (pane === 'sw') loadSwWorks();
  }

  function updateSwRegisterBtn() {
    var b = $('mopSwRegisterBtn');
    if (!b) return;
    if (state.role === '관리자') b.classList.remove('mop-hidden');
    else b.classList.add('mop-hidden');
  }

  function closeSwModal() {
    var bd = $('mopSwModalBackdrop');
    if (bd) bd.classList.add('mop-hidden');
    state.swModalPhotos = [];
    var pv = $('mopSwPhotoPreview');
    if (pv) pv.innerHTML = '';
    var fi = $('mopSwFormPhotos');
    if (fi) fi.value = '';
  }

  function compressImageFile(file, maxW, maxH, quality) {
    maxW = maxW || 1920;
    maxH = maxH || 1920;
    quality = quality == null ? 0.82 : quality;
    return new Promise(function (resolve, reject) {
      var reader = new FileReader();
      reader.onload = function (e) {
        var img = new Image();
        img.onload = function () {
          var w = img.width;
          var h = img.height;
          if (w > h) {
            if (w > maxW) {
              h = (h * maxW) / w;
              w = maxW;
            }
          } else if (h > maxH) {
            w = (w * maxH) / h;
            h = maxH;
          }
          var canvas = document.createElement('canvas');
          canvas.width = w;
          canvas.height = h;
          var ctx = canvas.getContext('2d');
          ctx.drawImage(img, 0, 0, w, h);
          resolve(canvas.toDataURL('image/jpeg', quality));
        };
        img.onerror = reject;
        img.src = e.target.result;
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  function renderMopSwPhotoPreview() {
    var pv = $('mopSwPhotoPreview');
    if (!pv) return;
    pv.innerHTML = state.swModalPhotos.map(function (photo, index) {
      return (
        '<div class="mop-sw-photo-thumb-wrap">' +
        '<img src="' + photo.url + '" alt="">' +
        '<button type="button" class="mop-sw-photo-remove" data-mop-sw-idx="' + index + '" aria-label="삭제">×</button>' +
        '</div>'
      );
    }).join('');
    pv.querySelectorAll('.mop-sw-photo-remove').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var i = parseInt(btn.getAttribute('data-mop-sw-idx'), 10);
        if (!isNaN(i)) {
          state.swModalPhotos.splice(i, 1);
          renderMopSwPhotoPreview();
        }
      });
    });
  }

  function handleMopSwPhotoInputChange(ev) {
    var files = Array.from((ev.target && ev.target.files) || []);
    var i = 0;
    function next() {
      if (i >= files.length) {
        if (ev.target) ev.target.value = '';
        renderMopSwPhotoPreview();
        return;
      }
      var file = files[i];
      i += 1;
      if (!file.type || file.type.indexOf('image/') !== 0) {
        next();
        return;
      }
      compressImageFile(file)
        .then(function (url) {
          state.swModalPhotos.push({ url: url });
          next();
        })
        .catch(function () {
          var reader = new FileReader();
          reader.onload = function (e) {
            state.swModalPhotos.push({ url: e.target.result });
            next();
          };
          reader.onerror = next;
          reader.readAsDataURL(file);
        });
    }
    next();
  }

  function fillSwModalCompanySelect() {
    var dst = $('mopSwFormCompany');
    var src = $('mopCompany');
    if (!dst || !src) return;
    dst.innerHTML = '';
    for (var j = 0; j < src.options.length; j++) {
      var o = src.options[j];
      if (!o.value) continue;
      var n = document.createElement('option');
      n.value = o.value;
      n.textContent = o.textContent;
      dst.appendChild(n);
    }
    if (!dst.options.length) {
      var ph = document.createElement('option');
      ph.value = '';
      ph.textContent = '화주사 없음';
      dst.appendChild(ph);
      return;
    }
    dst.selectedIndex = 0;
  }

  function mopSwSyncPriceFromType() {
    var sel = $('mopSwFormType');
    var price = $('mopSwFormPrice');
    if (!sel || !price || !sel.selectedOptions.length) return;
    var opt = sel.selectedOptions[0];
    var dp = opt.getAttribute('data-default-price');
    if (dp !== null && dp !== '' && !isNaN(Number(dp))) price.value = String(Math.round(Number(dp)));
  }

  function fillSwModalTypeSelect() {
    var sel = $('mopSwFormType');
    if (!sel) return Promise.resolve();
    sel.innerHTML = '<option value="">불러오는 중…</option>';
    return fetch(state.apiBase + '/api/special-works/types', {
      headers: authHeaders(),
      credentials: 'include'
    })
      .then(function (r) { return r.json(); })
      .then(function (res) {
        sel.innerHTML = '';
        var list = (res.success && res.data) ? res.data : [];
        state.swWorkTypes = list.slice();
        list.forEach(function (t) {
          var o = document.createElement('option');
          o.value = String(t.id);
          o.textContent = t.name || '';
          o.setAttribute('data-default-price', String(t.default_unit_price != null ? t.default_unit_price : ''));
          sel.appendChild(o);
        });
        if (!list.length) {
          var x = document.createElement('option');
          x.value = '';
          x.textContent = '등록된 종류 없음';
          sel.appendChild(x);
        } else {
          mopSwSyncPriceFromType();
        }
      })
      .catch(function () {
        sel.innerHTML = '<option value="">종류 로드 실패</option>';
      });
  }

  function openSwModal() {
    if (state.role !== '관리자') {
      toast('관리자만 등록할 수 있습니다.', true);
      return;
    }
    fillSwModalCompanySelect();
    return fillSwModalTypeSelect().then(function () {
      var d = $('mopSwFormDate');
      if (d) {
        var t = new Date();
        d.value = t.getFullYear() + '-' + String(t.getMonth() + 1).padStart(2, '0') + '-' + String(t.getDate()).padStart(2, '0');
      }
      var q = $('mopSwFormQty');
      if (q) q.value = '1';
      var me = $('mopSwFormMemo');
      if (me) me.value = '';
      state.swModalPhotos = [];
      renderMopSwPhotoPreview();
      var bd = $('mopSwModalBackdrop');
      if (bd) bd.classList.remove('mop-hidden');
    });
  }

  function loadSwWorks() {
    var listEl = $('mopSwList');
    if (!listEl) return Promise.resolve();
    listEl.innerHTML = '<div class="mop-empty">불러오는 중…</div>';
    state.month = ($('mopMonth') && $('mopMonth').value) || state.month;
    var range = monthKoreanToRange(state.month);
    var q = [];
    if (range.start) q.push('start_date=' + encodeURIComponent(range.start));
    if (range.end) q.push('end_date=' + encodeURIComponent(range.end));
    if (state.role === '관리자') {
      var cf = companyFilterForApi();
      if (cf) q.push('company_name=' + encodeURIComponent(cf));
    }
    var url = state.apiBase + '/api/special-works/works?' + q.join('&');
    return fetch(url, { headers: authHeaders(), credentials: 'include' })
      .then(function (r) { return r.json(); })
      .then(function (result) {
        if (result.success) {
          state.swList = result.data || [];
          renderSwList();
        } else {
          state.swList = [];
          listEl.innerHTML = '<div class="mop-empty">' + escapeHtml(result.message || '목록을 불러올 수 없습니다.') + '</div>';
          toast(result.message || '특수작업 목록 실패', true);
        }
      })
      .catch(function () {
        state.swList = [];
        listEl.innerHTML = '<div class="mop-empty">네트워크 오류</div>';
        toast('네트워크 오류', true);
      });
  }

  function renderSwList() {
    var listEl = $('mopSwList');
    if (!listEl) return;
    var rows = state.swList || [];
    if (!rows.length) {
      listEl.innerHTML = '<div class="mop-empty">해당 기간 특수작업이 없습니다.</div>';
      return;
    }
    var sorted = rows.slice().sort(function (a, b) {
      var c = String(b.work_date || '').localeCompare(String(a.work_date || ''));
      if (c !== 0) return c;
      return String(b.created_at || '').localeCompare(String(a.created_at || ''));
    });
    listEl.innerHTML = sorted.map(function (w) {
      var wd = (w.work_date || '').toString().slice(0, 10);
      var wdShort = wd.length >= 10 ? wd.slice(5).replace('-', '/') : wd;
      var type = escapeHtml(w.work_type_name || '-');
      var comp = escapeHtml(w.company_name || '');
      var amt = (w.total_price != null ? Math.round(Number(w.total_price)) : 0).toLocaleString('ko-KR');
      var memo = escapeHtml((w.memo || '').replace(/\s+/g, ' ').trim().slice(0, 80));
      var photos = parseSwPhotoUrls(w.photo_links);
      var thumbs = photos.slice(0, 4).map(function (u) {
        return '<img class="mop-sw-card__thumb" src="' + escapeHtml(u) + '" alt="" loading="lazy">';
      }).join('');
      return (
        '<article class="mop-sw-card" tabindex="0">' +
        '<div class="mop-sw-card__row1">' +
        '<span class="mop-sw-card__date">' + escapeHtml(wdShort) + '</span>' +
        '<span class="mop-sw-card__type">' + type + '</span>' +
        '<span class="mop-sw-card__amt">' + escapeHtml(amt) + '원</span>' +
        '</div>' +
        '<div class="mop-sw-card__row2">' + comp + (memo ? ' · ' + memo : '') + '</div>' +
        (thumbs ? '<div class="mop-sw-card__photos">' + thumbs + '</div>' : '') +
        '</article>'
      );
    }).join('');
  }

  function submitSwModal() {
    var btn = $('mopSwFormSubmit');
    var companySel = $('mopSwFormCompany');
    var typeSel = $('mopSwFormType');
    var dateEl = $('mopSwFormDate');
    var qtyEl = $('mopSwFormQty');
    var priceEl = $('mopSwFormPrice');
    var memoEl = $('mopSwFormMemo');
    var companyName = (companySel && companySel.value || '').trim();
    var workTypeId = typeSel && typeSel.value ? parseInt(typeSel.value, 10) : NaN;
    var workDate = (dateEl && dateEl.value || '').trim();
    var quantity = qtyEl ? parseFloat(qtyEl.value) : NaN;
    var unitPrice = priceEl ? parseFloat(priceEl.value) : NaN;
    var memo = (memoEl && memoEl.value || '').trim();
    if (!companyName) {
      toast('화주사를 선택해 주세요.', true);
      return;
    }
    if (!workTypeId) {
      toast('작업 종류를 선택해 주세요.', true);
      return;
    }
    if (!workDate) {
      toast('작업일을 선택해 주세요.', true);
      return;
    }
    if (!(quantity > 0)) {
      toast('수량은 1 이상이어야 합니다.', true);
      return;
    }
    if (isNaN(unitPrice) || unitPrice < 0) {
      toast('단가를 확인해 주세요.', true);
      return;
    }
    if (btn) btn.disabled = true;
    var photoLinksFinal = '';
    var chain = Promise.resolve();
    if (state.swModalPhotos.length) {
      var imgs = state.swModalPhotos.map(function (p) { return p.url; });
      var track = 'special_mop_' + companyName.replace(/[^a-zA-Z0-9]/g, '_') + '_' + Date.now();
      chain = fetch(state.apiBase + '/api/uploads/upload-images', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ images: imgs, trackingNumber: track })
      }).then(function (r) {
        if (r.status === 413) throw new Error('사진 용량이 너무 큽니다.');
        return r.json();
      }).then(function (up) {
        if (!up.success) throw new Error(up.message || '사진 업로드 실패');
        if (up.photoLinks) photoLinksFinal = parseUploadPhotoLinksString(up.photoLinks);
        else if (up.urls && up.urls.length) photoLinksFinal = up.urls.join(',');
      });
    }
    chain
      .then(function () {
        return fetch(state.apiBase + '/api/special-works/works', {
          method: 'POST',
          credentials: 'include',
          headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
          body: JSON.stringify({
            company_name: companyName,
            work_type_id: workTypeId,
            work_date: workDate,
            quantity: quantity,
            unit_price: unitPrice,
            photo_links: photoLinksFinal,
            memo: memo
          })
        });
      })
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (res.success) {
          toast('작업이 등록되었습니다.');
          closeSwModal();
          loadSwWorks();
        } else {
          toast(res.message || '등록 실패', true);
        }
      })
      .catch(function (e) {
        toast(e.message || '오류', true);
      })
      .finally(function () {
        if (btn) btn.disabled = false;
      });
  }

  function toast(msg, isErr) {
    var el = $('mopToast');
    if (!el) return;
    el.textContent = msg;
    el.className = 'mop-toast mop-toast--show' + (isErr ? ' mop-toast--err' : '');
    clearTimeout(toast._t);
    toast._t = setTimeout(function () {
      el.classList.remove('mop-toast--show');
    }, 2600);
  }

  function readLocalAuth() {
    try {
      state.company = localStorage.getItem(LS.company) || '';
      state.username = localStorage.getItem(LS.username) || '';
      state.role = (localStorage.getItem(LS.role) || '').trim();
    } catch (e) {
      state.company = '';
      state.username = '';
      state.role = '';
    }
  }

  function persistAuth(result) {
    state.company = result.company || '';
    state.username = result.username || '';
    state.role = (result.role || '').trim();
    try {
      localStorage.setItem(LS.company, state.company);
      localStorage.setItem(LS.username, state.username);
      localStorage.setItem(LS.role, state.role);
      localStorage.setItem(LS.loginTime, new Date().toISOString());
    } catch (e) { /* ignore */ }
  }

  function clearAuth() {
    state.company = '';
    state.username = '';
    state.role = '';
    try {
      localStorage.removeItem(LS.company);
      localStorage.removeItem(LS.username);
      localStorage.removeItem(LS.role);
      localStorage.removeItem(LS.loginTime);
    } catch (e) { /* ignore */ }
  }

  function showLogin() {
    $('mopLogin') && $('mopLogin').classList.remove('mop-hidden');
    $('mopApp') && $('mopApp').classList.add('mop-hidden');
  }

  function showApp() {
    $('mopLogin') && $('mopLogin').classList.add('mop-hidden');
    $('mopApp') && $('mopApp').classList.remove('mop-hidden');
    var sub = $('mopHeaderSub');
    if (sub) {
      sub.textContent = state.company + (state.role === '관리자' ? ' · 관리자' : '') + ' (' + state.username + ')';
    }
    state.mopPane = 'cs';
    setMopPane('cs');
    updateSwRegisterBtn();
    loadCompaniesIfAdmin();
    loadMonths().then(function () {
      return loadCs();
    });
  }

  function doLogin(ev) {
    if (ev) ev.preventDefault();
    var u = ($('mopUser') && $('mopUser').value || '').trim();
    var p = ($('mopPass') && $('mopPass').value || '').trim();
    var msg = $('mopLoginMsg');
    if (!u || !p) {
      if (msg) { msg.textContent = '아이디와 비밀번호를 입력해 주세요.'; msg.className = 'mop-msg mop-msg--err'; }
      return;
    }
    if (msg) { msg.textContent = '로그인 중…'; msg.className = 'mop-msg'; }
    performLogin(u, p)
      .then(function (result) {
        if (result.success) {
          persistAuth(result);
          saveAutoLoginIfChecked(u, p);
          if (msg) { msg.textContent = ''; msg.className = 'mop-msg'; }
          showApp();
        } else {
          clearAutoLoginStorage();
          if ($('mopRemember')) $('mopRemember').checked = false;
          if (msg) { msg.textContent = result.message || '로그인 실패'; msg.className = 'mop-msg mop-msg--err'; }
        }
      })
      .catch(function (err) {
        if (msg) { msg.textContent = '오류: ' + (err.message || ''); msg.className = 'mop-msg mop-msg--err'; }
      });
  }

  function tryAutoLoginFromSaved() {
    var cred = getSavedCredentials();
    if (!cred) return Promise.resolve(false);
    var msg = $('mopLoginMsg');
    if (msg) { msg.textContent = '저장된 계정으로 로그인 중…'; msg.className = 'mop-msg'; }
    return performLogin(cred.username, cred.password)
      .then(function (result) {
        if (result.success) {
          persistAuth(result);
          if (msg) { msg.textContent = ''; msg.className = 'mop-msg'; }
          showApp();
          return true;
        }
        clearAutoLoginStorage();
        if (msg) {
          msg.textContent = '자동 로그인에 실패했습니다. 비밀번호를 확인해 주세요.';
          msg.className = 'mop-msg mop-msg--err';
        }
        syncRememberCheckbox();
        return false;
      })
      .catch(function () {
        if (msg) {
          msg.textContent = '자동 로그인 중 네트워크 오류가 났습니다.';
          msg.className = 'mop-msg mop-msg--err';
        }
        return false;
      });
  }

  function doLogout() {
    clearAuth();
    closeSwModal();
    closeSheet();
    showLogin();
  }

  function loadCompaniesIfAdmin() {
    var wrap = $('mopCompanyWrap');
    var sel = $('mopCompany');
    if (!wrap || !sel) return;
    if (state.role !== '관리자') {
      wrap.classList.add('mop-hidden');
      return;
    }
    wrap.classList.remove('mop-hidden');
    return fetch(state.apiBase + '/api/auth/companies')
      .then(function (r) { return r.json(); })
      .then(function (result) {
        sel.innerHTML = '<option value="">전체 화주사</option>';
        if (result.success && result.companies) {
          result.companies.filter(function (c) { return c.role !== '관리자'; }).forEach(function (c) {
            var o = document.createElement('option');
            o.value = c.company_name;
            o.textContent = c.company_name;
            sel.appendChild(o);
          });
        }
      })
      .catch(function () { /* ignore */ });
  }

  function loadMonths() {
    var sel = $('mopMonth');
    if (!sel) return Promise.resolve();
    var companyFilter = state.role === '관리자' ? '' : state.company;
    var url = state.apiBase + '/api/cs/available-months?company=' + encodeURIComponent(companyFilter) +
      '&role=' + encodeURIComponent(state.role || '화주사');
    sel.innerHTML = '<option value="">월 불러오는 중…</option>';
    return fetch(url, { signal: AbortSignal.timeout(12000) })
      .then(function (r) { return r.json(); })
      .then(function (result) {
        sel.innerHTML = '';
        if (result.success && result.months && result.months.length) {
          result.months.forEach(function (m) {
            var o = document.createElement('option');
            o.value = m;
            o.textContent = m;
            sel.appendChild(o);
          });
          var today = new Date();
          var cur = today.getFullYear() + '년' + String(today.getMonth() + 1).padStart(2, '0') + '월';
          if (result.months.indexOf(cur) >= 0) sel.value = cur;
          else sel.value = result.months[0];
        } else {
          var t = new Date();
          var cm = t.getFullYear() + '년' + String(t.getMonth() + 1).padStart(2, '0') + '월';
          var o = document.createElement('option');
          o.value = cm;
          o.textContent = cm;
          sel.appendChild(o);
          sel.value = cm;
        }
        state.month = sel.value;
      })
      .catch(function () {
        sel.innerHTML = '';
        var t = new Date();
        var cm = t.getFullYear() + '년' + String(t.getMonth() + 1).padStart(2, '0') + '월';
        var o = document.createElement('option');
        o.value = cm;
        o.textContent = cm;
        sel.appendChild(o);
        sel.value = cm;
        state.month = cm;
      });
  }

  function companyFilterForApi() {
    if (state.role === '관리자') {
      var v = ($('mopCompany') && $('mopCompany').value) || '';
      return v;
    }
    return state.company;
  }

  function loadCs() {
    var sel = $('mopMonth');
    state.month = (sel && sel.value) || state.month;
    var url = state.apiBase + '/api/cs/?company=' + encodeURIComponent(companyFilterForApi()) +
      '&month=' + encodeURIComponent(state.month || '') +
      '&role=' + encodeURIComponent(state.role || '화주사');
    var listEl = $('mopCsList');
    if (listEl) listEl.innerHTML = '<div class="mop-empty">불러오는 중…</div>';
    return fetch(url, { signal: AbortSignal.timeout(15000) })
      .then(function (r) { return r.json(); })
      .then(function (result) {
        if (result.success) {
          state.csList = result.data || [];
          renderList();
        } else {
          state.csList = [];
          if (listEl) listEl.innerHTML = '<div class="mop-empty">' + escapeHtml(result.message || '목록을 불러올 수 없습니다.') + '</div>';
          toast(result.message || '목록 실패', true);
        }
      })
      .catch(function (err) {
        state.csList = [];
        if (listEl) listEl.innerHTML = '<div class="mop-empty">네트워크 오류</div>';
        toast(err.message || '오류', true);
      });
  }

  function filteredList() {
    var arr = state.csList.slice();
    if (state.filter === 'pending') {
      return arr.filter(function (c) { return c.status === '접수'; });
    }
    if (state.filter === 'hold') {
      return arr.filter(function (c) { return c.status === '보류'; });
    }
    if (state.filter === 'completed') {
      return arr.filter(function (c) { return c.status === '처리완료' || c.status === '처리불가'; });
    }
    return arr;
  }

  function renderList() {
    var listEl = $('mopCsList');
    if (!listEl) return;
    var rows = filteredList();
    if (!rows.length) {
      listEl.innerHTML = '<div class="mop-empty">표시할 C/S가 없습니다.</div>';
      return;
    }
    var html = rows.map(function (cs) {
      var st = cs.status || '접수';
      var type = escapeHtml(cs.issue_type || '-');
      var comp = escapeHtml(cs.company_name || '');
      var dt = escapeHtml(formatCsDate(cs));
      var snip = escapeHtml((cs.content || '').slice(0, 200));
      var mgmt = (cs.management_number || '').trim();
      var gen = (cs.generated_management_number || '').trim();
      var numRaw = mgmt || gen || '';
      var metaParts = [];
      if (numRaw) metaParts.push(escapeHtml(numRaw));
      if (comp) metaParts.push(comp);
      if (dt) metaParts.push(dt);
      var metaLine = metaParts.join(' · ');
      return (
        '<button type="button" class="mop-card" data-csid="' + Number(cs.id) + '">' +
        '<div class="mop-card__row">' +
        '<div class="mop-card__row-left">' +
        '<span class="' + issueTypeBadgeClass(cs.issue_type) + '">' + type + '</span>' +
        '</div>' +
        '<div class="mop-card__status">' +
        '<span class="mop-badge ' + statusClass(st) + '">' + escapeHtml(statusLabel(st)) + '</span>' +
        '</div>' +
        '</div>' +
        '<div class="mop-card__meta">' + metaLine + '</div>' +
        (snip ? '<div class="mop-card__text">' + snip + '</div>' : '') +
        '</button>'
      );
    }).join('');
    listEl.innerHTML = html;
    listEl.querySelectorAll('.mop-card').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = parseInt(btn.getAttribute('data-csid'), 10);
        openSheet(id);
      });
    });
  }

  function findCs(id) {
    return state.csList.find(function (c) { return Number(c.id) === Number(id); });
  }

  function closeSheet() {
    state.selectedId = null;
    var b = $('mopSheetBackdrop');
    if (b) b.classList.add('mop-hidden');
  }

  function openSheet(id) {
    var cs = findCs(id);
    if (!cs) return;
    state.selectedId = id;
    var st = cs.status || '접수';
    var body = $('mopSheetBody');
    if (!body) return;
    var isAdmin = state.role === '관리자';
    var adminBtns = isAdmin
      ? '<div class="mop-sheet__actions mop-sheet__actions--row">' +
        '<button type="button" class="mop-btn mop-btn--sheet-row mop-sheet__btn-hold" id="mopActHold">보류</button>' +
        '<button type="button" class="mop-btn mop-btn--sheet-row mop-btn--success" id="mopActComplete">처리완료</button>' +
        '<button type="button" class="mop-btn mop-btn--sheet-row mop-btn--danger" id="mopActImpossible">처리불가</button>' +
        '</div>' +
        '<div class="mop-sheet__gen-edit">' +
        '<label class="mop-sheet__label" for="mopSheetGenMgmt">생성된 관리번호</label>' +
        '<input type="text" id="mopSheetGenMgmt" class="mop-input" autocomplete="off" placeholder="물류 등에서 발급된 번호">' +
        '<label class="mop-sheet__label" for="mopSheetCustomerName">고객명 (선택)</label>' +
        '<input type="text" id="mopSheetCustomerName" class="mop-input" autocomplete="name" placeholder="고객명">' +
        '<button type="button" class="mop-btn mop-btn--primary mop-btn--sheet-block" id="mopActSaveGenMgmt">관리번호·고객명 저장</button>' +
        '</div>' +
        '<div class="mop-sheet__issue-edit">' +
        '<label class="mop-sheet__label" for="mopSheetIssueType">C/S 종류 변경</label>' +
        '<select id="mopSheetIssueType" class="mop-select mop-select--full"></select>' +
        '<button type="button" class="mop-btn mop-btn--primary mop-btn--sheet-block" id="mopActIssueType">종류 저장</button>' +
        '</div>'
      : '';
    body.innerHTML =
      '<div class="mop-sheet__head">' +
      '<h2 class="mop-sheet__title">접수 #' + escapeHtml(String(cs.id)) + '</h2>' +
      '<button type="button" class="mop-sheet__close" id="mopSheetClose" aria-label="닫기">×</button>' +
      '</div>' +
      '<div class="mop-sheet__block"><span class="mop-sheet__label">화주사</span>' + escapeHtml(cs.company_name || '') + '</div>' +
      '<div class="mop-sheet__block"><span class="mop-sheet__label">종류</span> <span class="' + issueTypeBadgeClass(cs.issue_type) + ' mop-type--inline">' + escapeHtml(cs.issue_type || '-') + '</span></div>' +
      '<div class="mop-sheet__block"><span class="mop-sheet__label">상태</span>' + escapeHtml(st) + '</div>' +
      '<div class="mop-sheet__block"><span class="mop-sheet__label">일시</span>' + escapeHtml(formatCsDate(cs)) + '</div>' +
      '<div class="mop-sheet__block"><span class="mop-sheet__label">접수 관리번호</span>' + escapeHtml((cs.management_number || '').trim() || '-') + '</div>' +
      '<div class="mop-sheet__block"><span class="mop-sheet__label">생성된 관리번호</span>' + escapeHtml((cs.generated_management_number || '').trim() || '-') + '</div>' +
      '<div class="mop-sheet__block"><span class="mop-sheet__label">내용</span>' + escapeHtml(cs.content || '') + '</div>' +
      (cs.admin_message ? '<div class="mop-sheet__block"><span class="mop-sheet__label">관리자 메시지</span>' + escapeHtml(cs.admin_message) + '</div>' : '') +
      adminBtns;

    $('mopSheetBackdrop') && $('mopSheetBackdrop').classList.remove('mop-hidden');
    var closeBtn = $('mopSheetClose');
    if (closeBtn) closeBtn.addEventListener('click', closeSheet);
    if (isAdmin) {
      $('mopActHold') && $('mopActHold').addEventListener('click', function () { actStatus(id, '보류'); });
      $('mopActComplete') && $('mopActComplete').addEventListener('click', function () { actStatus(id, '처리완료'); });
      $('mopActImpossible') && $('mopActImpossible').addEventListener('click', function () { actStatus(id, '처리불가'); });
      $('mopActSaveGenMgmt') && $('mopActSaveGenMgmt').addEventListener('click', function () { actSaveGenMgmt(id); });
      $('mopActIssueType') && $('mopActIssueType').addEventListener('click', function () { actIssueType(id); });
      var genInp = $('mopSheetGenMgmt');
      if (genInp) genInp.value = (cs.generated_management_number || '').trim();
      var custInp = $('mopSheetCustomerName');
      if (custInp) custInp.value = (cs.customer_name || '').trim();
      fillIssueTypeSelect(cs.issue_type || '');
    }
  }

  function fillIssueTypeSelect(current) {
    var sel = $('mopSheetIssueType');
    if (!sel) return;
    sel.innerHTML = '<option value="">불러오는 중…</option>';
    fetch(state.apiBase + '/api/cs/issue-types')
      .then(function (r) { return r.json(); })
      .then(function (result) {
        sel.innerHTML = '';
        var list = (result.success && result.data) ? result.data.filter(function (t) { return t.is_active !== false; }) : [];
        list.sort(function (a, b) { return (a.display_order || 0) - (b.display_order || 0); });
        var names = new Set(list.map(function (t) { return (t.name || '').trim(); }).filter(Boolean));
        var cur = (current || '').trim();
        if (cur && !names.has(cur)) {
          var o0 = document.createElement('option');
          o0.value = cur;
          o0.textContent = cur + ' (현재)';
          o0.selected = true;
          sel.appendChild(o0);
        }
        list.forEach(function (t) {
          var n = (t.name || '').trim();
          if (!n) return;
          var o = document.createElement('option');
          o.value = n;
          o.textContent = n;
          if (n === cur) o.selected = true;
          sel.appendChild(o);
        });
      })
      .catch(function () {
        sel.innerHTML = '<option value="">종류 목록 실패</option>';
      });
  }

  function actStatus(id, status) {
    var title = status === '처리완료' ? '처리완료' : (status === '처리불가' ? '처리불가' : '보류');
    var msg = global.prompt(title + ' — 메모 (선택)', '');
    if (msg === null) return;
    fetch(state.apiBase + '/api/cs/' + id + '/status', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        status: status,
        admin_message: msg ? msg.trim() : null,
        processor: state.company || ''
      })
    })
      .then(function (r) { return r.json(); })
      .then(function (result) {
        if (result.success) {
          toast('저장되었습니다.');
          closeSheet();
          loadCs();
        } else {
          toast(result.message || '실패', true);
        }
      })
      .catch(function (e) { toast(e.message || '오류', true); });
  }

  function actSaveGenMgmt(id) {
    var genInp = $('mopSheetGenMgmt');
    var custInp = $('mopSheetCustomerName');
    var genVal = (genInp && genInp.value || '').trim();
    var custVal = (custInp && custInp.value || '').trim();
    var base = state.apiBase + '/api/cs/' + id;
    Promise.all([
      fetch(base + '/generated-management-number', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ generated_management_number: genVal || null })
      }),
      fetch(base + '/customer-name', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ customer_name: custVal || null })
      })
    ])
      .then(function (responses) { return Promise.all(responses.map(function (r) { return r.json(); })); })
      .then(function (results) {
        var ok = results.every(function (r) { return r.success; });
        if (ok) {
          toast('관리번호·고객명이 저장되었습니다.');
          return loadCs().then(function () {
            if (state.selectedId === id) openSheet(id);
          });
        }
        var errMsg = results.filter(function (r) { return !r.success; }).map(function (r) { return r.message; }).join(', ');
        toast(errMsg || '저장 실패', true);
      })
      .catch(function (e) { toast(e.message || '오류', true); });
  }

  function actIssueType(id) {
    var sel = $('mopSheetIssueType');
    var v = (sel && sel.value || '').trim();
    if (!v) {
      toast('종류를 선택해 주세요.', true);
      return;
    }
    var url = state.apiBase + '/api/cs/' + id + '/issue-type?role=' + encodeURIComponent(state.role);
    fetch(url, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ issue_type: v })
    })
      .then(function (r) { return r.json(); })
      .then(function (result) {
        if (result.success) {
          toast('종류가 변경되었습니다.');
          closeSheet();
          loadCs();
        } else {
          toast(result.message || '실패', true);
        }
      })
      .catch(function (e) { toast(e.message || '오류', true); });
  }

  function setFilter(f) {
    state.filter = f;
    var map = [['mopChipAll', 'all'], ['mopChipPending', 'pending'], ['mopChipDone', 'completed'], ['mopChipHold', 'hold']];
    map.forEach(function (pair) {
      var el = $(pair[0]);
      if (el) el.classList.toggle('mop-chip--on', f === pair[1]);
    });
    renderList();
  }

  function bindUi() {
    var form = $('mopLoginForm');
    if (form) form.addEventListener('submit', doLogin);

    $('mopLogout') && $('mopLogout').addEventListener('click', doLogout);
    $('mopRefresh') && $('mopRefresh').addEventListener('click', function () {
      if (state.mopPane === 'sw') loadSwWorks();
      else loadCs();
    });

    $('mopTabCs') && $('mopTabCs').addEventListener('click', function () { setMopPane('cs'); });
    $('mopTabSw') && $('mopTabSw').addEventListener('click', function () { setMopPane('sw'); });

    $('mopSwRegisterBtn') && $('mopSwRegisterBtn').addEventListener('click', function () { openSwModal(); });
    $('mopSwModalClose') && $('mopSwModalClose').addEventListener('click', closeSwModal);
    $('mopSwModalBackdrop') && $('mopSwModalBackdrop').addEventListener('click', function (ev) {
      if (ev.target.id === 'mopSwModalBackdrop') closeSwModal();
    });
    $('mopSwPhotoPick') && $('mopSwPhotoPick').addEventListener('click', function () {
      $('mopSwFormPhotos') && $('mopSwFormPhotos').click();
    });
    $('mopSwFormPhotos') && $('mopSwFormPhotos').addEventListener('change', handleMopSwPhotoInputChange);
    $('mopSwFormType') && $('mopSwFormType').addEventListener('change', mopSwSyncPriceFromType);
    $('mopSwFormSubmit') && $('mopSwFormSubmit').addEventListener('click', submitSwModal);

    $('mopMonth') && $('mopMonth').addEventListener('change', function () {
      state.month = $('mopMonth').value;
      if (state.mopPane === 'sw') loadSwWorks();
      else loadCs();
    });
    $('mopCompany') && $('mopCompany').addEventListener('change', function () {
      if (state.mopPane === 'sw') loadSwWorks();
      else loadCs();
    });

    $('mopChipAll') && $('mopChipAll').addEventListener('click', function () { setFilter('all'); });
    $('mopChipPending') && $('mopChipPending').addEventListener('click', function () { setFilter('pending'); });
    $('mopChipHold') && $('mopChipHold').addEventListener('click', function () { setFilter('hold'); });
    $('mopChipDone') && $('mopChipDone').addEventListener('click', function () { setFilter('completed'); });

    $('mopSheetBackdrop') && $('mopSheetBackdrop').addEventListener('click', function (ev) {
      if (ev.target.id === 'mopSheetBackdrop') closeSheet();
    });
  }

  function init() {
    bindUi();
    readLocalAuth();
    if (state.company && state.username && state.role) {
      showApp();
      return;
    }
    tryAutoLoginFromSaved().then(function (ok) {
      if (!ok) {
        showLogin();
        syncRememberCheckbox();
      }
    });
  }

  global.MobileOpsPortal = {
    init: init,
    getApiBase: getApiBase,
    refreshCs: loadCs,
    refreshSw: loadSwWorks
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(typeof window !== 'undefined' ? window : this);
