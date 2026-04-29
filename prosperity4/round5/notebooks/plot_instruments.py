"""
Round 5 — GALAXY_SOUNDS price chart
5 subplots (one per variant): mid-price | SMA-300 | SMA-10 | EMA-10
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# ── Data ──────────────────────────────────────────────────────────────────────

DATA_DIR = "../data"
DAYS = [2, 3, 4]

dfs = []
for d in DAYS:
    df = pd.read_csv(f"{DATA_DIR}/prices_round_5_day_{d}.csv", sep=";")
    df["day"] = d
    dfs.append(df)

raw = pd.concat(dfs, ignore_index=True)
raw["global_tick"] = (raw["day"] - DAYS[0]) * 10_000 + raw["timestamp"] // 100

SYMBOLS = [
    "GALAXY_SOUNDS_BLACK_HOLES",
    "GALAXY_SOUNDS_DARK_MATTER",
    "GALAXY_SOUNDS_PLANETARY_RINGS",
    "GALAXY_SOUNDS_SOLAR_FLAMES",
    "GALAXY_SOUNDS_SOLAR_WINDS",
]

SLOW_WIN = 300
FAST_WIN = 10

C_MID  = "#4C9BE8"
C_SLOW = "#E85D4C"
C_FAST = "#F5A623"
C_EMA  = "#7ED321"

DAY_TICKS = [(d - DAYS[0]) * 10_000 for d in DAYS[1:]]

# ── Plot ──────────────────────────────────────────────────────────────────────

fig, axes = plt.subplots(5, 1, figsize=(18, 20), sharex=True)
fig.suptitle("GALAXY_SOUNDS — Mid price · SMA-300 · SMA-10 · EMA-10",
             fontsize=13, fontweight="bold", color="white", y=1.002)
fig.patch.set_facecolor("#0F0F1A")

for ax, sym in zip(axes, SYMBOLS):
    sub = (
        raw[raw["product"] == sym]
        .sort_values("global_tick")
        .reset_index(drop=True)
    )
    price = sub["mid_price"]
    tick  = sub["global_tick"]

    sma_slow = price.rolling(SLOW_WIN, min_periods=1).mean()
    sma_fast = price.rolling(FAST_WIN, min_periods=1).mean()
    ema_fast = price.ewm(span=FAST_WIN, adjust=False).mean()

    ax.set_facecolor("#0F0F1A")
    ax.plot(tick, price,    color=C_MID,  lw=0.6, alpha=0.85, label="Mid price")
    ax.plot(tick, sma_slow, color=C_SLOW, lw=1.5, alpha=0.90, label=f"SMA-{SLOW_WIN}")
    ax.plot(tick, sma_fast, color=C_FAST, lw=1.0, alpha=0.90, label=f"SMA-{FAST_WIN}")
    ax.plot(tick, ema_fast, color=C_EMA,  lw=1.0, alpha=0.90, label=f"EMA-{FAST_WIN}",
            linestyle="--")

    for dt in DAY_TICKS:
        ax.axvline(dt, color="white", lw=0.8, alpha=0.3, linestyle=":")

    label = sym.replace("GALAXY_SOUNDS_", "").replace("_", " ")
    ax.set_ylabel(label, color="white", fontsize=9)
    ax.tick_params(colors="white", labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor("#333355")
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f"))
    ax.grid(axis="y", color="#222244", lw=0.5)

    if ax is axes[0]:
        ax.legend(loc="upper left", fontsize=8,
                  facecolor="#1A1A2E", edgecolor="#333355", labelcolor="white")

def fmt(x, _):
    day_idx = int(x) // 10_000
    t = int(x) % 10_000
    return f"D{DAYS[0] + day_idx}\n{t:,}"

axes[-1].xaxis.set_major_formatter(mticker.FuncFormatter(fmt))
axes[-1].set_xlabel("Day / Tick", color="white", fontsize=9)
axes[-1].tick_params(axis="x", colors="white", labelsize=8)

plt.tight_layout()
plt.savefig("../data/chart_galaxy_sounds.png", dpi=130,
            bbox_inches="tight", facecolor=fig.get_facecolor())
plt.show()
