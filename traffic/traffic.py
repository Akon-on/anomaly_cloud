import requests
import time
import random
import threading
import os
import json


TARGET = os.getenv("TARGET", "http://victim:5000")
LOGIN_ENDPOINT = "/login"
NORMAL_ENDPOINTS = ["/", "/health", "/api/items", "/search"]
SEARCH_TERMS = ["status", "billing", "profile", "logs", "dashboard"]
SCAN_ENDPOINTS = [
    "/admin",
    "/config",
    "/.env",
    "/wp-login.php",
    "/server-status",
    "/api/secrets",
]
USER_AGENTS = [
    "Mozilla/5.0 normal-browser",
    "curl/8.0 health-check",
    "python-requests/2.31 internal-client",
    "CloudMonitor/1.0",
    "MobileApp/4.2",
    "EdgeBrowser/121.0",
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
REQUESTS_PER_SECOND = max(1, REQUESTS_PER_SECOND)
THREADS = max(1, THREADS)

NORMAL_TRAFFIC_RATIO = float(os.getenv("NORMAL_TRAFFIC_RATIO", "0.3"))
NORMAL_LOGIN_RATIO = float(os.getenv("NORMAL_LOGIN_RATIO", "0.10"))
NORMAL_LOGIN_FAILURE_RATE = float(os.getenv("NORMAL_LOGIN_FAILURE_RATE", "0.05"))
NORMAL_TRAFFIC_RATIO = min(1.0, max(0.0, NORMAL_TRAFFIC_RATIO))
NORMAL_LOGIN_RATIO = min(1.0, max(0.0, NORMAL_LOGIN_RATIO))
NORMAL_LOGIN_FAILURE_RATE = min(1.0, max(0.0, NORMAL_LOGIN_FAILURE_RATE))
RANDOM_SEED = int(os.getenv("RANDOM_SEED", "42"))
SCENARIO_NAME = os.getenv("SCENARIO_NAME", "adhoc")
LABEL_FILE = os.getenv("LABEL_FILE", "/logs/traffic_labels.jsonl")
WARMUP_SECONDS = int(os.getenv("WARMUP_SECONDS", "20"))
COOLDOWN_SECONDS = int(os.getenv("COOLDOWN_SECONDS", "20"))
COMPROMISED_USERS = ["admin", "ops", "dev", "billing", "support"]
LEAKED_PASSWORDS = ["admin123", "password1", "welcome1", "letmein", "qwerty123"]
SUPPORTED_ATTACK_STYLES = {
    "brute_force",
    "credential_stuffing",
    "slow_brute_force",
    "endpoint_scanning",
    "burst_traffic",
    "mixed",
}

label_lock = threading.Lock()


def write_label_event(label, worker_id, client_ip, endpoint, attack_style=None):
    event = {
        "time": time.time(),
        "label": label,
        "worker_id": worker_id,
        "scenario": SCENARIO_NAME,
        "client_ip": client_ip,
        "endpoint": endpoint,
    }
    if attack_style:
        event["attack_style"] = attack_style

    with label_lock:
        with open(LABEL_FILE, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(event) + "\n")


def request_headers(client_ip, rng):
    return {
        "X-Forwarded-For": client_ip,
        "User-Agent": rng.choice(USER_AGENTS),
    }


def normal_request(worker_id, rng):
    endpoint = LOGIN_ENDPOINT if rng.random() < NORMAL_LOGIN_RATIO else rng.choice(NORMAL_ENDPOINTS)
    client_ip = rng.choice(NORMAL_IPS)
    headers = request_headers(client_ip, rng)

    try:
        if endpoint == "/search":
            requests.get(
                TARGET + endpoint,
                params={"q": rng.choice(SEARCH_TERMS)},
                headers=headers,
                timeout=1,
            )
        elif endpoint == LOGIN_ENDPOINT:
            password = "admin" if rng.random() > NORMAL_LOGIN_FAILURE_RATE else "typo"
            requests.post(
                TARGET + endpoint,
                data={"username": rng.choice(COMPROMISED_USERS), "password": password},
                headers=headers,
                timeout=1,
            )
        else:
            requests.get(TARGET + endpoint, headers=headers, timeout=1)

        write_label_event("normal", worker_id, client_ip, endpoint)
    except requests.RequestException:
        pass


def login_attack_request(worker_id, rng, attack_style):
    client_ip = rng.choice(ATTACK_IPS)
    username = "admin"
    password = str(rng.randint(1000, 9999))

    if attack_style == "credential_stuffing":
        username = rng.choice(COMPROMISED_USERS)
        password = rng.choice(LEAKED_PASSWORDS)

    try:
        requests.post(
            TARGET + LOGIN_ENDPOINT,
            data={
                "username": username,
                "password": password,
            },
            headers=request_headers(client_ip, rng),
            timeout=1
        )
        write_label_event("attack", worker_id, client_ip, LOGIN_ENDPOINT, attack_style)
    except requests.RequestException:
        pass


def endpoint_scanning_request(worker_id, rng):
    client_ip = rng.choice(ATTACK_IPS)
    endpoint = rng.choice(SCAN_ENDPOINTS)
    try:
        requests.get(
            TARGET + endpoint,
            headers=request_headers(client_ip, rng),
            timeout=1,
        )
        write_label_event("attack", worker_id, client_ip, endpoint, "endpoint_scanning")
    except requests.RequestException:
        pass


def burst_traffic_request(worker_id, rng):
    client_ip = rng.choice(ATTACK_IPS)
    burst_size = rng.randint(2, 5)
    for _ in range(burst_size):
        endpoint = rng.choice(NORMAL_ENDPOINTS)
        headers = request_headers(client_ip, rng)
        try:
            if endpoint == "/search":
                requests.get(
                    TARGET + endpoint,
                    params={"q": rng.choice(SEARCH_TERMS)},
                    headers=headers,
                    timeout=1,
                )
            else:
                requests.get(TARGET + endpoint, headers=headers, timeout=1)

            write_label_event("attack", worker_id, client_ip, endpoint, "burst_traffic")
        except requests.RequestException:
            pass


def attack_request(worker_id, rng):
    attack_style = ATTACK_STYLE
    if attack_style not in SUPPORTED_ATTACK_STYLES:
        attack_style = "brute_force"

    if attack_style == "mixed":
        attack_style = rng.choice(
            [
                "brute_force",
                "credential_stuffing",
                "slow_brute_force",
                "endpoint_scanning",
                "burst_traffic",
            ]
        )

    if attack_style == "endpoint_scanning":
        endpoint_scanning_request(worker_id, rng)
        return 1.0

    if attack_style == "burst_traffic":
        burst_traffic_request(worker_id, rng)
        return 0.5

    if attack_style == "slow_brute_force":
        login_attack_request(worker_id, rng, attack_style)
        return rng.uniform(2.5, 4.0)

    login_attack_request(worker_id, rng, attack_style)
    return 1.0


def attack_worker(worker_id):
    rng = random.Random(RANDOM_SEED + worker_id)
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
            if rng.random() < normal_ratio:
                normal_request(worker_id, rng)
                delay_multiplier = 1.0
            else:
                delay_multiplier = attack_request(worker_id, rng)

            jitter = rng.uniform(0.75, 1.25)
            time.sleep((1 / REQUESTS_PER_SECOND) * jitter * delay_multiplier)

        print(f"[Worker {worker_id}] phase completed: {phase_name}")

    print(f"[Worker {worker_id}] finished")



if __name__ == "__main__":
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
            "normal_login_ratio": NORMAL_LOGIN_RATIO,
            "normal_login_failure_rate": NORMAL_LOGIN_FAILURE_RATE,
            "attack_style": ATTACK_STYLE,
        }
        handle.write(json.dumps(metadata) + "\n")

    print("Starting controlled normal/attack traffic simulation")
    print(f"Target: {TARGET}")
    print(
        "Phases: "
        f"warmup={WARMUP_SECONDS}s, "
        f"attack={ATTACK_DURATION}s, "
        f"cooldown={COOLDOWN_SECONDS}s"
    )
    print(f"Attack style: {ATTACK_STYLE}")
    print(f"Supported styles: {', '.join(sorted(SUPPORTED_ATTACK_STYLES))}")
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
