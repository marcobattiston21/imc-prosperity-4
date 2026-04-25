from datamodel import OrderDepth, TradingState, Order
import json
import math
from typing import List

VELVETFRUIT_SYMBOL = "VELVETFRUIT_EXTRACT"

POS_LIMITS = {
    VELVETFRUIT_SYMBOL: 200,
    "VEV_4000": 200,
    "VEV_4500": 200,
    "VEV_5000": 200,
    "VEV_5100": 200,
    "VEV_5200": 200,
    "VEV_5300": 200,
    "VEV_5400": 200,
    "VEV_5500": 200,
    "VEV_6000": 200,
    "VEV_6500": 200,
}


# ── Base class ────────────────────────────────────────────────────────────────
class ProductTrader:

    def __init__(self, name, state, prints, new_trader_data, product_group=None):
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
        self.worst_bid, self.worst_ask = self._get_worst_bid_ask()
        self.best_bid, self.mid_price, self.best_ask = self._get_best_bid_ask()
        self.second_best_bid, self.second_best_ask = self._get_second_best_bid_ask()
        self.max_allowed_buy_volume, self.max_allowed_sell_volume = self._get_max_volumes()
        self.spread = self.best_ask - self.best_bid if self.best_ask is not None and self.best_bid is not None else None

    def _load_trader_data(self):
        try:
            if self.state.traderData:
                return json.loads(self.state.traderData)
        except:
            pass
        return {}

    def _parse_order_depth(self):
        buy_orders, sell_orders = {}, {}
        try:
            od: OrderDepth = self.state.order_depths[self.name]
            buy_orders  = {p: abs(v) for p, v in sorted(od.buy_orders.items(),  reverse=True)}
            sell_orders = {p: abs(v) for p, v in sorted(od.sell_orders.items())}
        except:
            pass
        return buy_orders, sell_orders

    def _get_worst_bid_ask(self):
        worst_bid = worst_ask = None
        try: worst_bid = min(self.mkt_buy_orders)
        except: pass
        try: worst_ask = max(self.mkt_sell_orders)
        except: pass
        return worst_bid, worst_ask

    def _get_best_bid_ask(self):
        best_bid = max(self.mkt_buy_orders, default=None)
        best_ask = min(self.mkt_sell_orders, default=None)
        if best_bid is None:
            mid_price = best_ask
        elif best_ask is None:
            mid_price = best_bid
        else:
            mid_price = (best_bid + best_ask) / 2
        return best_bid, mid_price, best_ask

    def _get_second_best_bid_ask(self):
        bids = list(self.mkt_buy_orders.keys())
        asks = list(self.mkt_sell_orders.keys())
        return (bids[1] if len(bids) >= 2 else None), (asks[1] if len(asks) >= 2 else None)

    def _get_max_volumes(self):
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

    def ask(self, price, volume, logging=True):
        qty = min(abs(int(volume)), self.max_allowed_sell_volume)
        if qty <= 0:
            return
        self.orders.append(Order(self.name, int(price), -qty))
        if logging:
            group = self.prints.get(self.product_group, {})
            group.setdefault("SELLS", []).append({"p": int(price), "v": qty})
            self.prints[self.product_group] = group
        self.max_allowed_sell_volume -= qty

    def log(self, kind, message, product_group=None):
        group_key = product_group or self.product_group
        group = self.prints.get(group_key, {})
        group[kind] = message
        self.prints[group_key] = group

    def get_orders(self):
        return {}


