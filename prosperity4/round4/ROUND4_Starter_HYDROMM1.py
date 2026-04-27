from datamodel import OrderDepth, TradingState, Order
import json
from typing import List

HYDROGEL_SYMBOL = "HYDROGEL_PACK"
VELVET_SYMBOL = "VELVETFRUIT_EXTRACT"

ITM_OPTION_SYMBOLS = ["VEV_4000", "VEV_4500"]
ATM_OPTION_SYMBOLS = ["VEV_5000", "VEV_5100", "VEV_5200", "VEV_5300", "VEV_5400", "VEV_5500"]
OTM_OPTION_SYMBOLS = ["VEV_6000", "VEV_6500"]

POS_LIMITS = {
    HYDROGEL_SYMBOL: 200,
    VELVET_SYMBOL: 200,
    **{sym: 300 for sym in ITM_OPTION_SYMBOLS},
    **{sym: 300 for sym in ATM_OPTION_SYMBOLS},
    **{sym: 300 for sym in OTM_OPTION_SYMBOLS},
}



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


class HydrogelTrader(ProductTrader):

    def __init__(self, state: TradingState, prints: dict, new_trader_data: dict):
        super().__init__(HYDROGEL_SYMBOL, state, prints, new_trader_data)

    def get_orders(self) -> dict:

        if self.best_bid is None or self.best_ask is None:
            return {self.name: self.orders}

        fv = self.fv

        if self.best_ask <= fv + 1:
            self.bid(self.best_ask, self.mkt_sell_orders[self.best_ask])
        elif self.best_bid >= fv - 1:
            self.ask(self.best_bid, self.mkt_buy_orders[self.best_bid])
        
        else:
            self.bid(self.best_bid + 1, self.max_allowed_buy_volume)
            self.ask(self.best_ask - 1, self.max_allowed_sell_volume)

        self.log("FV",   fv)
        self.log("POS",  self.initial_position)

        return {self.name: self.orders}


class OptionTrader:

    LOOKBACK = 200    # rolling window length (ticks)
    ENTRY_Z  = 3.0    # enter when |z| exceeds this

    def __init__(self, state: TradingState, prints: dict, new_trader_data: dict):
        self.state = state
        self.prints = prints
        self.new_trader_data = new_trader_data

        all_symbols = (
            [VELVET_SYMBOL]
            + ATM_OPTION_SYMBOLS
        )

        self.instruments: list[ProductTrader] = [
            ProductTrader(sym, state, prints, new_trader_data)
            for sym in all_symbols
        ]

        self.itm_instruments: list[ProductTrader] = [
            ProductTrader(sym, state, prints, new_trader_data)
            for sym in ITM_OPTION_SYMBOLS
        ]
        self.last_traderData: dict = self.instruments[0].last_traderData

    def _get_z_score(self, key: str, price: float) -> tuple[float, float]:
        history: list = list(self.last_traderData.get(key, []))
        history.append(price)
        history = history[-self.LOOKBACK:]
        self.new_trader_data[key] = history
        n = len(history)
        if n < 200:
            return 0.0, price
        sma = sum(history) / n
        variance = sum((x - sma) ** 2 for x in history) / n
        std = variance ** 0.5
        if std < 1e-9:
            return 0.0, sma
        return (price - sma) / std, sma

    def _apply_mean_reversion(self, t: ProductTrader) -> None:
        if t.best_bid is None or t.best_ask is None or t.fv is None:
            return

        z, sma = self._get_z_score(t.name, t.fv)

        if z == 0.0:
            return

        # Accumulate shorts
        if z >= self.ENTRY_Z:
            # ENTRY short: price stretched above mean
            t.ask(t.best_bid, t.mkt_buy_orders[t.best_bid])
            t.ask(t.best_ask - 1, t.max_allowed_sell_volume)

        # Accumulate longs
        elif z <= -self.ENTRY_Z:
            # ENTRY long: price stretched below mean
            t.bid(t.best_ask, t.mkt_sell_orders[t.best_ask])
            t.bid(t.best_bid + 1, t.max_allowed_buy_volume)
        


        t.log("Z",   round(z, 3))
        t.log("SMA", round(sma, 2))
        t.log("POS", t.initial_position)

    def _apply_market_making(self, t: ProductTrader) -> None:

        if t.best_bid is None or t.best_ask is None or t.fv is None:
            return
        
        # Just market make at bb + 2 and ba - 2
        if t.best_bid < t.fv - 2:
            t.bid(t.best_bid + 2, t.max_allowed_buy_volume)
        if t.best_ask > t.fv + 2:
            t.ask(t.best_ask - 2, t.max_allowed_sell_volume)

    def get_orders(self) -> dict:
        result: dict = {}

        # Mean Reversion instruments
        for t in self.instruments:
            self._apply_mean_reversion(t)
            result[t.name] = t.orders
        
        # Market Making Instruments
        for t in self.itm_instruments:
            self._apply_market_making(t)
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