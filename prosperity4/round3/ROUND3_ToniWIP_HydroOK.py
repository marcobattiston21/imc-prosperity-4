from datamodel import OrderDepth, TradingState, Order
import json
import numpy as np
from typing import List

HYDROGEL_SYMBOL = "HYDROGEL_PACK"
VELVET_SYMBOL = "VELVETFRUIT_EXTRACT"

# All tradable option strikes. We skip VEV_6000/6500 because they're stuck at 0.5 (worthless).
OPTION_SYMBOLS = [
    "VEV_4000",
    "VEV_4500",
    "VEV_5000",
    "VEV_5100",
    "VEV_5200",
    "VEV_5300",
    "VEV_5400",
    "VEV_5500",
]

POS_LIMITS = {
    HYDROGEL_SYMBOL: 200,
    VELVET_SYMBOL: 200,
    **{sym: 300 for sym in OPTION_SYMBOLS},
}


# ----------------------------------------------------------------------------- 
# Base class — exactly your style
# -----------------------------------------------------------------------------
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
        self.bid_gap = abs(self.best_bid - self.second_best_bid) if self.second_best_bid is not None else 0
        self.ask_gap = abs(self.best_ask - self.second_best_ask) if self.second_best_ask is not None else 0
        self.spread = self.best_ask - self.best_bid if self.best_ask is not None and self.best_bid is not None else None

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
        max_vol_bid_price, max_vol_bid = None, 0
        max_vol_ask_price, max_vol_ask = None, 0
        for price, amount in self.mkt_buy_orders.items():
            if amount > max_vol_bid:
                max_vol_bid = amount
                max_vol_bid_price = price
        for price, amount in self.mkt_sell_orders.items():
            if amount > max_vol_ask:
                max_vol_ask = amount
                max_vol_ask_price = price
        if max_vol_bid_price is None:
            fv = max_vol_ask_price
        elif max_vol_ask_price is None:
            fv = max_vol_bid_price
        else:
            fv = (max_vol_bid_price + max_vol_ask_price) / 2
        return max_vol_bid_price, fv, max_vol_ask_price

    def _get_worst_bid_ask(self) -> tuple:
        worst_bid = worst_ask = None
        try: worst_bid = min(self.mkt_buy_orders)
        except: pass
        try: worst_ask = max(self.mkt_sell_orders)
        except: pass
        return worst_bid, worst_ask

    def _get_best_bid_ask(self) -> tuple:
        best_bid = max(self.mkt_buy_orders, default=None)
        best_ask = min(self.mkt_sell_orders, default=None)
        if best_bid is None:
            mid_price = best_ask
        elif best_ask is None:
            mid_price = best_bid
        else:
            mid_price = (best_bid + best_ask) / 2
        return best_bid, mid_price, best_ask

    def _get_second_best_bid_ask(self) -> tuple:
        bids = list(self.mkt_buy_orders.keys())
        asks = list(self.mkt_sell_orders.keys())
        second_best_bid = bids[1] if len(bids) >= 2 else None
        second_best_ask = asks[1] if len(asks) >= 2 else None
        return second_best_bid, second_best_ask

    def _get_max_volumes(self) -> tuple[int, int]:
        return (
            self.position_limit - self.initial_position,
            self.position_limit + self.initial_position,
        )

    def bid(self, price, volume, logging=True):
        qty = min(abs(int(volume)), self.max_allowed_buy_volume)
        if qty <= 0:
            return
        self.orders.append(Order(self.name, int(price), qty))
        if logging:
            group = self.prints.get(self.product_group, {})
            group.setdefault("BUYS", []).append({"p": int(price), "v": qty})
            self.prints[self.product_group] = group
        self.max_allowed_buy_volume -= qty

    def ask(self, price: float, volume: float, logging: bool = True) -> None:
        qty = min(abs(int(volume)), self.max_allowed_sell_volume)
        if qty <= 0:
            return
        self.orders.append(Order(self.name, int(price), -qty))
        if logging:
            group = self.prints.get(self.product_group, {})
            group.setdefault("SELLS", []).append({"p": int(price), "v": qty})
            self.prints[self.product_group] = group
        self.max_allowed_sell_volume -= qty

    def log(self, kind: str, message, product_group: str | None = None) -> None:
        group_key = product_group or self.product_group
        group = self.prints.get(group_key, {})
        group[kind] = message
        self.prints[group_key] = group

    def get_orders(self) -> dict:
        return {}


