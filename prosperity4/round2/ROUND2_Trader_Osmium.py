from datamodel import OrderDepth, TradingState, Order
import json
from typing import List


OSMIUM_SYMBOL  = "ASH_COATED_OSMIUM"

POS_LIMITS = {
    OSMIUM_SYMBOL:   80,
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
 

# Class used for OSMIUM
class OsmiumTrader(ProductTrader):
    
    # KALMAN FILTER PARAMETERS
    Q = 2.0       # Process noise: how much true FV can move per tick
    R = 10.0      # Measurement noise: how noisy we think the midpoint is
    P_INIT = 100.0  # Initial variance (large = we don't trust the initial guess)
    
    # Z SCORE PARAMETERS
    MEAN_REV_LOOKBACK = 500
    ZSCORE_THRESHOLD = 2.5

    # Inventory threshold: inside [-zscore, zscore], suppress bids above +INV_THRESHOLD and asks below -INV_THRESHOLD
    INV_THRESHOLD = 40
    TAKE_LIMIT = 2
    HALF_SPREAD = 8
 
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
    
    def _kalman_sma(self, fv_kalman: float, window: int = 10) -> float:
        history: list = self.last_traderData.get("ash_kf_sma_history", [])
        history.append(fv_kalman)
        history = history[-window:]
        self.new_trader_data["ash_kf_sma_history"] = history
        return sum(history) / len(history)

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

        
        
        # SETTING UP AND COMPUTING FV AND Z SCORE ################################################
        # If there are no bids and no asks, fall back to last known mid price
        if self.best_ask is None and self.best_bid is None:
            self.mid_price = self.last_traderData.get("osmium_last_mid_price", None)
        else:
            self.new_trader_data["osmium_last_mid_price"] = self.mid_price

        # Compute the Fair Value as the SMA of the last 10 Kalman filter estimates
        fv_kalman, fv_var = self._kalman_update(self.mid_price)
        fv = self._kalman_sma(fv_kalman)

        if self.best_ask is None and self.best_bid is None:
            if fv is not None:
                self.bid(fv - self.HALF_SPREAD, self.max_allowed_buy_volume, logging = True)
                self.ask(fv + self.HALF_SPREAD, self.max_allowed_sell_volume, logging = True)

            return {self.name: self.orders}

        # Compute Z-Score
        z_score = self._z_score(fv)

        # Between the 2 thresholds of Z score, we just do market making on both sides by placing at optimal +-1, if we are too high or low on inventory, we stop placing on that side
        if -self.ZSCORE_THRESHOLD <= z_score <= self.ZSCORE_THRESHOLD:
            
            # Check if we are too long or too short
            long_heavy  = self.initial_position >  self.INV_THRESHOLD
            short_heavy = self.initial_position < -self.INV_THRESHOLD

            # Buy fills #####################################
            # We check if best bid exists and it's less than fv - take limit and we don't have too much long inventory
            if self.best_bid is not None and self.best_bid < (fv - self.TAKE_LIMIT) and not long_heavy:
                self.bid(self.best_bid + 1, self.max_allowed_buy_volume, logging = True)
            
            # We check if best bid exists and it's more than our threshold and we are not too long
            # If it's above the threshold, check second best bid as above or place at fv - 8
            elif self.best_bid is not None and self.best_bid >= (fv - self.TAKE_LIMIT) and not long_heavy:
                if self.second_best_bid is not None and self.second_best_bid < (fv - self.TAKE_LIMIT):
                    self.bid(self.second_best_bid + 1, self.max_allowed_buy_volume, logging = True)
                else:
                    self.bid(fv - self.HALF_SPREAD, self.max_allowed_buy_volume, logging = True)
            
            # If there's no best bid, check that we are not too long, then place at fv - half spread
            elif self.best_bid is None and not long_heavy:
                self.bid(fv - self.HALF_SPREAD, self.max_allowed_buy_volume, logging = True)

            
            # Sell fills #####################################
            # We check if best ask exists and it's more than fv + take limit and we don't have too much short inventory
            if self.best_ask is not None and self.best_ask > (fv + self.TAKE_LIMIT) and not short_heavy:
                self.ask(self.best_ask - 1, self.max_allowed_sell_volume, logging = True)
            
            # We check if best ask exists and it's less than our threshold and we are not too short
            # If it's below the threshold, check second best ask as above or place at fv + half spread
            elif self.best_ask is not None and self.best_ask <= (fv + self.TAKE_LIMIT) and not short_heavy:
                if self.second_best_ask is not None and self.second_best_ask > (fv + self.TAKE_LIMIT):
                    self.ask(self.second_best_ask - 1, self.max_allowed_sell_volume, logging = True)
                else:
                    self.ask(fv + self.HALF_SPREAD, self.max_allowed_sell_volume, logging = True)
            
            # If there's no best ask, check that we are not too short, then place at fv + half spread
            elif self.best_ask is None and not short_heavy:
                self.ask(fv + self.HALF_SPREAD, self.max_allowed_sell_volume, logging = True)
            
                
        # If we are above the threshold or below the threshold, we pick all the mispriced orders in the opposite direction, ignoring the inventory limits
        elif z_score > self.ZSCORE_THRESHOLD:
            
            # Check if there's a best bid above the threshold we chose (fv - take limit), if there's fill that order
            if self.best_bid is not None and self.best_bid >= (fv - self.TAKE_LIMIT):
                for bid_price, bid_volume in self.mkt_buy_orders.items():
                    if bid_price >= (fv - self.TAKE_LIMIT):
                        self.ask(bid_price, bid_volume, logging=True)

            # Check the best ask, if it exists and it's above the threshold of fv + take limit, place right below it
            if self.best_ask is not None and self.best_ask > (fv + self.TAKE_LIMIT):
                self.ask(self.best_ask - 1, self.max_allowed_sell_volume, logging=True)

            # If the best ask does not exist or it's too low, place at fv + half spread
            else:
                self.ask(fv + self.HALF_SPREAD, self.max_allowed_sell_volume, logging=True)

        # Opposite of what we did above
        elif z_score < -self.ZSCORE_THRESHOLD:
            
            # Check if there's a best ask below the threshold we chose (fv + take limit), if there's fill that order
            if self.best_ask is not None and self.best_ask <= (fv + self.TAKE_LIMIT):
                for ask_price, ask_volume in self.mkt_sell_orders.items():
                    if ask_price <= (fv + self.TAKE_LIMIT):
                        self.bid(ask_price, ask_volume, logging=True)

            # Check the best bid, if it exists and it's below the threshold of fv - take limit, place right above it
            if self.best_bid is not None and self.best_bid < (fv - self.TAKE_LIMIT):
                self.bid(self.best_bid + 1, self.max_allowed_buy_volume, logging=True)
            
            # If the best bid does not exist or it's too high, place at fv - half spread
            else:
                self.bid(fv - self.HALF_SPREAD, self.max_allowed_buy_volume, logging=True)


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