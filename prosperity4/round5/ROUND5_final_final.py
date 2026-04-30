from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List, Optional, Tuple
import json
import math
import numpy as np

# =============================================================================
# SYMBOLS & POSITION LIMITS
# All products are capped at ±10 units.
# =============================================================================

GALAXY_SYMS = [
    "GALAXY_SOUNDS_BLACK_HOLES", "GALAXY_SOUNDS_DARK_MATTER",
    "GALAXY_SOUNDS_PLANETARY_RINGS", "GALAXY_SOUNDS_SOLAR_FLAMES",
    "GALAXY_SOUNDS_SOLAR_WINDS",
]
SLEEP_SYMS = [
    "SLEEP_POD_COTTON", "SLEEP_POD_LAMB_WOOL", "SLEEP_POD_NYLON",
    "SLEEP_POD_POLYESTER", "SLEEP_POD_SUEDE",
]
MICROCHIP_SYMS = [
    "MICROCHIP_CIRCLE", "MICROCHIP_OVAL", "MICROCHIP_RECTANGLE",
    "MICROCHIP_SQUARE", "MICROCHIP_TRIANGLE",
]
PEBBLES_SYMS = [
    "PEBBLES_XS", "PEBBLES_S", "PEBBLES_M", "PEBBLES_L", "PEBBLES_XL",
]
ROBOT_SYMS = [
    "ROBOT_DISHES", "ROBOT_IRONING", "ROBOT_LAUNDRY",
    "ROBOT_MOPPING", "ROBOT_VACUUMING",
]
UV_SYMS = [
    "UV_VISOR_AMBER", "UV_VISOR_MAGENTA", "UV_VISOR_ORANGE",
    "UV_VISOR_RED", "UV_VISOR_YELLOW",
]
TRANSLATOR_SYMS = [
    "TRANSLATOR_ASTRO_BLACK", "TRANSLATOR_ECLIPSE_CHARCOAL",
    "TRANSLATOR_GRAPHITE_MIST", "TRANSLATOR_SPACE_GRAY", "TRANSLATOR_VOID_BLUE",
]
PANEL_SYMS = [
    "PANEL_1X2", "PANEL_2X2", "PANEL_1X4", "PANEL_2X4", "PANEL_4X4",
]
OXYGEN_SYMS = [
    "OXYGEN_SHAKE_CHOCOLATE", "OXYGEN_SHAKE_EVENING_BREATH",
    "OXYGEN_SHAKE_GARLIC", "OXYGEN_SHAKE_MINT", "OXYGEN_SHAKE_MORNING_BREATH",
]
SNACKPACK_SYMS = [
    "SNACKPACK_CHOCOLATE", "SNACKPACK_PISTACHIO", "SNACKPACK_RASPBERRY",
    "SNACKPACK_STRAWBERRY", "SNACKPACK_VANILLA",
]

ALL_SYMS = (
    GALAXY_SYMS + SLEEP_SYMS + MICROCHIP_SYMS + PEBBLES_SYMS +
    ROBOT_SYMS + UV_SYMS + TRANSLATOR_SYMS + PANEL_SYMS +
    OXYGEN_SYMS + SNACKPACK_SYMS
)

POS_LIMITS: Dict[str, int] = {s: 10 for s in ALL_SYMS}

# =============================================================================
# STRATEGY CONFIGURATION
# All tuning knobs in one place, outside the classes, for easy iteration.
# =============================================================================

# Active universe for the standard market-making path (non-oracle).
# These were the profitable products identified from log analysis.
MM_ACTIVE_SYMS = {
    "SLEEP_POD_COTTON", "PANEL_4X4", "UV_VISOR_ORANGE", "UV_VISOR_RED",
    "OXYGEN_SHAKE_GARLIC", "MICROCHIP_OVAL", "MICROCHIP_TRIANGLE",
    "MICROCHIP_SQUARE", "GALAXY_SOUNDS_BLACK_HOLES", "TRANSLATOR_GRAPHITE_MIST",
    "GALAXY_SOUNDS_SOLAR_FLAMES", "SLEEP_POD_POLYESTER", "PEBBLES_XS",
    "SLEEP_POD_NYLON", "PANEL_2X4", "OXYGEN_SHAKE_CHOCOLATE", "PEBBLES_S",
    "SNACKPACK_STRAWBERRY", "TRANSLATOR_ASTRO_BLACK", "SLEEP_POD_SUEDE",
    "TRANSLATOR_ECLIPSE_CHARCOAL", "TRANSLATOR_VOID_BLUE", "MICROCHIP_CIRCLE",
    "SNACKPACK_PISTACHIO", "PEBBLES_L", "SNACKPACK_CHOCOLATE", "UV_VISOR_MAGENTA",
    "ROBOT_MOPPING", "ROBOT_IRONING", "ROBOT_VACUUMING", "SNACKPACK_VANILLA",
    "GALAXY_SOUNDS_SOLAR_WINDS", "PEBBLES_M",
}

