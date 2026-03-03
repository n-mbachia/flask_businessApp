# Business Management System

A Flask-based business intelligence platform that embeds a rich browser UI, RESTful integration surface, real-time dashboards, analytics/predictive services, and CLI automation. Browser views, HTMX-enhanced widgets, and Webpack-built assets live beside a fully documented `/api/v1` namespace plus Socket.IO‑driven dashboards so third-party systems can stay in sync.

## Integration Surfaces

### Browser UI & HTMX-driven workflows
- `app/routes/` (see `app/routes/ROUTES_README.md`) registers dashboard, auth, order, product, sales, customer, analytics, and API docs blueprints. Templates under `app/templates/` pair with HTMX-aware helpers in `app/static/js/htmx-global.js` to keep forms reactive without full page reloads.
- Business logic lives in `app/forms/`, `app/validators/`, and `app/schema.py`, which reuse shared helpers (see `app/utils/UTILS_README.md`) for consistent validation, serialization, and security logging.
- Static assets (`app/static/`, documented in `app/static/README.md`) supply Bootstrap/Plotly visuals, reusable components under `app/static/js/components/`, page scripts, and shared utilities that render the UX described in `app/static/js/pages/`.

### REST API & third-party documentation
- The `/api/v1` blueprint defined in `app/api/__init__.py` wires Flask-RESTx namespaces (`auth`, `products`, `customers`, `orders`, `enhanced_orders`, `inventory`, `sales`, `analytics`, `predictive`, `dashboard`) to database-aware services and shared helpers from `app/routes/api_utils.py`.
- Swagger/OpenAPI docs are hosted at `/api/v1/docs` through `Flasgger` configuration (`app/api/docs.py`), so integrators can explore payload schemas, security headers, and example responses.
- `app/api/v1/enhanced_orders.py` powers the HTMX integration that validates subtotals, taxes, shipping, and discounts ahead of saving orders, keeping browser and API totals aligned.

### Real-time dashboards & notifications
- When `flask-socketio` is installed, `run.py` boots Socket.IO through `app/services/socketio_handlers.py`, registering `connect`, `disconnect`, `join_dashboard`, `leave_dashboard`, `request_refresh`, `subscribe_metrics`, and `unsubscribe_metrics` events.
- `app/services/realtime_dashboard.py` broadcasts `new_order`, `inventory_change`, `sales_milestone`, `kpi_update`, `initial_state`, `notification`, and `system_alert` payloads to per-user rooms so dashboards reflect live activity.

### Operational CLI & automation
- `scripts/admin/bi_admin.py` (documented in `scripts/README.md`) replaces legacy `scripts/legacy/check_orders*.py`, exposing Click-powered reports for orders, customers, products, health, activity, and the dashboard.
- `scripts/manage_assets.py` and `scripts/build_assets.sh` orchestrate asset builds/cleans/validations using `config/static_assets.json`, while `scripts/download_deps.py` fetches vetted Bootstrap/Plotly files and verifies checksums.
- All CLI tooling reuses models/services so reports match the same business rules as the browser/API layers; update `app/services/SERVICES_IMPROVEMENTS.md` when business logic shifts.

## Architecture Highlights

### Backend (`app/`)
- **Blueprints & views**: `app/routes` serves templates, AJAX endpoints, and API docs; `app/routes/ROUTES_README.md` details each blueprint plus error handling.
- **Models & DB helpers**: Domain classes live in `app/models/` (customers, orders, order items, products, sales, inventory lots/movement, costs, analytics views, users). `app/models/__init__.py` helps migrations add constraints (e.g., non-negative shipping).
- **Services**: `app/services/` centralizes analytics (`analytics_service.py`, `dashboard_metrics.py`), inventory/profit (`inventory_service.py`, `profit_calculator.py`, `lot_analytics.py`), forecasting (`predictive_analytics.py`, `trend_services.py`), real-time (`realtime_dashboard.py`, `socketio_handlers.py`), and operational metrics (`performance_analyzer.py`, `sales_updater.py`).
- **Validation + helpers**: Forms, validators, schemas, and utilities (`app/forms`, `app/validators`, `app/schema.py`, `app/utils`) provide consistent serialization, caching, and email utilities—see `app/utils/UTILS_README.md` for conventions.
- **Security & extensions**: `app/extensions.py` wires Sentry, CSRF, caching, compression, CORS, and optional Socket.IO; `app/security/` and `app/middleware/rate_limiter.py` enforce auth middleware, security logging, and throttling while CSP, HSTS, and nonce header logic protect every response.

### Frontend & static assets
- `app/static/` contains SASS/CSS, JS entrypoints, shared components, HTMX helpers, and static media; `webpack.config.js` bundles `app`, `dashboard`, `analytics`, and `sales` entrypoints, extracts CSS, copies images/fonts, and shards vendors.
- `package.json` exposes `npm run build`, `npm run dev`, and `npm run clean`; npm dependencies include Bootstrap, Bootstrap Icons, Chart.js, and Plotly.
- `config/static_assets.json` (used by `scripts/manage_assets.py`) centralizes hashing, responsive images, lazy loading, and cache-control metadata for deployment.
- Built bundles land under `app/static/dist/`; `scripts/manage_assets.py clean` or `npm run clean` resets the folder when caches misbehave.

