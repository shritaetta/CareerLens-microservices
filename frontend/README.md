# CareerLens Frontend Service

React 19 single-page application built with Vite and React Router, styled with modern vanilla CSS and Lucide icons.

---

## Architecture & API Routing

All backend API communications are routed through `src/api.js`:
- Base API URL is configurable via `VITE_API_URL` (defaults to `/api`).
- `apiFetch(path, options)` automatically attaches `Authorization: Bearer <token>` from `localStorage('access_token')`.
- Handles `401 Unauthorized` by clearing local credentials and redirecting unauthenticated users to `/login`.
- Relative file URLs (e.g., uploaded resumes and certificates) are resolved via `getFileUrl(url)`.

### Endpoint Mappings
- **Auth**: `/login`, `/signup` → `/api/auth/login`, `/api/auth/signup`
- **Profile**: `/profile/:id` → `/api/profile/:id`
- **Files**: `/upload`, `/extract_pdf` → `/api/files/upload`, `/api/files/extract_pdf`
- **ML**: `/recommend`, `/feedback`, `/evaluate_ats`, `/enhance_profile`, `/internships/light` → `/api/ml/...`

---

## Environment Variables

Configurable in `.env` (see `.env.example`):

| Variable | Description | Default |
|---|---|---|
| `VITE_API_URL` | Base API URL prefix for client requests | `/api` |
| `VITE_GATEWAY_URL` | Gateway target URL for Vite dev server proxy | `http://localhost:8080` |

---

## Local Development

```bash
# 1. Install dependencies
npm install

# 2. Start Vite dev server with proxy to Gateway
npm run dev

# 3. Lint source files
npm run lint

# 4. Create production build
npm run build
```

During development with `npm run dev`, any requests sent to `/api/*` are automatically proxied to the gateway specified by `VITE_GATEWAY_URL` (default: `http://localhost:8080`).

---

## Docker Deployment

### Build the Image
```bash
docker build -t careerlens-frontend:latest .
```

### Run the Container
```bash
docker run -d -p 80:80 --name careerlens-frontend careerlens-frontend:latest
```
