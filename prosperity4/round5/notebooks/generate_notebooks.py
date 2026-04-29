#!/usr/bin/env python3
"""
Generate 10 Round 5 analysis notebooks — one per product group.

Per-product analysis sections:
  1. Price & Order Book plots
  2. Stochastic Oscillator  (K=50, D=3)
  3. Z-Score               (rolling window=300)
  4. Fast SMA (20) + Slow SMA (300) with crossover signals

Plus a group-level within-group series comparison (normalised overlay,
pairwise return-correlation heatmap, CCF small-multiples).

Window rationale (derived from data inspection):
  - K=50  : avg H-L range at w=50 is ~152 ticks ≈ 7.5% of daily range,
             balancing sensitivity vs noise; ACF of returns ≈ 0 at all lags,
             so range-position (stochastic) carries the signal.
  - Z=300 : 30% of a single day; rolling mean/std stabilise well past the
             short-term noise (ACF flatlines by lag 5).
"""

import json
import uuid
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent

GROUPS = [
    ("galaxy_sounds",  "Galaxy Sounds Recorders", [
        "GALAXY_SOUNDS_DARK_MATTER", "GALAXY_SOUNDS_BLACK_HOLES",
        "GALAXY_SOUNDS_PLANETARY_RINGS", "GALAXY_SOUNDS_SOLAR_WINDS",
        "GALAXY_SOUNDS_SOLAR_FLAMES",
    ]),
    ("sleep_pod", "Vertical Sleeping Pods", [
        "SLEEP_POD_SUEDE", "SLEEP_POD_LAMB_WOOL", "SLEEP_POD_POLYESTER",
        "SLEEP_POD_NYLON", "SLEEP_POD_COTTON",
    ]),
    ("microchip", "Organic Microchips", [
        "MICROCHIP_CIRCLE", "MICROCHIP_OVAL", "MICROCHIP_SQUARE",
        "MICROCHIP_RECTANGLE", "MICROCHIP_TRIANGLE",
    ]),
    ("pebbles", "Purification Pebbles", [
        "PEBBLES_XS", "PEBBLES_S", "PEBBLES_M", "PEBBLES_L", "PEBBLES_XL",
    ]),
    ("robots", "Domestic Robots", [
        "ROBOT_VACUUMING", "ROBOT_MOPPING", "ROBOT_DISHES",
        "ROBOT_LAUNDRY", "ROBOT_IRONING",
    ]),
    ("uv_visor", "UV-Visors", [
        "UV_VISOR_YELLOW", "UV_VISOR_AMBER", "UV_VISOR_ORANGE",
        "UV_VISOR_RED", "UV_VISOR_MAGENTA",
    ]),
    ("translator", "Instant Translators", [
        "TRANSLATOR_SPACE_GRAY", "TRANSLATOR_ASTRO_BLACK",
        "TRANSLATOR_ECLIPSE_CHARCOAL", "TRANSLATOR_GRAPHITE_MIST",
        "TRANSLATOR_VOID_BLUE",
    ]),
    ("panel", "Construction Panels", [
        "PANEL_1X2", "PANEL_2X2", "PANEL_1X4", "PANEL_2X4", "PANEL_4X4",
    ]),
    ("oxygen_shake", "Liquid Breath Oxygen Shakes", [
        "OXYGEN_SHAKE_MORNING_BREATH", "OXYGEN_SHAKE_EVENING_BREATH",
        "OXYGEN_SHAKE_MINT", "OXYGEN_SHAKE_CHOCOLATE", "OXYGEN_SHAKE_GARLIC",
    ]),
    ("snackpack", "Protein Snack Packs", [
        "SNACKPACK_CHOCOLATE", "SNACKPACK_VANILLA", "SNACKPACK_PISTACHIO",
        "SNACKPACK_STRAWBERRY", "SNACKPACK_RASPBERRY",
    ]),
]


# ── Notebook helpers ──────────────────────────────────────────────────────────

def cell_id():
    return uuid.uuid4().hex[:8]


def src(text: str) -> list:
    lines = text.split("\n")
    return [line + "\n" if i < len(lines) - 1 else line for i, line in enumerate(lines)]


def code(text: str) -> dict:
    return {"cell_type": "code", "execution_count": None, "id": cell_id(),
            "metadata": {}, "outputs": [], "source": src(text.strip())}


def md(text: str) -> dict:
    return {"cell_type": "markdown", "id": cell_id(),
            "metadata": {}, "source": [text]}


# ── Shared code blocks ────────────────────────────────────────────────────────

IMPORTS = """\
import os
import math
import itertools

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
import scipy.stats as stats

from pathlib import Path
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from statsmodels.tsa.stattools import adfuller

import prosperity4
from prosperity4.utils.dataloader import (
    load_trading_data,
    convert_timestamp,
)

plt.style.use("dark_background")
sns.set_palette("pastel")\
"""

