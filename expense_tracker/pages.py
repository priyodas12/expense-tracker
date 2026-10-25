from flask import Blueprint, render_template

bp = Blueprint("pages", __name__)


@bp.route("/terms-and-conditions")
def terms():
    return render_template("terms.html")


@bp.route("/privacy-policy")
def privacy():
    return render_template("privacy.html")
