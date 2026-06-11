"""Profile & security blueprint."""
from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request
from app.api_client import api
from app.blueprints.dashboard import login_required

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")


@profile_bp.route("/")
@login_required
def index():
    return render_template("profile/index.html", user=session.get("user"))


@profile_bp.route("/api/update", methods=["PUT"])
@login_required
def api_update():
    data = request.get_json()
    resp = api.put("/api/v1/users/me", data)
    if resp.status_code == 200:
        session["user"] = resp.json()
    return jsonify(resp.json()), resp.status_code


@profile_bp.route("/api/credentials")
@login_required
def api_credentials():
    resp = api.get("/api/v1/auth/webauthn/credentials")
    return jsonify(resp.json()), resp.status_code


@profile_bp.route("/api/credentials/<cid>", methods=["DELETE"])
@login_required
def api_delete_credential(cid):
    resp = api.delete(f"/api/v1/auth/webauthn/credentials/{cid}")
    return "", resp.status_code


@profile_bp.route("/api/devices")
@login_required
def api_devices():
    resp = api.get("/api/v1/security/devices")
    return jsonify(resp.json()), resp.status_code


@profile_bp.route("/api/devices/<did>", methods=["DELETE"])
@login_required
def api_delete_device(did):
    resp = api.delete(f"/api/v1/security/devices/{did}")
    return "", resp.status_code


@profile_bp.route("/api/security-logs")
@login_required
def api_security_logs():
    resp = api.get("/api/v1/security/logs")
    return jsonify(resp.json()), resp.status_code


@profile_bp.route("/api/bank-accounts", methods=["GET"])
@login_required
def api_bank_accounts():
    resp = api.get("/api/v1/bank-accounts/")
    return jsonify(resp.json()), resp.status_code


@profile_bp.route("/api/bank-accounts", methods=["POST"])
@login_required
def api_add_bank_account():
    data = request.get_json()
    resp = api.post("/api/v1/bank-accounts/", data)
    return jsonify(resp.json()), resp.status_code


@profile_bp.route("/api/bank-accounts/<aid>", methods=["DELETE"])
@login_required
def api_delete_bank_account(aid):
    resp = api.delete(f"/api/v1/bank-accounts/{aid}")
    return "", resp.status_code


@profile_bp.route("/api/webauthn/add/begin", methods=["POST"])
@login_required
def api_webauthn_add_begin():
    user = session.get("user", {})
    resp = api.post("/api/v1/auth/webauthn/register/begin", {"user_id": user.get("id")})
    return jsonify(resp.json()), resp.status_code


@profile_bp.route("/api/webauthn/add/complete", methods=["POST"])
@login_required
def api_webauthn_add_complete():
    data = request.get_json()
    user = session.get("user", {})
    data["user_id"] = user.get("id")
    resp = api.post("/api/v1/auth/webauthn/register/complete", data)
    return jsonify(resp.json()), resp.status_code
