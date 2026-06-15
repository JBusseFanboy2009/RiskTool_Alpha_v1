"""Sector-aware stress scenarios for portfolio simulation."""

from __future__ import annotations

# Sector shocks keyed by Yahoo / normalized sector labels (negative = loss).
STRESS_SCENARIOS: dict[str, dict] = {
    "tech_crash": {
        "label": "Tech-Sektor Crash",
        "description": "Technologie und Kommunikation stark betroffen, defensive Sektoren kaum.",
        "sector_shocks": {
            "Technology": -0.40,
            "Technologie": -0.40,
            "Communication Services": -0.35,
            "Kommunikation": -0.35,
            "Consumer Cyclical": -0.22,
            "Zyklische Konsumgüter": -0.22,
            "Financial Services": -0.18,
            "Finanzdienstleistungen": -0.18,
            "Consumer Defensive": -0.05,
            "Defensive Konsumgüter": -0.05,
            "Utilities": -0.03,
            "Versorger": -0.03,
            "Healthcare": -0.08,
            "Gesundheitswesen": -0.08,
            "Energy": -0.12,
            "Energie": -0.12,
        },
        "default_shock": -0.15,
    },
    "rate_shock": {
        "label": "Zins-Schock",
        "description": "Growth/Tech leidet, Versorger und Finanzen moderat, defensive stabil.",
        "sector_shocks": {
            "Technology": -0.28,
            "Technologie": -0.28,
            "Real Estate": -0.25,
            "Immobilien": -0.25,
            "Financial Services": -0.12,
            "Finanzdienstleistungen": -0.12,
            "Utilities": -0.06,
            "Versorger": -0.06,
            "Consumer Defensive": -0.04,
            "Defensive Konsumgüter": -0.04,
        },
        "default_shock": -0.12,
    },
    "market_wide": {
        "label": "Breiter Marktcrash",
        "description": "Gleichmäßiger Einbruch über alle Sektoren (Intensität steuerbar).",
        "sector_shocks": {},
        "default_shock": -0.25,
    },
    "energy_spike": {
        "label": "Energie-Krise",
        "description": "Energie und Industrie stark, Technologie moderat, Versorger leicht positiv.",
        "sector_shocks": {
            "Energy": -0.15,
            "Energie": -0.15,
            "Industrials": -0.20,
            "Industrie": -0.20,
            "Basic Materials": -0.12,
            "Grundstoffe": -0.12,
            "Technology": -0.18,
            "Technologie": -0.18,
            "Utilities": 0.02,
            "Versorger": 0.02,
            "Consumer Defensive": -0.06,
            "Defensive Konsumgüter": -0.06,
        },
        "default_shock": -0.14,
    },
}


def list_scenarios() -> list[dict]:
    return [
        {
            "id": key,
            "label": cfg["label"],
            "description": cfg["description"],
            "default_shock": cfg["default_shock"],
        }
        for key, cfg in STRESS_SCENARIOS.items()
    ]


def sector_shock_for(
    sector: str,
    scenario_id: str,
    intensity: float = 1.0,
    global_shock: float | None = None,
) -> float:
    cfg = STRESS_SCENARIOS.get(scenario_id) or STRESS_SCENARIOS["market_wide"]
    shocks = cfg.get("sector_shocks") or {}
    base = shocks.get(sector)
    if base is None:
        for key, val in shocks.items():
            if key.lower() in sector.lower() or sector.lower() in key.lower():
                base = val
                break
    if base is None:
        base = global_shock if global_shock is not None else cfg["default_shock"]
    return float(base) * float(intensity)
