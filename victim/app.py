from flask import Flask, request
import logging, json, time

app = Flask(__name__)

logging.basicConfig(
    filename="/logs/access.log",
    level=logging.INFO,
    format="%(message)s",
    force=True,
)

def client_ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr)


def write_access_log(endpoint, status):
    log = {
        "time": time.time(),
        "ip": client_ip(),
        "endpoint": endpoint,
        "status": status,
        "method": request.method,
        "user_agent": request.headers.get("User-Agent", "unknown")
    }
    logging.info(json.dumps(log))


@app.route("/")
def index():
    write_access_log("/", "ok")
    return "Victim service running"


@app.route("/health")
def health():
    write_access_log("/health", "ok")
    return {"status": "ok"}


@app.route("/api/items")
def api_items():
    write_access_log("/api/items", "ok")
    return {"items": ["alpha", "beta", "gamma"]}


@app.route("/search")
def search():
    write_access_log("/search", "ok")
    return {"query": request.args.get("q", ""), "results": []}


@app.route("/login", methods=["POST"])
def login():
    status = "fail"
    if request.form.get("password") == "admin":
        status = "success"

    write_access_log("/login", status)
    return "login attempt logged"

app.run(host="0.0.0.0", port=5000)