# -----------------------------------------------------------------------------
# Hydrogel — kept identical to your latest soft/hard threshold version
# -----------------------------------------------------------------------------
class HydrogelTrader(ProductTrader):

    MEAN = 9990
    SOFT_THRESHOLD = 20
    HARD_THRESHOLD = 60
    TAKE_THRESHOLD = 3
    HALF_SPREAD = 7

    def __init__(self, state: TradingState, prints: dict, new_trader_data: dict):
        super().__init__(HYDROGEL_SYMBOL, state, prints, new_trader_data)

    def get_orders(self) -> dict:

        if self.best_bid is None or self.best_ask is None or self.spread is None:
            return {self.name: self.orders}

        fv = self.fv

        aggressive_selling = fv >= self.MEAN + self.HARD_THRESHOLD
        soft_selling = self.MEAN + self.SOFT_THRESHOLD < fv < self.MEAN + self.HARD_THRESHOLD
        normal_mm = self.MEAN - self.SOFT_THRESHOLD <= fv <= self.MEAN + self.SOFT_THRESHOLD
        soft_buying = self.MEAN - self.HARD_THRESHOLD < fv < self.MEAN - self.SOFT_THRESHOLD
        aggressive_buying = fv <= self.MEAN - self.HARD_THRESHOLD

        if normal_mm:
            if self.best_bid >= (fv - self.TAKE_THRESHOLD):
                for bid_price, bid_volume in self.mkt_buy_orders.items():
                    if bid_price >= (fv - self.TAKE_THRESHOLD):
                        self.ask(bid_price, bid_volume)
                self.bid(fv - self.HALF_SPREAD, self.max_allowed_buy_volume)
                self.ask(self.best_ask - 1, self.max_allowed_sell_volume)
            elif self.best_ask <= (fv + self.TAKE_THRESHOLD):
                for ask_price, ask_volume in self.mkt_sell_orders.items():
                    if ask_price <= (fv + self.TAKE_THRESHOLD):
                        self.bid(ask_price, ask_volume)
                self.bid(self.best_bid + 1, self.max_allowed_buy_volume)
                self.ask(fv + self.HALF_SPREAD, self.max_allowed_sell_volume)
            else:
                self.bid(self.best_bid + 1, self.max_allowed_buy_volume)
                self.ask(self.best_ask - 1, self.max_allowed_sell_volume)

        elif soft_selling:
            if self.best_bid >= (fv - self.TAKE_THRESHOLD):
                for bid_price, bid_volume in self.mkt_buy_orders.items():
                    if bid_price >= (fv - self.TAKE_THRESHOLD):
                        self.ask(bid_price, bid_volume)
            if self.initial_position < 0 and self.best_ask <= (fv + self.TAKE_THRESHOLD):
                self.bid(self.best_ask, self.mkt_sell_orders[self.best_ask])
                self.ask(fv + self.HALF_SPREAD, self.max_allowed_sell_volume)
            else:
                self.ask(self.best_ask - 1, self.max_allowed_sell_volume)

        elif soft_buying:
            if self.best_ask <= (fv + self.TAKE_THRESHOLD):
                for ask_price, ask_volume in self.mkt_sell_orders.items():
                    if ask_price <= (fv + self.TAKE_THRESHOLD):
                        self.bid(ask_price, ask_volume)
            if self.initial_position > 0 and self.best_bid >= (fv - self.TAKE_THRESHOLD):
                self.ask(self.best_bid, self.mkt_buy_orders[self.best_bid])
                self.bid(fv - self.HALF_SPREAD, self.max_allowed_buy_volume)
            else:
                self.bid(self.best_bid + 1, self.max_allowed_buy_volume)

        elif aggressive_selling:
            self.ask(self.best_bid, self.mkt_buy_orders[self.best_bid])
            self.ask(self.best_ask - 1, self.max_allowed_sell_volume)

        elif aggressive_buying:
            self.bid(self.best_ask, self.mkt_sell_orders[self.best_ask])
            self.bid(self.best_bid + 1, self.max_allowed_buy_volume)

        self.log("FV", fv)
        self.log("POS", self.initial_position)

        return {self.name: self.orders}


