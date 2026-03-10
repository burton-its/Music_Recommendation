"""Flask app for music recommendations with auth microservice integration."""

from flask import Flask, request, redirect, render_template, url_for, session, jsonify, make_response
import requests
import re
from config import Config
from recommender import load_artifacts, recommend

app = Flask(__name__)
app.config.from_object(Config)

ARTIFACTS = None
REQUEST_TIMEOUT_SECONDS = 5


def _safe_post_json(url, payload):
    """Call an HTTP endpoint and return (ok, data_or_error_message, response)."""
    try:
        resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException:
        return False, "Service unavailable. Please try again.", None

    if 200 <= resp.status_code < 300:
        try:
            return True, resp.json(), resp
        except ValueError:
            return True, None, resp

    try:
        err_payload = resp.json()
        detail = err_payload.get("detail") or err_payload.get("error")
    except ValueError:
        detail = None
    return False, detail or f"Request failed ({resp.status_code}).", resp

# login route
@app.route("/")
@app.route("/login", methods=["GET", "POST"])
def login():
    """Render login form and authenticate users on POST.
    """
    msg = ""
    if request.method == "POST" and "email" in request.form and "password" in request.form:
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        auth_ok, auth_result, auth_resp = _safe_post_json(
            f"{app.config['AUTH_SERVICE_URL']}/auth/login",
            {"email": email, "password": password},
        )
        if not auth_ok:
            return render_template("login.html", msg=f"Login failed: {auth_result}")

        token = auth_resp.cookies.get("access_token") if auth_resp else None
        if not token:
            return render_template("login.html", msg="Login failed: missing access token.")

        validator_ok, validator_result, _ = _safe_post_json(
            f"{app.config['VALIDATOR_SERVICE_URL']}/validate-token",
            {"token": token},
        )
        if not validator_ok:
            return render_template("login.html", msg=f"Token validation failed: {validator_result}")

        if validator_result is not True:
            return render_template("login.html", msg="Token validation failed.")

        session["loggedin"] = True
        session["email"] = email
        response = make_response(render_template("index.html", msg="Logged in successfully!"))
        response.set_cookie(
            "access_token",
            token,
            httponly=True,
            secure=False,
            samesite="Lax",
            max_age=app.config["ACCESS_TOKEN_EXPIRE_SECONDS"],
        )
        return response

    return render_template("login.html", msg=msg)

# logout
@app.route("/logout")
def logout():
    """Clear session and redirect to login.
    """
    token = request.cookies.get("access_token")
    if token:
        _safe_post_json(
            f"{app.config['LOGOUT_SERVICE_URL']}/revoke",
            {"token": token, "reason": "user_logout"},
        )

    session.clear()
    response = make_response(redirect(url_for("login")))
    response.delete_cookie("access_token")
    return response

# register route
@app.route("/register", methods=["GET", "POST"])
def register():
    """Render registration form and create a new user on POST."""
    msg = ""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password_raw = request.form.get("password", "")
        # verification/auth
        if not email or not password_raw:
            return render_template("register.html", msg="Please fill out the form!")

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return render_template("register.html", msg="Invalid email address!")

        reg_ok, reg_result, _ = _safe_post_json(
            f"{app.config['AUTH_SERVICE_URL']}/auth/register",
            {"email": email, "password": password_raw},
        )
        if not reg_ok:
            return render_template("register.html", msg=f"Registration failed: {reg_result}")

        return redirect(url_for("login"))

    return render_template("register.html", msg=msg)

# preferences route
@app.route("/preferences")
def preferences():
    if not session.get("loggedin"):
        return redirect(url_for("login"))
    return render_template("preferences.html")

# recommendations route
@app.route("/recommendations", methods=["POST"])
def recommendations():
    if not session.get("loggedin"):
        return jsonify({"error": "auth required"}), 401

    data = request.get_json(silent=True) or {}

    
    genres = data.get("genres") or None
    k = int(data.get("k", 1)) 

    try:
        global ARTIFACTS
        if ARTIFACTS is None:

            ARTIFACTS = load_artifacts("music_dataset.csv")

        # recommend
        recs = recommend(
            artifacts=ARTIFACTS,
            genres=genres,
            k=k,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    if recs.empty:
        return jsonify({"error": "No recommendations found"}), 404

    #return one rec
    row0 = recs.iloc[0]
    return jsonify({
        "artist": row0.get("artists"),
        "title": row0.get("track_name"),
    })


if __name__ == "__main__":
    app.run(debug=True)
