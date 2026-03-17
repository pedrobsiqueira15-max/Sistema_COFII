from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.datafeed_import import import_datafeed_from_csv_text
from app.extensions import db
from app.funds_import import import_funds_from_excel_bytes
from app.models import Segment
from app.models import User
from app.services import (
    get_allocation_history,
    get_analyst_allocation_history,
    get_current_allocation,
    get_avg_allocation_timeseries,
    get_analyst_allocation_timeseries,
    get_latest_benchmark_weights,
    get_latest_ifix_composition_by_segment,
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
    ifix_date, ifix_alloc = get_latest_ifix_composition_by_segment()
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
        ifix_date=ifix_date,
        ifix_alloc=ifix_alloc,
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


@views_bp.route("/upload-cadastrais", methods=["POST"])
def upload_cadastrais():
    """Recebe Excel Dados Cadastrais - FIIs (código, nome, setor) e vincula FII ao segmento."""
    file = request.files.get("cadastrais_excel")
    if not file or file.filename == "":
        flash("Nenhum arquivo selecionado. Escolha o Excel Dados Cadastrais - FIIs.", "error")
        return redirect(url_for("views.dashboard"))

    if not (file.filename.lower().endswith(".xlsx") or file.filename.lower().endswith(".xls")):
        flash("Envie um arquivo Excel (.xlsx ou .xls).", "error")
        return redirect(url_for("views.dashboard"))

    try:
        excel_bytes = file.read()
        created, updated, errors = import_funds_from_excel_bytes(excel_bytes)
        msg = f"Cadastrais enviados: {created} FIIs criados, {updated} atualizados (vínculo com segmento)."
        if errors:
            msg += f" Avisos: {len(errors)}."
        flash(msg, "success")
    except Exception as e:
        flash(f"Erro ao processar o Excel: {e}", "error")

    return redirect(url_for("views.dashboard"))


@views_bp.route("/upload-data", methods=["POST"])
def upload_data():
    """Recebe arquivo CSV do datafeed Economatica e grava no banco (Supabase)."""
    file = request.files.get("datafeed_csv")
    if not file or file.filename == "":
        flash("Nenhum arquivo selecionado. Escolha um CSV do datafeed Economatica.", "error")
        return redirect(url_for("views.dashboard"))

    if not file.filename.lower().endswith(".csv"):
        flash("Envie um arquivo CSV (datafeed Economatica).", "error")
        return redirect(url_for("views.dashboard"))

    try:
        raw = file.read()
        for encoding in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
            try:
                csv_text = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            csv_text = raw.decode("latin-1", errors="ignore")

        num_metrics, num_ifix = import_datafeed_from_csv_text(csv_text)
        flash(
            f"Dados enviados para o banco: {num_metrics} indicadores e {num_ifix} pesos do IFIX.",
            "success",
        )
    except ValueError as e:
        flash(str(e), "error")
    except Exception as e:
        flash(f"Erro ao processar o arquivo: {e}", "error")

    return redirect(url_for("views.dashboard"))


@views_bp.route("/users")
def users():
    users_list = User.query.order_by(User.created_at.desc()).all()
    return render_template("users.html", users=users_list)