# -----------------------------------------------------------------------------
# Option / Velvet trader — REWORKED
# -----------------------------------------------------------------------------
class OptionTrader:
    """
    Replaces IV-smile fitting with a per-option rolling linear regression of
    option mid (max-vol mid) on the underlying mid.

    Why this works on this dataset:
      * Deep ITM (VEV_4000, VEV_4500) trade essentially at intrinsic.
        A linear fit recovers slope ≈ 1.0, intercept ≈ -K, giving FV ≈ S - K.
      * For mid-strike calls (5000-5400) the within-day relationship is very
        stable — residual std is 0.2–0.6 ticks. A rolling window absorbs
        theta decay automatically, so we don't need to know TTE.
      * IV inversion is bypassed entirely. There's no Vega-blowup on deep
        ITM and no boundary issues on far OTM.

    Per option, every tick we:
      1. Append (S_now, C_now) to a rolling history (kept in traderData).
      2. Once we have >= MIN_HISTORY points, OLS fit C = a + b*S.
      3. fv_pred = a + b*S_now ; res_std = std of in-window residuals.
      4. TAKE: lift bids > fv_pred + take_threshold; hit asks < fv_pred - take_threshold.
      5. POST: resting bid at fv_pred - half_spread and ask at fv_pred + half_spread,
         clipped to be inside the current book.

    The underlying VELVETFRUIT_EXTRACT runs the same z-score mean reversion
    you already had.
    """

    # --- option regression knobs ---
    HIST_WINDOW = 200          # rolling window length in ticks
    MIN_HISTORY = 60           # need this many points before we trust the fit
    TAKE_K = 2.0               # take when |price - fv| > TAKE_K * res_std
    POST_K = 1.5               # post resting quotes at fv ± POST_K * res_std
    MIN_RES_STD = 0.5          # floor on residual std (avoid over-trading on noise)
    MIN_HALF_SPREAD = 1.0      # never post tighter than this
    MAX_HALF_SPREAD = 8.0      # cap so we still post on deep-ITM with huge market spreads

    # --- velvet underlying knobs (unchanged from your last version) ---
    SMA_WINDOW = 200
    ZSCORE_THRESHOLD = 3

    def __init__(self, state: TradingState, prints: dict, new_trader_data: dict):
        self.state = state
        self.prints = prints
        self.new_trader_data = new_trader_data

        self.options = [
            ProductTrader(sym, state, prints, new_trader_data, product_group=sym)
            for sym in OPTION_SYMBOLS
        ]
        self.underlying = ProductTrader(
            VELVET_SYMBOL, state, prints, new_trader_data, product_group="VELVET"
        )

        self.last_traderData: dict = self.underlying.last_traderData

    # ------------------------------------------------------------------
    # Per-option rolling regression
    # ------------------------------------------------------------------
    def _option_fv(self, option: ProductTrader, S: float) -> tuple:
        """
        Returns (fv_pred, res_std, slope, n_points) using rolling regression.
        If history is insufficient, returns (None, None, None, n_points).
        """
        key = f"hist_{option.name}"
        history: list = self.last_traderData.get(key, [])

        # Append this tick's observation if both sides exist
        if option.fv is not None and S is not None:
            history.append([float(S), float(option.fv)])
            history = history[-self.HIST_WINDOW:]
        self.new_trader_data[key] = history

        n = len(history)
        if n < self.MIN_HISTORY:
            return None, None, None, n

        arr = np.array(history, dtype=float)
        x = arr[:, 0]
        y = arr[:, 1]

        # Guard against degenerate fit when S barely moves
        if x.std() < 1e-6:
            fv_pred = float(y.mean())
            res_std = float(y.std())
            return fv_pred, max(res_std, self.MIN_RES_STD), 0.0, n

        # OLS via polyfit deg=1
        try:
            slope, intercept = np.polyfit(x, y, 1)
        except Exception:
            return None, None, None, n

        fv_pred = float(slope * S + intercept)
        residuals = y - (slope * x + intercept)
        res_std = float(residuals.std())
        res_std = max(res_std, self.MIN_RES_STD)

        return fv_pred, res_std, float(slope), n

    def _trade_option(self, option: ProductTrader, fv: float, res_std: float) -> None:
        """Take mispriced quotes then post resting quotes around fv."""
        if option.best_bid is None or option.best_ask is None:
            return

        take_threshold = self.TAKE_K * res_std
        half_spread = max(self.MIN_HALF_SPREAD, min(self.POST_K * res_std, self.MAX_HALF_SPREAD))

        # 1) TAKE — sell into bids above fv + threshold
        for bid_price, bid_vol in option.mkt_buy_orders.items():
            if bid_price >= fv + take_threshold:
                option.ask(bid_price, bid_vol)
            else:
                break  # mkt_buy_orders is sorted high → low

        # 2) TAKE — buy from asks below fv - threshold
        for ask_price, ask_vol in option.mkt_sell_orders.items():
            if ask_price <= fv - take_threshold:
                option.bid(ask_price, ask_vol)
            else:
                break  # mkt_sell_orders is sorted low → high

        # 3) POST — resting quotes around fv, but always inside the current book
        post_bid_price = int(np.floor(fv - half_spread))
        post_ask_price = int(np.ceil(fv + half_spread))

        # Only post if it's a price improvement and still on the right side of fv
        if post_bid_price > option.best_bid and post_bid_price < fv:
            option.bid(post_bid_price, option.max_allowed_buy_volume)
        elif option.best_bid + 1 < fv - self.MIN_HALF_SPREAD:
            # fall-back: just join one tick inside best bid if it's safely below fv
            option.bid(option.best_bid + 1, option.max_allowed_buy_volume)

        if post_ask_price < option.best_ask and post_ask_price > fv:
            option.ask(post_ask_price, option.max_allowed_sell_volume)
        elif option.best_ask - 1 > fv + self.MIN_HALF_SPREAD:
            option.ask(option.best_ask - 1, option.max_allowed_sell_volume)

    # ------------------------------------------------------------------
    # Underlying — kept as your z-score mean reversion
    # ------------------------------------------------------------------
    def _trade_underlying(self, S: float) -> None:
        history: list = self.last_traderData.get("velvet_prices", [])
        history.append(S)
        history = history[-self.SMA_WINDOW:]
        self.new_trader_data["velvet_prices"] = history

        if len(history) < self.SMA_WINDOW:
            return
        if self.underlying.best_bid is None or self.underlying.best_ask is None:
            return

        arr = np.array(history, dtype=float)
        sma = arr.mean()
        std = arr.std()
        if std < 1e-9:
            return

        zscore = (S - sma) / std
        pos = self.underlying.initial_position

        self.underlying.log("ZSCORE", round(zscore, 4))
        self.underlying.log("SMA", round(sma, 2))

        if zscore >= self.ZSCORE_THRESHOLD:
            self.underlying.ask(self.underlying.best_bid, self.underlying.mkt_buy_orders[self.underlying.best_bid])
            self.underlying.ask(self.underlying.best_ask - 1, self.underlying.max_allowed_sell_volume)
        elif zscore <= -self.ZSCORE_THRESHOLD:
            self.underlying.bid(self.underlying.best_ask, self.underlying.mkt_sell_orders[self.underlying.best_ask])
            self.underlying.bid(self.underlying.best_bid + 1, self.underlying.max_allowed_buy_volume)
        else:
            # Inventory offload via mispriced orders
            if pos > 0:
                for bid_price, bid_vol in self.underlying.mkt_buy_orders.items():
                    if bid_price > S:
                        self.underlying.ask(bid_price, bid_vol)
            elif pos < 0:
                for ask_price, ask_vol in self.underlying.mkt_sell_orders.items():
                    if ask_price < S:
                        self.underlying.bid(ask_price, ask_vol)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    def get_orders(self) -> dict:
        result: dict = {}

        S = self.underlying.fv
        if S is None or S <= 0:
            for option in self.options:
                result[option.name] = option.orders
            result[self.underlying.name] = self.underlying.orders
            return result

        # --- Options: rolling regression FV per strike ---
        for option in self.options:
            fv_pred, res_std, slope, n_pts = self._option_fv(option, S)

            if fv_pred is None or res_std is None:
                # Not enough history yet — sit out this tick
                option.log("warmup", n_pts, product_group=option.name)
                result[option.name] = option.orders
                continue

            # Sanity check: deep ITM should give slope ≈ 1, ATM in (0, 1)
            # Reject obviously broken fits
            if slope is not None and (slope < -0.1 or slope > 1.5):
                option.log("bad_slope", round(slope, 3), product_group=option.name)
                result[option.name] = option.orders
                continue

            self._trade_option(option, fv_pred, res_std)

            option.log("FV", round(fv_pred, 2), product_group=option.name)
            option.log("RSD", round(res_std, 2), product_group=option.name)
            option.log("BETA", round(slope if slope is not None else 0.0, 3), product_group=option.name)
            option.log("POS", option.initial_position, product_group=option.name)

            result[option.name] = option.orders

        # --- Underlying: z-score mean reversion ---
        self._trade_underlying(S)
        result[self.underlying.name] = self.underlying.orders

        return result


# -----------------------------------------------------------------------------
# Top-level Trader
# -----------------------------------------------------------------------------
class Trader:

    def run(self, state: TradingState):

        new_trader_data: dict = {}
        prints: dict = {
            "GENERAL": {"t": state.timestamp, "pos": state.position},
        }

        product_traders = {
            HYDROGEL_SYMBOL: HydrogelTrader,
            VELVET_SYMBOL: OptionTrader,
        }

        result: dict = {}
        conversions: int = 0

        for symbol, TraderClass in product_traders.items():
            if symbol in state.order_depths:
                try:
                    trader = TraderClass(state, prints, new_trader_data)
                    result.update(trader.get_orders())
                except Exception as e:
                    prints[symbol] = {"ERROR": str(e)}

        try:
            final_trader_data = json.dumps(new_trader_data)
        except Exception:
            final_trader_data = ""

        try:
            print(json.dumps(prints))
        except Exception:
            pass

        return result, conversions, final_trader_data