### Data, migrations & operational files
- Alembic migrations live in `migrations/versions/` (e.g., `98b359474f0d_store_front_build.py`, `d4e2f3b7a9c1_add_product_images.py`). Run `flask db migrate`/`flask db upgrade` against the same database used by the app (`instance/profitability.db` locally; production reads `DATABASE_URL`).
- The repo keeps a working SQLite snapshot (`instance/profitability.db`) plus `tmp.db`; logs write to `logs/app.log*` and diagnostics hit `app/extensions.configure_logging`.

### Scripts & tooling
- `scripts/admin/bi_admin.py` handles daily BI reports, while `scripts/download_deps.py` ensures the frontend has verified vendor assets.
- `scripts/manage_assets.py` supports `build`, `clean`, and `validate` commands over the `app/static` tree using `config/static_assets.json`.
- Legacy helpers stay under `scripts/legacy/` for reference; new automation is documented in `scripts/README.md`.

## Getting Started

### Prerequisites
- Python 3.10+ (Flask 3.1, SQLAlchemy 2.x)
- Node.js 18+ / npm (Webpack 5, Babel, Sass)
- SQLite for local development; PostgreSQL or another DB for production
- Git for checkout; Redis and a cache-enabled store when using Flask-Caching/Flask-Limiter in prod

### Setup steps
1. `git clone <repo>` and `cd businessApp`.
2. `python -m venv venv && source venv/bin/activate` (Windows: `venv\Scripts\activate`).
3. `pip install --upgrade pip && pip install -r requirements.txt`.
4. `npm install` to pull frontend dependencies.
5. Optionally download vendor assets: `python scripts/download_deps.py` (see `scripts/README.md`).
6. Build assets with `npm run build` (development `npm run dev`). For further control run `python scripts/manage_assets.py build --env production` or `build --env development`.
7. Apply migrations: `export FLASK_APP=run.py` (`set FLASK_APP=run.py` on Windows) then `flask db upgrade`.
8. Start the server with `python run.py` (it will call `socketio.run` when installed) or `flask run` for simple Flask mode.

## Configuration

`run.py` loads `.env` via `python-dotenv`; supply these when running locally and override safely for production:

```env
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=change-me
DATABASE_URL=sqlite:///instance/profitability.db
JWT_SECRET_KEY=dev-jwt-secret
SALES_TAX_RATE=0.16
CACHE_TYPE=simple
CACHE_DEFAULT_TIMEOUT=300
CACHE_REDIS_URL=redis://localhost:6379/0
RATELIMIT_STORAGE_URL=memory://
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=
MAIL_PASSWORD=
SENTRY_DSN=
SESSION_COOKIE_SECURE=false
SESSION_COOKIE_SAMESITE=Lax
```

`config.py` pulls the same env variables and enforces `SESSION_COOKIE_SECURE=true` when SameSite=None. Production config (`config.ProductionConfig`) requires `DATABASE_URL` and `SECRET_KEY`, prefers Redis for cache/rate-limit storage, and extends session lifetime. Additional security knobs live under `app/security/config.py` (CSP, rate limits, API keys, upload limits) and `app/security/SECURITY_IMPROVEMENTS.md` documents suggested hardening steps.

## Assets & Frontend Pipeline

- Frontend entry points live under `app/static/js/` (`app.js`, `pages/dashboard.js`, `pages/analytics.js`, `pages/sales.js`). Components live in `app/static/js/components/`, utilities under `app/static/js/utils/`, and global behaviors in `app/static/js/htmx-global.js`.
- Stylesheets live under `app/static/css/`; CSS variables and themes live in `app/static/css/themes/variables.css`.
- `webpack.config.js` orchestrates multiple entry points, CSS extraction, vendor chunking, asset copying, and hashed filenames.
- `scripts/manage_assets.py` (commands: `build`, `clean`, `validate`) honors `config/static_assets.json` for caching rules, responsive/resized images, and manifest generation.
- Vendor assets are downloaded/validated by `scripts/download_deps.py`. `scripts/build_assets.sh` can still bootstrap directories when needed.

## REST API & Integration Surface

- `app/api/__init__.py` registers Flask-RESTx namespaces. Each namespace (names match folder names under `app/api/v1/`) exposes request parsers, schemas, and an `api_docs` helper for shared responses.
- `/api/v1/docs` (powered by `app/api/docs.py`) is the canonical API specification for partners, showing required JSON bodies, query parameters, and HTTP status codes.
- Authentication mixes session cookies, optional JWTs, and API keys (controlled through `app/security/config.py` and `app/security/auth_middleware.py`). Rate limits are enforced through `app/middleware/rate_limiter.py` and the in-memory limiter (swap in Redis for production by overriding `RATELIMIT_STORAGE_URL`).
- Shared helpers in `app/routes/api_utils.py` ensure consistent error formatting; real-time hooks in `app/services/socketio_handlers.py` and `app/services/realtime_dashboard.py` keep API-created orders/inventory changes in sync with live dashboards.

