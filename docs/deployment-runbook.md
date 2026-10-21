# Deployment & Operations Runbook

**Project:** Indian Stock Market Directional Prediction System (`stock-market-prediction-system`)  
**Phase:** 16 — Final Testing, Deployment Readiness & Operations  
**Document Version:** 1.0.0  
**Effective Date:** 2026-10-18  

---

## 1. System Overview & Deployment Topology

The stock market directional prediction system is an on-premise / virtual-machine hosted Python service combining:
- **FastAPI ASGI Application Server:** Serves HTTP APIs (`/api/predict`, `/api/health`, `/api/history`, `/api/events`, `/api/feedback`) and the static web UI (`/ui`).
- **Persistence Layer:** Local SQLite database files (`predictions.db`, `model_releases`) with WAL journal mode.
- **Model Storage:** Local filesystem storage for quantitative ML weights (`models/xgboost_direction.json`, `models/lightgbm_direction.txt`) and archived releases (`models/archive/`).
- **External Integration Points:** Yahoo Finance API (market data / live quotes) and local Ollama instance (Gemma 3 12B LLM for qualitative reasoning).

```
                      Internet / Browser Clients
                                  │
                                  ▼
                   ┌───────────────────────────────┐
                   │    Reverse Proxy / TLS Edge    │
                   │ (Nginx / Caddy / Cloudflare)   │
                   └──────────────┬────────────────┘
                                  │ HTTPS termination / Port 8000
                                  ▼
                   ┌───────────────────────────────┐
                   │     Uvicorn ASGI Server       │
                   │ (4 Workers, Binding: 127.0.0.1│
                   └──────────────┬────────────────┘
                                  │
            ┌─────────────────────┼─────────────────────┐
            ▼                     ▼                     ▼
┌───────────────────────┐ ┌───────────────┐ ┌───────────────────────┐
│  SQLite Database File │ │ Model Weights │ │  Ollama Service Host  │
│    (predictions.db)   │ │  (models/*)   │ │ (http://127.0.0.1:    │
│                       │ │               │ │         11434)        │
└───────────────────────┘ └───────────────┘ └───────────────────────┘
```

---

## 2. Environment Variables & Production Defaults

All configuration parameters are managed via environment variables and loaded through `app.core.config.Settings.from_env()`. A validated production template with safe placeholders is provided at [`.env.production.example`](../.env.production.example).

> [!SECURITY]
> **Strict `.gitignore` Policy:** Real `.env` files (e.g. `.env`, `.env.production`, `.env.local`) are strictly excluded by `.gitignore` to prevent database paths, model locations, credentials, or internal domains from being committed to Git. Only `.env.example` and `.env.production.example` are tracked.

### Mandatory Production Settings
| Variable | Required Value / Format | Default | Description & Constraint |
| :--- | :--- | :--- | :--- |
| `APP_ENV` | `production` | `development` | Setting to `production` disables OpenAPI `/docs`, `/redoc`, and `/openapi.json`, and enforces production CORS. |
| `APP_DEBUG` | `false` | `false` | **Must be `false`**. Setting to `true` in production causes startup failure (`ValueError`). |
| `APP_CORS_ORIGINS` | `https://trusted1.com,https://trusted2.com` | *None* | Comma-separated list of trusted origins. **Wildcards (`*`) and plain HTTP public origins are rejected at startup.** |
| `APP_DATA_DIR` | `/var/lib/stock-predictor/data` | `data` | Directory for persistent application data and default SQLite storage. |
| `DATABASE_PATH` | `/var/lib/stock-predictor/data/predictions.db` | `<APP_DATA_DIR>/predictions.db` | Path to persistent SQLite database file. Defaults to `data/predictions.db` (or `<APP_DATA_DIR>/predictions.db`). Can be explicitly overridden. |
| `APP_MODEL_DIR` | `/var/lib/stock-predictor/models` | `models` | Directory housing active model weights and archive subdirectories. Defaults to `models/` relative to project root. Can be overridden via `APP_MODEL_DIR`. |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | `http://127.0.0.1:11434` | URL of local Ollama server running Gemma 3 12B. |
| `OLLAMA_MODEL` | `gemma3:12b` | `gemma3:12b` | Target LLM model tag in Ollama. |
| `LOG_LEVEL` | `INFO` | `INFO` | Logging level (`INFO`, `WARNING`, `ERROR`). |