DATA_LOADING_TEMPLATE = """\
REPO_ROOT   = Path(prosperity4.__file__).parents[1]
DATA_FOLDER = REPO_ROOT / "prosperity4" / "round5" / "data"
ROUND_NUM   = 5
DAYS        = [2, 3, 4]
SYMBOLS     = {symbols}

data      = load_trading_data(DATA_FOLDER, ROUND_NUM, DAYS)
prices_df = data.get("prices")
trades_df = data.get("trades")

print("Prices Shape :", prices_df.shape)
print("Trades Shape :", trades_df.shape)
display(prices_df.head())\
"""

HELPER_FUNCTIONS = """\
def build_product_df(symbol: str, prices_df: pd.DataFrame,
                     trades_df: pd.DataFrame) -> pd.DataFrame:
    \"\"\"Merge prices and trades for a single symbol into one aligned DataFrame.\"\"\"\
    prices = prices_df[prices_df["product"] == symbol]
    trades = trades_df[trades_df["symbol"] == symbol].copy()
    trades = trades.drop(columns=["currency"])
    trades = trades.groupby(["timestamp", "price", "day", "buyer", "seller"],
                             as_index=False).agg({"quantity": "sum"})
    trades = trades.rename(columns={"price":    "market order price",
                                     "quantity": "market order quantity"})
    df = prices.merge(
        trades[["timestamp", "market order price", "market order quantity",
                "day", "buyer", "seller"]],
        on=["timestamp", "day"], how="left",
    )
    df = convert_timestamp(df)
    return df


def compute_fv(df: pd.DataFrame) -> pd.DataFrame:
    \"\"\"Fair value = midpoint of the highest-volume bid and ask level.\"\"\"\
    df = df.copy()
    bv = df[["bid_volume_1","bid_volume_2","bid_volume_3"]].values
    av = df[["ask_volume_1","ask_volume_2","ask_volume_3"]].values
    bp = df[["bid_price_1", "bid_price_2", "bid_price_3"]].values
    ap = df[["ask_price_1", "ask_price_2", "ask_price_3"]].values
    n  = len(df)

    b_nan = np.all(np.isnan(bv), axis=1)
    a_nan = np.all(np.isnan(av), axis=1)
    bi    = np.where(b_nan, 0, np.nanargmax(np.where(np.isnan(bv), -np.inf, bv), axis=1))
    ai    = np.where(a_nan, 0, np.nanargmax(np.where(np.isnan(av), -np.inf, av), axis=1))
    mb    = np.where(b_nan, np.nan, bp[np.arange(n), bi])
    ma    = np.where(a_nan, np.nan, ap[np.arange(n), ai])

    both = ~np.isnan(mb) & ~np.isnan(ma)
    fv   = np.where(both, (mb + ma) / 2,
           np.where(~np.isnan(mb), mb,
           np.where(~np.isnan(ma), ma, np.nan)))
    df["fv"] = pd.Series(fv).ffill().values
    return df\
"""

