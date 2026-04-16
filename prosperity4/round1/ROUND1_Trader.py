from datamodel import OrderDepth, TradingState, Order
import json
from typing import List


ROOT_SYMBOL  = "INTARIAN_PEPPER_ROOT"
OSMIUM_SYMBOL = "ASH_COATED_OSMIUM"

POS_LIMITS = {
    ROOT_SYMBOL:   80,
    OSMIUM_SYMBOL: 80,
}


# Blueprint class used as base for all the products. Has all the functions to recover the order book data, spread, possible trading volumes etc...
class ProductTrader:
 
    # Constructtor which assigns all the values based on the functions declared later
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
        self.expected_position: int = self.initial_position
 
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
        try: self.spread = self.best_ask - self.best_bid
        except: pass
 
 
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
    def bid(self, price: float, volume: float, logging: bool = True) -> None:
        
        # Computes the quantity as said before
        qty = min(abs(int(volume)), self.max_allowed_buy_volume)
        
        if qty <= 0:
            return
        
        self.orders.append(Order(self.name, int(price), qty))
        
        if logging:
            self.log("BUY", {"p": int(price), "v": qty})
        
        # Reduces the max allowed buy volume by the quantity we've just decided to buy
        self.max_allowed_buy_volume -= qty
 
    # Does the same thing as the bid function, just for the sell orders
    def ask(self, price: float, volume: float, logging: bool = True) -> None:
        
        qty = min(abs(int(volume)), self.max_allowed_sell_volume)
        
        if qty <= 0:
            return
        
        self.orders.append(Order(self.name, int(price), -qty))
        
        if logging:
            self.log("SELL", {"p": int(price), "v": qty})
        
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