#### Storage & Path Configuration Notes
- **Configurable Database Path (`DATABASE_PATH`):** By default, the application resolves its SQLite database to `predictions.db` inside `APP_DATA_DIR` (or `data/predictions.db` relative to the project root). Setting `DATABASE_PATH` explicitly overrides this and points the application directly to the specified file.
- **Configurable Model Directory (`APP_MODEL_DIR`):** Defaults to `models/` relative to the project root. Operators can override this by setting `APP_MODEL_DIR` to an absolute path on a persistent SSD volume. For backward compatibility, `MODEL_DIR` is also accepted as a fallback if `APP_MODEL_DIR` is unset.

---

## 3. Installation & Application Startup

### 3.1 Prerequisites
- Linux (Ubuntu 22.04 LTS recommended) or Windows Server
- Python 3.11 or 3.12 (Python 3.14 compatible)
- Local SQLite 3.35+
- Ollama service pre-installed with `gemma3:12b` model pulled

### 3.2 Step-by-Step Installation
```bash
# 1. Clone repository and navigate to workspace
git clone https://github.com/naiya555/stock-market-prediction-system.git
cd stock-market-prediction-system

# 2. Create isolated virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Upgrade pip and install pinned dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Verify dependency integrity
python -m pip check

# 5. Create production environment file from template
cp .env.production.example .env
# Edit .env to set your trusted domain in APP_CORS_ORIGINS (e.g., https://trading.yourfirm.in)
```

### 3.3 Production Startup via Uvicorn

> [!WARNING]
> **Strict Binding Policy:** Never bind Uvicorn directly to `0.0.0.0` or expose the ASGI socket to the public WAN without an authenticating reverse proxy or firewall. Always bind strictly to `127.0.0.1` (localhost loopback).

**Linux / macOS (Bash):**
```bash
# Export production environment variables (or load via .env)
export APP_ENV=production
export APP_DEBUG=false
export APP_CORS_ORIGINS="https://trading.yourfirm.in"
export APP_DATA_DIR="/var/lib/stock-predictor/data"
export APP_MODEL_DIR="/var/lib/stock-predictor/models"
export DATABASE_PATH="/var/lib/stock-predictor/data/predictions.db"

# Start Uvicorn ASGI server with 4 worker processes bound to localhost
uvicorn app.api.app:app \
  --host 127.0.0.1 \
  --port 8000 \
  --workers 4 \
  --no-access-log \
  --proxy-headers
```

**Windows Server / Local Windows (PowerShell):**
```powershell
# Set environment variables in session (or rely on .env file)
$env:APP_ENV = "production"
$env:APP_DEBUG = "false"
$env:APP_CORS_ORIGINS = "https://trading.yourfirm.in"
$env:APP_DATA_DIR = "data"
$env:APP_MODEL_DIR = "models"
$env:DATABASE_PATH = "data/predictions.db"

# Note: On Windows, single worker is recommended for local staging; multi-worker requires spawn-safe entrypoint
python -m uvicorn app.api.app:app --host 127.0.0.1 --port 8000 --workers 1 --proxy-headers
```

---

## 4. Reverse Proxy & External TLS Termination

Uvicorn does not manage automated TLS certificates (ACME). Production deployments require a fronting reverse proxy (e.g., Nginx, Caddy, or Cloudflare) to terminate TLS 1.3 and forward client IP headers.

### Recommended Nginx Configuration (`/etc/nginx/sites-available/stock-predictor`)
```nginx
server {
    listen 80;
    server_name trading.yourfirm.in;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name trading.yourfirm.in;

    ssl_certificate /etc/letsencrypt/live/trading.yourfirm.in/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/trading.yourfirm.in/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Forwarding headers for proxy-headers middleware
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # Prevent buffer attacks and set client limits
    client_max_body_size 2M;
    client_body_timeout 10s;
    client_header_timeout 10s;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }
}
```

### Alternative Caddy Configuration (`Caddyfile`)
Caddy provides automated zero-touch Let's Encrypt / ZeroSSL TLS certificates and works identically on Windows and Linux:
```caddy
trading.yourfirm.in {
    # Reverse proxy to local Uvicorn ASGI server
    reverse_proxy 127.0.0.1:8000 {
        header_up Host {host}
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
    }

    # Security headers
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
    }
}
```

