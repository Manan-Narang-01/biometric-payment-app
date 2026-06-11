"""Payment blueprint."""
from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request
from app.api_client import api
from app.blueprints.dashboard import login_required

payment_bp = Blueprint("payment", __name__, url_prefix="/payment")


@payment_bp.route("/send")
@login_required
def send():
    return render_template("payment/send.html", user=session.get("user"))


@payment_bp.route("/receive")
@login_required
def receive():
    return render_template("payment/receive.html", user=session.get("user"))


@payment_bp.route("/api/transfer", methods=["POST"])
@login_required
def api_transfer():
    data = request.get_json()
    resp = api.post("/api/v1/transactions/transfer", data)
    return jsonify(resp.json()), resp.status_code


@payment_bp.route("/api/qr-generate", methods=["POST"])
@login_required
def api_qr_generate():
    data = request.get_json()
    resp = api.post("/api/v1/wallet/qr", data)
    return jsonify(resp.json()), resp.status_code


@payment_bp.route("/api/qr-pay", methods=["POST"])
@login_required
def api_qr_pay():
    data = request.get_json()
    resp = api.post("/api/v1/transactions/qr-pay", data)
    return jsonify(resp.json()), resp.status_code


@payment_bp.route("/api/search-users")
@login_required
def api_search_users():
    q = request.args.get("q", "")
    resp = api.get("/api/v1/users/search", params={"q": q})
    return jsonify(resp.json()), resp.status_code
