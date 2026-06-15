import numpy as np
import pandas as pd
from scipy.stats import norm


def returns_from_prices(price_df: pd.DataFrame) -> pd.Series:
    if "Close" in price_df.columns:
        series = price_df["Close"]
    else:
        series = price_df.iloc[:, -1]
    return series.pct_change().dropna()


def annualized_volatility(returns: pd.Series, trading_days: int = 252) -> float:
    return float(returns.std() * np.sqrt(trading_days))


def correlation_matrix(returns_map: dict[str, pd.Series]) -> dict:
    df = pd.DataFrame(returns_map).dropna()
    return df.corr().fillna(0).to_dict()


def maximum_drawdown(returns: pd.Series) -> float:
    cumulative = (1 + returns).cumprod()
    drawdown = cumulative / cumulative.cummax() - 1
    return float(drawdown.min())


def drawdown_series(returns: pd.Series) -> dict[str, list]:
    cumulative = (1 + returns).cumprod()
    drawdown = cumulative / cumulative.cummax() - 1
    return {
        "dates": [str(i) for i in drawdown.index],
        "values": [float(v) for v in drawdown.values],
        "max_drawdown": float(drawdown.min()),
    }


def var_cvar_historical(returns: pd.Series, confidence: float = 0.95) -> tuple[float, float]:
    sorted_returns = np.sort(returns.dropna().values)
    index = int((1 - confidence) * len(sorted_returns))
    var = sorted_returns[index]
    cvar = sorted_returns[: index + 1].mean() if index >= 0 else var
    return float(var), float(cvar)


def var_parametric(returns: pd.Series, confidence: float = 0.95) -> float:
    mu = returns.mean()
    sigma = returns.std()
    z = norm.ppf(1 - confidence)
    return float(mu + z * sigma)
