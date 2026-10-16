#!/usr/bin/env python3
"""
CareerLens ML Service Acceptance Verification Script:
Verifies the acceptance criteria specified in user prompt:
1. Builds and starts the container with dataset mounted.
2. Waits for /health to return 200 (model and embeddings loaded).
3. Calls /recommend with Bearer JWT and verifies 3 results.
4. Dislikes one result via /feedback (stores constraints in Redis under feedback:{user_id}).
5. Restarts the container (docker restart).
6. Waits for /health to return 200 again.
7. Calls /recommend again and confirms the disliked internship is still excluded.
8. Cleans up test containers.
"""

import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

# Setup paths and environment
repo_root = Path(__file__).resolve().parent.parent.parent
ml_dir = repo_root / "services" / "ml"
data_dir = repo_root / "data"

sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(ml_dir))

os.environ.setdefault(
    "JWT_SECRET", "acceptance_test_secret_for_careerlens_ml_at_least_32_chars"
)
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "60")

from services.common.jwt_auth import create_access_token
import httpx

NETWORK_NAME = "careerlens-acceptance-net"
REDIS_CONTAINER = "careerlens-acceptance-redis"
ML_CONTAINER = "careerlens-acceptance-ml"
HOST_PORT = 8009


def run_cmd(cmd, check=True):
    print(f"--> {cmd}", flush=True)
    res = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and res.returncode != 0:
        print(f"Command failed (exit {res.returncode}):", flush=True)
        print("STDOUT:", res.stdout, flush=True)
        print("STDERR:", res.stderr, flush=True)
        raise RuntimeError(f"Command failed: {cmd}")
    return res


def cleanup():
    print("\n--- Cleaning up acceptance containers and network ---", flush=True)
    run_cmd(f"docker rm -f {ML_CONTAINER}", check=False)
    run_cmd(f"docker rm -f {REDIS_CONTAINER}", check=False)
    run_cmd(f"docker network rm {NETWORK_NAME}", check=False)


def wait_for_health(url: str, timeout: int = 60):
    print(f"Waiting for {url} to become healthy (HTTP 200)...", flush=True)
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = httpx.get(url, timeout=3.0)
            if resp.status_code == 200:
                print(f"Container is ready! /health returned 200: {resp.json()}", flush=True)
                return True
        except Exception:
            pass
        time.sleep(2)
    raise TimeoutError(f"Timed out waiting for {url} to become healthy.")


def run_acceptance():
    print("==================================================", flush=True)
    print("CareerLens ML Service - Container Acceptance Test", flush=True)
    print("==================================================", flush=True)

    cleanup()

    try:
        # 1. Create docker network
        print("\n[1/8] Creating test Docker network...", flush=True)
        run_cmd(f"docker network create {NETWORK_NAME}")

        # 2. Start Redis container
        print("\n[2/8] Starting isolated Redis container...", flush=True)
        run_cmd(
            f"docker run -d --name {REDIS_CONTAINER} --network {NETWORK_NAME} redis:7-alpine"
        )

        # 3. Build ML image
        print("\n[3/8] Building careerlens-ml Docker image...", flush=True)
        run_cmd(f"docker build -t careerlens-ml-test {ml_dir}")

        # 4. Start ML container with mounted dataset
        print("\n[4/8] Starting careerlens-ml container with dataset mounted...", flush=True)
        mount_data = str(data_dir.resolve()).replace("\\", "/")
        run_cmd(
            f'docker run -d --name {ML_CONTAINER} '
            f'--network {NETWORK_NAME} '
            f'-p {HOST_PORT}:8000 '
            f'-v "{mount_data}":/app/data '
            f'-e DATASET_PATH=/app/data/Book2.xlsx '
            f'-e REDIS_URL=redis://{REDIS_CONTAINER}:6379/0 '
            f'-e JWT_SECRET={os.environ["JWT_SECRET"]} '
            f'careerlens-ml-test'
        )

        # 5. Wait for /health
        base_url = f"http://localhost:{HOST_PORT}"
        wait_for_health(f"{base_url}/health", timeout=90)

        # 6. Call /recommend
        user_email = f"acceptance_user_{uuid.uuid4().hex[:6]}@careerlens.local"
        token = create_access_token(user_email)
        headers = {"Authorization": f"Bearer {token}"}

        print(f"\n[5/8] Requesting recommendations for {user_email}...", flush=True)
        resp = httpx.post(
            f"{base_url}/recommend",
            headers=headers,
            json={
                "skills": ["Python", "Machine Learning", "FastAPI"],
                "education": "Computer Science",
            },
            timeout=15.0,
        )
        assert resp.status_code == 200, f"Recommend failed: {resp.text}"
        recs = resp.json()
        print(f"      Received {len(recs)} recommendations.", flush=True)
        assert len(recs) == 3, f"Expected 3 recommendations, got {len(recs)}"

        disliked = recs[0]
        disliked_id = str(disliked["id"])
        disliked_title = disliked.get("title", "Untitled")
        print(f"      Selected internship to dislike: ID={disliked_id} ('{disliked_title}')", flush=True)

        # 7. Dislike via /feedback
        print(f"\n[6/8] Submitting feedback: disliking internship {disliked_id}...", flush=True)
        fb_resp = httpx.post(
            f"{base_url}/feedback",
            headers=headers,
            json={
                "internship_id": disliked_id,
                "reason": "location_not_suitable",
                "metadata": {"location": disliked.get("location", "")},
            },
            timeout=10.0,
        )
        assert fb_resp.status_code == 200, f"Feedback failed: {fb_resp.text}"
        fb_data = fb_resp.json()
        assert fb_data["status"] == "success"
        assert disliked_id in fb_data["active_constraints"]["exclude_ids"]
        print(f"      Feedback recorded. Excluded IDs in constraints: {fb_data['active_constraints']['exclude_ids']}", flush=True)

        # 8. Restart container
        print(f"\n[7/8] Restarting container {ML_CONTAINER}...", flush=True)
        run_cmd(f"docker restart {ML_CONTAINER}")
        wait_for_health(f"{base_url}/health", timeout=60)

        # 9. Request recommendations again and verify exclusion
        print(f"\n[8/8] Requesting recommendations again for {user_email} after container restart...", flush=True)
        resp_after = httpx.post(
            f"{base_url}/recommend",
            headers=headers,
            json={
                "skills": ["Python", "Machine Learning", "FastAPI"],
                "education": "Computer Science",
            },
            timeout=15.0,
        )
        assert resp_after.status_code == 200, f"Recommend after restart failed: {resp_after.text}"
        recs_after = resp_after.json()
        assert len(recs_after) == 3, f"Expected 3 recommendations, got {len(recs_after)}"

        after_ids = [str(r["id"]) for r in recs_after]
        print(f"      New recommendation IDs: {after_ids}", flush=True)
        assert disliked_id not in after_ids, (
            f"FAILED: Disliked ID {disliked_id} was STILL present in recommendations after container restart!"
        )
        print(f"      SUCCESS: Disliked ID {disliked_id} is properly excluded after container restart!", flush=True)

        print("\n==================================================", flush=True)
        print("ACCEPTANCE TEST PASSED SUCCESSFULLY!", flush=True)
        print("==================================================", flush=True)

    finally:
        cleanup()


if __name__ == "__main__":
    run_acceptance()
