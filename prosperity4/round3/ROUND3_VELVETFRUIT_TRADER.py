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
 
    # Constructor which assigns all the values based on the functions declared later
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
 
        # Recover the position limits from the initial dictionary defined before the class
        self.position_limit: int = POS_LIMITS.get(self.name, 0)
        
        # Recover the current position based on last iteration
        self.initial_position: int = self.state.position.get(self.name, 0)
        # self.expected_position: int = self.initial_position
 
        # Recover the order book data using the _parse_order_depth function, divides into mkt buy orders and sell orders dictionaries
        self.mkt_buy_orders, self.mkt_sell_orders = self._parse_order_depth()
        
        # Recover the max volume bid and ask price, the worst bid and ask prices (further from mid price) and the best ones (closer to the mid price) and computes the spread
        self.max_vol_bid, self.max_vol_ask = self._get_max_vol_ask_bid()
        self.worst_bid, self.worst_ask = self._get_worst_bid_ask()
        self.best_bid, self.mid_price, self.best_ask = self._get_best_bid_ask()
        self.second_best_bid, self.second_best_ask = self._get_second_best_bid_ask()
 
        # Computes the max volumes we can trade based on the _get_max_volumes function
        self.max_allowed_buy_volume, self.max_allowed_sell_volume = self._get_max_volumes()
 
        # Compute the bid gap and ask gap as the distance between best and second best
        self.bid_gap = abs(self.best_bid - self.second_best_bid) if self.second_best_bid is not None else 0
        self.ask_gap = abs(self.best_ask - self.second_best_ask) if self.second_best_ask is not None else 0
        
 
        # Compute the spread
        self.spread = self.best_ask - self.best_bid if self.best_ask is not None and self.best_bid is not None else None
 
 
    # Function used to recover all the data from the past iteration
    def _load_trader_data(self) -> dict:
        try:
            if self.state.traderData:
                return json.loads(self.state.traderData)
        except:
            pass
        return {}
 
    # Function used to recover the order book. Stores the buy orders as a dictionary in buy_orders{price, volume} and the same for sell orders (sorted from "best" to "worst" prices)
    def _parse_order_depth(self) -> tuple[dict, dict]:
        buy_orders: dict = {}
        sell_orders: dict = {}
        try:
            od: OrderDepth = self.state.order_depths[self.name]
            buy_orders  = {p: abs(v) for p, v in sorted(od.buy_orders.items(),  reverse=True)}
            sell_orders = {p: abs(v) for p, v in sorted(od.sell_orders.items())}
        except:
            pass
        return buy_orders, sell_orders
    
    # Function used to recover the max volume price of both bid and ask
    def _get_max_vol_ask_bid(self) -> tuple:
        
        max_vol_bid_price, max_vol_bid = 0, 0
        max_vol_ask_price, max_vol_ask = 0, 0
 
        for price, amount in self.mkt_buy_orders.items():
            if amount > max_vol_bid:
                max_vol_bid = amount
                max_vol_bid_price = price
 
        for price, amount in self.mkt_sell_orders.items():
            if amount > max_vol_ask:
                max_vol_ask = amount
                max_vol_ask_price = price
        
        return max_vol_bid_price, max_vol_ask_price
    
    # Function used to recover the worst price of both bid and ask and mid price
    def _get_worst_bid_ask(self) -> tuple:
 
        worst_bid = worst_ask = None
        
        try: worst_bid = min(self.mkt_buy_orders)
        except: pass
        try: worst_ask = max(self.mkt_sell_orders)
        except: pass
        
 
        return worst_bid, worst_ask
 
    # Function used to recover the best price of both bid and ask
    def _get_best_bid_ask(self) -> tuple:
    
        best_bid = max(self.mkt_buy_orders, default=None)
        best_ask = min(self.mkt_sell_orders, default=None)
        if best_bid is None:
            mid_price = best_ask
        elif best_ask is None:
            mid_price = best_bid
        else:
            mid_price = ( best_bid + best_ask ) / 2
        return best_bid, mid_price, best_ask
 
    # Function used to recover the second best price of both bid and ask
    def _get_second_best_bid_ask(self) -> tuple:
        
        bids = list(self.mkt_buy_orders.keys())
        asks = list(self.mkt_sell_orders.keys())
        second_best_bid = bids[1] if len(bids) >= 2 else None
        second_best_ask = asks[1] if len(asks) >= 2 else None
        
        return second_best_bid, second_best_ask
 
    # Function used to compute the maximum possible order size
    def _get_max_volumes(self) -> tuple[int, int]:
        return (
            self.position_limit - self.initial_position,
            self.position_limit + self.initial_position,
        )
 
    
    # Function used to place a buy order (bid), automatically checks if the volume set is higher than max possible, reduces it to that amount
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
    
    # Does the same thing as the bid function, just for the sell orders
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
 
    #Function used for the logs, doesn't matter to us for now
    def log(self, kind: str, message, product_group: str | None = None) -> None:
        group_key = product_group or self.product_group
        group = self.prints.get(group_key, {})
        group[kind] = message
        self.prints[group_key] = group
 
    # This class is here only for the name, it has to be re-defined in each of the subclasses
    def get_orders(self) -> dict:
        return {}


