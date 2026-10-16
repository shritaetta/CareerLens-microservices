# CareerLens API Gateway

Nginx-based reverse proxy and single entry point for CareerLens microservices and the React frontend single-page application.

---

## Architecture & Routing

The gateway listens on port `80` (mapped to `8080` or `80` on the host) and routes incoming traffic to internal microservices on the Docker network:

| Path Prefix | Target Upstream | Prefix Stripping / Rewriting | Notes |
|---|---|---|---|
| `/api/auth/` | `http://auth:8000/` | `/api/auth/*` → `/*` | Authentication & token endpoints (`/login`, `/signup`, `/me`) |
| `/api/profile/` | `http://profile:8000/profile/` | `/api/profile/*` → `/profile/*` | Profile storage & retrieval (`/profile/{user_id}`) |
| `/api/files/` | `http://files:8000/` | `/api/files/*` → `/*` | Uploads (`/upload`, `/extract_pdf`) & static files (`/uploads/*`) |
| `/api/ml/` | `http://ml:8000/` | `/api/ml/*` → `/*` | ML recommendations, ATS evaluation (`proxy_read_timeout 120s`) |
| `/` | `http://frontend:80/` | Passes request to SPA | React static assets and client-side routing |
| `/gateway-health` | Internal (Nginx) | None | Returns HTTP 200 `{"status":"ok","service":"gateway"}` |

---

## Configuration Features

- **Upload Body Size**: `client_max_body_size 20m;` allows large resumes and portfolio documents.
- **Header Forwarding**: Preserves `Host`, `X-Real-IP`, `X-Forwarded-For`, and `X-Forwarded-Proto` for microservice auditing and client IP resolution.
- **Gzip Compression**: Enabled for MIME types `text/plain`, `text/css`, `application/json`, `application/javascript`, and `text/xml`.
- **CORS Handling**: Because all microservices and frontend assets are served from the same gateway origin, cross-origin requests (CORS) are unnecessary.
- **ML Long-Running Timeouts**: `proxy_read_timeout 120s;` prevents gateway timeouts during heavy embedding calculations or model inference.

---

## Docker Deployment & Verification

### 1. Build the Docker Image
```bash
docker build -t careerlens-gateway:latest ./gateway
```

### 2. Verify Nginx Configuration Syntax
To test configuration validity in a standalone container prior to spinning up all backend containers, provide mock host mappings:
```bash
docker run --rm \
  --add-host=auth:127.0.0.1 \
  --add-host=profile:127.0.0.1 \
  --add-host=files:127.0.0.1 \
  --add-host=ml:127.0.0.1 \
  --add-host=frontend:127.0.0.1 \
  careerlens-gateway:latest nginx -t
```

### 3. Run the Container
```bash
docker run -d -p 8080:80 --name careerlens-gateway careerlens-gateway:latest
```

### 4. Health Check
```bash
curl -i http://localhost:8080/gateway-health
```
