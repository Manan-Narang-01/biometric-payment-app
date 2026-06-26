# BioPay — Biometric Payment Platform

A full-stack payment application secured with **WebAuthn / FIDO2 biometric authentication** (fingerprint, Windows Hello, passkeys). No passwords — every login and transaction is verified with biometrics.

## Features

- **Passwordless login** — WebAuthn/FIDO2 (fingerprint, face, PIN, phone passkey)
- **Send money** — search by username, phone number, or UPI ID
- **Receive money** — share your username, phone, or UPI ID
- **Bank account management** — add/remove bank accounts, gated behind biometric re-auth
- **Transaction history** — full dashboard with charts (monthly sent/received, by type)
- **Session security** — JWT tokens, 15-minute timeout, Redis-backed revocation
- **Rate limiting** — slowapi + nginx rate zones
- **Audit logging** — every security event recorded

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI + SQLAlchemy (async) + PostgreSQL |
| Auth | WebAuthn/FIDO2 (`py-webauthn`) + JWT |
| Cache / Sessions | Redis |
| Frontend | Flask + Jinja2 + Bootstrap 5 |
| Reverse Proxy | Nginx (HTTPS, rate limiting) |
| Containers | Docker + Docker Compose |
| Migrations | Alembic |

## Getting Started

### Prerequisites
- Docker Desktop
- OpenSSL (for self-signed cert)

### 1. Clone
```bash
git clone https://github.com/Manan-Narang-01/biopay.git
cd biopay
```

### 2. Create environment file
```bash
cp .env.example .env
# Edit .env with your secrets
```

### 3. Generate SSL certificate (required for WebAuthn)
```bash
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem -out nginx/ssl/cert.pem \
  -subj "/CN=localhost"
```

### 4. Start
```bash
docker compose up -d
```

### 5. Open `https://localhost` — accept the self-signed cert warning.

## Project Structure

```
biopay/
├── backend/               # FastAPI backend
│   ├── app/
│   │   ├── api/v1/        # REST endpoints
│   │   ├── core/          # DB, Redis, security, config
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   └── services/      # Business logic
│   └── alembic/           # DB migrations
├── frontend/              # Flask frontend
│   ├── app/
│   │   ├── blueprints/    # Route handlers
│   │   ├── templates/     # Jinja2 HTML
│   │   └── static/        # CSS + JS
├── nginx/                 # Reverse proxy config
└── docker-compose.yml
```

## Security Highlights

- Biometric re-auth required for every transaction and bank account change
- Account numbers masked in UI (`****1234`)
- No passwords stored — ever
- HTTPS enforced, HSTS enabled
- Sessions stored in Redis with TTL; revoked on logout

## License

MIT
