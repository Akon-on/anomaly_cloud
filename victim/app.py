import json
import logging
import time

from flask import Flask, g, request

app = Flask(__name__)

logging.basicConfig(
    filename="/logs/access.log",
    level=logging.INFO,
    format="%(message)s",
    force=True,
)

def client_ip():
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.remote_addr


def write_access_log(endpoint, status, status_code):
    log = {
        "time": time.time(),
        "ip": client_ip(),
        "endpoint": endpoint,
        "status": status,
        "status_code": status_code,
        "method": request.method,
        "user_agent": request.headers.get("User-Agent", "unknown"),
    }
    logging.info(json.dumps(log))


@app.after_request
def log_request(response):
    status = getattr(g, "access_status", None)
    if status is None:
        status = "ok" if response.status_code < 400 else f"error_{response.status_code}"
    write_access_log(request.path, status, response.status_code)
    return response


@app.route("/")
def index():
    return "Victim service running"


@app.route("/health")
def health():
    return {"status": "ok"}


@app.route("/api/items")
def api_items():
    return {"items": ["alpha", "beta", "gamma"]}


@app.route("/search")
def search():
    return {"query": request.args.get("q", ""), "results": []}


@app.route("/login", methods=["POST"])
def login():
    status = "fail"
    if request.form.get("password") == "admin":
        status = "success"

    g.access_status = status
    return "login attempt logged"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
