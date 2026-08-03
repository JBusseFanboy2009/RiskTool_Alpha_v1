# MyShares — Portfolio & Risiko-Analyse (Streamlit)

Portfolio-Dashboard mit yfinance-Marktdaten, Struktur-Analyse und Risiko-Tools.

## Lokal starten

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Öffne die URL aus der Konsole (standardmäßig `http://localhost:8501`).

## Auf share.streamlit.io veröffentlichen

1. Repository auf GitHub pushen
2. Auf [share.streamlit.io](https://share.streamlit.io) einloggen → **New app**
3. Repository, Branch und **Main file path** eintragen:

   **`streamlit_app.py`**

4. **Deploy** klicken

### Optional: Secrets (Produktion)

Unter *App settings → Secrets* z. B.:

```toml
SECRET_KEY = "dein-langer-zufalls-string"
```

Die App liest `SECRET_KEY` über `app/config.py` (Umgebungsvariable / `.env`).

## Hauptdatei

| Zweck | Pfad |
|--------|------|
| **Streamlit Entry Point (für Cloud)** | `streamlit_app.py` |
| UI-Seiten | `app/ui/` |
| Business-Logik | `app/services/` |
| Risiko-Berechnungen | `app/analytics/` |

## Features

- Login / Registrierung (SQLite)
- Portfolio-Übersicht mit Allokations-Chart
- MyShares: Positionen verwalten, Detail-Analyse, Sektor/Holdings-Charts
- Risiko-O-Meter (Gauge), Volatilität, Korrelations-Heatmap
- Drawdown-Verlauf, VaR/CVaR-Histogramme
- Branchen-spezifisches Stress-Testing

## Hinweis zur Datenbank

Auf Streamlit Cloud ist die SQLite-Datei (`myshares.db`) an den Container gebunden und kann bei Redeploys zurückgesetzt werden — für Demos ausreichend.