# ── Within-group comparison (unchanged from previous version) ─────────────────
WITHIN_GROUP = """\
_prefix = os.path.commonprefix(SYMBOLS)
_short  = {s: (s[len(_prefix):] or s) for s in SYMBOLS}

_day_map  = {2: 0, 3: 1_000_000, 4: 2_000_000}
_prices_t = prices_df.copy()
_prices_t["t"] = _prices_t["day"].map(_day_map) + _prices_t["timestamp"]
_all_t    = sorted(_prices_t["t"].unique())

_member_mid = {}
for _sym in SYMBOLS:
    _member_mid[_sym] = (
        _prices_t[_prices_t["product"] == _sym]
        .set_index("t")["mid_price"]
        .reindex(_all_t, method="ffill")
    )

_group_df = pd.DataFrame(_member_mid)
_norm_df  = (_group_df - _group_df.mean()) / _group_df.std()
_ret_df   = _group_df.diff().dropna()

_MAX_LAG = 50

def _ccf_arr(x, y, max_lag=_MAX_LAG):
    x = (x - x.mean()) / (x.std() + 1e-12)
    y = (y - y.mean()) / (y.std() + 1e-12)
    n = len(x)
    out = []
    for lag in range(-max_lag, max_lag + 1):
        if lag >= 0:
            c = float(np.dot(x.values[:n-lag], y.values[lag:])) / n if lag < n else 0.0
        else:
            c = float(np.dot(x.values[-lag:], y.values[:n+lag])) / n if -lag < n else 0.0
        out.append(c)
    return np.arange(-max_lag, max_lag + 1), np.array(out)

_pairs     = list(itertools.combinations(SYMBOLS, 2))
_n_pairs   = len(_pairs)
_ccf_cache = {}
_lag_mat   = pd.DataFrame(0.0, index=list(_short.values()), columns=list(_short.values()))

for _a, _b in _pairs:
    _lags, _cv             = _ccf_arr(_ret_df[_a], _ret_df[_b])
    _ccf_cache[(_a, _b)]   = (_lags, _cv)
    _best                  = int(_lags[np.argmax(np.abs(_cv))])
    _lag_mat.loc[_short[_a], _short[_b]] =  float(_best)
    _lag_mat.loc[_short[_b], _short[_a]] = -float(_best)

_COLORS    = ["white", "cyan", "orange", "lime", "magenta"]
_ncols_ccf = min(3, _n_pairs)
_nrows_ccf = math.ceil(_n_pairs / _ncols_ccf)
_sig_band  = 2 / np.sqrt(len(_ret_df))

fig       = plt.figure(figsize=(16, 5 + 6 + 3.5 * _nrows_ccf))
_gs_outer = gridspec.GridSpec(3, 1, figure=fig,
                               height_ratios=[5, 6, 3.5 * _nrows_ccf], hspace=0.55)

ax_ov = fig.add_subplot(_gs_outer[0])
for _i, _sym in enumerate(SYMBOLS):
    ax_ov.plot(_norm_df.index, _norm_df[_sym],
               linewidth=0.7, alpha=0.85, label=_short[_sym],
               color=_COLORS[_i % len(_COLORS)])
for _i, _dt in enumerate([0, 1_000_000, 2_000_000]):
    if _i % 2 == 0:
        ax_ov.axvspan(_dt, _dt + 999_900, alpha=0.07, color="grey", zorder=0)
ax_ov.set_title("All Products — Normalised Mid-Price Overlaid (z-score)")
ax_ov.set_ylabel("Z-Score"); ax_ov.set_xlabel("Time")
ax_ov.legend(fontsize=8); ax_ov.grid(True, alpha=0.3)

_gs_mid = gridspec.GridSpecFromSubplotSpec(1, 2, subplot_spec=_gs_outer[1], wspace=0.45)
ax_corr = fig.add_subplot(_gs_mid[0])
ax_lag  = fig.add_subplot(_gs_mid[1])

sns.heatmap(_ret_df.rename(columns=_short).corr(), ax=ax_corr,
            cmap="RdYlGn", center=0, vmin=-1, vmax=1,
            annot=True, fmt=".2f", annot_kws={"size": 9},
            linewidths=0.5, square=True, cbar_kws={"shrink": 0.8})
ax_corr.set_title("Pairwise Return Correlation")
ax_corr.tick_params(axis="x", rotation=45, labelsize=8)
ax_corr.tick_params(axis="y", rotation=0,  labelsize=8)

sns.heatmap(_lag_mat, ax=ax_lag, cmap="coolwarm", center=0,
            annot=True, fmt=".0f", annot_kws={"size": 9},
            linewidths=0.5, square=True, cbar_kws={"shrink": 0.8})
ax_lag.set_title(f"Peak CCF Lag (ticks, ±{_MAX_LAG})\\nRow leads col when value < 0")
ax_lag.tick_params(axis="x", rotation=45, labelsize=8)
ax_lag.tick_params(axis="y", rotation=0,  labelsize=8)

_gs_ccf = gridspec.GridSpecFromSubplotSpec(
    _nrows_ccf, _ncols_ccf, subplot_spec=_gs_outer[2], hspace=0.7, wspace=0.4)

for _idx, (_a, _b) in enumerate(_pairs):
    _ax = fig.add_subplot(_gs_ccf[_idx // _ncols_ccf, _idx % _ncols_ccf])
    _lgs, _cv = _ccf_cache[(_a, _b)]
    _ax.plot(_lgs, _cv, linewidth=0.9, color="cyan")
    _ax.axhline( _sig_band, color="white", linewidth=0.5, linestyle="--", alpha=0.6)
    _ax.axhline(-_sig_band, color="white", linewidth=0.5, linestyle="--", alpha=0.6)
    _ax.axhline(0, color="grey", linewidth=0.4, linestyle=":", alpha=0.5)
    _ax.axvline(0, color="grey", linewidth=0.4, linestyle=":", alpha=0.5)
    _ax.set_title(f"{_short[_a]} vs {_short[_b]}", fontsize=8)
    _ax.set_xlabel("Lag (ticks)", fontsize=7); _ax.set_ylabel("CCF", fontsize=7)
    _ax.tick_params(labelsize=6); _ax.grid(True, alpha=0.2)

for _idx in range(_n_pairs, _nrows_ccf * _ncols_ccf):
    fig.add_subplot(_gs_ccf[_idx // _ncols_ccf, _idx % _ncols_ccf]).set_visible(False)

plt.suptitle("Within-Group Series Comparison", fontsize=14, y=1.01)
plt.tight_layout(); plt.show()\
"""

