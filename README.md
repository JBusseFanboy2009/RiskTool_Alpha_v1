# MyShares - Finance & Risk Analysis App (Scaffold)

## Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Current Scope

- FastAPI backend with modular routers (`auth`, `positions`, `portfolio`, `market`, `risk`)
- SQLite + SQLAlchemy models for users, portfolios, positions, instrument mappings, market cache
- JWT login/register flow
- SPA shell with sidebar navigation
- Portfolio overview pie chart and MyShares management
- Position detail with price chart and structure analysis endpoint
- Risk endpoints: Risk-O-Meter, Volatility, Correlation, Maximum Drawdown, VaR/CVaR, Stress test
- Basic market-data cache in SQLite for quote/history calls

## Next Step Suggestions

- Add Alembic migrations
- Improve ISIN-to-Ticker mapping persistence and exchange normalization
- Add robust ETF holdings parsing (multiple Yahoo structures)
- Add test suite (unit + API)
- Harden auth/session handling for production