class OsmiumTrader(ProductTrader):
    
    # KALMAN FILTER PARAMETERS
    Q = 2.0       # Process noise: how much true FV can move per tick
    R = 10.0      # Measurement noise: how noisy we think the midpoint is
    P_INIT = 100.0  # Initial variance (large = we don't trust the initial guess)
    
    # Z SCORE PARAMETERS
    MEAN_REV_LOOKBACK = 100
    ZSCORE_THRESHOLD = 2

 
    def _kalman_update(self, observation: float) -> tuple[float, float]:

        kf = self.last_traderData.get("ash_kf", None)
 
        if kf is None:
            # First tick ever → initialize with the current observation
            x = observation
            P = self.P_INIT

        else:
            x_prev = kf["x"]
            P_prev = kf["P"]
 
            # --- PREDICT ---
            # State transition is identity (random walk), so x_pred = x_prev
            x_pred = x_prev
            P_pred = P_prev + self.Q
 
            # --- UPDATE ---
            # Innovation (observation residual)
            y = observation - x_pred
            # Innovation covariance
            S = P_pred + self.R
            # Kalman gain
            K = P_pred / S
            # New state estimate
            x = x_pred + K * y
            # New estimate variance
            P = (1 - K) * P_pred
 
        self.new_trader_data["ash_kf"] = {"x": x, "P": P}

        return x, P
    
    def _z_score(self, fv: float) -> float:

        history: list = self.last_traderData.get("tom_mr_history", [])
        history.append(fv)
        history = history[-self.MEAN_REV_LOOKBACK:]
        self.new_trader_data["tom_mr_history"] = history
 
        n = len(history)
        if n < 10:
            return 0.0
 
        sma = sum(history) / n
        variance = sum((x - sma) ** 2 for x in history) / n
        std = variance ** 0.5
 
        if std < 1e-9:
            return 0.0
 
        return (fv - sma) / std


    # Constructor, does the same things as the ProductTrader constructor using the super(), simply restricts to EMERALDS
    def __init__(self, state: TradingState, prints: dict, new_trader_data: dict):
        super().__init__(OSMIUM_SYMBOL, state, prints, new_trader_data)
 
    # Function which applies our strategy for Emeralds trading, outputs a dictionary containing the product name and the orders as a list
    def get_orders(self) -> dict:
        '''
        FV Estimation: We use a Kalman Filter on the mid price to filter out all the noise.
        Order logic: - Normal market making between Z-Score -2 and 2, where it is computed as fv - SMA(100)
                     - If Z-Score outside these thresholds, we accumulate inventory in the opposite direction
                     - If there are misplaced bids and asks compared to our FV, we use them to unload some inventory and take free fills
        '''

        # If there are no bids and no asks, skip the turn --- FIX THIS LATER BY PLACING BIDS AND ASKS AT PREVIOUS PRICES
        if self.best_ask == None and self.best_bid == None:
            return {self.name: self.orders}

        # Compute the Fair Value as the output of the Kalman Filter
        fv, fv_var = self._kalman_update(self.mid_price)

        # Compute Z-Score
        z_score = self._z_score(fv)

        if -self.ZSCORE_THRESHOLD <= z_score <= self.ZSCORE_THRESHOLD:
            
            # Pick mispriced orders both on the buy and sell side
            if self.best_bid >= fv or self.best_ask <= fv:

                if self.best_bid >= fv:

                    for bid_price, bid_volume in self.mkt_buy_orders.items():
                        if bid_price >= fv:
                            self.ask(bid_price, bid_volume, logging = True)

                    self.ask(self.best_ask - 1, self.max_allowed_sell_volume, logging = True)
                
                elif self.best_ask <= fv:
                        
                    for ask_price, ask_volume in self.mkt_sell_orders.items():
                        if ask_price <= fv:
                            self.bid(ask_price, ask_volume, logging = True)
                    
                    self.bid(self.best_bid + 1, self.max_allowed_buy_volume, logging = True)

            # Normal Market Making
            else:
                if self.best_bid is not None:
                    self.bid(self.best_bid + 1, self.max_allowed_buy_volume, logging = True)
                if self.best_ask is not None:
                    self.ask(self.best_ask - 1, self.max_allowed_sell_volume, logging = True)
 
        elif z_score > self.ZSCORE_THRESHOLD:
            
            if self.best_bid >= fv:

                for bid_price, bid_volume in self.mkt_buy_orders.items():
                    if bid_price >= fv:
                        self.ask(bid_price, bid_volume, logging = True)

            elif self.best_ask is not None:
                self.ask(self.best_ask - 1, self.max_allowed_sell_volume, logging = True)

        elif z_score < -self.ZSCORE_THRESHOLD:
            
            if self.best_ask <= fv:
                for ask_price, ask_volume in self.mkt_sell_orders.items():
                    if ask_price <= fv:
                        self.bid(ask_price, ask_volume, logging = True)

            elif self.best_bid is not None:
                self.bid(self.best_bid + 1, self.max_allowed_buy_volume, logging = True)


        return {self.name: self.orders}