# Minimum passive edge per category (ticks).
MAKER_EDGE: Dict[str, int] = {
    "Oxygen": 1,
    "Pebbles": 1,
    "Snackpacks": 1,
    "Microchips": 1,
    "UVVisors": 1,
    "Galaxy": 1,
    "Panels": 2,
    "SleepPods": 2,
    "Robots": 2,
    "Translators": 3,
}

CATEGORY: Dict[str, str] = {
    # Galaxy
    "GALAXY_SOUNDS_BLACK_HOLES": "Galaxy",
    "GALAXY_SOUNDS_DARK_MATTER": "Galaxy",
    "GALAXY_SOUNDS_PLANETARY_RINGS": "Galaxy",
    "GALAXY_SOUNDS_SOLAR_FLAMES": "Galaxy",
    "GALAXY_SOUNDS_SOLAR_WINDS": "Galaxy",

    # SleepPods
    "SLEEP_POD_COTTON": "SleepPods",
    "SLEEP_POD_LAMB_WOOL": "SleepPods",
    "SLEEP_POD_NYLON": "SleepPods",
    "SLEEP_POD_POLYESTER": "SleepPods",
    "SLEEP_POD_SUEDE": "SleepPods",

    # Microchips
    "MICROCHIP_CIRCLE": "Microchips",
    "MICROCHIP_OVAL": "Microchips",
    "MICROCHIP_RECTANGLE": "Microchips",
    "MICROCHIP_SQUARE": "Microchips",
    "MICROCHIP_TRIANGLE": "Microchips",

    # Pebbles
    "PEBBLES_XS": "Pebbles",
    "PEBBLES_S": "Pebbles",
    "PEBBLES_M": "Pebbles",
    "PEBBLES_L": "Pebbles",
    "PEBBLES_XL": "Pebbles",

    # Robots
    "ROBOT_DISHES": "Robots",
    "ROBOT_IRONING": "Robots",
    "ROBOT_LAUNDRY": "Robots",
    "ROBOT_MOPPING": "Robots",
    "ROBOT_VACUUMING": "Robots",

    # UVVisors
    "UV_VISOR_AMBER": "UVVisors",
    "UV_VISOR_MAGENTA": "UVVisors",
    "UV_VISOR_ORANGE": "UVVisors",
    "UV_VISOR_RED": "UVVisors",
    "UV_VISOR_YELLOW": "UVVisors",

    # Translators
    "TRANSLATOR_ASTRO_BLACK": "Translators",
    "TRANSLATOR_ECLIPSE_CHARCOAL": "Translators",
    "TRANSLATOR_GRAPHITE_MIST": "Translators",
    "TRANSLATOR_SPACE_GRAY": "Translators",
    "TRANSLATOR_VOID_BLUE": "Translators",

    # Panels
    "PANEL_1X2": "Panels",
    "PANEL_2X2": "Panels",
    "PANEL_1X4": "Panels",
    "PANEL_2X4": "Panels",
    "PANEL_4X4": "Panels",

    # Oxygen
    "OXYGEN_SHAKE_CHOCOLATE": "Oxygen",
    "OXYGEN_SHAKE_EVENING_BREATH": "Oxygen",
    "OXYGEN_SHAKE_GARLIC": "Oxygen",
    "OXYGEN_SHAKE_MINT": "Oxygen",
    "OXYGEN_SHAKE_MORNING_BREATH": "Oxygen",

    # Snackpacks
    "SNACKPACK_CHOCOLATE": "Snackpacks",
    "SNACKPACK_PISTACHIO": "Snackpacks",
    "SNACKPACK_RASPBERRY": "Snackpacks",
    "SNACKPACK_STRAWBERRY": "Snackpacks",
    "SNACKPACK_VANILLA": "Snackpacks",
}

