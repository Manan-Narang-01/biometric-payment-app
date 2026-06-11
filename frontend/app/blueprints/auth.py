"""Auth blueprint: register, login, logout routes."""
from flask import Blueprint, render_template, redirect, url_for, session, request, jsonify, current_app
from app.api_client import api

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/register", methods=["GET"])
def register():
    if session.get("access_token"):
        return redirect(url_for("dashboard.index"))
    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET"])
def login():
    if session.get("access_token"):
        return redirect(url_for("dashboard.index"))
    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    access_token = session.get("access_token")
    if access_token:
        try:
            api.post("/api/v1/auth/logout", token=access_token)
        except Exception:
            pass
    session.clear()
    return redirect(url_for("auth.login"))


# ── Proxy endpoints for JavaScript WebAuthn flow ──────────

@auth_bp.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json()
    resp = api.post("/api/v1/auth/register", data)
    return jsonify(resp.json()), resp.status_code


@auth_bp.route("/api/webauthn/register/begin", methods=["POST"])
def api_webauthn_register_begin():
    data = request.get_json()
    resp = api.post("/api/v1/auth/webauthn/register/begin", data)
    return jsonify(resp.json()), resp.status_code


@auth_bp.route("/api/webauthn/register/complete", methods=["POST"])
def api_webauthn_register_complete():
    data = request.get_json()
    resp = api.post("/api/v1/auth/webauthn/register/complete", data)
    return jsonify(resp.json()), resp.status_code


@auth_bp.route("/api/webauthn/login/begin", methods=["POST"])
def api_webauthn_login_begin():
    data = request.get_json()
    resp = api.post("/api/v1/auth/webauthn/login/begin", data)
    return jsonify(resp.json()), resp.status_code


@auth_bp.route("/api/webauthn/login/complete", methods=["POST"])
def api_webauthn_login_complete():
    data = request.get_json()
    resp = api.post("/api/v1/auth/webauthn/login/complete", data)
    if resp.status_code == 200:
        body = resp.json()
        session["access_token"] = body["access_token"]
        session["refresh_token"] = body["refresh_token"]
        session["user"] = body["user"]
    return jsonify(resp.json()), resp.status_code
