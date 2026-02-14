"""Authentication routes -- login, register, logout."""
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db, login_manager
from app.models.user_account import UserAccount

auth_bp = Blueprint("auth", __name__)


@login_manager.user_loader
def load_user(user_id):
    return UserAccount.query.get(int(user_id))


@auth_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("game.sessions"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("game.sessions"))
    return render_template("login.html")


@auth_bp.route("/login", methods=["POST"])
def login_post():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if not username or not password:
        flash("Username and password are required.", "error")
        return render_template("login.html"), 400

    user = UserAccount.query.filter_by(username=username).first()
    if user is None or not user.check_password(password):
        flash("Invalid username or password.", "error")
        return render_template("login.html"), 401

    login_user(user)
    return redirect(url_for("game.sessions"))


@auth_bp.route("/register", methods=["GET"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("game.sessions"))
    return render_template("login.html", register=True)


@auth_bp.route("/register", methods=["POST"])
def register_post():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if not username or not password:
        flash("Username and password are required.", "error")
        return render_template("login.html", register=True), 400

    if len(username) < 3 or len(username) > 64:
        flash("Username must be between 3 and 64 characters.", "error")
        return render_template("login.html", register=True), 400

    if len(password) < 4:
        flash("Password must be at least 4 characters.", "error")
        return render_template("login.html", register=True), 400

    existing = UserAccount.query.filter_by(username=username).first()
    if existing is not None:
        flash("Username is already taken.", "error")
        return render_template("login.html", register=True), 409

    user = UserAccount(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    login_user(user)
    return redirect(url_for("game.sessions"))


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