## Real-time Dashboards & Notifications

- Socket.IO handlers emit `dashboard_update`, `kpi_update`, `initial_state`, `refresh_complete`, `notification`, and `system_alert` messages, with rooms scoped per user to isolate data (`app/services/socketio_handlers.py`).
- `app/services/realtime_dashboard.py` keeps a registry of connected users and streams new orders, inventory adjustments, milestone-based sales updates, KPI deltas, and system alerts.
- If Socket.IO is unavailable, the app still functions via the REST API and HTMX/templated views; `run.py` falls back to plain Flask if `socketio` is `None`.

## Services & Security Layers

- Analytics & forecasting services: `app/services/analytics_service.py`, `app/services/dashboard_metrics.py`, `app/services/trend_services.py`, and `app/services/predictive_analytics.py` compute KPIs, trends, and forecasts used by both the UI and API.
- Profitability & inventory: `app/services/order_service.py`, `app/services/inventory_service.py`, `app/services/profit_calculator.py`, and `app/services/lot_analytics.py` keep stock levels, margin math, and shipped amounts accurate (see `app/models/orders.py` for shipping checks).
- Supporting helpers: `app/utils/` covers caching, context processors, decorators, email helpers, template filters, URL helpers, and logging configuration.
- Security: `app/extensions.py` stays responsible for Sentry, CSP/nonces, CSRF, caching, compression, and CORS headers. `app/security/auth_middleware.py` logs suspicious requests and enforces session integrity; `app/security/config.py` centralizes CSP, rate limits, upload restrictions, and optional API keys.

## Testing

- Run the suite with `python -m pytest`. Specific files include `tests/test_analytics.py`, `tests/test_business_intelligence.py`, `tests/test_enhanced_orders.py`, `tests/test_order_service.py`, and `tests/test_dashboard_metrics.py`.
- `pytest.ini` enforces consistent markers (`unit`, `integration`, `api`, `realtime`, `predictive`, etc.). Use `python app/run_tests.py --integration` (or `--api`, `--predictive`, `--realtime`, `--all`, `--coverage`, `-v`, etc.) to run categorized batches with the custom runner.

## Troubleshooting & Logs

- Check `logs/app.log*` for startup, request, and background-service diagnostics. `app/extensions.configure_logging` writes DB connection info on startup.
- Local state lives in `instance/profitability.db` (backup: `instance/profitability.db.backup`) and `tmp.db`. Delete/replace before sensitive debugging.
- Stale assets? Run `python scripts/manage_assets.py clean` or `npm run clean`, then rebuild (`npm run build` or `python scripts/manage_assets.py build --env production`).
- Missing vendor files? Re-run `python scripts/download_deps.py`; it validates SHA-256 checksums defined in `scripts/download_deps.py`.
- For caching or rate limiting issues, verify `CACHE_*`, `RATELIMIT_*`, and `SESSION_*` variables; production installs should prefer Redis and set `SESSION_COOKIE_SECURE=true`/`SESSION_COOKIE_SAMESITE=Lax`.
- Vendor/admin access: `/storefront/vendor` is guarded by `app/routes/storefront._ensure_vendor`, which now accepts both `is_vendor` and `is_admin` users (admins are treated as superusers). Use the Flask shell to seed the requested admin:

```python
from app import db
from app.models import User

admin = User(
    username='n_mbachia',
    email='mnventures2024@gmail.com',
    is_admin=True,
    is_vendor=True,
    confirmed=True
)
admin.set_password('mn_Adm!n@2026')
db.session.add(admin)
db.session.commit()
```

Regular vendors have `is_vendor=True` (non-admin), while general users rely on `is_user` semantics inside your UI logic. Once created, the superuser can log in, approve products, and view the vendor portal without hitting the 403 guard.
Alternatively, `flask create-admin` is now available (runs with the current `.venv/bin/flask` command) to bootstrap/update that account without typing the script, e.g. `flask create-admin --username n_mbachia --password 'mn_Adm!n@2026'`.

## Contributing

1. Keep new business rules within `app/services/` and add or update unit/integration tests in `tests/`.
2. Update `app/static/README.md`, `scripts/README.md`, `app/routes/ROUTES_README.md`, or this README when UI/asset/route contracts shift.
3. Run `python -m pytest` and `npm run build` before pushing; verify `/api/v1/docs` if you touched schemas.
4. Document configuration changes in `config/static_assets.json`, `config.py`, or `app/security/config.py` (see `app/security/SECURITY_IMPROVEMENTS.md`, `app/validators/VALIDATORS_IMPROVEMENTS.md`, and `app/services/SERVICES_IMPROVEMENTS.md` for detailed notes).
5. Use `scripts/admin/bi_admin.py` for CLI reports and `scripts/manage_assets.py` / `scripts/download_deps.py` for asset tooling.

## License

No license file is included. Contact the maintainers before redistributing or integrating this project into other codebases.
# flask_businessApp
