from datamodel import OrderDepth, TradingState, Order
import json
from typing import List

HYDROGEL_SYMBOL = "HYDROGEL_PACK"
VELVET_SYMBOL = "VELVETFRUIT_EXTRACT"

ATM_OPTION_SYMBOLS = [
    "VEV_5000",
    "VEV_5100",
    "VEV_5200",
    "VEV_5300",
    "VEV_5400",
]

MM_OPTION_SYMBOL          = "VEV_4500"   # simple MM
INFORMED_MM_OPTION_SYMBOL = "VEV_4000"   # MM gated by informed trader

USELESS_OPTIONS_SYMBOLS = [
    "VEV_5500",
    "VEV_6000",
    "VEV_6500",
]

POS_LIMITS = {
    HYDROGEL_SYMBOL: 200,
    VELVET_SYMBOL: 200,
    **{sym: 300 for sym in ATM_OPTION_SYMBOLS},
    MM_OPTION_SYMBOL: 300,
    INFORMED_MM_OPTION_SYMBOL: 300,
}

INFORMED_TRADER_ID = "Mark 14"
INFORMED_WINDOW = 500   # 5 timestamps × 100 ms each

NEUTRAL = 0
LONG = 1
SHORT = -1


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

    def check_for_informed(self) -> int:
        """
        Returns LONG, SHORT, or NEUTRAL based on whether the informed trader
        traded this product in the last 5 timestamps (INFORMED_WINDOW ms).
        Timestamps are stored as rolling lists keyed by '{name}_informed'.
        """
        key = self.name + "_informed"
        saved = self.last_traderData.get(key, {"buys": [], "sells": []})
        buy_timestamps: list = list(saved.get("buys", []))
        sell_timestamps: list = list(saved.get("sells", []))

        trades = (
            self.state.market_trades.get(self.name, [])
            + self.state.own_trades.get(self.name, [])
        )
        for trade in trades:
            if trade.buyer == INFORMED_TRADER_ID:
                buy_timestamps.append(trade.timestamp)
            if trade.seller == INFORMED_TRADER_ID:
                sell_timestamps.append(trade.timestamp)

        current_ts = self.state.timestamp
        buy_timestamps  = [ts for ts in buy_timestamps  if current_ts - ts <= INFORMED_WINDOW]
        sell_timestamps = [ts for ts in sell_timestamps if current_ts - ts <= INFORMED_WINDOW]

        self.new_trader_data[key] = {"buys": buy_timestamps, "sells": sell_timestamps}

        informed_bought = len(buy_timestamps) > 0
        informed_sold   = len(sell_timestamps) > 0

        if informed_bought and not informed_sold:
            direction = LONG
        elif informed_sold and not informed_bought:
            direction = SHORT
        elif informed_bought and informed_sold:
            if max(buy_timestamps) > max(sell_timestamps):
                direction = LONG
            elif max(sell_timestamps) > max(buy_timestamps):
                direction = SHORT
            else:
                direction = NEUTRAL
        else:
            direction = NEUTRAL

        self.log("TD", {"buys": buy_timestamps, "sells": sell_timestamps})
        self.log("ID", direction)
        return direction

    def get_orders(self) -> dict:
        return {}


class HydrogelTrader(ProductTrader):

    MEAN = 9994
    D_THRESHOLD_SOFT = 20    # distance (FV - mean) that switches regime
    D_THRESHOLD_HARD = 50

    def __init__(self, state: TradingState, prints: dict, new_trader_data: dict):
        super().__init__(HYDROGEL_SYMBOL, state, prints, new_trader_data)

    def get_orders(self) -> dict:

        if self.best_bid is None or self.best_ask is None:
            return {self.name: self.orders}

        fv = self.fv
        dist = fv - self.MEAN

        # Price well above mean → short-side focus: fill best bids, rest ask
        if dist > self.D_THRESHOLD_HARD:
            self.ask(self.best_bid, self.mkt_buy_orders[self.best_bid])
            self.ask(self.best_ask - 1, self.max_allowed_sell_volume)

        # Price well below mean → long-side focus: fill best asks, rest bid
        elif dist < -self.D_THRESHOLD_HARD:
            self.bid(self.best_ask, self.mkt_sell_orders[self.best_ask])
            self.bid(self.best_bid + 1, self.max_allowed_buy_volume)

        elif self.D_THRESHOLD_SOFT < dist < self.D_THRESHOLD_HARD:
            
            if self.best_bid >= fv:
                for bid_price, bid_vol in self.mkt_buy_orders.items():
                    if bid_price >= fv:
                        self.ask(bid_price, bid_vol)

            if self.best_ask > fv + 1:
                self.ask(self.best_ask - 1, self.max_allowed_sell_volume)
            else:
                self.ask(fv + 7, self.max_allowed_sell_volume)
        
        elif -self.D_THRESHOLD_HARD < dist < -self.D_THRESHOLD_SOFT:
            
            if self.best_ask <= fv:
                for ask_price, ask_vol in self.mkt_sell_orders.items():
                    if ask_price <= fv:
                        self.bid(ask_price, ask_vol)
                        
            if self.best_bid < fv - 1:
                self.bid(self.best_bid + 1, self.max_allowed_buy_volume)
            else:
                self.bid(fv - 7, self.max_allowed_buy_volume)

        # Within band → fill mispriced orders on both sides, then rest both
        else:
            
            if self.best_bid >= fv and self.initial_position > 0:
                for bid_price, bid_vol in self.mkt_buy_orders.items():
                    if bid_price >= fv:
                        self.ask(bid_price, bid_vol)
            
            elif self.best_ask <= fv and self.initial_position < 0:
                for ask_price, ask_vol in self.mkt_sell_orders.items():
                    if ask_price <= fv:
                        self.bid(ask_price, ask_vol)
            
            else:
                self.bid(self.best_bid + 1, self.max_allowed_buy_volume)
                self.ask(self.best_ask - 1, self.max_allowed_sell_volume)

        self.log("FV",   fv)
        self.log("DIST", round(dist, 2))
        self.log("POS",  self.initial_position)

        return {self.name: self.orders}


