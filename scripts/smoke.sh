#!/usr/bin/env bash
set -euo pipefail

GATEWAY_URL="${GATEWAY_URL:-http://localhost}"

echo "=========================================="
echo "CareerLens Microservices Stack Smoke Test"
echo "=========================================="

# 1. Bring stack up if not already running
if [ "${SKIP_COMPOSE:-false}" != "true" ]; then
  echo "[STEP 1] Bringing stack up with docker compose..."
  docker compose up -d --build
else
  echo "[STEP 1] Skipping docker compose up (SKIP_COMPOSE=true)..."
fi

echo "Waiting for all microservices to report healthy..."
MAX_RETRIES=40
READY=false
for i in $(seq 1 $MAX_RETRIES); do
  GW_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY_URL/gateway-health" || true)
  AUTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY_URL/api/auth/health" || true)
  PROF_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY_URL/api/profile/health" || true)
  FILES_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY_URL/api/files/health" || true)
  ML_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY_URL/api/ml/health" || true)

  if [ "$GW_STATUS" = "200" ] && [ "$AUTH_STATUS" = "200" ] && [ "$PROF_STATUS" = "200" ] && [ "$FILES_STATUS" = "200" ] && [ "$ML_STATUS" = "200" ]; then
    READY=true
    break
  fi
  echo "Waiting for services to become ready... (attempt $i/$MAX_RETRIES) [GW:$GW_STATUS, Auth:$AUTH_STATUS, Prof:$PROF_STATUS, Files:$FILES_STATUS, ML:$ML_STATUS]"
  sleep 3
done

if [ "$READY" = "true" ]; then
  echo "[PASS] Step 1: Stack is up and healthy"
else
  echo "[FAIL] Step 1: Services failed to report healthy in time"
  exit 1
fi

TIMESTAMP=$(date +%s%N 2>/dev/null || date +%s)
EMAIL="smoke_${TIMESTAMP}@example.com"
PASSWORD="SmokeTestPassword123!"
FULL_NAME="Smoke Test User"

# 2. Signup
echo "[STEP 2] Signing up new user ($EMAIL)..."
SIGNUP_PAYLOAD=$(printf '{"full_name":"%s","email":"%s","password":"%s"}' "$FULL_NAME" "$EMAIL" "$PASSWORD")
SIGNUP_RES=$(curl -s -w "\n%{http_code}" -X POST "$GATEWAY_URL/api/auth/signup" \
  -H "Content-Type: application/json" \
  -d "$SIGNUP_PAYLOAD")

SIGNUP_BODY=$(printf '%s\n' "$SIGNUP_RES" | sed '$d')
SIGNUP_CODE=$(printf '%s\n' "$SIGNUP_RES" | tail -n 1)

if [ "$SIGNUP_CODE" = "200" ] && printf '%s\n' "$SIGNUP_BODY" | grep -q '"status"[[:space:]]*:[[:space:]]*"success"'; then
  echo "[PASS] Step 2: User signup succeeded"
else
  echo "[FAIL] Step 2: User signup failed (HTTP $SIGNUP_CODE, Response: $SIGNUP_BODY)"
  exit 1
fi

# 3. Login
echo "[STEP 3] Logging in as user ($EMAIL)..."
LOGIN_PAYLOAD=$(printf '{"email":"%s","password":"%s"}' "$EMAIL" "$PASSWORD")
LOGIN_RES=$(curl -s -w "\n%{http_code}" -X POST "$GATEWAY_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "$LOGIN_PAYLOAD")

LOGIN_BODY=$(printf '%s\n' "$LOGIN_RES" | sed '$d')
LOGIN_CODE=$(printf '%s\n' "$LOGIN_RES" | tail -n 1)

TOKEN=$(printf '%s\n' "$LOGIN_BODY" | python -c "import sys, json; data=json.load(sys.stdin); print(data.get('access_token', ''))" 2>/dev/null || true)
USER_ID=$(printf '%s\n' "$LOGIN_BODY" | python -c "import sys, json; data=json.load(sys.stdin); print(data.get('user_id', ''))" 2>/dev/null || true)

if [ "$LOGIN_CODE" = "200" ] && [ -n "$TOKEN" ]; then
  echo "[PASS] Step 3: User login succeeded (JWT obtained)"
else
  echo "[FAIL] Step 3: User login failed (HTTP $LOGIN_CODE, Response: $LOGIN_BODY)"
  exit 1
fi

# 4. Save Profile
echo "[STEP 4] Saving user profile for $USER_ID..."
PROFILE_PAYLOAD='{"personalDetails":{"firstName":"Smoke","lastName":"Tester"},"skills":["Python","Docker","FastAPI","Machine Learning"],"education":{"graduation":{"institute":"Tech University","board":"B.Tech"}},"achievements":"Built scalable cloud systems"}'

PROFILE_RES=$(curl -s -w "\n%{http_code}" -X POST "$GATEWAY_URL/api/profile/$USER_ID" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "$PROFILE_PAYLOAD")

PROFILE_BODY=$(printf '%s\n' "$PROFILE_RES" | sed '$d')
PROFILE_CODE=$(printf '%s\n' "$PROFILE_RES" | tail -n 1)

if [ "$PROFILE_CODE" = "200" ] && printf '%s\n' "$PROFILE_BODY" | grep -q '"status"[[:space:]]*:[[:space:]]*"success"'; then
  echo "[PASS] Step 4: Save profile succeeded"
else
  echo "[FAIL] Step 4: Save profile failed (HTTP $PROFILE_CODE, Response: $PROFILE_BODY)"
  exit 1
fi

# 5. Call /api/ml/recommend
echo "[STEP 5] Calling /api/ml/recommend..."
ML_PAYLOAD='{"skills":["Python","Machine Learning"],"education":"Tech University, B.Tech","achievements":"Built scalable cloud systems","resume_text":"Python developer with machine learning experience"}'

ML_RES=$(curl -s -w "\n%{http_code}" -X POST "$GATEWAY_URL/api/ml/recommend" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "$ML_PAYLOAD")

ML_BODY=$(printf '%s\n' "$ML_RES" | sed '$d')
ML_CODE=$(printf '%s\n' "$ML_RES" | tail -n 1)

REC_COUNT=$(printf '%s\n' "$ML_BODY" | python -c "import sys, json; res=json.load(sys.stdin); print(len(res) if isinstance(res, list) else 0)" 2>/dev/null || echo 0)

if [ "$ML_CODE" = "200" ] && [ "$REC_COUNT" -gt 0 ]; then
  echo "[PASS] Step 5: Recommendations retrieved ($REC_COUNT recommendations returned)"
else
  echo "[FAIL] Step 5: Recommendations call failed (HTTP $ML_CODE, Count: $REC_COUNT, Response: $ML_BODY)"
  exit 1
fi

echo "=========================================="
echo "All smoke test steps PASSED successfully!"
echo "=========================================="
