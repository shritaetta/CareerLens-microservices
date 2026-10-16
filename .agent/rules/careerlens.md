---
trigger: always_on
---

# CareerLens migration rules

- Goal: split the FastAPI monolith in /backend into services under /services, per the agreed plan: auth, profile, files, ml, plus an nginx gateway and the React frontend.
- Do NOT modify /backend. It stays as the reference until the final cleanup step.
- Work only inside the directories named in the prompt. If a change outside them is needed, stop and ask.
- Every service: its own requirements.txt (pinned), Dockerfile (python:3.11-slim, non-root user), GET /health endpoint, env-var configuration only (no hardcoded paths, URLs or secrets), and a README with run instructions.
- Keep API behaviour identical unless the prompt says otherwise. Preserve response shapes the frontend already consumes.
- Use FastAPI `lifespan`, not `on_event`.
- Passwords: argon2 or bcrypt. Never log secrets or passwords.
- Never commit .env. Update .env.example when adding variables.
- After each task: run the service's tests or a smoke test, show the commands and output, and list files changed.
- Commit nothing yourself; I will commit after review.