class OptionTrader:
    """
    Unified 500-tick z-score strategy for VELVETFRUIT_EXTRACT and all VEV options.

    Entry (flat position only):
      z >  3.0 → aggressive short: sell at best_bid
      z >  2.0 → passive short: fill bids >= fv
      z < -3.0 → aggressive long: buy at best_ask
      z < -2.0 → passive long: fill asks <= fv
      |z| <= 2 → no trade

    Hold: position non-zero, exit condition not met → no orders.

    Exit:
      pos < 0 and z < 0 → buy back: fill asks <= fv + rest bid at best_bid + 1
      pos > 0 and z > 0 → sell down: fill bids >= fv + rest ask at best_ask - 1
      Exit volume capped to abs(initial_position) to prevent direction flip.
    """

    ZSCORE_LOOKBACK = 500
    ZSCORE_THR_SOFT = 2.0
    ZSCORE_THR_HARD = 3.0

    def __init__(self, state: TradingState, prints: dict, new_trader_data: dict):
        self.state = state
        self.prints = prints
        self.new_trader_data = new_trader_data

        self.instruments: list[ProductTrader] = [
            ProductTrader(VELVET_SYMBOL, state, prints, new_trader_data, product_group="VELVET"),
            ProductTrader(INFORMED_MM_OPTION_SYMBOL, state, prints, new_trader_data, product_group="OPTION"),
            ProductTrader(MM_OPTION_SYMBOL, state, prints, new_trader_data, product_group="OPTION"),
        ] + [
            ProductTrader(sym, state, prints, new_trader_data, product_group="OPTION")
            for sym in ATM_OPTION_SYMBOLS
        ]

        self.last_traderData: dict = self.instruments[0].last_traderData

    def _get_z_score_for(self, key: str, price: float) -> tuple[float, float]:
        history: list = list(self.last_traderData.get(key, []))
        history.append(price)
        history = history[-self.ZSCORE_LOOKBACK:]
        self.new_trader_data[key] = history
        n = len(history)
        if n < 10:
            return 0.0, price
        sma = sum(history) / n
        variance = sum((x - sma) ** 2 for x in history) / n
        std = variance ** 0.5
        if std < 1e-9:
            return 0.0, sma
        return (price - sma) / std, sma

    def _apply_zscore_strategy(self, t: ProductTrader) -> None:
        if t.best_bid is None or t.best_ask is None or t.fv is None:
            return

        zscore, sma = self._get_z_score_for(f"{t.name}_zs", t.fv)
        pos = t.initial_position

        if pos < 0 and zscore < 0:
            # EXIT SHORT: buy back up to abs(pos)
            close_vol = abs(pos)
            for ask_price, ask_vol in t.mkt_sell_orders.items():
                if ask_price <= t.fv:
                    t.bid(ask_price, ask_vol)

        elif pos > 0 and zscore > 0:
            # EXIT LONG: sell down to flat
            for bid_price, bid_vol in t.mkt_buy_orders.items():
                if bid_price >= t.fv:
                    t.ask(bid_price, bid_vol)

        if zscore > self.ZSCORE_THR_HARD:
            # ENTRY aggressive short
            t.ask(t.best_bid, t.mkt_buy_orders[t.best_bid])

        elif zscore > self.ZSCORE_THR_SOFT:
            # ENTRY passive short
            for bid_price, bid_vol in t.mkt_buy_orders.items():
                if bid_price >= t.fv:
                    t.ask(bid_price, bid_vol)

        elif zscore < -self.ZSCORE_THR_HARD:
            # ENTRY aggressive long
            t.bid(t.best_ask, t.mkt_sell_orders[t.best_ask])

        elif zscore < -self.ZSCORE_THR_SOFT:
            # ENTRY passive long
            for ask_price, ask_vol in t.mkt_sell_orders.items():
                if ask_price <= t.fv:
                    t.bid(ask_price, ask_vol)

        t.log("Z",   round(zscore, 4))
        t.log("SMA", round(sma, 2))
        t.log("POS", pos)

    def get_orders(self) -> dict:
        result: dict = {}
        for t in self.instruments:
            self._apply_zscore_strategy(t)
            result[t.name] = t.orders
        return result


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