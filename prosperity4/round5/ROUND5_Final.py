from datamodel import OrderDepth, TradingState, Order
import json
from typing import List

SOUNDS_RECORDERS_SYMBOLS = ["GALAXY_SOUNDS_DARK_MATTER", "GALAXY_SOUNDS_BLACK_HOLES", "GALAXY_SOUNDS_PLANETARY_RINGS", "GALAXY_SOUNDS_SOLAR_WINDS", "GALAXY_SOUNDS_SOLAR_FLAMES"]
SLEEPING_PODS_SYMBOLS = ["SLEEP_POD_SUEDE", "SLEEP_POD_LAMB_WOOL", "SLEEP_POD_POLYESTER", "SLEEP_POD_NYLON", "SLEEP_POD_COTTON"]
ORGANIC_MICROCHIPS_SYMBOLS =  ["MICROCHIP_CIRCLE", "MICROCHIP_OVAL", "MICROCHIP_SQUARE", "MICROCHIP_RECTANGLE", "MICROCHIP_TRIANGLE"]
PURIFICATION_PEBBLES_SYMBOLS = ["PEBBLES_XS", "PEBBLES_S", "PEBBLES_M", "PEBBLES_L", "PEBBLES_XL"]
DOMESTIC_ROBOTS_SYMBOLS = ["ROBOT_VACUUMING", "ROBOT_MOPPING", "ROBOT_DISHES", "ROBOT_LAUNDRY", "ROBOT_IRONING"]
UV_VISORS_SYMBOLS = ["UV_VISOR_YELLOW", "UV_VISOR_AMBER", "UV_VISOR_ORANGE", "UV_VISOR_RED", "UV_VISOR_MAGENTA"]
INSTANT_TRANSLATORS_SYMBOLS = ["TRANSLATOR_SPACE_GRAY", "TRANSLATOR_ASTRO_BLACK", "TRANSLATOR_ECLIPSE_CHARCOAL", "TRANSLATOR_GRAPHITE_MIST", "TRANSLATOR_VOID_BLUE"]
CONSTRUCTION_PANELS_SYMBOLS = ["PANEL_1X2", "PANEL_2X2", "PANEL_1X4", "PANEL_2X4", "PANEL_4X4"]
OXYGEN_SHAKES_SYMBOLS = ["OXYGEN_SHAKE_MORNING_BREATH", "OXYGEN_SHAKE_EVENING_BREATH", "OXYGEN_SHAKE_MINT", "OXYGEN_SHAKE_CHOCOLATE", "OXYGEN_SHAKE_GARLIC"]
SNACK_PACKS_SYMBOLS = ["SNACKPACK_CHOCOLATE", "SNACKPACK_VANILLA", "SNACKPACK_PISTACHIO", "SNACKPACK_STRAWBERRY", "SNACKPACK_RASPBERRY"]

POS_LIMITS = {
    **{sym: 10 for sym in SOUNDS_RECORDERS_SYMBOLS},
    **{sym: 10 for sym in SLEEPING_PODS_SYMBOLS},
    **{sym: 10 for sym in ORGANIC_MICROCHIPS_SYMBOLS},
    **{sym: 10 for sym in PURIFICATION_PEBBLES_SYMBOLS},
    **{sym: 10 for sym in DOMESTIC_ROBOTS_SYMBOLS},
    **{sym: 10 for sym in UV_VISORS_SYMBOLS},
    **{sym: 10 for sym in INSTANT_TRANSLATORS_SYMBOLS},
    **{sym: 10 for sym in CONSTRUCTION_PANELS_SYMBOLS},
    **{sym: 10 for sym in OXYGEN_SHAKES_SYMBOLS},
    **{sym: 10 for sym in SNACK_PACKS_SYMBOLS}
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

class AllTrader(ProductTrader):

    def __init__(self, state: TradingState, prints: dict, new_trader_data: dict):
        self.state = state
        self.prints = prints
        self.new_trader_data = new_trader_data

        all_symbols = [
            *SOUNDS_RECORDERS_SYMBOLS, *SLEEPING_PODS_SYMBOLS, *ORGANIC_MICROCHIPS_SYMBOLS,
            *PURIFICATION_PEBBLES_SYMBOLS, *DOMESTIC_ROBOTS_SYMBOLS, *UV_VISORS_SYMBOLS,
            *INSTANT_TRANSLATORS_SYMBOLS, *CONSTRUCTION_PANELS_SYMBOLS, *OXYGEN_SHAKES_SYMBOLS,
            *SNACK_PACKS_SYMBOLS
        ]

        self.instruments: list[ProductTrader] = [
            ProductTrader(sym, state, prints, new_trader_data)
            for sym in all_symbols
        ]

        self.last_traderData: dict = self.instruments[0].last_traderData


    def _apply_market_making(self, t: ProductTrader) -> None:

        if t.best_bid is None or t.best_ask is None or t.fv is None:
            return

        # Just market make at bb + 1 and ba - 1
        if t.best_bid < t.fv - 1:
            t.bid(t.best_bid + 1, t.max_allowed_buy_volume)
        if t.best_ask > t.fv + 1:
            t.ask(t.best_ask - 1, t.max_allowed_sell_volume)

        

    def get_orders(self) -> dict:
        result: dict = {}

        # Mean Reversion instruments
        for t in self.instruments:
            self._apply_market_making(t)
            result[t.name] = t.orders

        return result


        

class Trader:

    def run(self, state: TradingState):

        new_trader_data: dict = {}
        prints: dict = {
            "GENERAL": {"t": state.timestamp, "pos": state.position},
        }

        result: dict = {}
        conversions: int = 0

        try:
            trader = AllTrader(state, prints, new_trader_data)
            result.update(trader.get_orders())
        except Exception as e:
            prints["ALL"] = {"ERROR": str(e)}

        try:
            final_trader_data = json.dumps(new_trader_data)
        except Exception:
            final_trader_data = ""

        try:
            print(json.dumps(prints))
        except Exception:
            pass

        return result, conversions, final_trader_data