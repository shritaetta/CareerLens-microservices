import os
import sys
import time
import json
import urllib.request
import urllib.error
import subprocess

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost").rstrip("/")

def log(msg: str):
    print(msg, flush=True)

def request_json(url: str, method: str = "GET", data: dict = None, headers: dict = None):
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            code = resp.status
            content = resp.read().decode("utf-8")
            try:
                res_json = json.loads(content)
            except Exception:
                res_json = content
            return code, res_json
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        try:
            res_json = json.loads(content)
        except Exception:
            res_json = content
        return e.code, res_json
    except Exception as e:
        return 0, str(e)

def main():
    log("==========================================")
    log("CareerLens Microservices Stack Smoke Test")
    log("==========================================")

    # 1. Bring stack up
    if os.environ.get("SKIP_COMPOSE", "false").lower() != "true":
        log("[STEP 1] Bringing stack up with docker compose...")
        compose_cmd = ["docker", "compose", "up", "-d", "--build"]
        ret = subprocess.run(compose_cmd)
        if ret.returncode != 0:
            log("[FAIL] Step 1: docker compose up --build failed")
            sys.exit(1)
    else:
        log("[STEP 1] Skipping docker compose up (SKIP_COMPOSE=true)...")

    log("Waiting for microservices to report healthy...")
    endpoints = {
        "Gateway": f"{GATEWAY_URL}/gateway-health",
        "Auth": f"{GATEWAY_URL}/api/auth/health",
        "Profile": f"{GATEWAY_URL}/api/profile/health",
        "Files": f"{GATEWAY_URL}/api/files/health",
        "ML": f"{GATEWAY_URL}/api/ml/health",
    }

    max_retries = 50
    ready = False
    for i in range(1, max_retries + 1):
        statuses = {}
        all_ok = True
        for name, ep in endpoints.items():
            code, _ = request_json(ep)
            statuses[name] = code
            if code != 200:
                all_ok = False
        if all_ok:
            ready = True
            break
        log(f"Waiting for services to become ready... (attempt {i}/{max_retries}) {statuses}")
        time.sleep(3)

    if not ready:
        log("[FAIL] Step 1: Services failed to become healthy within timeout")
        sys.exit(1)
    log("[PASS] Step 1: Stack is up and healthy")

    # 2. Signup
    ts = int(time.time() * 1000)
    email = f"smoke_{ts}@example.com"
    password = "SmokeTestPassword123!"
    full_name = "Smoke Test User"

    log(f"[STEP 2] Signing up user {email}...")
    signup_url = f"{GATEWAY_URL}/api/auth/signup"
    code, res = request_json(signup_url, method="POST", data={
        "full_name": full_name,
        "email": email,
        "password": password
    })
    if code == 200 and isinstance(res, dict) and res.get("status") == "success":
        log("[PASS] Step 2: User signup succeeded")
    else:
        log(f"[FAIL] Step 2: User signup failed (HTTP {code}, Response: {res})")
        sys.exit(1)

    # 3. Login
    log(f"[STEP 3] Logging in as {email}...")
    login_url = f"{GATEWAY_URL}/api/auth/login"
    code, res = request_json(login_url, method="POST", data={
        "email": email,
        "password": password
    })
    if code == 200 and isinstance(res, dict) and res.get("access_token"):
        token = res["access_token"]
        user_id = res.get("user_id", email)
        log("[PASS] Step 3: User login succeeded (JWT obtained)")
    else:
        log(f"[FAIL] Step 3: User login failed (HTTP {code}, Response: {res})")
        sys.exit(1)

    # 4. Save Profile
    log(f"[STEP 4] Saving profile for {user_id}...")
    profile_url = f"{GATEWAY_URL}/api/profile/{user_id}"
    code, res = request_json(
        profile_url,
        method="POST",
        headers={"Authorization": f"Bearer {token}"},
        data={
            "personalDetails": {"firstName": "Smoke", "lastName": "Tester"},
            "skills": ["Python", "Docker", "FastAPI", "Machine Learning"],
            "education": {"graduation": {"institute": "Tech University", "board": "B.Tech"}},
            "achievements": "Built scalable cloud systems",
            "resumeText": "Experienced developer with Python, Docker, ML"
        }
    )
    if code == 200 and isinstance(res, dict) and res.get("status") == "success":
        log("[PASS] Step 4: Save profile succeeded")
    else:
        log(f"[FAIL] Step 4: Save profile failed (HTTP {code}, Response: {res})")
        sys.exit(1)

    # 5. Call /api/ml/recommend
    log("[STEP 5] Calling /api/ml/recommend...")
    ml_url = f"{GATEWAY_URL}/api/ml/recommend"
    code, res = request_json(
        ml_url,
        method="POST",
        headers={"Authorization": f"Bearer {token}"},
        data={
            "skills": ["Python", "Machine Learning"],
            "education": "Tech University, B.Tech",
            "achievements": "Built scalable cloud systems",
            "resume_text": "Experienced developer"
        }
    )
    if code == 200 and isinstance(res, list) and len(res) > 0:
        log(f"[PASS] Step 5: Recommendations retrieved ({len(res)} recommendations returned)")
    else:
        log(f"[FAIL] Step 5: Recommendations call failed (HTTP {code}, Response: {res})")
        sys.exit(1)

    log("==========================================")
    log("All smoke test steps PASSED successfully!")
    log("==========================================")

if __name__ == "__main__":
    main()
