from __future__ import annotations

from collections import defaultdict
from datetime import date

from sqlalchemy import func

from app.extensions import db
from app.models import (
    AnalystWeight,
    BenchmarkWeight,
    FundMetric,
    PortfolioFund,
    PortfolioMetricHistory,
    Segment,
)


def get_latest_meeting_date() -> date | None:
    return db.session.query(func.max(AnalystWeight.meeting_date)).scalar()


def get_avg_allocation_for_date(meeting_date: date):
    rows = (
        db.session.query(Segment.name, func.avg(AnalystWeight.weight))
        .join(AnalystWeight, AnalystWeight.segment_id == Segment.id)
        .filter(AnalystWeight.meeting_date == meeting_date)
        .group_by(Segment.name)
        .all()
    )
    return {name: round(weight or 0, 2) for name, weight in rows}


def get_current_allocation():
    meeting_date = get_latest_meeting_date()
    if not meeting_date:
        return None, {}
    return meeting_date, get_avg_allocation_for_date(meeting_date)


def get_latest_benchmark_weights():
    latest_date = db.session.query(func.max(BenchmarkWeight.as_of_date)).scalar()
    if not latest_date:
        return None, {}
    rows = (
        db.session.query(Segment.name, BenchmarkWeight.weight)
        .join(BenchmarkWeight, BenchmarkWeight.segment_id == Segment.id)
        .filter(BenchmarkWeight.as_of_date == latest_date)
        .all()
    )
    return latest_date, {name: round(weight or 0, 2) for name, weight in rows}


def upsert_analyst_weights(user_id: int, meeting_date: date, weights_by_segment: dict[int, float]):
    total = round(sum(weights_by_segment.values()), 2)
    if abs(total - 100.0) > 0.01:
        raise ValueError("A soma dos pesos deve ser 100%.")

    for segment_id, weight in weights_by_segment.items():
        existing = (
            AnalystWeight.query.filter_by(
                user_id=user_id, segment_id=segment_id, meeting_date=meeting_date
            )
            .limit(1)
            .first()
        )
        if existing:
            existing.weight = weight
        else:
            db.session.add(
                AnalystWeight(
                    user_id=user_id,
                    segment_id=segment_id,
                    meeting_date=meeting_date,
                    weight=weight,
                )
            )
    db.session.commit()


def get_allocation_history():
    dates = (
        db.session.query(AnalystWeight.meeting_date)
        .distinct()
        .order_by(AnalystWeight.meeting_date.desc())
        .all()
    )
    history = []
    for (meeting_date,) in dates:
        history.append((meeting_date, get_avg_allocation_for_date(meeting_date)))
    return history


def get_analyst_allocation_for_date(user_id: int, meeting_date: date):
    rows = (
        db.session.query(Segment.name, AnalystWeight.weight)
        .join(AnalystWeight, AnalystWeight.segment_id == Segment.id)
        .filter(AnalystWeight.meeting_date == meeting_date, AnalystWeight.user_id == user_id)
        .all()
    )
    return {name: round(weight or 0, 2) for name, weight in rows}


def get_analyst_allocation_history(user_id: int):
    dates = (
        db.session.query(AnalystWeight.meeting_date)
        .filter(AnalystWeight.user_id == user_id)
        .distinct()
        .order_by(AnalystWeight.meeting_date.desc())
        .all()
    )
    history = []
    for (meeting_date,) in dates:
        history.append((meeting_date, get_analyst_allocation_for_date(user_id, meeting_date)))
    return history


def get_avg_allocation_timeseries():
    """Retorna (dates_asc, segment_names_asc, series_by_segment_name)."""
    dates = (
        db.session.query(AnalystWeight.meeting_date)
        .distinct()
        .order_by(AnalystWeight.meeting_date.asc())
        .all()
    )
    if not dates:
        return [], [], {}
    date_list = [d for (d,) in dates]
    segments = Segment.query.order_by(Segment.name.asc()).all()
    segment_names = [s.name for s in segments]

    # Inicializar com zeros
    series = {name: [0.0 for _ in date_list] for name in segment_names}
    for idx, d in enumerate(date_list):
        alloc = get_avg_allocation_for_date(d)
        for name in segment_names:
            if name in alloc:
                series[name][idx] = float(alloc[name])
    return date_list, segment_names, series


