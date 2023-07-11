from logging import getLogger
from typing import Any

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user
from werkzeug.wrappers.response import Response

auth = Blueprint("auth", __name__)
login_manager: LoginManager = LoginManager()
logger = getLogger("dash_app")


class User(UserMixin):
    def __init__(self, id: int, username: str, password: str) -> None:
        self.id = id
        self.username = username
        self.password = password

    def get_id(self) -> str:
        return self.username

    def check_password(self, password: str) -> bool:
        return self.password == password


users: dict[str, User] = {
    "example6@email.com": User(
        id=1, username="example6@email.com", password="password123"
    ),
}


@auth.route("/login", methods=["POST"])
def login_post() -> Response:
    username: str = request.form.get("username")  # type: ignore
    password: str = request.form.get("password")  # type: ignore
    # remember: str = request.form.get("remember")

    if not username or username not in users:
        flash("No such user")
        logger.info(f"No such user: {username}")
        return redirect(url_for("auth.login_get"))

    if not users[username].check_password(password):
        flash("Please check your login details and try again.")
        logger.info(f"Wrong password for user {username}")
        return redirect(url_for("auth.login_get"))

    user = users.get(username)
    login_user(user, remember=True)
    logger.info(f"User {username} logged in")
    return redirect("/dash/")


@auth.route("/login", methods=["GET"])
def login_get() -> str:
    return render_template("login.html")


@auth.route("/logout")
@login_required
def logout() -> Response:
    logout_user()
    return redirect(url_for("auth.login_get"))


@login_manager.user_loader
def load_user(username: str) -> Any:
    return users.get(username)