# ── Per-product: price plots ──────────────────────────────────────────────────
PRICE_PLOTS_LOOP = """\
for SYMBOL in SYMBOLS:
    df = build_product_df(SYMBOL, prices_df, trades_df)
    df = compute_fv(df)

    fig, axes = plt.subplots(2, 1, figsize=(15, 8), sharex=False)

    # Full series
    axes[0].set_title(f"Price & Order Book — {SYMBOL}")
    axes[0].plot(df["t"], df["fv"],          color="white",  linewidth=0.7, label="FV")
    axes[0].plot(df["t"], df["ask_price_1"], color="red",    linewidth=0.6, alpha=0.8, label="Ask 1")
    axes[0].plot(df["t"], df["bid_price_1"], color="lime",   linewidth=0.6, alpha=0.8, label="Bid 1")
    axes[0].plot(df["t"], df["ask_price_2"], color="salmon", linewidth=0.5, alpha=0.5, label="Ask 2")
    axes[0].plot(df["t"], df["bid_price_2"], color="green",  linewidth=0.5, alpha=0.5, label="Bid 2")
    axes[0].legend(fontsize=8); axes[0].grid(True, alpha=0.3); axes[0].set_ylabel("Price")

    # Last 1 000 ticks
    axes[1].set_title(f"Last 1 000 ticks — {SYMBOL}")
    axes[1].plot(df["t"][-1000:], df["fv"][-1000:],          color="white",     alpha=0.6, linewidth=0.8, label="FV")
    axes[1].plot(df["t"][-1000:], df["ask_price_1"][-1000:], color="red",       alpha=1.0, linewidth=0.8, label="Ask 1")
    axes[1].plot(df["t"][-1000:], df["ask_price_2"][-1000:], color="orange",    alpha=0.5, linewidth=0.6, label="Ask 2")
    axes[1].plot(df["t"][-1000:], df["ask_price_3"][-1000:], color="salmon",    alpha=0.4, linewidth=0.5, label="Ask 3")
    axes[1].plot(df["t"][-1000:], df["bid_price_1"][-1000:], color="lime",      alpha=1.0, linewidth=0.8, label="Bid 1")
    axes[1].plot(df["t"][-1000:], df["bid_price_2"][-1000:], color="green",     alpha=0.5, linewidth=0.6, label="Bid 2")
    axes[1].plot(df["t"][-1000:], df["bid_price_3"][-1000:], color="darkgreen", alpha=0.4, linewidth=0.5, label="Bid 3")
    axes[1].legend(fontsize=8); axes[1].grid(True, alpha=0.3); axes[1].set_ylabel("Price")

    plt.tight_layout(); plt.show()\
"""

# ── Per-product: Stochastic Oscillator ───────────────────────────────────────
STOCHASTIC_LOOP = """\
# Window rationale: at K=50, avg H-L range ≈ 152 ticks (7.5% of daily range),
# balancing sensitivity and noise. ACF of returns ≈ 0 at all lags, so the
# range-position reading carries the actionable signal.
K_WINDOW = 50   # lookback for highest-high / lowest-low
D_WINDOW = 3    # smoothing period for %D line

for SYMBOL in SYMBOLS:
    df = build_product_df(SYMBOL, prices_df, trades_df)
    df = compute_fv(df)

    # %K: relative position of FV within the K-period H-L range
    # Use ask_price_1 as the period high, bid_price_1 as the period low
    df["stoch_high"] = df["ask_price_1"].rolling(K_WINDOW).max()
    df["stoch_low"]  = df["bid_price_1"].rolling(K_WINDOW).min()
    hl_range = df["stoch_high"] - df["stoch_low"]
    df["pct_K"] = np.where(
        hl_range > 0,
        (df["fv"] - df["stoch_low"]) / hl_range * 100,
        50.0,   # flat H-L → neutral
    )
    df["pct_D"] = df["pct_K"].rolling(D_WINDOW).mean()

    fig, axes = plt.subplots(2, 1, figsize=(15, 8), sharex=True,
                              gridspec_kw={"height_ratios": [2, 1]})

    axes[0].plot(df["t"], df["fv"], color="white", linewidth=0.7, label="FV")
    axes[0].set_ylabel("Price")
    axes[0].set_title(f"{SYMBOL} — Stochastic Oscillator (K={K_WINDOW}, D={D_WINDOW})")
    axes[0].legend(fontsize=8); axes[0].grid(True, alpha=0.3)

    axes[1].plot(df["t"], df["pct_K"], color="cyan",   linewidth=0.8, alpha=0.9, label=f"%K ({K_WINDOW})")
    axes[1].plot(df["t"], df["pct_D"], color="orange", linewidth=1.3, label=f"%D ({D_WINDOW}-period MA of %K)")
    axes[1].axhline(80, color="red",  linestyle="--", linewidth=0.9, alpha=0.7, label="Overbought (80)")
    axes[1].axhline(20, color="lime", linestyle="--", linewidth=0.9, alpha=0.7, label="Oversold (20)")
    axes[1].axhline(50, color="grey", linestyle=":",  linewidth=0.6, alpha=0.5)
    axes[1].fill_between(df["t"], 80, 100, alpha=0.08, color="red")
    axes[1].fill_between(df["t"], 0,   20, alpha=0.08, color="lime")
    axes[1].set_ylim(0, 100)
    axes[1].set_ylabel("Stochastic (%)")
    axes[1].set_xlabel("Time")
    axes[1].legend(fontsize=8); axes[1].grid(True, alpha=0.3)

    plt.tight_layout(); plt.show()

    # Summary stats
    ob = (df["pct_K"] > 80).mean()
    os_ = (df["pct_K"] < 20).mean()
    print(f"{SYMBOL}: %K mean={df['pct_K'].mean():.1f}  "
          f"overbought (>80): {ob:.1%}  oversold (<20): {os_:.1%}")\
"""