class RootTrader(ProductTrader):
    """
    Strategy for INTARIAN_PEPPER_ROOT
    ─────────────────────────────────
    The asset follows an almost perfect linear trend (R²=0.9999, slope=0.001).
    Residuals mean-revert with half-life < 1 timestamp, so there's no time to
    trade mean-reversion directly. Instead we:

    1. TREND LEG  – reserve TREND_ALLOC units as a permanent long from t=0.
                    Buy it immediately and never sell until end of day.

    2. MM LEG     – use the remaining FLUCT_ALLOC units to market-make around
                    the rolling fair value. The spread is ~13 ticks wide, so
                    quoting 1 tick inside best bid/ask captures ~5-6 ticks per
                    round trip while staying close to fair value.
                    We skew quotes based on current inventory to stay neutral.
    """

    # Linear model parameters (from analysis)
    SLOPE     = 0.001           # price units per timestamp
    # INTERCEPT = 13000.0048      # from regression

    # Position split (out of 80 limit)
    TREND_ALLOC = 48            # held as permanent long
    FLUCT_ALLOC = 32            # available for market making

    # Market making params (tuned to the ~13 tick spread, 6.5 tick depth)
    QUOTE_OFFSET   = 1          # quote 1 tick inside best bid/ask
    MAX_SKEW       = 28         # start skewing quotes when abs(mm_pos) > this
    SKEW_STEP      = 1          # extra ticks added per skew level

    def __init__(self, state: TradingState, prints: dict, new_trader_data: dict):
        super().__init__(ROOT_SYMBOL, state, prints, new_trader_data)

        # Retrieve persistent state from previous iteration
        self.trend_bought: bool = self.last_traderData.get("root_trend_bought", False)
        self.mm_position:  int  = self.last_traderData.get("root_mm_pos", 0)

        self.INTERCEPT = self._get_best_bid_ask()[1]
        # # Set intercept dynamically as the mid price of the first timestamp
        # if "root_intercept" in self.last_traderData:
        #     self.INTERCEPT = self.last_traderData["root_intercept"]
        # else:
        #     # Calculate what the intercept was originally based on the first observed price
        #     self.INTERCEPT = self.mid_price - (self.SLOPE * self.state.timestamp)
        
        # self.new_trader_data["root_intercept"] = self.INTERCEPT

    def _fair_value(self) -> float:
        # Rolling fair value: intercept + slope × current timestamp
        return self.INTERCEPT + self.SLOPE * self.state.timestamp

    def _mm_capacity(self) -> tuple[int, int]:
        """
        The MM book can go from -FLUCT_ALLOC to +FLUCT_ALLOC around neutral.
        Returns (max_mm_buy, max_mm_sell) based on current mm_position.
        """
        max_mm_buy  = self.FLUCT_ALLOC - self.mm_position
        max_mm_sell = self.FLUCT_ALLOC + self.mm_position
        return max(max_mm_buy, 0), max(max_mm_sell, 0)

    def get_orders(self) -> dict:

        if self.best_bid is None or self.best_ask is None:
            return {self.name: self.orders}

        fv = self._fair_value()

        # TREND LEG: buy TREND_ALLOC once at the very first timestamp
        if not self.trend_bought:
            # Place a market-aggressive bid to get filled immediately
            # We bid at best_ask to guarantee a fill
            self.bid(self.best_ask, self.TREND_ALLOC)
            self.new_trader_data["root_trend_bought"] = True
        else:
            self.new_trader_data["root_trend_bought"] = True

        # MM LEG: quote around fair value
        mm_buy_cap, mm_sell_cap = self._mm_capacity()

        # Inventory skew: if we're long, push ask closer and bid further to
        # offload. If short, do the opposite. Each SKEW_STEP units of imbalance
        # adds 1 tick of skew.
        skew = 0
        if abs(self.mm_position) > self.MAX_SKEW:
            # How many skew levels are we at?
            levels = (abs(self.mm_position) - self.MAX_SKEW) // self.SKEW_STEP + 1
            skew   = int(levels) * (1 if self.mm_position > 0 else -1)

        # Quote 1 tick inside current best bid/ask, skewed by inventory
        # Also clip to never cross fair value (don't buy above FV or sell below)
        bid_price = min(self.best_bid + self.QUOTE_OFFSET - skew, int(fv) - 1)
        ask_price = max(self.best_ask - self.QUOTE_OFFSET - skew, int(fv) + 1)

        # Only quote if there's capacity in the MM book
        if mm_buy_cap > 0:
            self.bid(bid_price, mm_buy_cap)

        if mm_sell_cap > 0:
            self.ask(ask_price, mm_sell_cap)

        # Persist MM position estimate for next iteration
        # (actual fills are unknown at this point; this is updated via position diff)
        self.new_trader_data["root_mm_pos"] = (
            self.initial_position - (self.TREND_ALLOC if self.trend_bought else 0)
        )

        # Logging
        self.log("POS",    self.initial_position)
        self.log("FV",     round(fv, 2))
        self.log("SKEW",   skew)
        self.log("MM_POS", self.mm_position)
        self.log("BBID",   self.best_bid)
        self.log("BASK",   self.best_ask)
        self.log("SPREAD", self.spread)

        return {self.name: self.orders}


class Trader:

    def run(self, state: TradingState):

        new_trader_data: dict = {}
        prints: dict = {
            "GENERAL": {"t": state.timestamp, "pos": state.position},
        }

        product_traders = {
            ROOT_SYMBOL:   RootTrader,
            OSMIUM_SYMBOL: OsmiumTrader,
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