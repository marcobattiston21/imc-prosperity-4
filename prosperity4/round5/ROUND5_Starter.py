from datamodel import OrderDepth, TradingState, Order
import json
import numpy as np
from typing import List, Dict, Optional
 
# =============================================================================
# SYMBOLS
# =============================================================================
 
SNACKPACK_CHOC  = "SNACKPACK_CHOCOLATE"
SNACKPACK_VAN   = "SNACKPACK_VANILLA"
SNACKPACK_PIST  = "SNACKPACK_PISTACHIO"
SNACKPACK_RASP  = "SNACKPACK_RASPBERRY"
SNACKPACK_STRAW = "SNACKPACK_STRAWBERRY"
SNACKPACK_SYMS  = [SNACKPACK_CHOC, SNACKPACK_VAN, SNACKPACK_PIST,
                   SNACKPACK_RASP, SNACKPACK_STRAW]
 
ROBOT_DISH = "ROBOT_DISHES"
ROBOT_IRON = "ROBOT_IRONING"
ROBOT_LAUN = "ROBOT_LAUNDRY"
ROBOT_MOP  = "ROBOT_MOPPING"
ROBOT_VAC  = "ROBOT_VACUUMING"
ROBOT_SYMS = [ROBOT_DISH, ROBOT_IRON, ROBOT_LAUN, ROBOT_MOP, ROBOT_VAC]
 
GALAXY_SYMS = [
    "GALAXY_SOUNDS_BLACK_HOLES", "GALAXY_SOUNDS_DARK_MATTER",
    "GALAXY_SOUNDS_PLANETARY_RINGS", "GALAXY_SOUNDS_SOLAR_FLAMES",
    "GALAXY_SOUNDS_SOLAR_WINDS",
]
SLEEP_SYMS = [
    "SLEEP_POD_COTTON", "SLEEP_POD_LAMB_WOOL", "SLEEP_POD_NYLON",
    "SLEEP_POD_POLYESTER", "SLEEP_POD_SUEDE",
]
TRANSLATOR_SYMS = [
    "TRANSLATOR_ASTRO_BLACK", "TRANSLATOR_ECLIPSE_CHARCOAL",
    "TRANSLATOR_GRAPHITE_MIST", "TRANSLATOR_SPACE_GRAY", "TRANSLATOR_VOID_BLUE",
]
UV_SYMS = [
    "UV_VISOR_AMBER", "UV_VISOR_MAGENTA", "UV_VISOR_ORANGE",
    "UV_VISOR_RED", "UV_VISOR_YELLOW",
]
# All 20 cluster products (GALAXY + SLEEP + TRANSLATOR + UV share a common factor,
# pairwise group-index return correlation ~0.31-0.42)
CLUSTER_SYMS = GALAXY_SYMS + SLEEP_SYMS + TRANSLATOR_SYMS + UV_SYMS
 
