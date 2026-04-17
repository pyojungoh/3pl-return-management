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
  var _hpPortalUploadApiBase = '';
  var _hpSvcCarouselCleanup = null;
  var _hpScrollFxBound = false;
  var _hpScrollObserver = null;

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

  var _hpHeroSliderTimer = null;

  function _hpHeroSliderClearTimer() {
    if (_hpHeroSliderTimer) {
      clearInterval(_hpHeroSliderTimer);
      _hpHeroSliderTimer = null;
    }
  }

  function buildHeroSlides(slides) {
    var root = document.getElementById('hpHeroSliderRoot');
    if (!root) return;
    _hpHeroSliderClearTimer();
    root.innerHTML = '';
    root.style.display = 'none';
    if (!slides || !slides.length) return;

    root.style.display = 'block';
    var viewport = document.createElement('div');
    viewport.className = 'hp-hero-slider-viewport';
    var track = document.createElement('div');
    track.className = 'hp-hero-slider-track';
    var n = slides.length;
    var idx = 0;

    slides.forEach(function (s, i) {
      var slide = document.createElement('div');
      slide.className = 'hp-hero-slide';
      slide.setAttribute('role', 'group');
      slide.setAttribute('aria-roledescription', 'slide');
      slide.setAttribute('aria-label', '슬라이드 ' + (i + 1) + ' / ' + n);
      var img = document.createElement('img');
      img.src = s.image_url;
      img.alt = '';
      img.className = 'hp-hero-slide-img';
      img.loading = i === 0 ? 'eager' : 'lazy';
      img.decoding = 'async';
      slide.appendChild(img);
      var href = String(s.link_url || '').trim();
      var lab = String(s.button_label || '').trim() || '자세히 보기';
      var btn;
      if (href) {
        btn = document.createElement('a');
        btn.href = href;
        if (/^https?:\/\//i.test(href)) {
          btn.target = '_blank';
          btn.rel = 'noopener noreferrer';
        }
      } else {
        btn = document.createElement('span');
      }
      btn.className = 'hp-hero-slide-cta hp-btn-solid';
      btn.textContent = lab;
      slide.appendChild(btn);
      track.appendChild(slide);
    });

    track.style.width = n * 100 + '%';
    track.querySelectorAll('.hp-hero-slide').forEach(function (sl) {
      sl.style.flex = '0 0 ' + 100 / n + '%';
    });

    var prev = document.createElement('button');
    prev.type = 'button';
    prev.className = 'hp-hero-slider-arrow hp-hero-slider-arrow--prev';
    prev.setAttribute('aria-label', '이전 슬라이드');
    prev.innerHTML = '‹';
    var next = document.createElement('button');
    next.type = 'button';
    next.className = 'hp-hero-slider-arrow hp-hero-slider-arrow--next';
    next.setAttribute('aria-label', '다음 슬라이드');
    next.innerHTML = '›';
    var dots = document.createElement('div');
    dots.className = 'hp-hero-slider-dots';

    function render() {
      var pct = (100 / n) * idx;
      track.style.transform = 'translateX(-' + pct + '%)';
      prev.disabled = n <= 1;
      next.disabled = n <= 1;
      dots.querySelectorAll('button').forEach(function (b, j) {
        b.classList.toggle('hp-hero-slider-dot--active', j === idx);
      });
    }

    function go(delta) {
      idx = (idx + delta + n) % n;
      render();
    }

    function startAutoplay() {
      _hpHeroSliderClearTimer();
      if (n > 1) {
        _hpHeroSliderTimer = setInterval(function () {
          go(1);
        }, 6000);
      }
    }

    for (var d = 0; d < n; d++) {
      (function (j) {
        var dot = document.createElement('button');
        dot.type = 'button';
        dot.className = 'hp-hero-slider-dot';
        dot.setAttribute('aria-label', '슬라이드 ' + (j + 1));
        dot.addEventListener('click', function () {
          idx = j;
          render();
        });
        dots.appendChild(dot);
      })(d);
    }

    prev.addEventListener('click', function () {
      go(-1);
    });
    next.addEventListener('click', function () {
      go(1);
    });

    viewport.addEventListener('mouseenter', _hpHeroSliderClearTimer);
    viewport.addEventListener('mouseleave', startAutoplay);

    viewport.appendChild(track);
    viewport.appendChild(prev);
    viewport.appendChild(next);
    viewport.appendChild(dots);
    root.appendChild(viewport);

    render();
    startAutoplay();
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

  var DEFAULT_SERVICE_CARDS = [
    { image_url: '', title: '넓은 연결 창고 · 3단 적재', body: '4동을 이어 사용하는 넓고 쾌적한 창고 환경이며, 3단 적재가 가능해 보관 효율을 높입니다.' },
    { image_url: '', title: '자체 솔루션 · C/S·반품 가시화', body: '자체 개발 솔루션으로 빠른 C/S 처리와 상세한 반품 내역 확인을 지원합니다.' },
    { image_url: '', title: '반품·누락 투명 보상', body: '솔루션으로 반품·누락을 명확히 기록하고, 규정에 따른 투명한 보상 체계를 운영합니다.' },
    { image_url: '', title: '꼼꼼한 정산서 · 미리보기·사진', body: '세밀한 정산 내역과 함께 미리보기, 증빙 사진 등을 연계해 숫자와 현장을 동시에 확인할 수 있습니다.' },
    { image_url: '', title: '당일 100% 출고', body: '일일 출고 목표를 당일 내 100% 완료하도록 프로세스를 설계·운영합니다.' },
    { image_url: '', title: '전 직원 바코드 · 오배송 0% 지향', body: '전 직원 바코드 스캔으로 피킹·패킹 전 과정을 검증해 오배송을 구조적으로 줄입니다.' },
    { image_url: '', title: 'QR 파레트 · 입·출고 전산', body: '보관 파레트 전용 자체 개발 QR 전산으로 입고·출고를 실시간 추적합니다.' }
  ];

  function effectiveServiceCards(config) {
    var raw = (config && config.service_cards) || [];
    var list = [];
    raw.forEach(function (item) {
      if (!item || typeof item !== 'object') return;
      var title = String(item.title || '').trim();
      if (!title) return;
      list.push({
        image_url: String(item.image_url || '').trim(),
        title: title,
        body: String(item.body || '').trim()
      });
    });
    list = list.slice(0, 8);
    if (list.length >= 3) return list;
    var out = list.slice();
    for (var i = 0; out.length < 3 && i < DEFAULT_SERVICE_CARDS.length; i++) {
      var d = DEFAULT_SERVICE_CARDS[i];
      if (!out.some(function (x) { return x.title === d.title; })) out.push({ image_url: d.image_url, title: d.title, body: d.body });
    }
    return out.slice(0, 8);
  }

  function _hpStopServiceCarousel() {
    if (typeof _hpSvcCarouselCleanup === 'function') {
      try {
        _hpSvcCarouselCleanup();
      } catch (e) {
        /* noop */
      }
    }
    _hpSvcCarouselCleanup = null;
  }

  function buildServiceCarousel(config) {
    var root = document.getElementById('hpServicesCarouselRoot');
    if (!root) return;
    _hpStopServiceCarousel();
    root.classList.remove('hp-svc-carousel-static');
    root.innerHTML = '';
    var cards = effectiveServiceCards(config);
    var n = cards.length;
    if (n < 1) return;

    var reduceMotion = false;
    try {
      reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    } catch (e) {
      reduceMotion = false;
    }

    function oneCardEl(c, idx) {
      var art = document.createElement('article');
      art.className = 'hp-svc-orbit-card';
      art.setAttribute('role', 'group');
      art.setAttribute('aria-roledescription', 'slide');
      art.setAttribute('aria-label', (c.title || '서비스') + ' ' + (idx + 1) + ' / ' + n);
      var media = document.createElement('div');
      media.className = 'hp-svc-orbit-card-media';
      var url = (c.image_url || '').trim();
      if (url) {
        var im = document.createElement('img');
        im.src = url;
        im.alt = '';
        im.loading = idx === 0 ? 'eager' : 'lazy';
        im.decoding = 'async';
        media.appendChild(im);
      } else {
        var ph = document.createElement('div');
        ph.className = 'hp-svc-orbit-card-ph';
        ph.textContent = 'Photo';
        media.appendChild(ph);
      }
      var text = document.createElement('div');
      text.className = 'hp-svc-orbit-card-text';
      var h = document.createElement('h3');
      h.className = 'hp-svc-orbit-card-title';
      h.textContent = c.title || '';
      var p = document.createElement('p');
      p.className = 'hp-svc-orbit-card-body';
      p.textContent = c.body || '';
      text.appendChild(h);
      text.appendChild(p);
      art.appendChild(media);
      art.appendChild(text);
      return art;
    }

    if (reduceMotion || n < 3) {
      var wrap = document.createElement('div');
      wrap.className = 'hp-svc-carousel-static';
      cards.forEach(function (c, i) {
        wrap.appendChild(oneCardEl(c, i));
      });
      root.appendChild(wrap);
      return;
    }

    root.classList.remove('hp-svc-carousel-static');
    var stage = document.createElement('div');
    stage.className = 'hp-svc-carousel-stage';
    var track = document.createElement('div');
    track.className = 'hp-svc-carousel-track';
    var nodes = cards.map(function (c, i) {
      return oneCardEl(c, i);
    });
    nodes.forEach(function (node) {
      track.appendChild(node);
    });
    stage.appendChild(track);
    root.appendChild(stage);

    var angle = 0;
    var mousePaused = false;
    var rafId = null;
    var lastTs = 0;
    var dwellUntil = 0;
    var dwellStartTs = 0;
    var lastLeader = -1;
    var DWELL_MS = 2200;
    var ZOOM_IN_MS = 420;
    var ZOOM_OUT_MS = 420;
    var HOLD_CENTER_MS = Math.max(200, DWELL_MS - ZOOM_IN_MS - ZOOM_OUT_MS);
    var LEADER_MIN = 0.94;

    function easeInOutCubic(t) {
      t = Math.min(1, Math.max(0, t));
      return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    }

    function layout(ts) {
      if (!lastTs) lastTs = ts;
      var dt = Math.min(48, Math.max(0, ts - lastTs));
      lastTs = ts;

      var dwellActive = dwellUntil > 0 && ts < dwellUntil;
      if (!mousePaused && !dwellActive) {
        angle += (dt / 1000) * 0.34;
      }

      var rx = 38;
      var ry = 26;
      var i;
      var frontIdx = 0;
      var maxF = -1;
      var thetas = [];
      var fronts = [];
      for (i = 0; i < n; i += 1) {
        var th = (Math.PI * 2 * i) / n + angle + Math.PI / 2;
        thetas.push(th);
        var fn = (1 + Math.sin(th)) / 2;
        fronts.push(fn);
        if (fn > maxF) {
          maxF = fn;
          frontIdx = i;
        }
      }

      if (!mousePaused && maxF > LEADER_MIN && frontIdx !== lastLeader) {
        lastLeader = frontIdx;
        dwellStartTs = ts;
        dwellUntil = ts + DWELL_MS;
      }

      var dwellElapsed = dwellActive ? ts - dwellStartTs : 0;
      var centerBlend = 0;
      if (dwellActive) {
        if (dwellElapsed < ZOOM_IN_MS) {
          centerBlend = easeInOutCubic(dwellElapsed / ZOOM_IN_MS);
        } else if (dwellElapsed < ZOOM_IN_MS + HOLD_CENTER_MS) {
          centerBlend = 1;
        } else {
          centerBlend = 1 - easeInOutCubic((dwellElapsed - ZOOM_IN_MS - HOLD_CENTER_MS) / ZOOM_OUT_MS);
        }
      }

      var peakOrbitScale = 0.58 + 0.42;
      var dwellCenterScale = peakOrbitScale * 2;
      for (i = 0; i < n; i += 1) {
        var theta = thetas[i];
        var frontness = fronts[i];
        var orbitX = 50 + Math.cos(theta) * rx;
        var orbitY = 44 + Math.sin(theta) * ry;
        var orbitScale = 0.58 + 0.42 * frontness;
        var x = orbitX;
        var y = orbitY;
        var scale = orbitScale;
        var opacity = 0.45 + 0.55 * frontness;
        var blurPx = (1 - frontness) * 2.2;
        var z = Math.round(100 + 80 * frontness);
        if (dwellActive && i === frontIdx) {
          x = orbitX + (50 - orbitX) * centerBlend;
          y = orbitY + (50 - orbitY) * centerBlend;
          scale = orbitScale + (dwellCenterScale - orbitScale) * centerBlend;
          opacity = 0.55 + 0.45 * (0.45 + 0.55 * frontness) + 0.2 * centerBlend;
          if (opacity > 1) opacity = 1;
          blurPx = (1 - frontness) * 2.2 * (1 - centerBlend);
          z = 380 + Math.round(60 * centerBlend);
        } else if (dwellActive) {
          opacity *= 1 - 0.52 * centerBlend;
          blurPx = Math.max(blurPx, 0.9 + 0.7 * centerBlend);
        }
        var node = nodes[i];
        node.style.left = x + '%';
        node.style.top = y + '%';
        node.style.transform = 'translate(-50%, -50%) scale(' + scale + ')';
        node.style.opacity = String(opacity);
        node.style.zIndex = String(z);
        node.style.filter = blurPx > 0.12 ? 'blur(' + blurPx.toFixed(2) + 'px)' : 'none';
        var leaderProminent = dwellActive && i === frontIdx && centerBlend > 0.65;
        node.style.pointerEvents = leaderProminent ? 'auto' : !dwellActive && frontness > 0.82 ? 'auto' : 'none';
        node.classList.toggle(
          'hp-svc-orbit-card--front',
          (dwellActive && i === frontIdx && centerBlend > 0.35) || (!dwellActive && frontness > 0.88)
        );
      }
      rafId = window.requestAnimationFrame(layout);
    }

    rafId = window.requestAnimationFrame(layout);

    function onEnter() {
      mousePaused = true;
    }
    function onLeave() {
      mousePaused = false;
    }
    root.addEventListener('mouseenter', onEnter);
    root.addEventListener('mouseleave', onLeave);

    _hpSvcCarouselCleanup = function () {
      if (rafId) window.cancelAnimationFrame(rafId);
      rafId = null;
      root.removeEventListener('mouseenter', onEnter);
      root.removeEventListener('mouseleave', onLeave);
    };
  }

  var HP_SVC_CARD_MAX = 8;

  function updateSvcCardRowPreview(row) {
    if (!row) return;
    var urlIn = row.querySelector('.hp-svc-card-img-url');
    var prev = row.querySelector('.hp-svc-card-editor-preview-img');
    var ph = row.querySelector('.hp-svc-card-editor-preview-ph');
    var u = urlIn && urlIn.value ? urlIn.value.trim() : '';
    if (prev) {
      if (u) {
        prev.src = u;
        prev.style.display = 'block';
        if (ph) ph.style.display = 'none';
      } else {
        prev.removeAttribute('src');
        prev.style.display = 'none';
        if (ph) ph.style.display = 'flex';
      }
    }
  }

  function buildServiceCardRowEl(data) {
    data = data || {};
    var row = document.createElement('div');
    row.className = 'hp-svc-card-editor-row';
    row.innerHTML =
      '<div class="hp-svc-card-editor-preview">' +
      '<img class="hp-svc-card-editor-preview-img" alt="" style="display:none;" />' +
      '<span class="hp-svc-card-editor-preview-ph">이미지</span>' +
      '</div>' +
      '<div class="hp-svc-card-editor-fields">' +
      '<label class="hp-hero-slide-label"><span>이미지 URL</span><input type="text" class="request-input hp-svc-card-img-url" placeholder="https://…" /></label>' +
      '<div class="hp-hero-slide-upload-wrap">' +
      '<input type="file" class="hp-svc-card-file" accept="image/*" style="display:none;" />' +
      '<button type="button" class="refresh-btn hp-svc-card-upload-btn">📤 Cloudinary 업로드</button>' +
      '</div>' +
      '<label class="hp-hero-slide-label"><span>카드 제목</span><input type="text" class="request-input hp-svc-card-title-inp" placeholder="한 줄 제목" /></label>' +
      '<label class="hp-hero-slide-label"><span>본문</span><textarea class="request-input hp-svc-card-body-inp" rows="3" placeholder="설명 문구"></textarea></label>' +
      '</div>' +
      '<button type="button" class="hp-svc-card-editor-remove" title="삭제">✕</button>';

    var imgUrl = row.querySelector('.hp-svc-card-img-url');
    var tit = row.querySelector('.hp-svc-card-title-inp');
    var body = row.querySelector('.hp-svc-card-body-inp');
    if (imgUrl) imgUrl.value = String(data.image_url || '').trim();
    if (tit) tit.value = String(data.title || '').trim();
    if (body) body.value = String(data.body || '').trim();
    updateSvcCardRowPreview(row);
    if (imgUrl) {
      imgUrl.addEventListener('input', function () {
        updateSvcCardRowPreview(row);
      });
    }
    return row;
  }

  function serviceCardRowCount() {
    var ed = document.getElementById('hpServiceCardsEditor');
    return ed ? ed.querySelectorAll('.hp-svc-card-editor-row').length : 0;
  }

  function refreshServiceCardAddBtn() {
    var b = document.getElementById('hpServiceCardAddBtn');
    if (!b) return;
    b.disabled = serviceCardRowCount() >= HP_SVC_CARD_MAX;
  }

  function renderServiceCardsEditor(list) {
    var wrap = document.getElementById('hpServiceCardsEditor');
    if (!wrap) return;
    wrap.innerHTML = '';
    var arr = list && list.length ? list.slice(0, HP_SVC_CARD_MAX) : [{}];
    arr.forEach(function (s) {
      wrap.appendChild(buildServiceCardRowEl(s));
    });
    refreshServiceCardAddBtn();
  }

  function getServiceCardsFromEditor() {
    var wrap = document.getElementById('hpServiceCardsEditor');
    var out = [];
    if (!wrap) return out;
    wrap.querySelectorAll('.hp-svc-card-editor-row').forEach(function (row) {
      var tit = row.querySelector('.hp-svc-card-title-inp');
      var title = tit && tit.value ? tit.value.trim() : '';
      if (!title) return;
      var img = row.querySelector('.hp-svc-card-img-url');
      var body = row.querySelector('.hp-svc-card-body-inp');
      out.push({
        image_url: img && img.value ? img.value.trim() : '',
        title: title,
        body: body && body.value ? body.value.trim() : ''
      });
    });
    return out.slice(0, HP_SVC_CARD_MAX);
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
    buildHeroSlides(config.hero_slides || []);

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
    buildServiceCarousel(config);

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
    refreshScrollFxTargets();
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

  function _hpScrollFxSetTargets() {
    var root = document.getElementById('loginSection');
    if (!root) return;
    var groups = [
      { sel: '.hp-hero-copy', dir: 'up' },
      { sel: '.hp-hero-art', dir: 'right' },
      { sel: '#hpMarqueeRoot', dir: 'up' },
      { sel: '.hp-sec-header', dir: 'up' },
      { sel: '.hp-quote-intro-wrap', dir: 'up' },
      { sel: '.hp-quote-teaser', dir: 'up' },
      { sel: '.hp-quote-card', dir: 'up' }
    ];
    groups.forEach(function (g) {
      root.querySelectorAll(g.sel).forEach(function (el) {
        el.classList.add('hp-reveal', 'hp-reveal--' + g.dir);
      });
    });
    function markStagger(sel, step, dir) {
      root.querySelectorAll(sel).forEach(function (group) {
        var items = group.querySelectorAll(':scope > *');
        var i;
        for (i = 0; i < items.length; i += 1) {
          var it = items[i];
          it.classList.add('hp-reveal', 'hp-reveal--' + (dir || 'up'));
          it.style.setProperty('--hp-reveal-delay', (i * step).toFixed(2) + 's');
        }
      });
    }
    markStagger('#hpYoutubeGrid', 0.1, 'up');
    markStagger('#hpServicesCarouselRoot .hp-svc-carousel-static', 0.08, 'up');
    markStagger('#hpServicesCarouselRoot .hp-svc-carousel-track', 0.05, 'up');
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      root.querySelectorAll('.hp-reveal').forEach(function (el) {
        el.classList.add('is-visible');
      });
    }
  }

  function refreshScrollFxTargets() {
    _hpScrollFxSetTargets();
    if (!_hpScrollObserver) return;
    document.querySelectorAll('.hp-reveal:not(.is-visible)').forEach(function (el) {
      _hpScrollObserver.observe(el);
    });
  }

  function initScrollFxOnce() {
    if (_hpScrollFxBound) {
      refreshScrollFxTargets();
      return;
    }
    _hpScrollFxBound = true;
    _hpScrollFxSetTargets();
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      document.querySelectorAll('.hp-reveal').forEach(function (el) {
        el.classList.add('is-visible');
      });
      return;
    }
    _hpScrollObserver = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          entry.target.classList.add('is-visible');
          _hpScrollObserver.unobserve(entry.target);
        });
      },
      { threshold: 0.16, rootMargin: '0px 0px -8% 0px' }
    );
    document.querySelectorAll('.hp-reveal:not(.is-visible)').forEach(function (el) {
      _hpScrollObserver.observe(el);
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
    initScrollFxOnce();
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
      'X-User-Role': encodeURIComponent(role),
      'X-User-Name': encodeURIComponent(name)
    };
  }

  function adminHeadersMultipart() {
    var role = localStorage.getItem('client_role') || '';
    var name = localStorage.getItem('client_username') || '';
    return {
      'X-User-Role': encodeURIComponent(role),
      'X-User-Name': encodeURIComponent(name)
    };
  }

  function uploadHomepagePortalImage(apiBase, file) {
    var base = (apiBase || '').replace(/\/$/, '');
    if (!base && window.location && window.location.origin && window.location.origin !== 'null') {
      base = window.location.origin.replace(/\/$/, '');
    }
    var path = base ? base + '/api/homepage/upload-image' : '/api/homepage/upload-image';
    var fd = new FormData();
    fd.append('file', file);
    return fetch(path, {
      method: 'POST',
      headers: adminHeadersMultipart(),
      body: fd
    })
      .then(function (r) {
        return r.json().then(function (j) {
          return { ok: r.ok, j: j };
        });
      })
      .then(function (x) {
        if (x.ok && x.j && x.j.success && x.j.data && x.j.data.file_url) return x.j.data.file_url;
        throw new Error((x.j && x.j.message) || '업로드 실패');
      });
  }

  var HP_SLIDES_MAX = 12;

  function updateHeroSlideRowPreview(row) {
    if (!row) return;
    var urlIn = row.querySelector('.hp-hero-slide-img-url');
    var prev = row.querySelector('.hp-hero-slide-preview-img');
    var ph = row.querySelector('.hp-hero-slide-preview-ph');
    var u = urlIn && urlIn.value ? urlIn.value.trim() : '';
    if (prev) {
      if (u) {
        prev.src = u;
        prev.style.display = 'block';
        if (ph) ph.style.display = 'none';
      } else {
        prev.removeAttribute('src');
        prev.style.display = 'none';
        if (ph) ph.style.display = 'flex';
      }
    }
  }

  function buildHeroSlideRowEl(data) {
    data = data || {};
    var row = document.createElement('div');
    row.className = 'hp-hero-slide-row';
    row.innerHTML =
      '<div class="hp-hero-slide-preview">' +
      '<img class="hp-hero-slide-preview-img" alt="" style="display:none;" />' +
      '<span class="hp-hero-slide-preview-ph">미리보기</span>' +
      '</div>' +
      '<div class="hp-hero-slide-fields">' +
      '<label class="hp-hero-slide-label"><span>이미지 URL</span><input type="text" class="request-input hp-hero-slide-img-url" placeholder="https://…" /></label>' +
      '<div class="hp-hero-slide-upload-wrap">' +
      '<input type="file" class="hp-hero-slide-file" accept="image/*" style="display:none;" />' +
      '<button type="button" class="refresh-btn hp-hero-slide-upload-btn">📤 Cloudinary 업로드</button>' +
      '</div>' +
      '<label class="hp-hero-slide-label"><span>버튼 문구</span><input type="text" class="request-input hp-hero-slide-btn-label" placeholder="예: 회사 소개" /></label>' +
      '<label class="hp-hero-slide-label"><span>이동 URL</span><input type="text" class="request-input hp-hero-slide-link" placeholder="비우면 링크 없음 · #quote 가능" /></label>' +
      '</div>' +
      '<button type="button" class="hp-hero-slide-row-remove" title="이 줄 삭제">✕</button>';

    var imgUrl = row.querySelector('.hp-hero-slide-img-url');
    var lab = row.querySelector('.hp-hero-slide-btn-label');
    var link = row.querySelector('.hp-hero-slide-link');
    if (imgUrl) imgUrl.value = String(data.image_url || '').trim();
    if (lab) lab.value = String(data.button_label || '').trim();
    if (link) link.value = String(data.link_url || '').trim();
    updateHeroSlideRowPreview(row);
    if (imgUrl) {
      imgUrl.addEventListener('input', function () {
        updateHeroSlideRowPreview(row);
      });
    }
    return row;
  }

  function heroSlidesRowCount() {
    var ed = document.getElementById('hpHeroSlidesEditor');
    return ed ? ed.querySelectorAll('.hp-hero-slide-row').length : 0;
  }

  function refreshHeroSlideAddButtonState() {
    var b = document.getElementById('hpHeroSlideAddBtn');
    if (!b) return;
    b.disabled = heroSlidesRowCount() >= HP_SLIDES_MAX;
  }

  function renderHeroSlidesEditor(slides) {
    var wrap = document.getElementById('hpHeroSlidesEditor');
    if (!wrap) return;
    wrap.innerHTML = '';
    var list = slides && slides.length ? slides.slice(0, HP_SLIDES_MAX) : [{}];
    list.forEach(function (s) {
      wrap.appendChild(buildHeroSlideRowEl(s));
    });
    refreshHeroSlideAddButtonState();
  }

  function getHeroSlidesFromEditor() {
    var wrap = document.getElementById('hpHeroSlidesEditor');
    var out = [];
    if (!wrap) return out;
    wrap.querySelectorAll('.hp-hero-slide-row').forEach(function (row) {
      var img = row.querySelector('.hp-hero-slide-img-url');
      var lab = row.querySelector('.hp-hero-slide-btn-label');
      var link = row.querySelector('.hp-hero-slide-link');
      var image_url = img && img.value ? img.value.trim() : '';
      if (!image_url) return;
      out.push({
        image_url: image_url,
        button_label: (lab && lab.value ? lab.value.trim() : '') || '자세히 보기',
        link_url: link && link.value ? link.value.trim() : ''
      });
    });
    return out.slice(0, HP_SLIDES_MAX);
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
      youtube_items: parseYoutubeLines(val('hpAdYoutubeLines')),
      hero_slides: getHeroSlidesFromEditor(),
      service_cards: getServiceCardsFromEditor()
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
    renderHeroSlidesEditor(config.hero_slides || []);
    renderServiceCardsEditor(config.service_cards || []);
    (config.features || []).forEach(function (f, i) {
      if (i > 3) return;
      set('hpAdFeat' + i + 'Icon', f.icon);
      set('hpAdFeat' + i + 'Title', f.title);
      set('hpAdFeat' + i + 'Desc', f.desc);
    });
  }

  function adminLoad(apiBase) {
    _hpPortalUploadApiBase = apiBase != null ? String(apiBase).replace(/\/$/, '') : '';
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
    _hpPortalUploadApiBase = apiBase != null ? String(apiBase).replace(/\/$/, '') : '';
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

  var _hpAdminPortalTabsBound = false;
  function bindHomepageAdminPortalTabs() {
    if (_hpAdminPortalTabsBound) return;
    var tabRoot = document.getElementById('homepageSettingsTab');
    if (!tabRoot) return;
    _hpAdminPortalTabsBound = true;

    var edInit = document.getElementById('hpHeroSlidesEditor');
    if (edInit && !edInit.querySelector('.hp-hero-slide-row')) {
      renderHeroSlidesEditor([]);
    }
    var scInit = document.getElementById('hpServiceCardsEditor');
    if (scInit && !scInit.querySelector('.hp-svc-card-editor-row')) {
      renderServiceCardsEditor([]);
    }

    tabRoot.addEventListener('click', function (e) {
      var bodyBtn = e.target.closest('[data-hp-body-panel]');
      if (bodyBtn && bodyBtn.tagName === 'BUTTON') {
        var bid = bodyBtn.getAttribute('data-hp-body-panel');
        if (bid) {
          tabRoot.querySelectorAll('.hp-admin-body-tab[data-hp-body-panel]').forEach(function (b) {
            var on = b === bodyBtn;
            b.classList.toggle('hp-admin-body-tab--active', on);
            b.setAttribute('aria-selected', on ? 'true' : 'false');
          });
          ['hpBodyPanelSlides', 'hpBodyPanelHeadline', 'hpBodyPanelBanner', 'hpBodyPanelMid', 'hpBodyPanelFeatures', 'hpBodyPanelQuote'].forEach(function (pid) {
            var p = document.getElementById(pid);
            if (p) p.hidden = pid !== bid;
          });
        }
        return;
      }

      if (e.target.closest('#hpLogoCloudUploadBtn')) {
        var li = document.getElementById('hpLogoCloudUploadInput');
        if (li) li.click();
        return;
      }
      if (e.target.closest('#hpBannerCloudUploadBtn')) {
        var bi = document.getElementById('hpBannerCloudUploadInput');
        if (bi) bi.click();
        return;
      }

      if (e.target.closest('#hpHeroSlideAddBtn')) {
        var ed = document.getElementById('hpHeroSlidesEditor');
        if (!ed) return;
        if (heroSlidesRowCount() >= HP_SLIDES_MAX) {
          window.alert('슬라이드는 최대 ' + HP_SLIDES_MAX + '개까지입니다.');
          return;
        }
        ed.appendChild(buildHeroSlideRowEl({}));
        refreshHeroSlideAddButtonState();
        return;
      }

      var uploadSlide = e.target.closest('.hp-hero-slide-upload-btn');
      if (uploadSlide) {
        var row = uploadSlide.closest('.hp-hero-slide-row');
        var fin = row && row.querySelector('.hp-hero-slide-file');
        if (fin) fin.click();
        return;
      }

      var rem = e.target.closest('.hp-hero-slide-row-remove');
      if (rem) {
        var rowR = rem.closest('.hp-hero-slide-row');
        if (rowR && rowR.parentNode) rowR.parentNode.removeChild(rowR);
        var ed2 = document.getElementById('hpHeroSlidesEditor');
        if (ed2 && heroSlidesRowCount() === 0) ed2.appendChild(buildHeroSlideRowEl({}));
        refreshHeroSlideAddButtonState();
        return;
      }

      if (e.target.closest('#hpServiceCardAddBtn')) {
        var sce = document.getElementById('hpServiceCardsEditor');
        if (!sce) return;
        if (serviceCardRowCount() >= HP_SVC_CARD_MAX) {
          window.alert('서비스 카드는 최대 ' + HP_SVC_CARD_MAX + '개까지입니다.');
          return;
        }
        sce.appendChild(buildServiceCardRowEl({}));
        refreshServiceCardAddBtn();
        return;
      }

      var svcUp = e.target.closest('.hp-svc-card-upload-btn');
      if (svcUp) {
        var srow = svcUp.closest('.hp-svc-card-editor-row');
        var sfin = srow && srow.querySelector('.hp-svc-card-file');
        if (sfin) sfin.click();
        return;
      }

      var svcRem = e.target.closest('.hp-svc-card-editor-remove');
      if (svcRem) {
        var srowR = svcRem.closest('.hp-svc-card-editor-row');
        if (srowR && srowR.parentNode) srowR.parentNode.removeChild(srowR);
        var sce2 = document.getElementById('hpServiceCardsEditor');
        if (sce2 && serviceCardRowCount() === 0) sce2.appendChild(buildServiceCardRowEl({}));
        refreshServiceCardAddBtn();
        return;
      }

      var btn = e.target.closest('[data-hp-portal-panel]');
      if (!btn || btn.tagName !== 'BUTTON') return;
      var id = btn.getAttribute('data-hp-portal-panel');
      if (!id) return;
      tabRoot.querySelectorAll('.hp-admin-portal-tab[data-hp-portal-panel]').forEach(function (b) {
        var on = b === btn;
        b.classList.toggle('hp-admin-portal-tab--active', on);
        b.setAttribute('aria-selected', on ? 'true' : 'false');
      });
      ['hpPanelNav', 'hpPanelFooter', 'hpPanelBody'].forEach(function (pid) {
        var p = document.getElementById(pid);
        if (p) p.hidden = pid !== id;
      });
    });

    tabRoot.addEventListener('change', function (e) {
      var t = e.target;
      if (!t || t.tagName !== 'INPUT' || t.type !== 'file') return;
      var apiBase = _hpPortalUploadApiBase;
      function resetInput() {
        t.value = '';
      }
      var file = t.files && t.files[0];
      if (!file) return;
      if (!file.type.startsWith('image/')) {
        window.alert('이미지 파일만 업로드할 수 있습니다.');
        resetInput();
        return;
      }
      if (file.size > 8 * 1024 * 1024) {
        window.alert('이미지는 8MB 이하여야 합니다.');
        resetInput();
        return;
      }

      if (t.id === 'hpLogoCloudUploadInput') {
        uploadHomepagePortalImage(apiBase, file)
          .then(function (url) {
            var el = document.getElementById('hpAdLogoUrl');
            if (el) el.value = url;
          })
          .catch(function (err) {
            window.alert(err.message || String(err));
          })
          .finally(resetInput);
        return;
      }

      if (t.id === 'hpBannerCloudUploadInput') {
        uploadHomepagePortalImage(apiBase, file)
          .then(function (url) {
            var ta = document.getElementById('hpAdBannerUrls');
            if (!ta) return;
            var lines = ta.value.trim() ? ta.value.split(/\r?\n/).map(function (x) { return x.trim(); }).filter(Boolean) : [];
            if (lines.length >= 20) {
              window.alert('배너는 최대 20장까지입니다.');
              return;
            }
            lines.push(url);
            ta.value = lines.join('\n');
          })
          .catch(function (err) {
            window.alert(err.message || String(err));
          })
          .finally(resetInput);
        return;
      }

      if (t.classList.contains('hp-hero-slide-file')) {
        var row = t.closest('.hp-hero-slide-row');
        uploadHomepagePortalImage(apiBase, file)
          .then(function (url) {
            var inp = row && row.querySelector('.hp-hero-slide-img-url');
            if (inp) inp.value = url;
            updateHeroSlideRowPreview(row);
          })
          .catch(function (err) {
            window.alert(err.message || String(err));
          })
          .finally(resetInput);
        return;
      }

      if (t.classList.contains('hp-svc-card-file')) {
        var srow = t.closest('.hp-svc-card-editor-row');
        uploadHomepagePortalImage(apiBase, file)
          .then(function (url) {
            var inp2 = srow && srow.querySelector('.hp-svc-card-img-url');
            if (inp2) inp2.value = url;
            updateSvcCardRowPreview(srow);
          })
          .catch(function (err) {
            window.alert(err.message || String(err));
          })
          .finally(resetInput);
      }
    });
  }

  bindHomepageAdminPortalTabs();

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