# ── VEV_4000 Trader ───────────────────────────────────────────────────────────
class Vev4000Trader(ProductTrader):
    """
    Strategy: Rolling-median mean reversion + market making on VEV_4000.

    Calibrated from JSON data:
      - VEV_4000 mid price ~1265, spread ~21 (bid ~1257, ask ~1278)
      - Two bid levels visible: best ~1257 (15 qty), second ~1254 (27 qty)
      - Price oscillates with amplitude ~6 around a drifting mean

    Phase 1 (< MIN_HISTORY ticks): quote inside spread passively to collect
    spread while building history. Quote at best_bid+1 / best_ask-1.

    Phase 2 (enough history): mean reversion.
      - dev < -ENTRY_THRESH: buy aggressively (lift ask + resting bid)
      - dev > +ENTRY_THRESH: sell aggressively (hit bid + resting ask)
      - |dev| small: passive MM inside spread + unwind inventory toward fv

    ENTRY_THRESH = 8 ≈ spread/2.5, ensures we only enter with real edge.
    """

    WINDOW       = 50    # rolling median window in ticks
    MIN_HISTORY  = 10    # ticks before mean-reversion kicks in
    ENTRY_THRESH = 8     # deviation threshold to enter (calibrated to spread)
    TRADE_SIZE   = 20    # contracts per signal
    HALF_SPREAD  = 5     # passive quote offset from mid
    INV_LIMIT    = 150   # inventory limit before reducing aggression

    def _update_history(self, mid: float) -> list:
        history: list = self.last_traderData.get("vev4000_hist", [])
        history.append(mid)
        history = history[-self.WINDOW:]
        self.new_trader_data["vev4000_hist"] = history
        return history

    def _rolling_median(self, history: list) -> float:
        s = sorted(history)
        n = len(s)
        if n % 2 == 1:
            return float(s[n // 2])
        return (s[n // 2 - 1] + s[n // 2]) / 2.0

    def __init__(self, state, prints, new_trader_data):
        super().__init__("VEV_4000", state, prints, new_trader_data)

    def get_orders(self) -> dict:

        if self.mid_price is None:
            return {self.name: self.orders}

        history = self._update_history(self.mid_price)
        pos     = self.initial_position
        n       = len(history)

        long_heavy  = pos >  self.INV_LIMIT
        short_heavy = pos < -self.INV_LIMIT

        # ── PHASE 1: warmup — passive MM to collect spread ────────────────────
        if n < self.MIN_HISTORY:
            if self.best_bid is not None and not long_heavy:
                self.bid(self.best_bid + 1, self.TRADE_SIZE)
            if self.best_ask is not None and not short_heavy:
                self.ask(self.best_ask - 1, self.TRADE_SIZE)
            return {self.name: self.orders}

        fv  = self._rolling_median(history)
        dev = self.mid_price - fv

        # ── PHASE 2a: aggressive mean reversion ──────────────────────────────
        if dev < -self.ENTRY_THRESH and not long_heavy:
            # Price well below fair value → BUY
            if self.best_ask is not None:
                self.bid(self.best_ask, self.TRADE_SIZE)          # lift ask
            if self.best_bid is not None:
                self.bid(self.best_bid + 1, self.TRADE_SIZE)      # resting bid

        elif dev > self.ENTRY_THRESH and not short_heavy:
            # Price well above fair value → SELL
            if self.best_bid is not None:
                self.ask(self.best_bid, self.TRADE_SIZE)          # hit bid
            if self.best_ask is not None:
                self.ask(self.best_ask - 1, self.TRADE_SIZE)      # resting ask

        # ── PHASE 2b: passive MM + inventory unwind ───────────────────────────
        else:
            if self.best_bid is not None and not long_heavy:
                self.bid(self.best_bid + 1, self.TRADE_SIZE)
            elif not long_heavy:
                self.bid(int(fv) - self.HALF_SPREAD, self.TRADE_SIZE)

            if self.best_ask is not None and not short_heavy:
                self.ask(self.best_ask - 1, self.TRADE_SIZE)
            elif not short_heavy:
                self.ask(int(fv) + self.HALF_SPREAD, self.TRADE_SIZE)

            # Unwind existing inventory toward fair value
            if pos > 0 and self.best_bid is not None:
                exit_price = max(int(fv), self.best_bid + 1)
                self.ask(exit_price, abs(pos))
            elif pos < 0 and self.best_ask is not None:
                exit_price = min(int(fv), self.best_ask - 1)
                self.bid(exit_price, abs(pos))

        self.log("POS",  pos)
        self.log("FV",   round(fv, 2))
        self.log("DEV",  round(dev, 2))
        self.log("N",    n)

        return {self.name: self.orders}



# ── Main Trader ───────────────────────────────────────────────────────────────
class Trader:

    def run(self, state: TradingState):

        new_trader_data: dict = {}
        prints: dict = {"GENERAL": {"t": state.timestamp, "pos": state.position}}

        product_traders = {
            # VELVETFRUIT_SYMBOL: OsmiumTrader,
            "VEV_4000":         Vev4000Trader,
        }

        result: dict = {}
        conversions: int = 0

        for symbol, TraderClass in product_traders.items():
            if symbol in state.order_depths:
                try:
                    trader = TraderClass(state, prints, new_trader_data)
                    result.update(trader.get_orders())
                except:
                    pass

        try:
            final_trader_data = json.dumps(new_trader_data)
        except:
            final_trader_data = ""

        try:
            print(json.dumps(prints))
        except:
            pass

        return result, conversions, final_trader_data