def get_analyst_allocation_timeseries(user_id: int):
    dates = (
        db.session.query(AnalystWeight.meeting_date)
        .filter(AnalystWeight.user_id == user_id)
        .distinct()
        .order_by(AnalystWeight.meeting_date.asc())
        .all()
    )
    if not dates:
        return [], [], {}
    date_list = [d for (d,) in dates]
    segments = Segment.query.order_by(Segment.name.asc()).all()
    segment_names = [s.name for s in segments]
    series = {name: [0.0 for _ in date_list] for name in segment_names}
    for idx, d in enumerate(date_list):
        alloc = get_analyst_allocation_for_date(user_id, d)
        for name in segment_names:
            if name in alloc:
                series[name][idx] = float(alloc[name])
    return date_list, segment_names, series


def _get_latest_holdings_date() -> date | None:
    return db.session.query(func.max(PortfolioFund.as_of_date)).scalar()


def _get_latest_metrics_date() -> date | None:
    return db.session.query(func.max(FundMetric.as_of_date)).scalar()


def get_latest_portfolio_segment_weights():
    latest_date = _get_latest_holdings_date()
    if not latest_date:
        return None, {}
    rows = (
        db.session.query(Segment.name, func.sum(PortfolioFund.weight))
        .join(PortfolioFund, PortfolioFund.segment_id == Segment.id)
        .filter(PortfolioFund.as_of_date == latest_date)
        .group_by(Segment.name)
        .all()
    )
    return latest_date, {name: round(weight or 0, 2) for name, weight in rows}


def compute_portfolio_metrics(as_of_date: date | None = None):
    holdings_date = as_of_date or _get_latest_holdings_date()
    metrics_date = _get_latest_metrics_date()
    if not holdings_date or not metrics_date:
        return None, {}

    holdings = (
        db.session.query(PortfolioFund.fund_code, PortfolioFund.weight)
        .filter(PortfolioFund.as_of_date == holdings_date)
        .all()
    )
    metrics = (
        db.session.query(
            FundMetric.fund_code,
            FundMetric.dy_12m,
            FundMetric.volatility,
            FundMetric.leverage,
            FundMetric.beta,
            FundMetric.p_vp,
        )
        .filter(FundMetric.as_of_date == metrics_date)
        .all()
    )
    metrics_by_fund = {row[0]: row[1:] for row in metrics}

    weighted = defaultdict(float)
    total_weight = 0.0
    for fund_code, weight in holdings:
        if fund_code not in metrics_by_fund:
            continue
        total_weight += weight
        dy_12m, volatility, leverage, beta, p_vp = metrics_by_fund[fund_code]
        for key, value in (
            ("dy_12m", dy_12m),
            ("volatility", volatility),
            ("leverage", leverage),
            ("beta", beta),
            ("p_vp", p_vp),
        ):
            if value is not None:
                weighted[key] += weight * value

    if total_weight == 0:
        return holdings_date, {}

    result = {k: round(v / total_weight, 4) for k, v in weighted.items()}
    return holdings_date, result


def store_portfolio_metrics_snapshot(as_of_date: date | None = None):
    snapshot_date, metrics = compute_portfolio_metrics(as_of_date)
    if not snapshot_date or not metrics:
        return None

    existing = PortfolioMetricHistory.query.filter_by(as_of_date=snapshot_date).first()
    if existing:
        existing.dy_12m = metrics.get("dy_12m")
        existing.volatility = metrics.get("volatility")
        existing.leverage = metrics.get("leverage")
        existing.beta = metrics.get("beta")
        existing.p_vp = metrics.get("p_vp")
    else:
        db.session.add(
            PortfolioMetricHistory(
                as_of_date=snapshot_date,
                dy_12m=metrics.get("dy_12m"),
                volatility=metrics.get("volatility"),
                leverage=metrics.get("leverage"),
                beta=metrics.get("beta"),
                p_vp=metrics.get("p_vp"),
            )
        )
    db.session.commit()
    return snapshot_date


def get_latest_portfolio_metrics():
    latest = (
        PortfolioMetricHistory.query.order_by(PortfolioMetricHistory.as_of_date.desc())
        .limit(1)
        .first()
    )
    if latest:
        return latest.as_of_date, {
            "dy_12m": latest.dy_12m,
            "volatility": latest.volatility,
            "leverage": latest.leverage,
            "beta": latest.beta,
            "p_vp": latest.p_vp,
        }
    return compute_portfolio_metrics()
