from flask import Flask, request
import logging, json, time

app = Flask(__name__)

logging.basicConfig(
    filename="/logs/access.log",
    level=logging.INFO,
    format="%(message)s"
)

@app.route("/")
def index():
    log = {
        "time": time.time(),
        "ip": request.remote_addr,
        "endpoint": "/",
        "status": "ok"
    }
    logging.info(json.dumps(log))
    return "Victim service running"

@app.route("/login", methods=["POST"])
def login():
    status = "fail"
    if request.form.get("password") == "admin":
        status = "success"

    log = {
        "time": time.time(),
        "ip": request.remote_addr,
        "endpoint": "/login",
        "status": status
    }
    logging.info(json.dumps(log))
    return "login attempt logged"

app.run(host="0.0.0.0", port=5000)
