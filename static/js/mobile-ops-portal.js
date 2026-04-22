/**
 * 모바일 작업 포털 — C/S 조회·간단 관리 (mobile_ops.html)
 * API·localStorage 키는 대시보드(dashboard_server.html)와 동일 계약을 따른다.
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
    selectedId: null
  };

  function $(id) {
    return document.getElementById(id);
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
      return (
        '<button type="button" class="mop-card" data-csid="' + Number(cs.id) + '">' +
        '<div class="mop-card__row">' +
        '<span class="' + issueTypeBadgeClass(cs.issue_type) + '">' + type + '</span>' +
        '<span class="mop-badge ' + statusClass(st) + '">' + escapeHtml(st) + '</span>' +
        '</div>' +
        '<div class="mop-card__meta">' + comp + ' · ' + dt + '</div>' +
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
      ? '<div class="mop-sheet__actions">' +
        '<button type="button" class="mop-btn mop-btn--muted" id="mopActHold" style="background:linear-gradient(135deg,#a29bfe 0%,#6c5ce7 100%);color:#fff;border:none">보류</button>' +
        '<button type="button" class="mop-btn mop-btn--success" id="mopActComplete">처리완료</button>' +
        '<button type="button" class="mop-btn mop-btn--danger" id="mopActImpossible">처리불가</button>' +
        '<label class="mop-sheet__label" style="margin-top:0.5rem">C/S 종류 변경</label>' +
        '<select id="mopSheetIssueType" class="mop-select" style="width:100%"></select>' +
        '<button type="button" class="mop-btn mop-btn--primary" id="mopActIssueType">종류 저장</button>' +
        '</div>'
      : '';
    body.innerHTML =
      '<h2>접수 #' + escapeHtml(String(cs.id)) + '</h2>' +
      '<div class="mop-sheet__block"><span class="mop-sheet__label">화주사</span>' + escapeHtml(cs.company_name || '') + '</div>' +
      '<div class="mop-sheet__block"><span class="mop-sheet__label">종류</span> <span class="' + issueTypeBadgeClass(cs.issue_type) + ' mop-type--inline">' + escapeHtml(cs.issue_type || '-') + '</span></div>' +
      '<div class="mop-sheet__block"><span class="mop-sheet__label">상태</span>' + escapeHtml(st) + '</div>' +
      '<div class="mop-sheet__block"><span class="mop-sheet__label">일시</span>' + escapeHtml(formatCsDate(cs)) + '</div>' +
      '<div class="mop-sheet__block"><span class="mop-sheet__label">관리번호</span>' + escapeHtml(cs.management_number || '-') + '</div>' +
      '<div class="mop-sheet__block"><span class="mop-sheet__label">내용</span>' + escapeHtml(cs.content || '') + '</div>' +
      (cs.admin_message ? '<div class="mop-sheet__block"><span class="mop-sheet__label">관리자 메시지</span>' + escapeHtml(cs.admin_message) + '</div>' : '') +
      adminBtns +
      '<button type="button" class="mop-btn mop-btn--muted" id="mopSheetClose" style="margin-top:0.75rem">닫기</button>';

    $('mopSheetBackdrop') && $('mopSheetBackdrop').classList.remove('mop-hidden');
    var closeBtn = $('mopSheetClose');
    if (closeBtn) closeBtn.addEventListener('click', closeSheet);
    if (isAdmin) {
      $('mopActHold') && $('mopActHold').addEventListener('click', function () { actStatus(id, '보류'); });
      $('mopActComplete') && $('mopActComplete').addEventListener('click', function () { actStatus(id, '처리완료'); });
      $('mopActImpossible') && $('mopActImpossible').addEventListener('click', function () { actStatus(id, '처리불가'); });
      $('mopActIssueType') && $('mopActIssueType').addEventListener('click', function () { actIssueType(id); });
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
    $('mopRefresh') && $('mopRefresh').addEventListener('click', function () { loadCs(); });

    $('mopMonth') && $('mopMonth').addEventListener('change', function () {
      state.month = $('mopMonth').value;
      loadCs();
    });
    $('mopCompany') && $('mopCompany').addEventListener('change', function () { loadCs(); });

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
    refreshCs: loadCs
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(typeof window !== 'undefined' ? window : this);