# ── VEV_5300 Trader ───────────────────────────────────────────────────────────
class Vev5300Trader(ProductTrader):
    """
    Strategy: Volume-weighted mid-price market making on VEV_5300.

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
    TRADE_SIZE   =  20  # contracts per signal
    HALF_SPREAD  = 5     # passive quote offset from mid
    INV_LIMIT    = 150   # inventory limit before reducing aggression

    def _update_history(self, mid: float) -> list:
        history: list = self.last_traderData.get("vev5300_hist", [])
        history.append(mid)
        history = history[-self.WINDOW:]
        self.new_trader_data["vev5300_hist"] = history
        return history

    def _rolling_median(self, history: list) -> float:
        s = sorted(history)
        n = len(s)
        if n % 2 == 1:
            return float(s[n // 2])
        return (s[n // 2 - 1] + s[n // 2]) / 2.0

    def __init__(self, state, prints, new_trader_data):
        super().__init__("VEV_5300", state, prints, new_trader_data)

    def get_orders(self) -> dict:

        # Step 1: Compute mid price using second best bid/ask if available, otherwise first        if self.best_bid is None or self.best_ask is None:
        if self.max_vol_bid == 0 or self.max_vol_ask == 0:
            return {self.name: self.orders}


        mid_price = (self.max_vol_bid + self.max_vol_ask) / 2
        if self.best_ask <= mid_price and self.best_ask is not None:
            # Buy the TRADE_SIZE amount at the best_ask price
            self.bid(self.best_ask, self.mkt_sell_orders[self.best_ask])
            if self.second_best_ask is not None:
                self.ask(self.second_best_ask -1, self.max_allowed_sell_volume)
            else:
                self.ask(mid_price+8, self.max_allowed_sell_volume)

        if self.best_bid >= mid_price and self.best_bid is not None:
            self.ask(self.best_bid, self.mkt_buy_orders[self.best_bid]) 
            if self.second_best_bid is not None:
                self.bid(self.second_best_bid+1, self.max_allowed_buy_volume)
            else:
                self.bid(mid_price-8, self.max_allowed_buy_volume)
        
        if self.initial_position>0 and self.best_ask is not None:
            self.ask(self.best_ask-1, self.max_allowed_sell_volume)
        elif self.initial_position<0 and self.best_bid is not None:
            self.bid(self.best_bid+1, self.max_allowed_buy_volume)
        elif self.initial_position == 0:
            pass
            
        return {self.name: self.orders}



# ── Main Trader ───────────────────────────────────────────────────────────────
class Trader:

    def run(self, state: TradingState):

        new_trader_data: dict = {}
        prints: dict = {"GENERAL": {"t": state.timestamp, "pos": state.position}}

        product_traders = {
            "VEV_5300": Vev5300Trader,
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


