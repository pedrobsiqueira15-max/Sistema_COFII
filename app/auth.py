import os

from flask import Blueprint, redirect, render_template, request, url_for, flash
from flask_login import login_user, logout_user

from app.models import User
from app.extensions import db

auth_bp = Blueprint("auth", __name__)

def _registration_allowed() -> bool:
    allow_public = os.environ.get("ALLOW_PUBLIC_REGISTER", "").lower() in {"1", "true", "yes"}
    if allow_public:
        return True
    return User.query.count() == 0


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("Credenciais invalidas.", "error")
        else:
            login_user(user)
            return redirect(url_for("views.dashboard"))
    return render_template("login.html", can_register=_registration_allowed())


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if not _registration_allowed():
        flash("Cadastro publico desativado. Contate o admin.", "error")
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or not password:
            flash("Preencha nome, email e senha.", "error")
            return render_template("register.html")
        if User.query.filter_by(email=email).first():
            flash("Email ja cadastrado.", "error")
            return render_template("register.html")
        user = User(email=email, name=name)
        try:
            user.set_password(password)
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template("register.html")
        db.session.add(user)
        db.session.commit()
        flash("Cadastro realizado. Faça login.", "success")
        return redirect(url_for("auth.login"))
    return render_template("register.html")


@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