# MICROCHIP_CIRCLE leads its siblings by a fixed number of book-update ticks.
# Each entry: (lag, beta) — FV += clip(beta * circle_delta, -20, 20).
MICRO_LEADS: Dict[str, Tuple[int, float]] = {
    "MICROCHIP_OVAL":      (50,  0.1127),
    "MICROCHIP_SQUARE":    (100, 0.1131),
    "MICROCHIP_RECTANGLE": (150, 0.2126),
    "MICROCHIP_TRIANGLE":  (200, 0.1304),
}

# Short-window mean-reversion nudge applied to the FV of selected products.
# Entry: (window, alpha, max_shift_ticks).
MEAN_REVERSION: Dict[str, Tuple[int, float, float]] = {
    "ROBOT_IRONING":             (10, 0.35, 15.0),
    "ROBOT_MOPPING":             (10, 0.20, 10.0),
    "OXYGEN_SHAKE_EVENING_BREATH": (10, 0.25, 15.0),
    "OXYGEN_SHAKE_CHOCOLATE":    (10, 0.25, 15.0),
    "SNACKPACK_CHOCOLATE":       (10, 0.20, 10.0),
}

# Snackpack pair-sum mean reversion.
# Entry: (sym_a, sym_b, window, k, max_shift).
# When (mid_a + mid_b) > rolling mean of the sum, shade both FVs down.
SNACK_SUM_PAIRS: List[Tuple[str, str, int, float, float]] = [
    ("SNACKPACK_CHOCOLATE", "SNACKPACK_VANILLA",   100, 0.08, 15.0),
    ("SNACKPACK_PISTACHIO", "SNACKPACK_RASPBERRY",  150, 0.04, 15.0),
    ("SNACKPACK_STRAWBERRY", "SNACKPACK_RASPBERRY", 150, 0.04, 15.0),
]

MAX_HISTORY    = 225   # ticks of mid-price kept per product
INVENTORY_SKEW = 0.35  # FV nudge per unit of net position (lean against inventory)
TAKE_EDGE      = 8.0   # minimum gap from FV before crossing the spread
MAX_PASSIVE    = 10    # maximum lots posted on each side of the passive quote


# =============================================================================
# HELPERS
# =============================================================================

def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


# =============================================================================
# BASE CLASS: MultiProductTrader
#
# Strategy pattern: manages a group of N symbols together.
# Provides shared order-book parsing, safe order submission (capacity-aware),
# and logging. Concrete subclasses override SYMBOLS and implement get_orders().
# =============================================================================
class MultiProductTrader:
    """
    Base class for all group-level traders.

    Subclasses declare SYMBOLS and implement get_orders(). The Trader.run()
    loop calls each instance via get_orders() and merges the result dict.

    Book parsing, position tracking, and safe-order submission are handled
    here so subclasses contain only strategy-specific logic.
    """
    SYMBOLS: List[str] = []

    def __init__(self, state: TradingState, new_trader_data: dict):
        self.state           = state
        self.new_td          = new_trader_data
        self.group           = self.__class__.__name__

        self.last_td: dict = self._load_td()

        # Per-symbol order books
        self._buys : Dict[str, Dict[int, int]] = {}
        self._sells: Dict[str, Dict[int, int]] = {}
        self._bbs  : Dict[str, Optional[int]]  = {}
        self._bas  : Dict[str, Optional[int]]  = {}
        self._mids : Dict[str, Optional[float]]= {}
        self._pos  : Dict[str, int]            = {}
        self._cap_b: Dict[str, int]            = {}  # remaining buy capacity
        self._cap_s: Dict[str, int]            = {}  # remaining sell capacity
        self._orders: Dict[str, List[Order]]   = {s: [] for s in self.SYMBOLS}

        self._parse_all()

    def _load_td(self) -> dict:
        try:
            return json.loads(self.state.traderData) if self.state.traderData else {}
        except Exception:
            return {}

    def _parse_all(self) -> None:
        for sym in self.SYMBOLS:
            od   = self.state.order_depths.get(sym, OrderDepth())
            buys = {p: abs(v) for p, v in sorted(od.buy_orders.items(),  reverse=True)}
            sell = {p: abs(v) for p, v in sorted(od.sell_orders.items())}
            self._buys[sym] = buys
            self._sells[sym] = sell
            bb = max(buys, default=None)
            ba = min(sell, default=None)
            self._bbs[sym] = bb
            self._bas[sym] = ba
            self._mids[sym] = (bb + ba) / 2.0 if (bb is not None and ba is not None) \
                              else (bb if bb is not None else ba)
            lim = POS_LIMITS.get(sym, 10)
            pos = self.state.position.get(sym, 0)
            self._pos[sym]  = pos
            self._cap_b[sym] = lim - pos
            self._cap_s[sym] = lim + pos

    def _bid(self, sym: str, price: float, volume: float) -> None:
        qty = min(abs(int(volume)), self._cap_b[sym])
        if qty <= 0:
            return
        self._orders[sym].append(Order(sym, int(price), qty))
        self._cap_b[sym] -= qty

    def _ask(self, sym: str, price: float, volume: float) -> None:
        qty = min(abs(int(volume)), self._cap_s[sym])
        if qty <= 0:
            return
        self._orders[sym].append(Order(sym, int(price), -qty))
        self._cap_s[sym] -= qty

    def mid(self, sym: str)  -> Optional[float]: return self._mids.get(sym)
    def bb(self, sym: str)   -> Optional[int]:   return self._bbs.get(sym)
    def ba(self, sym: str)   -> Optional[int]:   return self._bas.get(sym)
    def pos(self, sym: str)  -> int:             return self._pos.get(sym, 0)
    def cap_b(self, sym: str)-> int:             return self._cap_b[sym]
    def cap_s(self, sym: str)-> int:             return self._cap_s[sym]

    def get_orders(self) -> Dict[str, List[Order]]:
        return {s: orders for s, orders in self._orders.items() if orders}



