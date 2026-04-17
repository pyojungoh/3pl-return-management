/**
 * 홈페이지형 로그인 전 화면 — 반응형 랜딩 + 로그인 모달 + 견적 mailto
 */
(function (global) {
  'use strict';

  var _defaultAppTitle = null;
  var _modalBound = false;
  var _quoteBound = false;
  var _hpHashRoutingBound = false;
  var _mobileNavBound = false;
  var _escHandler = null;
  var _lastPortalConfig = null;

  function ensureDefaultTitleCaptured() {
    if (_defaultAppTitle != null) return;
    var t = document.querySelector('title');
    _defaultAppTitle = t && t.textContent ? t.textContent : 'JJAY 3PL';
  }

  function buildPortalTabTitle(config) {
    var hero = (config.hero_title || '').trim() || 'JJAY 3PL';
    var full = hero + ' — 통합 포털';
    if (full.length > 80) {
      full = full.slice(0, 77) + '…';
    }
    return full;
  }

  function applyDocumentTitleForPortal(config) {
    ensureDefaultTitleCaptured();
    var ttl = document.querySelector('title');
    if (!ttl || !config) return;
    var custom = (config.browser_tab_title || '').trim();
    ttl.textContent = custom ? custom.slice(0, 120) : buildPortalTabTitle(config);
  }

  function restoreAppDocumentTitle() {
    ensureDefaultTitleCaptured();
    var ttl = document.querySelector('title');
    if (ttl && _defaultAppTitle != null) {
      ttl.textContent = _defaultAppTitle;
    }
  }

  function esc(s) {
    var d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
    return d.innerHTML;
  }

  function setLogoFromConfig(config) {
    var url = (config.logo_url || '').trim();
    var alt = (config.hero_title || '로고').slice(0, 40);
    var navImg = document.getElementById('hpNavLogo');
    if (navImg) {
      if (url) {
        navImg.src = url;
        navImg.alt = alt;
        navImg.style.visibility = '';
      } else {
        navImg.removeAttribute('src');
        navImg.alt = '';
        navImg.style.visibility = 'hidden';
      }
    }
    var modalImg = document.getElementById('loginLogo');
    if (modalImg && url) {
      modalImg.src = url;
      modalImg.alt = alt;
    }
  }

  function closeMobileNav() {
    var d = document.getElementById('hpMobileNav');
    if (d) d.open = false;
  }

  function extractYoutubeId(raw) {
    var s = (raw || '').trim();
    if (!s) return '';
    if (/^[a-zA-Z0-9_-]{11}$/.test(s)) return s;
    var m = s.match(/(?:youtu\.be\/|youtube\.com\/(?:embed\/|watch\?v=))([a-zA-Z0-9_-]{11})/);
    return m ? m[1] : '';
  }

  function parseBannerUrls(text) {
    if (!text) return [];
    return text.split(/\r?\n/).map(function (l) { return l.trim(); }).filter(Boolean).slice(0, 20);
  }

  function parseYoutubeLines(text) {
    var out = [];
    if (!text) return out;
    text.split(/\r?\n/).forEach(function (line) {
      line = line.trim();
      if (!line) return;
      var i = line.indexOf('|');
      var first = (i === -1 ? line : line.slice(0, i)).trim();
      var title = (i === -1 ? 'YouTube' : line.slice(i + 1)).trim() || 'YouTube';
      var vid = extractYoutubeId(first);
      if (vid) out.push({ video_id: vid, title: title });
    });
    return out.slice(0, 12);
  }

  function joinLines(arr) {
    if (!arr || !arr.length) return '';
    return arr
      .map(function (x) {
        return String(x).trim();
      })
      .filter(Boolean)
      .join('\n');
  }

  function youtubeLinesFromConfig(list) {
    if (!list || !list.length) return '';
    return list.map(function (v) {
      return (v.video_id || '') + '|' + (v.title || '');
    }).join('\n');
  }

  function buildMarquee(imgs) {
    var root = document.getElementById('hpMarqueeRoot');
    var track = document.getElementById('hpMarqueeTrack');
    if (!root || !track) return;
    track.innerHTML = '';
    if (!imgs || !imgs.length) {
      root.style.display = 'none';
      return;
    }
    root.style.display = 'block';
    function oneRun() {
      var f = document.createDocumentFragment();
      imgs.forEach(function (url) {
        var slide = document.createElement('div');
        slide.className = 'hp-marquee-slide';
        var im = document.createElement('img');
        im.src = url;
        im.alt = '';
        im.loading = 'lazy';
        im.decoding = 'async';
        slide.appendChild(im);
        f.appendChild(slide);
      });
      return f;
    }
    track.appendChild(oneRun());
    track.appendChild(oneRun());
  }

  function _hpPick(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
  }

  function _hpFmtNum(n) {
    var s = String(Math.round(n));
    return s.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  }

  function _hpRandVolume() {
    var r = Math.random();
    var base;
    if (r < 0.25) base = 400 + Math.floor(Math.random() * 2600);
    else if (r < 0.55) base = 2000 + Math.floor(Math.random() * 5500);
    else if (r < 0.85) base = 5000 + Math.floor(Math.random() * 9000);
    else base = 8000 + Math.floor(Math.random() * 14000);
    var round = [50, 100, 200][Math.floor(Math.random() * 3)];
    return Math.max(300, Math.round(base / round) * round);
  }

  function _hpFakeCompanyName() {
    var pre = _hpPick(['', '', '(주)', '㈜', '(유)']);
    var a = _hpPick([
      '코스모', '라이트', '스마트', '티엔', '제이', '한빛', '미르', '에이블', '와이드', '노바',
      '스타', '그린', '오션', '써니', '트루', '베스트', '퍼스트', '골든', '실버', '레드',
      '블루', '아이', '유니', '메가', '프라임', '퀀텀', '링크', '넥스트', '허브', '패스트',
      '스카이', '어스', '모던', '클래식', '뉴웨이', '원', '투', '쓰리', '포인트', '센트럴'
    ]);
    var b = _hpPick([
      '커머스', '트레이딩', '물류', '마켓', '글로벌', '코리아', '통상', '리테일', '라이프',
      '스토어', '샵', '플랫폼', '디스트리', '유통', '브랜드', '패밀리', '그룹', '홀딩스',
      '인터내셔널', '시스템즈', '솔루션', '파트너스', '앤코', '앤드', '코퍼레이션', '엔터프라이즈'
    ]);
    var tail = Math.random() < 0.35 ? _hpPick(['', '닷컴', '코리아', '24', '365']) : '';
    var name = a + b + tail;
    return (pre ? pre + name : name).slice(0, 28);
  }

  function _hpMaskCompanyName(company) {
    var s = String(company || '').trim();
    if (!s) return '***';
    var pre = '';
    var rest = s;
    if (s.indexOf('(주)') === 0) {
      pre = '(주)';
      rest = s.slice(3);
    } else if (s.indexOf('(유)') === 0) {
      pre = '(유)';
      rest = s.slice(3);
    } else if (s.indexOf('㈜') === 0) {
      pre = '㈜';
      rest = s.slice(1);
    }
    rest = rest.trim();
    if (!rest.length) return pre + '***';
    var show = rest.length <= 3 ? 1 : rest.length <= 7 ? 2 : 3;
    return pre + rest.slice(0, show) + '***';
  }

  function _hpInquiryTail() {
    return _hpPick(['…', '…', '…', '....', '…']);
  }

  function _hpInquiryMessage(cat, vol) {
    var v = _hpFmtNum(vol);
    var lines = [
      '안녕하세요, ' + cat + ' 쪽인데요. 지금 월 ' + v + '건 전후로 나가고 있어서 단가랑 창고 가능 여부만 먼저 여쭤보려고요',
      '급하게 문의드려요. ' + cat + ' 라인이고 출고가 월 ' + v + '건 안팎인데, 당일컷 가능한지랑 반품 처리 방식이 궁금합니다',
      cat + ' 위주로 돌아가는데 월 택배가 ' + v + '건 정도예요. 쿠팡 연동이랑 정산서 미리보기 되는지 알려주시면',
      '처음 맡겨보는 거라 헷갈리는데요, 월 ' + v + '건 나가는 ' + cat + '면 보관 파렛트 대략 몇 판 잡으면 될지',
      '견적 몇 군데 받아보는 중인데요 저희는 ' + cat + ', 월 출고 ' + v + '건쯤 봐주시면 될 거 같아요. 최소 계약',
      '내일까지 대략이라도 받아볼 수 있을까 해서요. ' + cat + ', 물량은 월 ' + v + '건 전후라고 보시면 되고요',
      cat + '인데 피킹 인력이랑 포장 방식이 궁금해요. 월 ' + v + '건 정도 물량이고 성수기엔 조금 더 튈 수',
      '혹시 창고 온도대 나눠져 있는지요. ' + cat + '이고 월 ' + v + '건 내외 출고예요, 냉장',
      'CS 응답이 얼마나 빠른 편인지도 같이 알고 싶어요. ' + cat + ', 월 택배 ' + v + '건 정도',
      '반품 들어올 때 화주 쪽에서 상세 로그 확인 가능한지 궁금합니다. ' + cat + ', 월 ' + v + '건',
      'B2B 납품이랑 택배가 섞여 있는데 ' + cat + ' 비중이 커요. 월 ' + v + '건 전후로 봐주시면',
      '단가표 받아볼 수 있을까요? ' + cat + ' 쪽이고 월 ' + v + '건 정도 나가요, 창고+택배',
      'API 연동 일정이 대략 얼마나 걸리는지도 여쭤봅니다. ' + cat + ', 월 출고 ' + v + '건',
      cat + '라서 입고 검수 기준이랑 파손 클레임 처리만 먼저 알려주실 수 있을까요. 물량은 월 ' + v + '건',
      '해외직구 물량도 조금 섞여 있는데 괜찮을지요. ' + cat + ' 주력이고 월 ' + v + '건',
      '지금 쓰는 곳이랑 비교 중이라, ' + cat + ' 월 ' + v + '건 기준으로 대략 보관료+출고료',
      '키트 조립 같은 거 맡길 수 있는지도요. ' + cat + ', 월 ' + v + '건 전후',
      '도서지 배송 추가비 있는지만 짧게 알려주시면 감사하겠습니다. ' + cat + ', 월 ' + v + '건',
      '샘플 몇 박스만 먼저내볼 수 있는지도 궁금해요. ' + cat + '이고 본 물량은 월 ' + v + '건',
      '급행 옵션이 따로 있는지요. ' + cat + ', 평소엔 월 ' + v + '건인데 이번 달은 좀 더',
      '재고 실사 주기가 어떻게 되는지, ' + cat + ' 월 ' + v + '건 기준으로',
      '택배사 여러 개 쓰는 것도 가능한지 문의드려요. ' + cat + ', 월 ' + v + '건',
      '프로모션 기간에 단기로 물량 늘릴 수도 있어서요. ' + cat + ', 평균 월 ' + v + '건',
      '말씀만이라도 먼저 듣고 싶어서 연락드렸어요. ' + cat + ', 월 ' + v + '건 전후 출고',
      '담당자 바뀌어서 다시 정리 중인데요, ' + cat + ' 월 ' + v + '건이면 대략',
      '냉동이랑 상온이 같이 있는데 구역 분리 어떻게 되는지요. ' + cat + ', 월 ' + v + '건',
      '누락 건 보상 규정이 궁금합니다. ' + cat + '이고 월 ' + v + '건 정도',
      '월말 정산이랑 미리보기 되는 정산서 형태가 있으면 보고 싶어요. ' + cat + ', 월 ' + v + '건',
      '신규 런칭이라 물량이 튈 수 있는데 그때도 대응 가능한지. ' + cat + ', 지금은 월 ' + v + '건',
      '바코드 전 구간 스캔 맞는지 확인차 연락드립니다. ' + cat + ', 월 ' + v + '건 전후'
    ];
    return _hpPick(lines) + _hpInquiryTail();
  }

  function _hpOneTickerCard() {
    var fullCompany = _hpFakeCompanyName();
    var cat = _hpPick([
      '의류·패션', '이너웨어', '신발·잡화', '뷰티·화장품', '헬스·영양제', '식품·간편식',
      '생활소품', '주방용품', '가전·소형가전', '디지털·액세서리', '완구·키즈', '문구·굿즈',
      '펫용품', '스포츠용품', '캠핑·아웃도어', '가구·인테리어', '침구·홈텍스', '도서·음반',
      '핸드메이드', '리빙·수납', '청소·세제', '자동차용품', '공구·DIY', '사무·B2B소모품',
      '건강기능식품', '다이어트', '티·커피', '과자·스낵', '냉동·냉장', '신선·밀키트',
      '전자부품', '악세서리', '잡화·소품', '잡화·라이프스타일', '리빙몰', '브랜드몰'
    ]);
    var vol = _hpRandVolume();
    return {
      company: _hpMaskCompanyName(fullCompany),
      category: cat,
      message: _hpInquiryMessage(cat, vol)
    };
  }

  function _hpTickerCardKey(c) {
    return c.company + '\t' + c.category + '\t' + c.message;
  }

  function _hpBuildTickerCards(count) {
    var cards = [];
    var seen = {};
    var guard = 0;
    while (cards.length < count && guard < count * 10) {
      guard += 1;
      var c = _hpOneTickerCard();
      var k = _hpTickerCardKey(c);
      if (seen[k]) continue;
      seen[k] = 1;
      cards.push(c);
    }
    while (cards.length < count) {
      cards.push(_hpOneTickerCard());
    }
    return cards;
  }

  function _hpAppendTickerField(root, labelText, valueText, rowClass) {
    var row = document.createElement('div');
    row.className = 'hp-ticker-field' + (rowClass ? ' ' + rowClass : '');
    var lab = document.createElement('span');
    lab.className = 'hp-ticker-field-label';
    lab.textContent = labelText;
    var sep = document.createElement('span');
    sep.className = 'hp-ticker-field-sep';
    sep.textContent = ':';
    var val = document.createElement('span');
    val.className = 'hp-ticker-field-value';
    val.textContent = valueText;
    row.appendChild(lab);
    row.appendChild(sep);
    row.appendChild(val);
    root.appendChild(row);
  }

  function buildQuoteActivityTicker() {
    var track = document.getElementById('hpQuoteTickerTrack');
    if (!track) return;
    track.innerHTML = '';
    var cards = _hpBuildTickerCards(220);
    function oneRun() {
      var run = document.createElement('div');
      run.className = 'hp-ticker-run';
      cards.forEach(function (c) {
        var chip = document.createElement('article');
        chip.className = 'hp-ticker-item';
        chip.setAttribute('lang', 'ko');
        var inner = document.createElement('div');
        inner.className = 'hp-ticker-card-inner';
        _hpAppendTickerField(inner, '업체명', c.company, '');
        _hpAppendTickerField(inner, '카테고리', c.category, '');
        _hpAppendTickerField(inner, '문의사항', c.message, 'hp-ticker-field--message');
        chip.appendChild(inner);
        run.appendChild(chip);
      });
      return run;
    }
    track.appendChild(oneRun());
    track.appendChild(oneRun());
    track.style.animationDuration = '';
    requestAnimationFrame(function () {
      try {
        var half = track.scrollWidth / 2;
        if (half > 0) {
          var sec = Math.max(72, Math.min(220, half / 55)) * 4;
          track.style.animationDuration = sec + 's';
        }
      } catch (e) {
        /* noop */
      }
    });
  }

  function buildYoutube(list) {
    var grid = document.getElementById('hpYoutubeGrid');
    var empty = document.getElementById('hpYoutubeEmpty');
    if (!grid) return;
    grid.innerHTML = '';
    if (!list || !list.length) {
      if (empty) empty.style.display = 'block';
      return;
    }
    if (empty) empty.style.display = 'none';
    list.forEach(function (v) {
      var card = document.createElement('article');
      card.className = 'hp-yt-card';
      var cap = document.createElement('p');
      cap.className = 'hp-yt-caption';
      cap.textContent = v.title || 'YouTube';
      var wrap = document.createElement('div');
      wrap.className = 'hp-yt-frame-wrap';
      var ifr = document.createElement('iframe');
      ifr.setAttribute('loading', 'lazy');
      ifr.setAttribute('title', v.title || 'YouTube');
      ifr.src = 'https://www.youtube.com/embed/' + v.video_id + '?rel=0';
      ifr.setAttribute('allow', 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share');
      ifr.setAttribute('allowfullscreen', 'true');
      wrap.appendChild(ifr);
      card.appendChild(cap);
      card.appendChild(wrap);
      grid.appendChild(card);
    });
  }

  function applyLoginLayout(config) {
    if (!config) return;
    _lastPortalConfig = config;

    var meta = document.getElementById('hpMetaDescription');
    if (meta) {
      var md = (config.meta_description || '').trim();
      meta.setAttribute('content', md || '3PL 반품·출고·스케줄·CS 통합 관리 포털');
    }

    var navText = document.getElementById('hpNavBrandText');
    if (navText) navText.textContent = config.hero_title || '';
    setLogoFromConfig(config);

    var notice = document.getElementById('hpNoticeBar');
    if (notice) {
      if (config.notice_visible && (config.notice_text || '').trim()) {
        notice.style.display = 'block';
        notice.textContent = config.notice_text.trim();
      } else {
        notice.style.display = 'none';
        notice.textContent = '';
      }
    }

    buildMarquee(config.banner_images || []);

    var pTitle = document.getElementById('hpPartnerTitle');
    if (pTitle) pTitle.textContent = config.partner_section_title || '';
    var pLead = document.getElementById('hpPartnerLead');
    if (pLead) pLead.textContent = config.partner_section_lead || '';
    buildQuoteActivityTicker();

    var yTitle = document.getElementById('hpYoutubeTitle');
    if (yTitle) yTitle.textContent = config.youtube_section_title || '';
    var yLead = document.getElementById('hpYoutubeLead');
    if (yLead) yLead.textContent = config.youtube_section_lead || '';
    buildYoutube(config.youtube_items || []);

    var ht = document.getElementById('hpHeroTitle');
    if (ht) ht.textContent = config.hero_title || '';
    var st = document.getElementById('hpHeroSubtitle');
    if (st) st.textContent = config.hero_subtitle || '';

    var svcH = document.getElementById('hpServicesHeading');
    if (svcH) svcH.textContent = config.service_section_title || '3PL 서비스 소개';
    var svcL = document.getElementById('hpServicesLead');
    if (svcL) {
      svcL.textContent =
        config.service_section_lead ||
        '연결 창고·자체 솔루션·정산·출고 품질까지, 화주사 운영에 필요한 요소를 한곳에서 제안합니다.';
    }

    var lt = document.getElementById('hpLoginCardTitle');
    if (lt) lt.textContent = config.login_card_title || '로그인';

    var qt = document.getElementById('hpQuoteTitle');
    if (qt) qt.textContent = config.quote_section_title || '견적 · 서비스 문의';
    var qs = document.getElementById('hpQuoteSubtitle');
    if (qs) qs.textContent = config.quote_section_subtitle || '';
    var qh = document.getElementById('hpQuoteMailHint');
    if (qh) {
      var em = (config.inquiry_email || '').trim();
      qh.textContent = em
        ? '아래 버튼을 누르면 메일 앱으로 전송됩니다. 수신: ' + em
        : '견적 메일 수신 주소는 관리자 홈페이지 설정에서 등록할 수 있습니다.';
    }

    var fc = document.getElementById('hpFooterCompany');
    if (fc) fc.textContent = config.footer_company || '';
    var f2 = document.getElementById('hpFooterLine2');
    if (f2) {
      f2.textContent = config.footer_line2 || '';
      f2.style.display = (config.footer_line2 || '').trim() ? 'block' : 'none';
    }
    var tel = document.getElementById('hpFooterTel');
    if (tel) {
      var t = (config.footer_tel || '').trim();
      tel.textContent = t ? '문의: ' + t : '';
      tel.style.display = t ? 'block' : 'none';
    }

    var seo = document.getElementById('hpFooterSeoBlock');
    if (seo) {
      var sb = (config.footer_seo_block || '').trim();
      seo.textContent = sb;
      seo.style.display = sb ? 'block' : 'none';
    }
    var cr = document.getElementById('hpFooterCopyright');
    if (cr) {
      var cpy = (config.footer_copyright || '').trim();
      cr.textContent = cpy;
      cr.style.display = cpy ? 'block' : 'none';
    }

    var cta = document.getElementById('hpCtaBtn');
    if (cta) {
      var cl = (config.cta_label || '').trim();
      var cu = (config.cta_url || '').trim();
      if (cl && cu) {
        cta.href = cu;
        cta.textContent = cl;
        cta.style.display = 'inline-flex';
      } else {
        cta.style.display = 'none';
        cta.removeAttribute('href');
      }
    }

    applyDocumentTitleForPortal(config);
    syncHpPortalViewFromHash();
  }

  function getModalEl() {
    return document.getElementById('hpLoginModal');
  }

  function closeLoginModal() {
    var modal = getModalEl();
    if (!modal) return;
    modal.classList.add('hp-modal-hidden');
    modal.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('hp-modal-open');
    if (_escHandler) {
      document.removeEventListener('keydown', _escHandler, true);
      _escHandler = null;
    }
  }

  function openLoginModal() {
    var modal = getModalEl();
    if (!modal) return;
    closeMobileNav();
    modal.classList.remove('hp-modal-hidden');
    modal.setAttribute('aria-hidden', 'false');
    document.body.classList.add('hp-modal-open');
    if (!_escHandler) {
      _escHandler = function (e) {
        if (e.key === 'Escape') {
          e.preventDefault();
          closeLoginModal();
        }
      };
      document.addEventListener('keydown', _escHandler, true);
    }
    setTimeout(function () {
      var u = document.getElementById('username');
      if (u) u.focus();
    }, 50);
  }

  function bindLoginModalOnce() {
    if (_modalBound) return;
    _modalBound = true;

    var openBtn = document.getElementById('hpBtnOpenLogin');
    if (openBtn) openBtn.addEventListener('click', openLoginModal);

    document.querySelectorAll('[data-hp-open-login]').forEach(function (el) {
      el.addEventListener('click', function () {
        openLoginModal();
      });
    });

    var bd = document.getElementById('hpLoginModalBackdrop');
    if (bd) bd.addEventListener('click', closeLoginModal);
    var x = document.getElementById('hpLoginModalClose');
    if (x) x.addEventListener('click', closeLoginModal);

  }

  function syncHpPortalViewFromHash() {
    var root = document.getElementById('loginSection');
    if (!root || !root.classList.contains('hp-site')) return;
    var raw = (location.hash || '').trim();
    if (raw === '#hpQuoteAnchor' && window.history && window.history.replaceState) {
      history.replaceState(null, '', '#quote');
    }
    var h = (location.hash || '').trim();
    var quoteMode = h === '#quote' || h === '#hpQuoteAnchor';
    root.classList.toggle('hp-view-quote-only', quoteMode);
    document.body.classList.toggle('hp-view-quote-only', quoteMode);
    document.documentElement.classList.toggle('hp-view-quote-only', quoteMode);
    var navQuote = document.getElementById('hpNavQuoteLink');
    if (navQuote) navQuote.classList.toggle('hp-nav-quote-active', quoteMode);
    if (quoteMode) {
      window.scrollTo(0, 0);
    }
  }

  function bindHpHashRoutingOnce() {
    if (_hpHashRoutingBound) return;
    _hpHashRoutingBound = true;
    window.addEventListener('hashchange', syncHpPortalViewFromHash);
  }

  function bindMobileNavOnce() {
    if (_mobileNavBound) return;
    _mobileNavBound = true;
    document.querySelectorAll('.hp-mobile-sheet-link').forEach(function (a) {
      a.addEventListener('click', function () {
        closeMobileNav();
      });
    });
  }

  function bindQuoteFormOnce() {
    if (_quoteBound) return;
    _quoteBound = true;
    var form = document.getElementById('hpQuoteForm');
    if (!form) return;
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var cfg = _lastPortalConfig || {};
      var to = (cfg.inquiry_email || '').trim();
      if (!to) {
        window.alert('견적 메일 수신 주소가 아직 등록되지 않았습니다. 관리자에게 문의하시거나, 홈페이지 설정에서 inquiry 이메일을 입력해 주세요.');
        return;
      }
      function v(id) {
        var el = document.getElementById(id);
        return el && el.value != null ? String(el.value).trim() : '';
      }
      var company = v('hpQCompany');
      var name = v('hpQName');
      var phone = v('hpQPhone');
      var email = v('hpQEmail');
      var product = v('hpQProduct');
      var monthlyOut = v('hpQMonthlyOut');
      var pallets = v('hpQPallets');
      var sku = v('hpQSku');
      var memo = v('hpQMemo');
      var privacyEl = document.getElementById('hpQPrivacy');
      var privacyOk = privacyEl && privacyEl.checked;
      if (!company) {
        window.alert('회사명을 입력해 주세요.');
        return;
      }
      if (!name) {
        window.alert('담당자 성함을 입력해 주세요.');
        return;
      }
      if (!phone) {
        window.alert('전화번호를 입력해 주세요.');
        return;
      }
      if (!email) {
        window.alert('이메일을 입력해 주세요.');
        return;
      }
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        window.alert('이메일 형식을 확인해 주세요.');
        return;
      }
      if (!privacyOk) {
        window.alert('개인정보 수집·이용에 동의해 주세요.');
        return;
      }
      var subj = encodeURIComponent('[견적요청] ' + (cfg.hero_title || '3PL') + ' — ' + company);
      var bodyPlain =
        '[견적 문의]\n\n' +
        '회사명: ' +
        company +
        '\n담당자 성함: ' +
        name +
        '\n전화번호: ' +
        phone +
        '\n이메일: ' +
        email +
        '\n제품: ' +
        (product || '-') +
        '\n월 출고량: ' +
        (monthlyOut || '-') +
        '\n보관 파레트수: ' +
        (pallets || '-') +
        '\nSKU 종류: ' +
        (sku || '-') +
        '\n\n문의 내용:\n' +
        (memo || '-') +
        '\n\n개인정보처리동의: 동의함';
      var body = encodeURIComponent(bodyPlain);
      window.location.href = 'mailto:' + to + '?subject=' + subj + '&body=' + body;
    });
  }

  function fetchConfig(apiBase) {
    var base = (apiBase || '').replace(/\/$/, '');
    return fetch(base + '/api/homepage/config')
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (j && j.success && j.config) return j.config;
        return null;
      })
      .catch(function () { return null; });
  }

  function initLoginPage(apiBase) {
    bindLoginModalOnce();
    bindHpHashRoutingOnce();
    bindMobileNavOnce();
    bindQuoteFormOnce();
    return fetchConfig(apiBase)
      .then(function (cfg) {
        if (cfg) applyLoginLayout(cfg);
        else syncHpPortalViewFromHash();
      })
      .catch(function () {
        syncHpPortalViewFromHash();
      });
  }

  function adminHeaders() {
    var role = localStorage.getItem('client_role') || '';
    var name = localStorage.getItem('client_username') || '';
    return {
      'Content-Type': 'application/json',
      'X-User-Role': role,
      'X-User-Name': encodeURIComponent(name)
    };
  }

  function val(id) {
    var el = document.getElementById(id);
    return el ? el.value : '';
  }
  function chk(id) {
    var el = document.getElementById(id);
    return el ? !!el.checked : false;
  }

  function collectAdminForm() {
    var feats = [];
    for (var i = 0; i < 4; i++) {
      feats.push({
        icon: val('hpAdFeat' + i + 'Icon'),
        title: val('hpAdFeat' + i + 'Title'),
        desc: val('hpAdFeat' + i + 'Desc')
      });
    }
    return {
      hero_title: val('hpAdHeroTitle'),
      hero_subtitle: val('hpAdHeroSubtitle'),
      service_section_title: val('hpAdServiceTitle'),
      service_section_lead: val('hpAdServiceLead'),
      notice_text: val('hpAdNoticeText'),
      notice_visible: chk('hpAdNoticeVisible'),
      login_card_title: val('hpAdLoginCardTitle'),
      logo_url: val('hpAdLogoUrl'),
      features: feats,
      footer_company: val('hpAdFooterCompany'),
      footer_line2: val('hpAdFooterLine2'),
      footer_tel: val('hpAdFooterTel'),
      footer_copyright: val('hpAdFooterCopyright'),
      footer_seo_block: val('hpAdFooterSeoBlock'),
      meta_description: val('hpAdMetaDescription'),
      cta_label: val('hpAdCtaLabel'),
      cta_url: val('hpAdCtaUrl'),
      browser_tab_title: val('hpAdBrowserTabTitle'),
      quote_section_title: val('hpAdQuoteTitle'),
      quote_section_subtitle: val('hpAdQuoteSubtitle'),
      inquiry_email: val('hpAdInquiryEmail'),
      banner_images: parseBannerUrls(val('hpAdBannerUrls')),
      partner_section_title: val('hpAdPartnerSecTitle'),
      partner_section_lead: val('hpAdPartnerSecLead'),
      partner_logos: [],
      youtube_section_title: val('hpAdYoutubeSecTitle'),
      youtube_section_lead: val('hpAdYoutubeSecLead'),
      youtube_items: parseYoutubeLines(val('hpAdYoutubeLines'))
    };
  }

  function fillAdminForm(config) {
    if (!config) return;
    function set(id, v) {
      var el = document.getElementById(id);
      if (el) el.value = v != null ? String(v) : '';
    }
    set('hpAdHeroTitle', config.hero_title);
    set('hpAdHeroSubtitle', config.hero_subtitle);
    set('hpAdServiceTitle', config.service_section_title);
    set('hpAdServiceLead', config.service_section_lead);
    set('hpAdNoticeText', config.notice_text);
    var nv = document.getElementById('hpAdNoticeVisible');
    if (nv) nv.checked = !!config.notice_visible;
    set('hpAdLoginCardTitle', config.login_card_title);
    set('hpAdLogoUrl', config.logo_url);
    set('hpAdFooterCompany', config.footer_company);
    set('hpAdFooterLine2', config.footer_line2);
    set('hpAdFooterTel', config.footer_tel);
    set('hpAdFooterCopyright', config.footer_copyright);
    set('hpAdFooterSeoBlock', config.footer_seo_block);
    set('hpAdMetaDescription', config.meta_description);
    set('hpAdCtaLabel', config.cta_label);
    set('hpAdCtaUrl', config.cta_url);
    set('hpAdBrowserTabTitle', config.browser_tab_title);
    set('hpAdQuoteTitle', config.quote_section_title);
    set('hpAdQuoteSubtitle', config.quote_section_subtitle);
    set('hpAdInquiryEmail', config.inquiry_email);
    set('hpAdBannerUrls', joinLines(config.banner_images));
    set('hpAdPartnerSecTitle', config.partner_section_title);
    set('hpAdPartnerSecLead', config.partner_section_lead);
    set('hpAdYoutubeSecTitle', config.youtube_section_title);
    set('hpAdYoutubeSecLead', config.youtube_section_lead);
    set('hpAdYoutubeLines', youtubeLinesFromConfig(config.youtube_items));
    (config.features || []).forEach(function (f, i) {
      if (i > 3) return;
      set('hpAdFeat' + i + 'Icon', f.icon);
      set('hpAdFeat' + i + 'Title', f.title);
      set('hpAdFeat' + i + 'Desc', f.desc);
    });
  }

  function adminLoad(apiBase) {
    var msg = document.getElementById('hpAdMessage');
    if (msg) msg.textContent = '불러오는 중…';
    var base = (apiBase || '').replace(/\/$/, '');
    fetch(base + '/api/homepage/config')
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (j && j.success && j.config) {
          fillAdminForm(j.config);
          if (msg) msg.textContent = '최신 설정을 불러왔습니다.';
        } else {
          if (msg) msg.textContent = (j && j.message) || '불러오기 실패';
        }
      })
      .catch(function (e) {
        if (msg) msg.textContent = '오류: ' + (e.message || String(e));
      });
  }

  function adminSave(apiBase) {
    var msg = document.getElementById('hpAdMessage');
    var base = (apiBase || '').replace(/\/$/, '');
    var body = JSON.stringify({ config: collectAdminForm() });
    fetch(base + '/api/homepage/config', {
      method: 'PUT',
      headers: adminHeaders(),
      body: body
    })
      .then(function (r) {
        return r.json().then(function (j) {
          return { ok: r.ok, j: j };
        }).catch(function () {
          return { ok: false, j: { message: '응답 파싱 실패' } };
        });
      })
      .then(function (x) {
        if (x.ok && x.j && x.j.success) {
          if (msg) msg.textContent = x.j.message || '저장되었습니다.';
          applyLoginLayout(x.j.config);
        } else {
          if (msg) msg.textContent = (x.j && x.j.message) || '저장 실패';
        }
      })
      .catch(function (e) {
        if (msg) msg.textContent = '오류: ' + (e.message || String(e));
      });
  }

  global.HomepagePortal = {
    applyLoginLayout: applyLoginLayout,
    initLoginPage: initLoginPage,
    adminLoad: adminLoad,
    adminSave: adminSave,
    restoreAppDocumentTitle: restoreAppDocumentTitle,
    openLoginModal: openLoginModal,
    closeLoginModal: closeLoginModal,
    syncHpPortalViewFromHash: syncHpPortalViewFromHash
  };
})(window);
