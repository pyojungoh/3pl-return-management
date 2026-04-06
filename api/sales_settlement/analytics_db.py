"""
매출정산 통계 집계 (settlements 테이블 기준)
라우트와 분리해 테스트·수정이 쉽도록 유지
"""
from collections import defaultdict
from typing import Any, Dict, List, Optional


def _parse_year_month(ym: str) -> Optional[tuple]:
    if not ym or len(ym) < 7:
        return None
    try:
        y = int(ym[:4])
        m = int(ym[5:7])
        if m < 1 or m > 12:
            return None
        return (y, m)
    except (ValueError, TypeError):
        return None


def _in_year_range(ym: str, year_from: Optional[str], year_to: Optional[str]) -> bool:
    parsed = _parse_year_month(ym)
    if not parsed:
        return False
    y, _ = parsed
    if year_from:
        try:
            if y < int(year_from):
                return False
        except ValueError:
            pass
    if year_to:
        try:
            if y > int(year_to):
                return False
        except ValueError:
            pass
    return True


def build_settlement_analytics(
    rows: List[Dict[str, Any]],
    *,
    months_back: int = 24,
    year_from: Optional[str] = None,
    year_to: Optional[str] = None,
) -> Dict[str, Any]:
    """
    settlements 행 목록으로 월별·연별·화주사 순위·KPI 산출.

    rows: dict with keys settlement_year_month, company_name, total_amount, status
    """
    monthly: Dict[str, int] = defaultdict(int)
    month_rows: Dict[str, int] = defaultdict(int)
    yearly: Dict[str, int] = defaultdict(int)
    company_totals: Dict[str, int] = defaultdict(int)
    status_counts: Dict[str, int] = defaultdict(int)
    total_amount = 0
    row_count = 0

    for r in rows:
        ym = (r.get('settlement_year_month') or '').strip()
        if not _in_year_range(ym, year_from, year_to):
            continue
        amt = int(r.get('total_amount') or 0)
        cn = (r.get('company_name') or '').strip() or '(미지정)'
        st = (r.get('status') or '대기') or '대기'

        total_amount += amt
        row_count += 1
        monthly[ym] += amt
        month_rows[ym] += 1
        ykey = ym[:4] if len(ym) >= 4 else ''
        if ykey:
            yearly[ykey] += amt
        company_totals[cn] += amt
        status_counts[st] += 1

    # 월별 시계열 (오름차순), 최근 months_back개만
    months_sorted = sorted(monthly.keys())
    if months_back > 0 and len(months_sorted) > months_back:
        months_sorted = months_sorted[-months_back:]
    monthly_series = [
        {'month': m, 'total': monthly[m], 'rows': month_rows[m]}
        for m in months_sorted
    ]

    # 연별 (필터 범위 내)
    years_sorted = sorted(yearly.keys())
    yearly_series = [{'year': int(y), 'total': yearly[y]} for y in years_sorted]

    # 화주사 순위 (상위 20)
    ranked = sorted(company_totals.items(), key=lambda x: -x[1])
    top_n = ranked[:20]
    grand = total_amount if total_amount > 0 else 1
    company_ranking = [
        {
            'company_name': name,
            'total_amount': amt,
            'share_pct': round(amt / grand * 100, 2),
        }
        for name, amt in top_n
    ]

    # KPI
    n_months = len(months_sorted)
    avg_monthly = int(total_amount / n_months) if n_months else 0
    best_month = None
    best_month_amt = 0
    for m in months_sorted:
        if monthly[m] > best_month_amt:
            best_month_amt = monthly[m]
            best_month = m

    best_year = None
    best_year_amt = 0
    for y in years_sorted:
        if yearly[y] > best_year_amt:
            best_year_amt = yearly[y]
            best_year = int(y)

    # 전월 대비 (월별 시계열 마지막 두 달)
    mom_pct = None
    if len(months_sorted) >= 2:
        m1, m2 = months_sorted[-2], months_sorted[-1]
        a1, a2 = monthly[m1], monthly[m2]
        if a1 > 0:
            mom_pct = round((a2 - a1) / a1 * 100, 2)

    # 입금완료 비율
    done = status_counts.get('입금완료', 0)
    completed_ratio = round(done / row_count * 100, 2) if row_count else 0.0

    return {
        'filters': {
            'months_back': months_back,
            'year_from': year_from or None,
            'year_to': year_to or None,
        },
        'kpi': {
            'total_amount': total_amount,
            'row_count': row_count,
            'avg_monthly': avg_monthly,
            'best_month': best_month,
            'best_month_amount': best_month_amt,
            'best_year': best_year,
            'best_year_amount': best_year_amt,
            'mom_last_pct': mom_pct,
            'completed_ratio_pct': completed_ratio,
        },
        'monthly_series': monthly_series,
        'yearly_series': yearly_series,
        'company_ranking': company_ranking,
        'status_breakdown': dict(status_counts),
    }
