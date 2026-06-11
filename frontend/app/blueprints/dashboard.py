"""Dashboard blueprint."""
from functools import wraps
from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request
from app.api_client import api

dashboard_bp = Blueprint("dashboard", __name__)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("access_token"):
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


@dashboard_bp.route("/")
@login_required
def index():
    return render_template("dashboard/index.html", user=session.get("user"))


@dashboard_bp.route("/dashboard/api/wallet")
@login_required
def api_wallet():
    resp = api.get("/api/v1/wallet/")
    return jsonify(resp.json()), resp.status_code


@dashboard_bp.route("/dashboard/api/transactions")
@login_required
def api_transactions():
    page = request.args.get("page", 1)
    page_size = request.args.get("page_size", 20)
    resp = api.get("/api/v1/transactions/", params={"page": page, "page_size": page_size})
    return jsonify(resp.json()), resp.status_code


@dashboard_bp.route("/dashboard/api/analytics")
@login_required
def api_analytics():
    resp = api.get("/api/v1/wallet/analytics")
    return jsonify(resp.json()), resp.status_code
