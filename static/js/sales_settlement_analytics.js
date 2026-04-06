/**
 * 매출정산 > 연별 정산 통계 (차트·순위)
 * Chart.js 전역(대시보드 로드) 사용. 단독 페이지면 CDN 필요.
 */
(function () {
  'use strict';

  var charts = { monthly: null, yearly: null, status: null };

  function destroyCharts() {
    ['monthly', 'yearly', 'status'].forEach(function (key) {
      if (charts[key]) {
        try {
          charts[key].destroy();
        } catch (e) {}
        charts[key] = null;
      }
    });
  }

  function ensureChartJs(cb) {
    if (typeof Chart !== 'undefined') {
      cb();
      return;
    }
    var s = document.createElement('script');
    s.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
    s.onload = cb;
    document.head.appendChild(s);
  }

  function fmt(n) {
    return (n != null ? Number(n) : 0).toLocaleString();
  }

  window.ssSwitchSalesView = function (view) {
    var listEl = document.getElementById('ssViewList');
    var statsEl = document.getElementById('ssViewStats');
    document.querySelectorAll('.ss-subnav-btn').forEach(function (b) {
      b.classList.toggle('active', b.getAttribute('data-view') === view);
    });
    if (listEl) listEl.style.display = view === 'list' ? 'block' : 'none';
    if (statsEl) statsEl.style.display = view === 'stats' ? 'block' : 'none';
    if (view === 'stats') {
      ensureChartJs(function () {
        window.ssLoadAnalytics();
      });
    } else {
      destroyCharts();
    }
  };

  window.ssLoadAnalytics = function () {
    var yf = document.getElementById('ssAnYearFrom');
    var yt = document.getElementById('ssAnYearTo');
    var mb = document.getElementById('ssAnMonthsBack');
    var params = new URLSearchParams();
    if (yf && yf.value) params.set('year_from', yf.value);
    if (yt && yt.value) params.set('year_to', yt.value);
    if (mb && mb.value) params.set('months_back', mb.value);

    var kpi = document.getElementById('ssAnKpi');
    var rankBody = document.getElementById('ssAnRankBody');
    var insight = document.getElementById('ssAnInsight');
    if (kpi) kpi.innerHTML = '<div class="ss-no-data">불러오는 중...</div>';
    if (rankBody) rankBody.innerHTML = '';
    if (insight) insight.textContent = '';

    var headers = typeof ssGetUserHeaders === 'function' ? ssGetUserHeaders() : {};

    fetch('/api/sales_settlement/analytics?' + params.toString(), {
      credentials: 'include',
      headers: headers,
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (res) {
        if (!res.success) {
          if (kpi) kpi.innerHTML = '<div class="ss-no-data">' + (res.message || '조회 실패') + '</div>';
          return;
        }
        var d = res.data || {};
        var k = d.kpi || {};
        if (kpi) {
          kpi.innerHTML =
            '<div class="ss-card ss-kpi-card"><div class="ss-card-title">기간 합계 (세전)</div><div class="ss-card-value">' +
            fmt(k.total_amount) +
            '원</div></div>' +
            '<div class="ss-card ss-kpi-card"><div class="ss-card-title">정산 건수</div><div class="ss-card-value" style="font-size:20px;font-weight:800;color:#ff6b35;">' +
            fmt(k.row_count) +
            '건</div></div>' +
            '<div class="ss-card ss-kpi-card"><div class="ss-card-title">월평균 매출</div><div class="ss-card-value" style="font-size:20px;font-weight:800;color:#ff6b35;">' +
            fmt(k.avg_monthly) +
            '원</div></div>' +
            '<div class="ss-card ss-kpi-card"><div class="ss-card-title">최고 매출 월</div><div class="ss-card-value" style="font-size:16px;font-weight:700;color:#2d3436;">' +
            (k.best_month || '-') +
            '<br><span style="color:#ff6b35">' +
            fmt(k.best_month_amount) +
            '원</span></div></div>' +
            '<div class="ss-card ss-kpi-card"><div class="ss-card-title">최고 매출 연도</div><div class="ss-card-value" style="font-size:16px;font-weight:700;color:#2d3436;">' +
            (k.best_year != null ? k.best_year + '년' : '-') +
            '<br><span style="color:#ff6b35">' +
            fmt(k.best_year_amount) +
            '원</span></div></div>' +
            '<div class="ss-card ss-kpi-card"><div class="ss-card-title">입금완료 비율</div><div class="ss-card-value" style="font-size:20px;font-weight:800;color:#00a085;">' +
            (k.completed_ratio_pct != null ? k.completed_ratio_pct : 0) +
            '%</div></div>';
        }
        if (insight) {
          var parts = [];
          if (k.mom_last_pct != null) {
            parts.push('최근 비교 월 매출 전월 대비 ' + (k.mom_last_pct >= 0 ? '+' : '') + k.mom_last_pct + '%');
          }
          parts.push('상위 화주사는 기간 합계 기준입니다.');
          insight.textContent = parts.join(' · ');
        }

        var ms = d.monthly_series || [];
        var ys = d.yearly_series || [];
        var st = d.status_breakdown || {};
        var rank = d.company_ranking || [];

        if (rankBody) {
          rankBody.innerHTML = rank
            .map(function (row, i) {
              var name = (row.company_name || '').replace(/</g, '&lt;');
              return (
                '<tr><td>' +
                (i + 1) +
                '</td><td>' +
                name +
                '</td><td style="text-align:right">' +
                fmt(row.total_amount) +
                '원</td><td style="text-align:right">' +
                (row.share_pct != null ? row.share_pct : 0) +
                '%</td></tr>'
              );
            })
            .join('');
        }

        ensureChartJs(function () {
          destroyCharts();

          var ctxM = document.getElementById('ssChartMonthly');
          var ctxY = document.getElementById('ssChartYearly');
          var ctxS = document.getElementById('ssChartStatus');

          if (ctxM && ms.length) {
            charts.monthly = new Chart(ctxM, {
              type: 'line',
              data: {
                labels: ms.map(function (x) {
                  return x.month;
                }),
                datasets: [
                  {
                    label: '월별 매출(원)',
                    data: ms.map(function (x) {
                      return x.total;
                    }),
                    borderColor: '#ff6b35',
                    backgroundColor: 'rgba(255,107,53,0.12)',
                    fill: true,
                    tension: 0.2,
                  },
                ],
              },
              options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: { display: true },
                  title: { display: true, text: '월간 매출 추이' },
                },
                scales: { y: { beginAtZero: true } },
              },
            });
          }

          if (ctxY && ys.length) {
            charts.yearly = new Chart(ctxY, {
              type: 'bar',
              data: {
                labels: ys.map(function (x) {
                  return x.year + '년';
                }),
                datasets: [
                  {
                    label: '연간 매출(원)',
                    data: ys.map(function (x) {
                      return x.total;
                    }),
                    backgroundColor: 'rgba(0, 184, 148, 0.75)',
                  },
                ],
              },
              options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  title: { display: true, text: '연간 매출 합계' },
                },
                scales: { y: { beginAtZero: true } },
              },
            });
          }

          if (ctxS) {
            var labels = Object.keys(st);
            var vals = labels.map(function (l) {
              return st[l];
            });
            if (labels.length) {
              charts.status = new Chart(ctxS, {
                type: 'doughnut',
                data: {
                  labels: labels,
                  datasets: [
                    {
                      data: vals,
                      backgroundColor: ['#dfe6e9', '#74b9ff', '#00b894', '#00a085', '#fdcb6e', '#e17055'],
                    },
                  ],
                },
                options: {
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: {
                    title: { display: true, text: '상태별 건수' },
                    legend: { position: 'bottom' },
                  },
                },
              });
            }
          }
        });
      })
      .catch(function (err) {
        console.error('[SS Analytics]', err);
        if (kpi) kpi.innerHTML = '<div class="ss-no-data">통계를 불러오지 못했습니다.</div>';
      });
  };
})();
