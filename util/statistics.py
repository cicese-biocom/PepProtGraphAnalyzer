from scipy import stats
import pandas as pd


def get_stats(data: pd.Series):
    if data.empty or data.isna().all():
        return {
            "count": 0, "mean": None, "std": None, "min": None,
            "p25": None, "p50": None, "p75": None, "max": None,
            "skewness": None, "kurtosis": None
        }

    std_dev = data.std()

    stats_dict = {
        "count": data.count(),
        "min": data.min(),
        "mean": data.mean(),
        "std": std_dev,
        "p25": data.quantile(0.25),
        "p50": data.quantile(0.50),
        "p75": data.quantile(0.75),
        "max": data.max()
    }

    if std_dev > 1e-8:
        stats_dict["skewness"] = stats.skew(data.dropna())
        stats_dict["kurtosis"] = stats.kurtosis(data.dropna(), fisher=False)
    else:
        stats_dict["skewness"] = None
        stats_dict["kurtosis"] = None

    return stats_dict