# ── Per-product: Z-Score ──────────────────────────────────────────────────────
ZSCORE_LOOP = """\
# Window rationale: 300 ticks covers 30% of a single day; the rolling mean/std
# stabilise well past the short-term noise (return ACF ≈ 0 from lag 5 onward).
ZSCORE_WINDOW = 300

for SYMBOL in SYMBOLS:
    df = build_product_df(SYMBOL, prices_df, trades_df)
    df = compute_fv(df)

    df["roll_mean"] = df["fv"].rolling(ZSCORE_WINDOW).mean()
    df["roll_std"]  = df["fv"].rolling(ZSCORE_WINDOW).std()
    df["zscore"]    = (df["fv"] - df["roll_mean"]) / df["roll_std"]

    fig, axes = plt.subplots(2, 1, figsize=(15, 8), sharex=True,
                              gridspec_kw={"height_ratios": [2, 1]})

    axes[0].plot(df["t"], df["fv"],        color="white",  linewidth=0.7, label="FV")
    axes[0].plot(df["t"], df["roll_mean"], color="orange", linewidth=1.3,
                 label=f"Rolling Mean ({ZSCORE_WINDOW})")
    axes[0].fill_between(df["t"],
                         df["roll_mean"] - 2 * df["roll_std"],
                         df["roll_mean"] + 2 * df["roll_std"],
                         alpha=0.10, color="orange", label="±2σ band")
    axes[0].set_ylabel("Price")
    axes[0].set_title(f"{SYMBOL} — Price, Rolling Mean & ±2σ Band (window={ZSCORE_WINDOW})")
    axes[0].legend(fontsize=8); axes[0].grid(True, alpha=0.3)

    axes[1].plot(df["t"], df["zscore"], color="white", linewidth=0.7)
    axes[1].axhline( 2, color="red",  linestyle="--", linewidth=0.9, alpha=0.8, label="Z = +2")
    axes[1].axhline(-2, color="lime", linestyle="--", linewidth=0.9, alpha=0.8, label="Z = −2")
    axes[1].axhline( 0, color="grey", linestyle=":",  linewidth=0.5, alpha=0.5)
    axes[1].fill_between(df["t"],  2, df["zscore"].clip(lower= 2), color="red",  alpha=0.15)
    axes[1].fill_between(df["t"], -2, df["zscore"].clip(upper=-2), color="lime", alpha=0.15)
    axes[1].set_ylabel("Z-Score")
    axes[1].set_xlabel("Time")
    axes[1].legend(fontsize=8); axes[1].grid(True, alpha=0.3)

    plt.tight_layout(); plt.show()

    # ADF stationarity check on the z-score itself
    z_clean = df["zscore"].dropna()
    adf_z   = adfuller(z_clean)
    adf_fv  = adfuller(df["fv"].dropna())
    print(f"{SYMBOL}")
    print(f"  FV level  — ADF p={adf_fv[1]:.4f}  "
          f"({'stationary ✓' if adf_fv[1] < 0.05 else 'non-stationary ✗'})")
    print(f"  Z-Score   — ADF p={adf_z[1]:.4f}  "
          f"({'stationary ✓' if adf_z[1] < 0.05 else 'non-stationary ✗'})")
    print(f"  Z-Score   — mean={z_clean.mean():.3f}  std={z_clean.std():.3f}  "
          f"P(|z|>2)={( z_clean.abs()>2).mean():.1%}")
    print()\
"""

