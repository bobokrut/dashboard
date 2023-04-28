from flask import request, redirect, Blueprint, render_template, url_for, flash
from flask_login import login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.wrappers.response import Response
from flask_login import LoginManager, UserMixin

from typing import Any

user = Blueprint("user", __name__)
login_manager: LoginManager = LoginManager()


class User(UserMixin):
    def __init__(self, id: int, username: str, password: str) -> None:
        self.id = id
        self.username = username
        self.password = password

    def get_id(self) -> int:
        return self.id

    def check_password(self, password: str) -> bool:
        return self.password == password

users = {
    1: User(id=1, username="admin", password="admin"),
}


@user.route("/signup", methods=["POST"])
def signup_post() -> Response:
    email: str = request.form.get("email")  # type: ignore
    username: str = request.form.get("username")  # type: ignore
    password: str = request.form.get("password")  # type: ignore

    new_user = User(
        email=email,
        username=username,
        password=generate_password_hash(password, method="sha256"),
    )
    db.session.add(new_user)
    db.session.commit()

    return redirect(url_for("user.login_get"))


@user.route("/signup", methods=["GET"])
def signup_get() -> str:
    return render_template("signup.html")


@user.route("/login", methods=["POST"])
def login_post() -> Response:
    username: str = request.form.get("username")  # type: ignore
    password: str = request.form.get("password")  # type: ignore
    remember: str = request.form.get("remember")

    if username != "123" or password != "123":
        flash("Please check your login details and try again.")
        return redirect(url_for("user.login_get"))

    login_user(user, remember=remember)
    return redirect(url_for("gallery.view_gallery"))


@user.route("/login", methods=["GET"])
def login_get() -> str:
    return render_template("login.html")


@user.route("/logout")
@login_required
def logout() -> Response:
    logout_user()
    return redirect(url_for("user.login_get"))


@login_manager.user_loader
def load_user(user_id: int) -> Any:
    return users.get(int(user_id))
