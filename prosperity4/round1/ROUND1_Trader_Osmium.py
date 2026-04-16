from datamodel import OrderDepth, TradingState, Order
import json
from typing import List
 
 
# Assigning the variables instead of using the string all the time
OSMIUM_SYMBOL = "ASH_COATED_OSMIUM"
 
# Hardcoding the position limits
POS_LIMITS = {
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
 
 
# Class used for EMERALDS
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
 
 
# TRADER CLASS
class Trader:
 
    def run(self, state: TradingState):
 
        new_trader_data: dict = {}
        prints: dict = {
            "GENERAL": {"t": state.timestamp, "pos": state.position},
        }
 
        # Register one TraderClass per product symbol.
        # Trader.run() instantiates each class only when its symbol
        # appears in the live order book.
        product_traders = {
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