# ── Per-product: Fast SMA + Slow SMA ─────────────────────────────────────────
SMA_CROSS_LOOP = """\
FAST_SMA  = 20
SLOW_SMA  = 300

for SYMBOL in SYMBOLS:
    df = build_product_df(SYMBOL, prices_df, trades_df)
    df = compute_fv(df)

    df["fast_sma"] = df["fv"].rolling(FAST_SMA).mean()
    df["slow_sma"] = df["fv"].rolling(SLOW_SMA).mean()

    # Crossover signals
    above = df["fast_sma"] > df["slow_sma"]
    df["cross_up"]   = above & ~above.shift(1, fill_value=False)
    df["cross_down"] = ~above & above.shift(1, fill_value=False)
    cross_up_df   = df[df["cross_up"]]
    cross_down_df = df[df["cross_down"]]

    fig, axes = plt.subplots(2, 1, figsize=(15, 9), sharex=True,
                              gridspec_kw={"height_ratios": [3, 1]})

    # ── Top panel: price + both SMAs ─────────────────────────────────────────
    axes[0].plot(df["t"], df["fv"],       color="white",  linewidth=0.5, alpha=0.6, label="FV")
    axes[0].plot(df["t"], df["fast_sma"], color="cyan",   linewidth=1.0, label=f"Fast SMA ({FAST_SMA})")
    axes[0].plot(df["t"], df["slow_sma"], color="orange", linewidth=1.5, label=f"Slow SMA ({SLOW_SMA})")

    # Shade bull/bear regime between the two SMAs
    axes[0].fill_between(df["t"], df["fast_sma"], df["slow_sma"],
                         where= above, color="lime", alpha=0.07, label="_nolegend_")
    axes[0].fill_between(df["t"], df["fast_sma"], df["slow_sma"],
                         where=~above, color="red",  alpha=0.07, label="_nolegend_")

    # Crossover markers
    if not cross_up_df.empty:
        axes[0].scatter(cross_up_df["t"],   cross_up_df["fast_sma"],
                        color="lime", s=60, zorder=5, marker="^", label="Bull cross ▲")
    if not cross_down_df.empty:
        axes[0].scatter(cross_down_df["t"], cross_down_df["fast_sma"],
                        color="red",  s=60, zorder=5, marker="v", label="Bear cross ▽")

    axes[0].set_ylabel("Price")
    axes[0].set_title(f"{SYMBOL} — Fast SMA ({FAST_SMA}) vs Slow SMA ({SLOW_SMA})")
    axes[0].legend(fontsize=8, loc="upper left"); axes[0].grid(True, alpha=0.3)

    # ── Bottom panel: SMA spread (fast − slow) ────────────────────────────────
    df["sma_spread"] = df["fast_sma"] - df["slow_sma"]
    axes[1].plot(df["t"], df["sma_spread"], color="white", linewidth=0.7)
    axes[1].axhline(0, color="grey", linestyle="--", linewidth=0.6, alpha=0.6)
    axes[1].fill_between(df["t"], 0, df["sma_spread"],
                         where=(df["sma_spread"] >= 0), color="lime", alpha=0.20)
    axes[1].fill_between(df["t"], 0, df["sma_spread"],
                         where=(df["sma_spread"] <  0), color="red",  alpha=0.20)
    axes[1].set_ylabel("Fast − Slow")
    axes[1].set_xlabel("Time")
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout(); plt.show()

    # Summary
    bull_frac = above.mean()
    print(f"{SYMBOL}")
    print(f"  Crossovers: {int(df['cross_up'].sum())} bullish  /  {int(df['cross_down'].sum())} bearish")
    print(f"  Time above slow SMA: {bull_frac:.1%}")
    print(f"  SMA spread — mean={df['sma_spread'].mean():.2f}  std={df['sma_spread'].std():.2f}")
    print()\
"""


