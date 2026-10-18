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

All configuration parameters are managed via environment variables and loaded through `app.core.config.Settings.from_env()`.

### Mandatory Production Settings
| Variable | Required Value / Format | Default | Description & Constraint |
| :--- | :--- | :--- | :--- |
| `APP_ENV` | `production` | `development` | Setting to `production` disables OpenAPI `/docs`, `/redoc`, and `/openapi.json`, and enforces production CORS. |
| `APP_DEBUG` | `false` | `false` | **Must be `false`**. Setting to `true` in production causes startup failure (`ValueError`). |
| `APP_CORS_ORIGINS` | `https://trusted1.com,https://trusted2.com` | *None* | Comma-separated list of trusted origins. **Wildcards (`*`) and plain HTTP public origins are rejected at startup.** |
| `DATABASE_PATH` | `/var/lib/stock-predictor/predictions.db` | `predictions.db` | Path to persistent SQLite database file. Must be on persistent SSD storage. |
| `MODEL_DIR` | `/var/lib/stock-predictor/models` | `models` | Directory housing active model weights and archive subdirectories. |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | `http://127.0.0.1:11434` | URL of local Ollama server running Gemma 3 12B. |
| `OLLAMA_MODEL` | `gemma3:12b` | `gemma3:12b` | Target LLM model tag in Ollama. |
| `LOG_LEVEL` | `INFO` | `INFO` | Logging level (`INFO`, `WARNING`, `ERROR`). |

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
```

### 3.3 Production Startup via Uvicorn
Do not bind Uvicorn directly to `0.0.0.0` without an authenticating reverse proxy or firewall.
```bash
# Export production environment variables
export APP_ENV=production
export APP_DEBUG=false
export APP_CORS_ORIGINS="https://trading.yourfirm.in"
export DATABASE_PATH="/var/lib/stock-predictor/predictions.db"
export MODEL_DIR="/var/lib/stock-predictor/models"

# Start Uvicorn ASGI server with 4 worker processes bound to localhost
uvicorn app.api.app:app \
  --host 127.0.0.1 \
  --port 8000 \
  --workers 4 \
  --no-access-log \
  --proxy-headers
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
sqlite3 /var/lib/stock-predictor/predictions.db ".backup /var/backups/stock-predictor/predictions_$(date +%Y%m%d_%H%M%S).db"
```
Schedule this command via `cron` daily at 00:00 UTC.

### 5.3 Disaster Recovery Procedure
1. Stop Uvicorn service: `sudo systemctl stop stock-predictor`
2. Move corrupt database file aside: `mv /var/lib/stock-predictor/predictions.db /var/lib/stock-predictor/predictions_corrupt.db`
3. Restore last verified backup: `cp /var/backups/stock-predictor/predictions_latest.db /var/lib/stock-predictor/predictions.db`
4. Verify database file integrity: `sqlite3 /var/lib/stock-predictor/predictions.db "PRAGMA integrity_check;"` (must output `ok`).
5. Restart Uvicorn service: `sudo systemctl start stock-predictor`
6. Verify service health: `curl -s http://127.0.0.1:8000/api/health | jq .`

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
| `HTTP 503` on `/api/health` | SQLite database lock contention or disk write failure | Check disk space (`df -h`). Inspect `/var/lib/stock-predictor/predictions.db-wal` size. Run `PRAGMA integrity_check;`. |
| Elevated latency (>2000ms) on `/api/predict` | Ollama LLM inference queue backlog or CPU throttling | Verify Ollama status (`curl http://127.0.0.1:11434/api/tags`). Switch client requests to quantitative ML (`model_name: "xgboost"`). |
| High rate of `STALE_DATA` warnings | Yahoo Finance rate limiting or market holiday gap | Verify symbol format (`.NS` suffix). Check national holiday calendar. Review quote provider logs. |
| Model candidate rejected during retraining | Candidate model failed one of the 6 validation gates | Inspect `model_releases` table for failing gate name and observed metric. Active model remains 100% untouched. |

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