> [!CAUTION]
> **Reverse Proxy Template Review Notice:**
> The above Nginx and Caddy configurations are illustrative reference templates. Before deploying in any production environment, your systems/DevOps team must review and adjust domain names, SSL certificate storage locations, firewall rules, client timeouts, rate-limiting directives, and buffer sizes for compliance with your organization's specific security policies.

---

## 5. Database Initialization, Backup & Disaster Recovery

### 5.1 Initialization & Schema Migrations
The SQLite database initializes automatically when `PredictionRepository` instantiates. Table definitions are idempotent (`CREATE TABLE IF NOT EXISTS`).
- `predictions`: Records directional forecast, probabilities, data quality metrics, and input timestamps.
- `model_releases`: Records model candidate releases, training cutoffs, validation gate results, and promotion status.

### 5.2 Online Hot Backup
SQLite supports concurrent online backup without locking the database or taking the API offline:
```bash
# Execute safe point-in-time online backup
sqlite3 /var/lib/stock-predictor/data/predictions.db ".backup /var/backups/stock-predictor/predictions_$(date +%Y%m%d_%H%M%S).db"
```
Schedule this command via `cron` daily at 00:00 UTC.

### 5.3 Disaster Recovery Procedure
1. Stop Uvicorn service: `sudo systemctl stop stock-predictor`
2. Move corrupt database file aside: `mv /var/lib/stock-predictor/data/predictions.db /var/lib/stock-predictor/data/predictions_corrupt.db`
3. Restore last verified backup: `cp /var/backups/stock-predictor/predictions_latest.db /var/lib/stock-predictor/data/predictions.db`
4. Verify database file integrity: `sqlite3 /var/lib/stock-predictor/data/predictions.db "PRAGMA integrity_check;"` (must output `ok`).
5. Restart Uvicorn service: `sudo systemctl start stock-predictor`
6. Verify service health: `curl -s http://127.0.0.1:8000/api/health | jq .`

### 5.4 Non-Destructive Backup & Restore Verification
To verify that backup snapshots exist, are uncorrupted, and can be restored without risking or overwriting the active live production database:

> [!IMPORTANT]
> **SQLite WAL Mode Consistency:**
> When SQLite is configured in WAL mode (`PRAGMA journal_mode=WAL;`), active transactions may reside in the write-ahead log (`predictions.db-wal`). Never perform a raw file copy (`cp` or `copy`) of an open database file without checkpointing. Always use SQLite's online backup API (`.backup` command or Python `conn.backup()`), which safely checkpoints and merges WAL pages into a single consistent snapshot without locking ongoing readers or writers.

1. **Verify Backup File Presence & Timestamp:**
   - **Linux / Bash:**
     ```bash
     ls -lh /var/backups/stock-predictor/predictions_*.db
     ```
   - **Windows / PowerShell:**
     ```powershell
     Get-ChildItem -Path C:\var\backups\stock-predictor\predictions_*.db | Format-Table Name, Length, LastWriteTime
     ```

2. **In-Place SQLite Integrity Check on Backup:**
   - **Linux / Bash:**
     ```bash
     sqlite3 /var/backups/stock-predictor/predictions_latest.db "PRAGMA integrity_check;"
     # Expected output: ok
     ```
   - **Cross-Platform / Python:**
     ```bash
     python -c "import sqlite3; con = sqlite3.connect('predictions_latest.db'); print(con.execute('PRAGMA integrity_check;').fetchone()[0]); con.close()"
     # Expected output: ok
     ```

