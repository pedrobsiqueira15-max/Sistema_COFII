from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.extensions import db
from app.models import Segment
from app.models import User
from app.services import (
    get_allocation_history,
    get_analyst_allocation_history,
    get_current_allocation,
    get_avg_allocation_timeseries,
    get_analyst_allocation_timeseries,
    get_latest_benchmark_weights,
    get_latest_portfolio_segment_weights,
    get_latest_portfolio_metrics,
    upsert_analyst_weights,
)

views_bp = Blueprint("views", __name__)


@views_bp.route("/")
def index():
    return redirect(url_for("views.dashboard"))


@views_bp.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    segments = Segment.query.order_by(Segment.name.asc()).all()
    users = User.query.order_by(User.name.asc()).all()
    selected_user_id = None
    if users:
        selected_user_id = request.args.get("user_id") or request.form.get("user_id")
        if selected_user_id is None:
            selected_user_id = users[0].id
        else:
            selected_user_id = int(selected_user_id)

    if request.method == "POST":
        if not selected_user_id:
            flash("Cadastre um analista antes de salvar.", "error")
            return redirect(url_for("views.dashboard"))
        weights = {}
        for segment in segments:
            raw_value = request.form.get(f"segment_{segment.id}", "0").replace(",", ".")
            try:
                weight = float(raw_value)
            except ValueError:
                weight = 0.0
            weights[segment.id] = weight
        try:
            upsert_analyst_weights(selected_user_id, date.today(), weights)
            flash("Pesos salvos com sucesso.", "success")
            return redirect(url_for("views.dashboard", user_id=selected_user_id))
        except ValueError as exc:
            flash(str(exc), "error")

    current_date, current_alloc = get_current_allocation()
    portfolio_date, portfolio_alloc = get_latest_portfolio_segment_weights()
    benchmark_date, benchmark_alloc = get_latest_benchmark_weights()
    metrics_date, metrics = get_latest_portfolio_metrics()

    return render_template(
        "dashboard.html",
        segments=segments,
        users=users,
        selected_user_id=selected_user_id,
        current_date=current_date,
        current_alloc=current_alloc,
        portfolio_date=portfolio_date,
        portfolio_alloc=portfolio_alloc,
        benchmark_date=benchmark_date,
        benchmark_alloc=benchmark_alloc,
        metrics_date=metrics_date,
        metrics=metrics,
    )


@views_bp.route("/history")
def history():
    users = User.query.order_by(User.name.asc()).all()
    selected_user_id = request.args.get("user_id")
    selected_user_id_int = int(selected_user_id) if selected_user_id else None

    consolidated_history = get_allocation_history()
    analyst_history = (
        get_analyst_allocation_history(selected_user_id_int) if selected_user_id_int else []
    )

    dates, segment_names, series = get_avg_allocation_timeseries()
    analyst_dates, _, analyst_series = (
        get_analyst_allocation_timeseries(selected_user_id_int) if selected_user_id_int else ([], [], {})
    )

    return render_template(
        "history.html",
        users=users,
        selected_user_id=selected_user_id_int,
        consolidated_history=consolidated_history,
        analyst_history=analyst_history,
        timeline_dates=dates,
        timeline_segment_names=segment_names,
        timeline_series=series,
        analyst_timeline_dates=analyst_dates,
        analyst_timeline_series=analyst_series,
    )


@views_bp.route("/users")
def users():
    users_list = User.query.order_by(User.created_at.desc()).all()
    return render_template("users.html", users=users_list)