# =============================================================================
# StandardMMTrader
#
# Strategy: adaptive fair-value market-making with three FV enrichment layers.
#
# Base FV = current mid-price, then:
#   1. Inventory skew — shift FV against the current position to encourage
#      mean-reversion of inventory (prevents runaway one-sided exposure).
#   2. Short-window mean reversion — for selected volatile products, nudge FV
#      toward the recent rolling mean (exploits fast oscillations).
#   3. Lead-lag signal for Microchips — CIRCLE price changes propagate to the
#      other chips after a fixed lag; the lagged delta is folded into their FV.
#   4. Snackpack pair-sum signal — CHOC+VAN and PIST+RASP sum to a
#      near-constant; when the pair-sum deviates, shade both FVs toward
#      equilibrium.
#
# Orders:
#   - Taker: cross the spread when the best opposing quote is more than
#     TAKE_EDGE ticks from FV.
#   - Maker: post a passive quote 1 tick inside the best opposite quote and
#     at least MAKER_EDGE ticks from FV.
#
# =============================================================================
class StandardMMTrader(MultiProductTrader):
    """
    Main market-making engine for all products not handled by OracleTrader.
    Uses a rolling mid-price history (loaded from traderData) to compute
    multi-signal fair-value estimates and issues both taker and maker orders.
    """
    SYMBOLS = list(MM_ACTIVE_SYMS)

    def __init__(self, state: TradingState, new_td: dict,
                 history: Dict[str, List[float]], oracle_mode: bool):
        self.history     = history
        self.oracle_mode = oracle_mode
        super().__init__(state, new_td)

    # ------------------------------------------------------------------
    # Fair-value computation
    # ------------------------------------------------------------------
    def _compute_fv(self, sym: str) -> float:
        m = self.mid(sym)
        fv = m

        # 1) Inventory skew
        fv -= INVENTORY_SKEW * self.pos(sym)

        # 2) Short-window mean reversion
        if sym in MEAN_REVERSION:
            window, alpha, max_shift = MEAN_REVERSION[sym]
            h = self.history.get(sym, [])
            if len(h) >= window:
                fv += _clip(alpha * (_mean(h[-window:]) - m), -max_shift, max_shift)

        # 3) Microchip lead-lag
        if sym in MICRO_LEADS:
            lag, beta = MICRO_LEADS[sym]
            circle_h = self.history.get("MICROCHIP_CIRCLE", [])
            if len(circle_h) > lag:
                delta = circle_h[-1] - circle_h[-lag - 1]
                fv += _clip(beta * delta, -20.0, 20.0)

        # 4) Snackpack pair-sum signal
        for a, b, window, k, max_shift in SNACK_SUM_PAIRS:
            if sym not in (a, b):
                continue
            ha = self.history.get(a, [])
            hb = self.history.get(b, [])
            if len(ha) >= window and len(hb) >= window:
                recent_sums = [ha[-i] + hb[-i] for i in range(1, window + 1)]
                deviation   = (ha[-1] + hb[-1]) - _mean(recent_sums)
                fv += _clip(-k * deviation, -max_shift, max_shift)

        return fv

    # ------------------------------------------------------------------
    # Per-symbol order logic
    # ------------------------------------------------------------------
    def _trade(self, sym: str) -> None:
        m = self.mid(sym)
        if m is None:
            return

        bb, ba = self.bb(sym), self.ba(sym)
        if bb is None or ba is None:
            return

        spread = ba - bb
        ts     = self.state.timestamp
        fv          = self._compute_fv(sym)
        maker_edge  = MAKER_EDGE.get(CATEGORY.get(sym, ""), 2)
        if spread <= 2:
            maker_edge += 1  # require extra edge when the market is already tight

        # Aggressive taker: lift cheap asks, hit expensive bids
        for ask_p in sorted(self._sells[sym]):
            if ask_p >= fv - TAKE_EDGE:
                break
            avail = self._sells[sym][ask_p]
            if avail > 0:
                self._bid(sym, ask_p, avail)

        for bid_p in sorted(self._buys[sym], reverse=True):
            if bid_p <= fv + TAKE_EDGE:
                break
            avail = self._buys[sym][bid_p]
            if avail > 0:
                self._ask(sym, bid_p, avail)

        # Passive maker: improve the best quote by 1 tick, respecting FV edge
        buy_cap  = min(MAX_PASSIVE, self.cap_b(sym))
        sell_cap = min(MAX_PASSIVE, self.cap_s(sym))

        passive_bid = min(bb + 1, ba - 1, math.floor(fv - maker_edge))
        passive_ask = max(ba - 1, bb + 1, math.ceil(fv + maker_edge))

        if buy_cap > 0 and passive_bid > 0 and passive_bid < ba and fv - passive_bid >= maker_edge:
            self._bid(sym, passive_bid, buy_cap)

        if sell_cap > 0 and passive_ask > bb and passive_ask > passive_bid and passive_ask - fv >= maker_edge:
            self._ask(sym, passive_ask, sell_cap)

    def get_orders(self) -> Dict[str, List[Order]]:
        for sym in self.SYMBOLS:
            od = self.state.order_depths.get(sym)
            if od is None or not od.buy_orders or not od.sell_orders:
                continue
            try:
                self._trade(sym)
            except Exception:
                pass
        return super().get_orders()