POS_LIMITS: Dict[str, int] = {
    s: 10 for s in SNACKPACK_SYMS + ROBOT_SYMS + CLUSTER_SYMS
}
 
 
# =============================================================================
# BASE CLASS: ProductTrader  (single-product — identical to starter)
# =============================================================================
class ProductTrader:
 
    def __init__(
        self,
        name: str,
        state: TradingState,
        prints: dict,
        new_trader_data: dict,
        product_group: str | None = None,
    ):
        self.orders: List[Order] = []
        self.name = name
        self.state = state
        self.prints = prints
        self.new_trader_data = new_trader_data
        self.product_group = name if product_group is None else product_group
 
        self.last_traderData: dict = self._load_trader_data()
        self.position_limit: int = POS_LIMITS.get(self.name, 0)
        self.initial_position: int = self.state.position.get(self.name, 0)
 
        self.mkt_buy_orders, self.mkt_sell_orders = self._parse_order_depth()
        self.max_vol_bid, self.fv, self.max_vol_ask = self._get_max_vol_ask_bid()
        self.worst_bid, self.worst_ask = self._get_worst_bid_ask()
        self.best_bid, self.mid_price, self.best_ask = self._get_best_bid_ask()
        self.second_best_bid, self.second_best_ask = self._get_second_best_bid_ask()
        self.max_allowed_buy_volume, self.max_allowed_sell_volume = self._get_max_volumes()
        self.bid_gap  = abs(self.best_bid  - self.second_best_bid)  if self.second_best_bid  else 0
        self.ask_gap  = abs(self.best_ask  - self.second_best_ask)  if self.second_best_ask  else 0
        self.spread   = self.best_ask - self.best_bid if (self.best_ask and self.best_bid) else None
 
    def _load_trader_data(self) -> dict:
        try:
            if self.state.traderData:
                return json.loads(self.state.traderData)
        except:
            pass
        return {}
 
    def _parse_order_depth(self) -> tuple[dict, dict]:
        buy_orders, sell_orders = {}, {}
        try:
            od: OrderDepth = self.state.order_depths[self.name]
            buy_orders  = {p: abs(v) for p, v in sorted(od.buy_orders.items(),  reverse=True)}
            sell_orders = {p: abs(v) for p, v in sorted(od.sell_orders.items())}
        except:
            pass
        return buy_orders, sell_orders
 
    def _get_max_vol_ask_bid(self) -> tuple:
        mvb_p, mvb = None, 0
        mva_p, mva = None, 0
        for p, a in self.mkt_buy_orders.items():
            if a > mvb: mvb = a; mvb_p = p
        for p, a in self.mkt_sell_orders.items():
            if a > mva: mva = a; mva_p = p
        if mvb_p is None:   fv = mva_p
        elif mva_p is None: fv = mvb_p
        else:               fv = (mvb_p + mva_p) / 2
        return mvb_p, fv, mva_p
 
    def _get_worst_bid_ask(self) -> tuple:
        worst_bid = worst_ask = None
        try: worst_bid = min(self.mkt_buy_orders)
        except: pass
        try: worst_ask = max(self.mkt_sell_orders)
        except: pass
        return worst_bid, worst_ask
 
    def _get_best_bid_ask(self) -> tuple:
        best_bid = max(self.mkt_buy_orders,  default=None)
        best_ask = min(self.mkt_sell_orders, default=None)
        if best_bid is None:   mid = best_ask
        elif best_ask is None: mid = best_bid
        else:                  mid = (best_bid + best_ask) / 2
        return best_bid, mid, best_ask
 
    def _get_second_best_bid_ask(self) -> tuple:
        bids = list(self.mkt_buy_orders.keys())
        asks = list(self.mkt_sell_orders.keys())
        return (bids[1] if len(bids) >= 2 else None,
                asks[1] if len(asks) >= 2 else None)
 
    def _get_max_volumes(self) -> tuple[int, int]:
        return (self.position_limit - self.initial_position,
                self.position_limit + self.initial_position)
 
    def bid(self, price, volume, logging=True):
        qty = min(abs(int(volume)), self.max_allowed_buy_volume)
        if qty <= 0: return
        self.orders.append(Order(self.name, int(price), qty))
        if logging:
            g = self.prints.get(self.product_group, {})
            g.setdefault("BUYS", []).append({"p": int(price), "v": qty})
            self.prints[self.product_group] = g
        self.max_allowed_buy_volume -= qty
 
    def ask(self, price: float, volume: float, logging: bool = True) -> None:
        qty = min(abs(int(volume)), self.max_allowed_sell_volume)
        if qty <= 0: return
        self.orders.append(Order(self.name, int(price), -qty))
        if logging:
            g = self.prints.get(self.product_group, {})
            g.setdefault("SELLS", []).append({"p": int(price), "v": qty})
            self.prints[self.product_group] = g
        self.max_allowed_sell_volume -= qty
 
    def log(self, kind: str, message, product_group: str | None = None) -> None:
        gk = product_group or self.product_group
        g  = self.prints.get(gk, {})
        g[kind] = message
        self.prints[gk] = g
 
    def get_orders(self) -> dict:
        return {}
 
 