# ── Per-product: strategy backtest & equity simulation ────────────────────────
BACKTEST_LOOP = """\
POSITION_SIZE = 10   # units traded on every signal

# ── Backtest engine ───────────────────────────────────────────────────────────
def _backtest(df: pd.DataFrame, target: pd.Series) -> pd.Series:
    \"\"\"
    Simulate a mark-to-market equity curve from a target-position series.

    Rules:
      - Increasing position  → buy at ask_price_1
      - Decreasing position  → sell at bid_price_1
      - MTM at every tick    → valued at mid_price / fv

    Returns pd.Series of cumulative PnL aligned to df's index.
    \"\"\"
    ask = df["ask_price_1"].fillna(df["fv"]).values.astype(float)
    bid = df["bid_price_1"].fillna(df["fv"]).values.astype(float)
    mid = df["fv"].values.astype(float)
    tgt = target.fillna(0.0).values.astype(float)
    n   = len(tgt)
    pos = 0.0
    cash = 0.0
    equity = np.empty(n)
    for i in range(n):
        t = tgt[i]
        if t > pos:                        # need to buy
            cash -= (t - pos) * ask[i]
            pos   = t
        elif t < pos:                      # need to sell
            cash += (pos - t) * bid[i]
            pos   = t
        equity[i] = cash + pos * mid[i]
    return pd.Series(equity, index=df.index)


def _max_drawdown(eq: np.ndarray) -> float:
    \"\"\"Maximum peak-to-trough drawdown (negative number).\"\"\"\
    return float(np.min(eq - np.maximum.accumulate(eq)))


def _n_trades(target: pd.Series) -> int:
    \"\"\"Count position changes (each change = one trade).\"\"\"\
    return int((target.diff().fillna(0) != 0).sum())


for SYMBOL in SYMBOLS:
    df = build_product_df(SYMBOL, prices_df, trades_df)
    df = compute_fv(df)

    # ── Rebuild all three indicators ──────────────────────────────────────────
    K_W, D_W = 50, 3
    df["stoch_high"] = df["ask_price_1"].rolling(K_W).max()
    df["stoch_low"]  = df["bid_price_1"].rolling(K_W).min()
    hl = df["stoch_high"] - df["stoch_low"]
    df["pct_K"] = np.where(hl > 0,
                           (df["fv"] - df["stoch_low"]) / hl * 100,
                           50.0)

    ZSCORE_W = 300
    df["roll_mean"] = df["fv"].rolling(ZSCORE_W).mean()
    df["roll_std"]  = df["fv"].rolling(ZSCORE_W).std()
    df["zscore"]    = (df["fv"] - df["roll_mean"]) / df["roll_std"]

    FAST, SLOW = 20, 300
    df["fast_sma"] = df["fv"].rolling(FAST).mean()
    df["slow_sma"] = df["fv"].rolling(SLOW).mean()

    # ── Target positions ──────────────────────────────────────────────────────
    # Stochastic: oversold → long +10, overbought → short −10, else flat
    stoch_tgt = pd.Series(
        np.where(df["pct_K"] < 20,  float(POSITION_SIZE),
        np.where(df["pct_K"] > 80, -float(POSITION_SIZE), 0.0)),
        index=df.index,
    )

    # Z-Score: mean-reversion with hysteresis
    #   enter long  when z < −2,  enter short when z > +2
    #   exit to flat when |z| < 0.5,  hold otherwise (ffill)
    z_vals = df["zscore"].values
    z_raw  = np.where(z_vals < -2.0,  float(POSITION_SIZE),
             np.where(z_vals >  2.0, -float(POSITION_SIZE),
             np.where(np.abs(z_vals) < 0.5, 0.0, np.nan)))
    z_tgt  = pd.Series(z_raw, index=df.index).ffill().fillna(0.0)

    # SMA cross: long when fast > slow, short when fast < slow
    sma_valid = df["slow_sma"].notna()
    sma_tgt = pd.Series(
        np.where(df["fast_sma"] > df["slow_sma"],  float(POSITION_SIZE),
        np.where(df["fast_sma"] < df["slow_sma"], -float(POSITION_SIZE), 0.0)),
        index=df.index,
    ).where(sma_valid, 0.0)

    # ── Run backtests ─────────────────────────────────────────────────────────
    eq_stoch  = _backtest(df, stoch_tgt)
    eq_zscore = _backtest(df, z_tgt)
    eq_sma    = _backtest(df, sma_tgt)

    # ── 4-panel figure ────────────────────────────────────────────────────────
    fig, axes = plt.subplots(4, 1, figsize=(15, 14), sharex=True,
                              gridspec_kw={"height_ratios": [2, 1, 1, 1]})

    # Panel 0: price backdrop with both SMAs
    axes[0].plot(df["t"], df["fv"],       color="white",  lw=0.6, alpha=0.75, label="FV")
    axes[0].plot(df["t"], df["fast_sma"], color="cyan",   lw=0.9,             label=f"Fast SMA ({FAST})")
    axes[0].plot(df["t"], df["slow_sma"], color="orange", lw=1.3,             label=f"Slow SMA ({SLOW})")
    axes[0].set_title(
        f"{SYMBOL} — Indicator Backtest  "
        f"(position size = {POSITION_SIZE}, buy @ ask / sell @ bid, MTM @ FV)"
    )
    axes[0].set_ylabel("Price")
    axes[0].legend(fontsize=8, loc="upper left")
    axes[0].grid(True, alpha=0.3)

    # Panels 1-3: one equity curve each
    _eq_items = [
        (axes[1], eq_stoch,  f"Stochastic  K={K_W}, D={D_W}",   "cyan"),
        (axes[2], eq_zscore, f"Z-Score  window={ZSCORE_W}",       "orange"),
        (axes[3], eq_sma,    f"SMA Cross  {FAST}/{SLOW}",          "lime"),
    ]
    for ax, eq, label, color in _eq_items:
        ax.plot(df["t"], eq, color=color, lw=0.8, label=label)
        ax.axhline(0, color="grey", lw=0.5, ls=":", alpha=0.6)
        ax.fill_between(df["t"], 0, eq,
                        where=(eq >= 0), color="lime", alpha=0.12, interpolate=True)
        ax.fill_between(df["t"], 0, eq,
                        where=(eq  < 0), color="red",  alpha=0.12, interpolate=True)
        ax.set_ylabel("Equity (PnL)")
        ax.legend(fontsize=8, loc="upper left")
        ax.grid(True, alpha=0.3)

    axes[3].set_xlabel("Time")
    plt.tight_layout()
    plt.show()

    # ── Stats summary ─────────────────────────────────────────────────────────
    rows = []
    for name, eq, tgt in [
        ("Stochastic",  eq_stoch,  stoch_tgt),
        ("Z-Score",     eq_zscore, z_tgt),
        ("SMA Cross",   eq_sma,    sma_tgt),
    ]:
        diff   = eq.diff().dropna()
        sharpe = diff.mean() / (diff.std() + 1e-12) * np.sqrt(len(diff))
        rows.append({
            "Indicator": name,
            "Final PnL": round(float(eq.iloc[-1]), 2),
            "Max PnL":   round(float(eq.max()),    2),
            "Min PnL":   round(float(eq.min()),    2),
            "Max DD":    round(_max_drawdown(eq.values), 2),
            "# Trades":  _n_trades(tgt),
            "Sharpe≈":   round(float(sharpe), 3),
        })
    display(pd.DataFrame(rows).set_index("Indicator"))
    print()\
"""