3. **Isolated Dry-Run Restoration Drill (Zero Live Mutation):**
   Restore the backup to an ephemeral temporary directory to test data accessibility without touching the active production database:
   - **Linux / Bash:**
     ```bash
     mkdir -p /tmp/stock-predictor-verify
     cp /var/backups/stock-predictor/predictions_latest.db /tmp/stock-predictor-verify/verify.db
     sqlite3 /tmp/stock-predictor-verify/verify.db "SELECT count(*) AS total_predictions FROM predictions; SELECT count(*) AS releases FROM model_releases;"
     rm -rf /tmp/stock-predictor-verify
     ```
   - **Windows / PowerShell:**
     ```powershell
     New-Item -ItemType Directory -Force -Path "$env:TEMP\stock-predictor-verify"
     Copy-Item -Path "C:\var\backups\stock-predictor\predictions_latest.db" -Destination "$env:TEMP\stock-predictor-verify\verify.db"
     python -c "import sqlite3; c = sqlite3.connect(r'$env:TEMP\stock-predictor-verify\verify.db'); print('predictions:', c.execute('SELECT count(*) FROM predictions;').fetchone()[0]); print('releases:', c.execute('SELECT count(*) FROM model_releases;').fetchone()[0]); c.close()"
     Remove-Item -Recurse -Force -Path "$env:TEMP\stock-predictor-verify"
     ```
   - **Automated Verification Script:**
     ```bash
     python scripts/verify_day49_backup_restore.py
     ```
   This proves recovery readiness while ensuring the live database at `/var/lib/stock-predictor/data/predictions.db` remains completely untouched.

---

## 6. Model Artifact Storage, Promotion & Rollback

### 6.1 Artifact Structure
```
models/
├── xgboost_direction.json      # Active XGBoost model
├── lightgbm_direction.txt      # Active LightGBM model
├── candidates/                 # Quarantined candidate models during retraining
│   └── xgboost_candidate_*.json
└── archive/                    # Immutable previous versions for instant rollback
    └── xgboost_direction_20261015_*.json
```

### 6.2 Controlled Retraining & Promotion Workflow (ADR 10)
Retraining is never automated blindly during inference requests. It must be triggered via the administrative retraining workflow (`app.training.retraining.ControlledRetrainingService`).

The 6-gate promotion protocol:
1. **Gate 0: Chronological Integrity Gate** — Asserts training end date strictly precedes validation start date by at least the configured embargo window (eliminating look-ahead bias).
2. **Gate 1: Sample Sufficiency Gate** — Verifies minimum training and validation observations.
3. **Gate 2: Class Balance Gate** — Verifies directional target balance in training set.
4. **Gate 3: Baseline Superiority Gate** — Outperforms naive majority class baseline.
5. **Gate 4: Minimum Accuracy Gate** — Exceeds minimum validation threshold (>50%).
6. **Gate 5: Non-Degradation Gate** — Must not degrade active model performance by more than margin (2.0%).

### 6.3 Transactional Promotion & Rollback
- On passing all gates: The active model is archived into `models/archive/`, the candidate is moved into place via atomic filesystem replacement (`os.replace`), and SQLite release records are committed.
- On promotion failure: If filesystem or database errors occur during promotion, `ControlledRetrainingService` automatically restores the previous active model from `models/archive/`.

---

## 7. Operational Telemetry, Monitoring & Incident Response

### 7.1 Health Check Endpoint (`GET /api/health`)
Monitored by synthetic pingers every 30 seconds.
```bash
curl -s http://127.0.0.1:8000/api/health
```
**Response Format:**
```json
{
  "status": "healthy",
  "app_name": "Indian Stock Market Prediction System",
  "environment": "production",
  "timestamp": "2026-10-18T15:30:00Z",
  "dependencies": {
    "database": {
      "status": "ok",
      "details": "SQLite database connection and query operational"
    },
    "models": {
      "status": "ok",
      "details": "Model artifact storage directory is accessible"
    },
    "llm": {
      "status": "configured",
      "details": "Local Ollama Gemma 3 12B integration configured (runtime-deferred)"
    }
  }
}
```

### 7.2 Key Telemetry Metrics & Log Signatures
- **Latency & Access Telemetry:** Every response includes `X-Process-Time-Ms` header. The application logs:
  `HTTP GET /api/predict -> 200 (45.20ms)`
- **Data Quality Warnings:** Stale market data warnings logged as:
  `Market data for TCS.NS is stale by 3 days.`
- **Quote Failures:** Safely sanitized in API responses; internal logs record exact failure reason.

