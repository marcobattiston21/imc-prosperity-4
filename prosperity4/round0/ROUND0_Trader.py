from datamodel import OrderDepth, TradingState, Order
import json
from typing import List
 
 
# Assigning the variables instead of using the string all the time
EMERALD_SYMBOL = "EMERALDS"
TOMATOES_SYMBOL = "TOMATOES"
 
# Hardcoding the position limits
POS_LIMITS = {
    EMERALD_SYMBOL: 80,
    TOMATOES_SYMBOL: 80,
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
 
 
# Class used for EMERALDS
class EmeraldsTrader(ProductTrader):
    
    FV = 10000
 
    # Constructor, does the same things as the ProductTrader constructor using the super(), simply restricts to EMERALDS
    def __init__(self, state: TradingState, prints: dict, new_trader_data: dict):
        super().__init__(EMERALD_SYMBOL, state, prints, new_trader_data)
 
    # Function which applies our strategy for Emeralds trading, outputs a dictionary containing the product name and the orders as a list
    def get_orders(self) -> dict:
        '''
        Stratagy for the EMERALDS:
        - FAIR VALUE: Set fixed at 10_000
        - MARKET TAKING: Since the fair value is fixed, we fill all the bid orders above the fair value (placing an ask order at that price)
                         Since the fair value is fixed, we fill all the ask orders below the fair value (placing a bid order at that price)
        - MARKET MAKING: We set orders at best_bid + 1 and best_ask -1 so that they get filled before the ones at the best possible values, if they don't get filled in the timestep,
                        they get automatically cancelled.
        - INVENTORY MANAGEMENT: If we have a short position open, and a sell order appears at fair value, use it to reduce the current position. Applies the other way for long positions 
        '''
        fv = self.FV
 
        # --- MARKET TAKING ---
        # If there are orders at FV, take them to offload some inventory
 
        for sp, sv in self.mkt_sell_orders.items():
            
            # If there's an order below fair value, bid and fill that order. Max allocation is updated automatically ### THIS PRETTY MUCH NEVER HAPPENS
            if sp < fv:
                self.bid(sp, sv, logging = True)
            
            # If we have short positions open and there's a sell order at fair value, put a bid at fair value to close the position ### THIS HAPPENS QUITE OFTEN
            elif sp == fv and self.initial_position < 0:
 
                # Flatten short inventory at fair value
                self.bid(sp, min(sv, abs(self.initial_position)), logging = True)
 
 
        # This loop checks all the buy orders in the order book {bp = price, bv = volume}
        for bp, bv in self.mkt_buy_orders.items():
            
            # If there's an order above fair value, ask and fill that order. Max allocation is updated automatically
            if bp > fv:
                self.ask(bp, bv, logging = True)
            
            # If we have a long position open and there's a buy order at fair value, but an ask at fair value to close the position
            elif bp == fv and self.initial_position > 0:
 
                # Flatten long inventory at fair value
                self.ask(bp, min(bv, self.initial_position), logging = True)
 
        # --- MARKET MAKING ---
 
        # Quote 1 tick better than current best bid and ask, checking that we're not crossing fair value; sizes limited by remaining capacity
        if self.best_bid is not None:
            self.bid(min(self.best_bid + 1, fv - 1), self.max_allowed_buy_volume)
        if self.best_ask is not None:
            self.ask(max(self.best_ask - 1, fv + 1), self.max_allowed_sell_volume)
 
        self.log("POS",  self.initial_position)
        self.log("BBID", self.best_bid)
        self.log("BASK", self.best_ask)
        self.log("MAXBUY", self.max_allowed_buy_volume)
        self.log("MAXSELL", self.max_allowed_sell_volume)
 
 
        return {self.name: self.orders}
 
# Class used for TOMATOES
class TomatoesTrader(ProductTrader):
 
    '''
    TOMATOES STRATEGY:
 
    FV Estimation: mid price of max-volume bid and ask levels.
 
    Two operating modes based on z-score from 200-tick rolling mean:
 
    === NORMAL MODE (|z-score| <= ZSCORE_THRESHOLD) ===
    Exactly the baseline: gap exploitation to flatten inventory, then two-sided MM.
 
    === MEAN-REVERSION MODE (|z-score| > ZSCORE_THRESHOLD) ===
    Price is many standard deviations from its long-run mean → expect it to revert.
 
    How we BUILD directional inventory:
    1. Gap exploitation is FLIPPED: instead of using outlier orders to flatten,
       we use them to build position in the reversion direction.
       - Price too HIGH → sell into any isolated high bid (even if we're already short)
       - Price too LOW  → buy any isolated low ask (even if we're already long)
    2. We also aggressively take any mispriced levels that align with our direction
       (market-take all bids above FV when going short, all asks below FV when going long).
 
    How we HOLD directional inventory:
    3. One-sided MM: only quote on the accumulation side, so bots can't fill us
       back to neutral. If we want short → only place asks. If we want long → only place bids.
    4. The position limit cap in bid()/ask() naturally prevents over-accumulation.
    '''
 
    GAP_THRESHOLD = 2
    INV_THRESHOLD = 0
    FV_THRESHOLD_LOADING = 2
    FV_THRESHOLD_CLEARING = 1
    SPREAD_THRESHOLD = 10
 
    # --- Mean-reversion parameters ---
    MEAN_REV_LOOKBACK = 100    # Rolling window for long-run SMA and std dev
    ZSCORE_THRESHOLD_LOADING = 2    # Z-score level to enter mean-reversion mode (tune this)
    ZSCORE_THRESHOLD_CLEARING = 1       

    def __init__(self, state: TradingState, prints: dict, new_trader_data: dict):
        super().__init__(TOMATOES_SYMBOL, state, prints, new_trader_data)
 
 
    def _compute_deviation(self, fv: float) -> float:
        """
        Appends current FV to a 100-tick rolling history (persisted in traderData).
        Returns z-score = (fv - sma) / std, measuring how many standard deviations
        the current price is from its rolling mean.
        Returns 0.0 during warmup (< 20 observations) so we stay in normal mode.
        """
        history: list = self.last_traderData.get("tom_mr_history", [])
        history.append(fv)
        history = history[-self.MEAN_REV_LOOKBACK:]
        self.new_trader_data["tom_mr_history"] = history
 
        n = len(history)
        if n < 50:
            return 0.0
 
        sma = sum(history) / n
        variance = sum((x - sma) ** 2 for x in history) / n
        std = variance ** 0.5
 
        if std < 1e-9:
            return 0.0
 
        return (fv - sma) / std
 
    def get_orders(self) -> dict:
 
        # --- SAFETY: need valid order book data ---
        if self.best_bid is None or self.best_ask is None:
            return {self.name: self.orders}
 
        fv = (self.max_vol_bid + self.max_vol_ask) / 2
        deviation = self._compute_deviation(fv)
 
        # Determine regime
        mean_rev_short = deviation > self.ZSCORE_THRESHOLD_LOADING    # price too HIGH → want to go short
        mean_rev_long  = deviation < -self.ZSCORE_THRESHOLD_LOADING   # price too LOW  → want to go long
        mean_rev_active = mean_rev_short or mean_rev_long
 

        if mean_rev_active:
 
            if mean_rev_short:
                # --- GOAL: accumulate and hold SHORT inventory ---

                # We fill all buy orders that are above our threshold (fv - 2)
                for bp, bv in self.mkt_buy_orders.items():
                    if bp >= int(fv - self.FV_THRESHOLD_LOADING):
                        self.ask(bp, bv, logging = True)
                
                # ONE-SIDED MM: only place asks so bots can't buy us back to neutral
                self.ask(self.best_ask - 1, self.max_allowed_sell_volume, logging = True)
 
            elif mean_rev_long:
                # --- GOAL: accumulate and hold LONG inventory ---

                # We fill all sell orders that are below our threshold (fv + 2)
                for ap, av in self.mkt_sell_orders.items():
                    if ap <= round(fv + self.FV_THRESHOLD_LOADING):
                        self.bid(ap, av, logging = True)

                # ONE-SIDED MM: only place bids so bots can't sell us back to neutral
                self.bid(self.best_bid + 1, self.max_allowed_buy_volume, logging = True)
 
 

        else:
 
            if self.spread <= self.SPREAD_THRESHOLD:
                
                # If the order is inside a certain range from FV, pick it
                if self.bid_gap > self.GAP_THRESHOLD and self.best_bid >= int(fv - self.FV_THRESHOLD_CLEARING) and self.initial_position > self.INV_THRESHOLD and -self.ZSCORE_THRESHOLD_CLEARING <= deviation <= self.ZSCORE_THRESHOLD_CLEARING:
                    self.ask(self.best_bid, min(self.initial_position, self.mkt_buy_orders[self.best_bid]), logging = True)
 
                elif self.ask_gap > self.GAP_THRESHOLD and self.best_ask <= round(fv + self.FV_THRESHOLD_CLEARING) and self.initial_position < -self.INV_THRESHOLD and -self.ZSCORE_THRESHOLD_CLEARING <= deviation <= self.ZSCORE_THRESHOLD_CLEARING:
                    self.bid(self.best_ask, min(abs(self.initial_position), self.mkt_sell_orders[self.best_ask]), logging = True)
                
                # Otherwise just market make inside the bid ask spread
                else:
                    self.bid(self.best_bid + 1, self.max_allowed_buy_volume, logging = True)
                    self.ask(self.best_ask - 1, self.max_allowed_sell_volume, logging = True)
            
            # If the spread is wide, do normal market making
            elif self.spread > self.SPREAD_THRESHOLD:
                self.bid(self.best_bid + 1, self.max_allowed_buy_volume, logging = True)
                self.ask(self.best_ask - 1, self.max_allowed_sell_volume, logging = True)
 
 
        self.log("POS", self.initial_position)
        self.log("FV", round(fv, 2))
        self.log("ZSCORE", round(deviation, 2))
        self.log("REGIME", "SHORT" if mean_rev_short else ("LONG" if mean_rev_long else "NORMAL"))
        self.log("BBID", self.best_bid)
        self.log("BASK", self.best_ask)
        self.log("SPREAD", self.spread)
        self.log("BID_GAP", self.bid_gap)
        self.log("ASK_GAP", self.ask_gap)
        self.log("MAXBUY", self.max_allowed_buy_volume)
        self.log("MAXSELL", self.max_allowed_sell_volume)
 
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
            EMERALD_SYMBOL: EmeraldsTrader,
            TOMATOES_SYMBOL: TomatoesTrader,
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
 