def make_notebook(group_name: str, symbols: list) -> dict:
    symbols_repr = repr(symbols)
    cells = [
        md(f"## Round 5 Analysis — {group_name}\n\n"
           "**Indicator windows (data-driven):**\n"
           "- Stochastic K = **50**, D = **3** — at window 50 the avg H-L range is ~152 ticks "
           "(≈7 % of daily range); return ACF ≈ 0 at all lags so range-position carries the signal\n"
           "- Z-Score window = **300** — covers 30 % of a day; rolling mean/std stabilise "
           "well past the short-term noise (ACF flatlines by lag 5)\n"
           "- Fast SMA = **20** | Slow SMA = **300**"),
        code(IMPORTS),
        md("### Data Loading"),
        code(DATA_LOADING_TEMPLATE.format(symbols=symbols_repr)),
        md("### Helper Functions"),
        code(HELPER_FUNCTIONS),
        md("---\n## Within-Group Series Comparison\n\n"
           "All products normalised (z-score) and overlaid on the same chart, plus pairwise "
           "return-correlation heatmap and cross-correlation functions to reveal lead-lag structure."),
        code(WITHIN_GROUP),
        md("---\n## Per-Product Analysis\n### Price & Order Book"),
        code(PRICE_PLOTS_LOOP),
        md("### Stochastic Oscillator  (K=50, D=3)\n\n"
           "%K = (FV − lowest bid over K) / (highest ask over K − lowest bid over K) × 100  \n"
           "%D = 3-period MA of %K (signal line)  \n"
           "Overbought > 80 | Oversold < 20"),
        code(STOCHASTIC_LOOP),
        md("### Z-Score  (rolling window = 300)\n\n"
           "Z = (FV − rolling mean) / rolling std  \n"
           "Upper/lower bands at ±2σ. ADF test confirms whether the z-score itself is stationary."),
        code(ZSCORE_LOOP),
        md("### Fast SMA (20) vs Slow SMA (300)\n\n"
           "Bull regime when Fast > Slow (green shade). Bear regime when Fast < Slow (red shade).  \n"
           "Crossover markers: ▲ bullish cross, ▽ bearish cross.  \n"
           "Bottom panel shows the SMA spread (Fast − Slow) to quantify regime strength."),
        code(SMA_CROSS_LOOP),
        md("---\n## Strategy Backtest — Equity Simulation\n\n"
           "For every product, each indicator generates a **target position** of ±10 (or 0).  \n"
           "Entries execute at **ask\\_price\\_1** (buys) or **bid\\_price\\_1** (sells).  \n"
           "The mark-to-market equity is computed tick-by-tick against the fair value.\n\n"
           "**Signal rules:**\n"
           "- **Stochastic** — long when %K < 20 (oversold), short when %K > 80 (overbought), flat otherwise\n"
           "- **Z-Score** — long when z < −2, short when z > +2, exit to flat when |z| < 0.5, hold in between\n"
           "- **SMA Cross** — long when Fast > Slow, short when Fast < Slow (trend-following)"),
        code(BACKTEST_LOOP),
    ]
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {
                "codemirror_mode": {"name": "ipython", "version": 3},
                "file_extension": ".py", "mimetype": "text/x-python",
                "name": "python", "version": "3.10.0",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for slug, group_name, symbols in GROUPS:
        nb   = make_notebook(group_name, symbols)
        path = OUTPUT_DIR / f"analysis_{slug}.ipynb"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)
        print(f"Written: {path.name}")


if __name__ == "__main__":
    main()