### 7.3 Incident Response Runbook
| Symptom / Alert | Root Cause | Immediate Remediation |
| :--- | :--- | :--- |
| `HTTP 503` on `/api/health` | SQLite database lock contention or disk write failure | Check disk space (`df -h`). Inspect `/var/lib/stock-predictor/data/predictions.db-wal` size. Run `PRAGMA integrity_check;`. |
| Elevated latency (>2000ms) on `/api/predict` | Ollama LLM inference queue backlog or CPU throttling | Verify Ollama status (`curl http://127.0.0.1:11434/api/tags`). Switch client requests to quantitative ML (`model_name: "xgboost"`). |
| High rate of `STALE_DATA` warnings | Yahoo Finance rate limiting or market holiday gap | Verify symbol format (`.NS` suffix). Check national holiday calendar. Review quote provider logs. |
| Model candidate rejected during retraining | Candidate model failed one of the 6 validation gates | Inspect `model_releases` table for failing gate name and observed metric. Active model remains 100% untouched. |

### 7.4 Deployment Smoke-Test Command & Expected Verification Results
Before putting any new deployment or update into service, run the local staging smoke-test runner:
```bash
# Execute isolated local deployment smoke test
python scripts/run_local_staging.py --host 127.0.0.1 --port 8899 --requests 20 --concurrency 2
```

**Expected Verification Checklist:**
| Check | Expected Result | Operational Meaning |
| :--- | :--- | :--- |
| **[1] Loopback Isolation** | `PASS` | Bound strictly to `127.0.0.1`; WAN/public interfaces inaccessible. |
| **[2] Production Startup** | `PASS` | Server started with `APP_ENV=production` and `APP_DEBUG=false`. |
| **[3] /api/health Endpoint** | `PASS` | Returned HTTP 200 with `status: "healthy"` and dependencies verified. |
| **[4] Security Headers** | `PASS` | `nosniff`, `DENY`, `strict-origin-when-cross-origin`, and `X-Process-Time-Ms` present. |
| **[5] OpenAPI /docs Lockdown** | `PASS` | `/docs`, `/redoc`, and `/openapi.json` return HTTP 404 in production. |
| **[6] Smoke Tests** | `PASS` | UI root `/` and `/api/events` return valid HTTP 200 responses. |
| **[7] Dev Database Untouched** | `PASS` | SHA-256 fingerprint matches pre-test hash (0 bytes mutated). |
| **[8] Models Storage Untouched**| `PASS` | Model directory files match pre-test hashes (0 bytes mutated). |
| **Throughput & Latency** | `> 100 req/s, p50 < 25ms` | Baseline local loopback responsiveness confirmed. |
| **Port & Cleanup** | `0 errors` | Port 8899 cleanly released; ephemeral directory removed. |

---

## 8. Graceful Shutdown & Recovery Procedures

### 8.1 Systemd Service Unit (`/etc/systemd/system/stock-predictor.service`)
```ini
[Unit]
Description=Indian Stock Market Prediction API
After=network.target

[Service]
Type=simple
User=stockpredictor
Group=stockpredictor
WorkingDirectory=/opt/stock-market-prediction-system
Environment="PATH=/opt/stock-market-prediction-system/.venv/bin"
EnvironmentFile=/etc/stock-predictor.env
ExecStart=/opt/stock-market-prediction-system/.venv/bin/uvicorn app.api.app:app --host 127.0.0.1 --port 8000 --workers 4 --proxy-headers
Restart=always
RestartSec=5
KillSignal=SIGTERM
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

### 8.2 Maintenance Commands
```bash
# Reload configuration
sudo systemctl daemon-reload

# Restart service gracefully
sudo systemctl restart stock-predictor

# View live operational logs
journalctl -u stock-predictor -f -n 100
```

---

## 9. Known Limitations & Operational Constraints

1. **Staging Deployment Soak Test:** Local concurrency and simulation benchmarks (`scripts/staging_soak_test.py`) validate error isolation and request concurrency. However, a multi-hour soak test on a production-equivalent staging cluster during live exchange market hours remains a pending milestone prerequisite.
2. **Third-Party Quote Latency:** Live quote retrieval depends on public Yahoo Finance API availability and is subject to potential rate limits and up to 15-minute exchange delays.
3. **No Automatic Live Retraining:** In accordance with ADR 10, automated live retraining loops triggered by user predictions are strictly disabled. Retraining must be invoked by authorized administrators.
4. **Automated CI/CD Scanner:** CI dependency vulnerability scanning is defined in `.github/workflows/ci.yml`. Running local audits requires `pip install pip-audit`.
5. **No Profitability Guarantee:** Passing software health checks and automated tests demonstrates deterministic software stability; it does NOT constitute financial profitability or guarantee immunity against market drawdown.