# =============================================================================
# TOP-LEVEL TRADER
# =============================================================================
class Trader:
    """
    Entry point called by the exchange engine each tick.

    Routing:
      - OracleTrader   fires first when the oracle fingerprint is confirmed.
      - StandardMMTrader handles the filtered active universe on every tick.
        In oracle mode, oracle orders take priority; any remaining capacity
        is filled by StandardMMTrader.

    State persistence:
      - Mid-price history and oracle_mode flag are stored in traderData (JSON).
    """

    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}
        conversions = 0

        # ── Load persistent cache ─────────────────────────────────────────
        try:
            cache = json.loads(state.traderData) if state.traderData else {}
        except Exception:
            cache = {}

        history: Dict[str, List[float]] = cache.get("mid", {})
        oracle_mode: Optional[bool]     = cache.get("oracle_mode", None)

        # ── First pass: compute current mids, verify oracle fingerprint ───
        current_mid: Dict[str, float] = {}
        for sym, od in state.order_depths.items():
            if sym not in POS_LIMITS or not od.buy_orders or not od.sell_orders:
                continue
            bb = max(od.buy_orders)
            ba = min(od.sell_orders)
            current_mid[sym] = (bb + ba) / 2.0

        # ── Update rolling history (standard products only) ───────────────
        for sym, mid_val in current_mid.items():
            if sym not in MM_ACTIVE_SYMS and sym != "MICROCHIP_CIRCLE":
                continue
            h = history.setdefault(sym, [])
            h.append(mid_val)
            if len(h) > MAX_HISTORY:
                history[sym] = h[-MAX_HISTORY:]

        # ── New traderData dict (accumulated by trader instances) ─────────
        new_td: dict = {}

        # ── Standard market-maker (multi-signal FV, active universe) ─────
        std_trader = StandardMMTrader(state, new_td, history, oracle_mode)
        for sym, orders in std_trader.get_orders().items():
            if sym not in result:
                result[sym] = orders

        # ── Persist state ─────────────────────────────────────────────────
        try:
            trader_data = json.dumps({"mid": history, "oracle_mode": oracle_mode},
                                     separators=(",", ":"))
        except Exception:
            trader_data = ""

        return result, conversions, trader_data