# =============================================================================
# BASE CLASS: MultiProductTrader  (group-level strategies, N products)
# Mirrors ProductTrader's interface but manages a whole group of symbols.
# =============================================================================
class MultiProductTrader:
    """
    Base class for strategies that span multiple correlated products.
    Subclasses declare SYMBOLS and implement get_orders().
    The Trader.run() loop calls each instance the same way it calls
    single-product traders.
    """
    SYMBOLS: List[str] = []  # override in subclass
 
    def __init__(self, state: TradingState, prints: dict, new_trader_data: dict):
        self.state           = state
        self.prints          = prints
        self.new_trader_data = new_trader_data
        self.product_group   = self.__class__.__name__
 
        # Load persistent state from previous tick
        self.last_td: dict = self._load_td()
 
        # Per-symbol order books and derived quantities (populated by _parse_all)
        self._buy_orders : Dict[str, Dict[int, int]]  = {}
        self._sell_orders: Dict[str, Dict[int, int]]  = {}
        self._best_bids  : Dict[str, Optional[int]]   = {}
        self._best_asks  : Dict[str, Optional[int]]   = {}
        self._mids       : Dict[str, Optional[float]] = {}
        self._positions  : Dict[str, int]             = {}
        self._max_buys   : Dict[str, int]             = {}
        self._max_sells  : Dict[str, int]             = {}
        self._all_orders : Dict[str, List[Order]]     = {s: [] for s in self.SYMBOLS}
 
        self._parse_all()
 
    # -------------------------------------------------------------------------
    # Initialisation helpers
    # -------------------------------------------------------------------------
    def _load_td(self) -> dict:
        try:
            if self.state.traderData:
                return json.loads(self.state.traderData)
        except:
            pass
        return {}
 
    def _parse_all(self) -> None:
        for sym in self.SYMBOLS:
            od   = self.state.order_depths.get(sym, OrderDepth())
            buys = {p: abs(v) for p, v in sorted(od.buy_orders.items(),  reverse=True)}
            sell = {p: abs(v) for p, v in sorted(od.sell_orders.items())}
            self._buy_orders[sym]  = buys
            self._sell_orders[sym] = sell
            bb = max(buys, default=None)
            ba = min(sell, default=None)
            self._best_bids[sym] = bb
            self._best_asks[sym] = ba
            self._mids[sym]      = (bb + ba) / 2 if (bb is not None and ba is not None) \
                                   else (bb if bb is not None else ba)
            lim = POS_LIMITS.get(sym, 200)
            pos = self.state.position.get(sym, 0)
            self._positions[sym] = pos
            self._max_buys[sym]  = lim - pos
            self._max_sells[sym] = lim + pos
 
    # -------------------------------------------------------------------------
    # Order helpers  (mirror ProductTrader.bid / ProductTrader.ask)
    # -------------------------------------------------------------------------
    def _bid(self, sym: str, price: float, volume: float) -> None:
        qty = min(abs(int(volume)), self._max_buys[sym])
        if qty <= 0: return
        self._all_orders[sym].append(Order(sym, int(price), qty))
        self._max_buys[sym] -= qty
 
    def _ask(self, sym: str, price: float, volume: float) -> None:
        qty = min(abs(int(volume)), self._max_sells[sym])
        if qty <= 0: return
        self._all_orders[sym].append(Order(sym, int(price), -qty))
        self._max_sells[sym] -= qty
 
    # -------------------------------------------------------------------------
    # Convenience accessors
    # -------------------------------------------------------------------------
    def _mid(self, sym: str)      -> Optional[float]: return self._mids.get(sym)
    def _bb (self, sym: str)      -> Optional[int]:   return self._best_bids.get(sym)
    def _ba (self, sym: str)      -> Optional[int]:   return self._best_asks.get(sym)
    def _pos(self, sym: str)      -> int:             return self._positions.get(sym, 0)
    def _max_buy(self, sym: str)  -> int:             return self._max_buys[sym]
    def _max_sell(self, sym: str) -> int:             return self._max_sells[sym]
 
    def log(self, kind: str, message) -> None:
        g = self.prints.get(self.product_group, {})
        g[kind] = message
        self.prints[self.product_group] = g
 
    # -------------------------------------------------------------------------
    # Reusable z-score pair trading engine (both legs managed here)
    # sym_a: the "reference" leg whose spread is measured as (A − B)
    # When z > +entry_z → A is expensive → sell A, buy  B
    # When z < −entry_z → A is cheap    → buy  A, sell B
    # When |z| < exit_z → flatten both legs
    # -------------------------------------------------------------------------
    def _trade_pair(
        self,
        sym_a: str,
        sym_b: str,
        hist_key: str,
        window: int,
        entry_z: float,
        exit_z: float,
        lot: int,
        min_hist: int | None = None,
    ) -> Optional[float]:
        if min_hist is None:
            min_hist = window // 4
 
        mid_a = self._mid(sym_a)
        mid_b = self._mid(sym_b)
        if mid_a is None or mid_b is None:
            return None
 
        # --- Update rolling spread history ---
        history: List[float] = self.last_td.get(hist_key, [])
        spread = mid_a - mid_b
        history = (history + [spread])[-window:]
        self.new_trader_data[hist_key] = history
 
        if len(history) < min_hist:
            return None
 
        mu    = float(np.mean(history))
        sigma = float(np.std(history))
        if sigma < 1e-6:
            return None
 
        z     = (spread - mu) / sigma
        pos_a = self._pos(sym_a)
        pos_b = self._pos(sym_b)
 
        # --- Entry: cross the spread (taker) ---
        if z > entry_z:
            # A is expensive vs B → sell A at A's best bid, buy B at B's best ask
            if self._bb(sym_a): self._ask(sym_a, self._bb(sym_a), lot)
            if self._ba(sym_b): self._bid(sym_b, self._ba(sym_b), lot)
 
        elif z < -entry_z:
            # A is cheap vs B → buy A at A's best ask, sell B at B's best bid
            if self._ba(sym_a): self._bid(sym_a, self._ba(sym_a), lot)
            if self._bb(sym_b): self._ask(sym_b, self._bb(sym_b), lot)
 
        # --- Exit: flatten both legs when spread has reverted ---
        elif abs(z) < exit_z:
            if pos_a < 0 and self._ba(sym_a):
                self._bid(sym_a, self._ba(sym_a), abs(pos_a))
            elif pos_a > 0 and self._bb(sym_a):
                self._ask(sym_a, self._bb(sym_a), pos_a)
            if pos_b < 0 and self._ba(sym_b):
                self._bid(sym_b, self._ba(sym_b), abs(pos_b))
            elif pos_b > 0 and self._bb(sym_b):
                self._ask(sym_b, self._bb(sym_b), pos_b)
 
        self.log(f"Z_{hist_key}", round(z, 3))
        return z
 
    # -------------------------------------------------------------------------
    # Plain market-making for a single symbol (use when no pair signal applies)
    # -------------------------------------------------------------------------
    def _mm_solo(self, sym: str, half_spread: int, lot_fraction: int = 4) -> None:
        mid = self._mid(sym)
        if mid is None: return
        self._bid(sym, mid - half_spread, self._max_buy(sym)  // lot_fraction)
        self._ask(sym, mid + half_spread, self._max_sell(sym) // lot_fraction)
 
    def get_orders(self) -> dict:
        return {s: orders for s, orders in self._all_orders.items() if orders}
 
 
# =============================================================================
# SNACKPACK TRADER
# Strategy 1 — CHOC / VAN pair  (return corr = −0.927, CHOC+VAN sum ≈ 19 925 ± 74)
# Strategy 2 — PIST / RASP pair (return corr = −0.803, sum = 19 567 ± 214)
# Strategy 3 — STRAW            (plain MM; STRAW is correlated to PIST/RASP but
#                                  traded separately to avoid 3-leg complexity)
# =============================================================================
class SnackpackTrader(MultiProductTrader):
    SYMBOLS = SNACKPACK_SYMS
 
    # --- Pair parameters ---
    # CHOC/VAN: spread std ≈ 397, bid-ask cost ~34 (17 per leg)
    # Entry at 2σ ⟹ ≈794 ticks of room vs 34 ticks cost → good risk/reward
    CV_WINDOW   = 200
    CV_ENTRY_Z  = 2.0
    CV_EXIT_Z   = 0.5
    CV_LOT      = 50
 
    # PIST/RASP: slightly weaker but still exploitable
    PR_WINDOW   = 200
    PR_ENTRY_Z  = 2.0
    PR_EXIT_Z   = 0.5
    PR_LOT      = 40
 
    # STRAW plain MM (spread ≈ 17)
    STRAW_HALF_SPREAD = 8
 
    def get_orders(self) -> dict:
        # Pair 1: CHOCOLATE ↔ VANILLA
        self._trade_pair(
            sym_a    = SNACKPACK_CHOC,
            sym_b    = SNACKPACK_VAN,
            hist_key = "snack_cv_spread",
            window   = self.CV_WINDOW,
            entry_z  = self.CV_ENTRY_Z,
            exit_z   = self.CV_EXIT_Z,
            lot      = self.CV_LOT,
        )
 
        # Pair 2: PISTACHIO ↔ RASPBERRY
        self._trade_pair(
            sym_a    = SNACKPACK_PIST,
            sym_b    = SNACKPACK_RASP,
            hist_key = "snack_pr_spread",
            window   = self.PR_WINDOW,
            entry_z  = self.PR_ENTRY_Z,
            exit_z   = self.PR_EXIT_Z,
            lot      = self.PR_LOT,
        )
 
        # STRAWBERRY: simple market-making
        self._mm_solo(SNACKPACK_STRAW, self.STRAW_HALF_SPREAD)
 
        self.log("POS", {
            s.replace("SNACKPACK_", ""): self._pos(s) for s in self.SYMBOLS
        })
        return super().get_orders()
 
 
# =============================================================================
# ROBOT TRADER
# Strategy 1 — LAUNDRY / MOPPING pair
#   (sum = 20 669 ± 275, half-life ≈ 33 ticks — fastest mean-reverter found)
# Strategy 2 — DISHES / VACUUMING pair
#   (sum = 19 236 ± 391, secondary opportunity)
# Strategy 3 — IRONING plain MM (tightest spread in group, 6 ticks)
# =============================================================================
class RobotTrader(MultiProductTrader):
    SYMBOLS = ROBOT_SYMS
 
    # LAUNDRY/MOPPING: bid-ask cost ~15 (7+8), very fast reversion
    # Entry at z=1.5 ⟹ 1.5 × spread_std units of expected PnL
    LM_WINDOW  = 100
    LM_ENTRY_Z = 1.5
    LM_EXIT_Z  = 0.5
    LM_LOT     = 50
 
    # DISHES/VACUUMING: slower, use wider window
    DV_WINDOW  = 150
    DV_ENTRY_Z = 1.5
    DV_EXIT_Z  = 0.5
    DV_LOT     = 30
 
    # IRONING plain MM (spread ≈ 6)
    IRON_HALF_SPREAD = 3
 
    def get_orders(self) -> dict:
        # Pair 1: LAUNDRY ↔ MOPPING  (fastest reversion, highest priority)
        self._trade_pair(
            sym_a    = ROBOT_LAUN,
            sym_b    = ROBOT_MOP,
            hist_key = "robot_lm_spread",
            window   = self.LM_WINDOW,
            entry_z  = self.LM_ENTRY_Z,
            exit_z   = self.LM_EXIT_Z,
            lot      = self.LM_LOT,
        )
 
        # Pair 2: DISHES ↔ VACUUMING
        self._trade_pair(
            sym_a    = ROBOT_DISH,
            sym_b    = ROBOT_VAC,
            hist_key = "robot_dv_spread",
            window   = self.DV_WINDOW,
            entry_z  = self.DV_ENTRY_Z,
            exit_z   = self.DV_EXIT_Z,
            lot      = self.DV_LOT,
        )
 
        # IRONING: plain MM
        self._mm_solo(ROBOT_IRON, self.IRON_HALF_SPREAD)
 
        self.log("POS", {
            s.replace("ROBOT_", ""): self._pos(s) for s in self.SYMBOLS
        })
        return super().get_orders()
 
 
# =============================================================================
# CLUSTER GROUP TRADER  (base class)
# The four groups GALAXY / SLEEP / TRANSLATOR / UV share a common latent factor:
#   pairwise group-index return correlation ≈ 0.31 – 0.42.
#
# Strategy: for each product in the group, track its rolling deviation from the
# cross-group cluster index (equal-weighted average of all 20 cluster products).
# When a product is significantly above/below its expected level vs the index,
# lean the market-making quotes accordingly (or take liquidity at extremes).
# =============================================================================
class ClusterGroupTrader(MultiProductTrader):
    """
    Subclass SYMBOLS to cover one of the four correlated groups.
    The cluster index is always computed over all 20 products (CLUSTER_SYMS),
    providing a cross-group anchor that is ~5× less volatile than any individual
    product and is uncorrelated with group-specific noise.
    """
 
    # MM tuning
    HALF_SPREAD  : int   = 6      # base half-spread for passive quotes
    LOT_FRACTION : int   = 4      # use 1/N of remaining allowed volume
    TAKE_Z       : float = 2.0    # z-score to cross the spread (take liquidity)
    WINDOW       : int   = 150    # rolling window for deviation history
    MIN_HIST     : int   = 30     # ticks before the cluster signal is trusted
    INV_SKEW     : float = 0.05   # inventory skew coefficient (ticks per unit pos)
 
    def _cluster_index(self) -> Optional[float]:
        """
        Equal-weighted mid of all 20 cluster products.
        Products with missing quotes are skipped (robust to gaps).
        """
        mids = []
        for sym in CLUSTER_SYMS:
            od = self.state.order_depths.get(sym, OrderDepth())
            bb = max(od.buy_orders,  default=None)
            ba = min(od.sell_orders, default=None)
            if bb is not None and ba is not None:
                mids.append((bb + ba) / 2.0)
        return float(np.mean(mids)) if mids else None
 
    def _trade_vs_cluster(self, sym: str, cluster_idx: float) -> None:
        """
        Market-make sym using its rolling deviation from the cluster index as FV.
 
        FV  = cluster_idx  + mean(rolling_deviation)
        The rolling_deviation history captures each product's stable structural
        offset from the index (e.g. GALAXY tends to be ~275 above the index).
 
        When z-score of current deviation vs FV exceeds TAKE_Z we cross the
        spread; otherwise we post passive quotes skewed by inventory and z-score.
        """
        mid = self._mid(sym)
        if mid is None:
            return
 
        # --- Maintain rolling deviation history ---
        dev_key = f"cdev_{sym}"
        history: List[float] = self.last_td.get(dev_key, [])
        dev = mid - cluster_idx
        history = (history + [dev])[-self.WINDOW:]
        self.new_trader_data[dev_key] = history
 
        # --- Not enough history: fall back to plain MM around mid ---
        if len(history) < self.MIN_HIST:
            self._mm_solo(sym, self.HALF_SPREAD, self.LOT_FRACTION)
            return
 
        mean_dev = float(np.mean(history))
        std_dev  = float(np.std(history))
 
        # FV: cluster index shifted by the product's historical structural offset
        fv = cluster_idx + mean_dev
 
        # Z-score of current mid relative to FV
        if std_dev < 1e-6:
            zscore = 0.0
        else:
            zscore = (mid - fv) / std_dev
 
        pos = self._pos(sym)
 
        # --- Inventory skew: lean quotes opposite to position ---
        inv_skew = -pos * self.INV_SKEW
 
        # --- Passive quotes ---
        bid_px = fv - self.HALF_SPREAD + inv_skew
        ask_px = fv + self.HALF_SPREAD + inv_skew
        self._bid(sym, bid_px, self._max_buy(sym)  // self.LOT_FRACTION)
        self._ask(sym, ask_px, self._max_sell(sym) // self.LOT_FRACTION)
 
        # --- Aggressive take at extremes ---
        if zscore > self.TAKE_Z:
            # Product is expensive vs cluster → sell into best bid
            bb = self._bb(sym)
            if bb is not None and self._buy_orders[sym].get(bb):
                self._ask(sym, bb, self._buy_orders[sym][bb])
 
        elif zscore < -self.TAKE_Z:
            # Product is cheap vs cluster → buy at best ask
            ba = self._ba(sym)
            if ba is not None and self._sell_orders[sym].get(ba):
                self._bid(sym, ba, self._sell_orders[sym][ba])
 
    def get_orders(self) -> dict:
        cluster_idx = self._cluster_index()
 
        if cluster_idx is None:
            return {}
 
        for sym in self.SYMBOLS:
            try:
                self._trade_vs_cluster(sym, cluster_idx)
            except Exception:
                pass
 
        self.log("CLUSTER_IDX", round(cluster_idx, 1))
        self.log("POS", {s.split("_")[-1]: self._pos(s) for s in self.SYMBOLS})
        return super().get_orders()
 
 
# =============================================================================
# CONCRETE CLUSTER TRADERS
# Each inherits everything from ClusterGroupTrader; only SYMBOLS changes.
# TRANSLATOR gets a tighter spread because it has the narrowest bid-ask (≈6).
# SLEEP gets a wider spread because its products are more volatile (std ≈ 8-18).
# =============================================================================
class GalaxySoundsTrader(ClusterGroupTrader):
    SYMBOLS      = GALAXY_SYMS
    HALF_SPREAD  = 6
    TAKE_Z       = 2.0
 
 
class SleepPodTrader(ClusterGroupTrader):
    SYMBOLS      = SLEEP_SYMS
    HALF_SPREAD  = 7      # slightly wider: POLYESTER and COTTON are more volatile
    TAKE_Z       = 1.8
 
 
class TranslatorTrader(ClusterGroupTrader):
    SYMBOLS      = TRANSLATOR_SYMS
    HALF_SPREAD  = 4      # tightest bid-ask in the cluster (≈6), use narrow spread
    TAKE_Z       = 2.0
 
 
class UvVisorTrader(ClusterGroupTrader):
    SYMBOLS      = UV_SYMS
    HALF_SPREAD  = 6
    TAKE_Z       = 2.0
 
 
# =============================================================================
# TOP-LEVEL TRADER
# Mirrors the starter's run() exactly:
#   - single-product traders  → keyed by symbol
#   - multi-product traders   → keyed by group name, checked via SYMBOLS list
# Both sets call get_orders() and merge via result.update().
# =============================================================================
class Trader:
 
    def run(self, state: TradingState):
 
        new_trader_data: dict = {}
        prints: dict = {
            "GENERAL": {"t": state.timestamp, "pos": state.position},
        }
 
        result:      dict = {}
        conversions: int  = 0
 
        # -----------------------------------------------------------------
        # Single-product traders (same pattern as starter; add yours here)
        # -----------------------------------------------------------------
        single_product_traders: dict = {
            # e.g.  HYDROGEL_SYMBOL: HydrogelTrader,
        }
 
        for symbol, TraderClass in single_product_traders.items():
            if symbol in state.order_depths:
                try:
                    trader = TraderClass(state, prints, new_trader_data)
                    result.update(trader.get_orders())
                except Exception as e:
                    prints[symbol] = {"ERROR": str(e)}
 
        # -----------------------------------------------------------------
        # Multi-product (group) traders
        # Checked via TraderClass.SYMBOLS: at least one symbol must be live.
        # -----------------------------------------------------------------
        group_traders: dict = {
            "SNACKPACK"    : SnackpackTrader,
            "ROBOT"        : RobotTrader,
            "GALAXY_SOUNDS": GalaxySoundsTrader,
            "SLEEP_POD"    : SleepPodTrader,
            "TRANSLATOR"   : TranslatorTrader,
            "UV_VISOR"     : UvVisorTrader,
        }
 
        for group_name, TraderClass in group_traders.items():
            if any(s in state.order_depths for s in TraderClass.SYMBOLS):
                try:
                    trader = TraderClass(state, prints, new_trader_data)
                    result.update(trader.get_orders())
                except Exception as e:
                    prints[group_name] = {"ERROR": str(e)}
 
        # -----------------------------------------------------------------
        # Serialise state and flush logs
        # -----------------------------------------------------------------
        try:
            final_trader_data = json.dumps(new_trader_data)
        except Exception:
            final_trader_data = ""
 
        try:
            print(json.dumps(prints))
        except Exception:
            pass
 
        return result, conversions, final_trader_data