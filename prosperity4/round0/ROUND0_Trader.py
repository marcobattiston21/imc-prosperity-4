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
        self.max_vol_bid_price, self.max_vol_ask_price = self._get_max_vol_ask_bid()
        self.worst_bid, self.worst_ask = self._get_worst_bid_ask()
        self.best_bid, self.mid_price, self.best_ask = self._get_best_bid_ask()
        try: self.spread = self.best_ask - self.best_bid
        except: pass
        # Computes the max volumes we can trade based on the _get_max_volumes function
        self.max_allowed_buy_volume, self.max_allowed_sell_volume = self._get_max_volumes()


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
        mid_price = (best_bid + best_ask) / 2
        return best_bid, mid_price, best_ask

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
        # Here we're setting the fair value to 10000 (assumption based on the data)
        fv = 10_000

        # --- MARKET TAKING ---

        # This loop checks all the sell orders in the order book {sp = price, sv = volume}
        for sp, sv in self.mkt_sell_orders.items():
            
            # If there's an order below fair value, bid and fill that order. Max allocation is updated automatically
            if sp < fv:
                self.bid(sp, sv, logging=False)
            
            # If we have short positions open and there's a sell order at fair value, put a bid at fair value to close the position
            elif sp == fv and self.initial_position < 0:

                # Flatten short inventory at fair value
                self.bid(sp, min(sv, abs(self.initial_position)), logging=False)


        # This loop checks all the buy orders in the order book {bp = price, bv = volume}
        for bp, bv in self.mkt_buy_orders.items():
            
            # If there's an order above fair value, ask and fill that order. Max allocation is updated automatically
            if bp > fv:
                self.ask(bp, bv, logging=False)
            
            # If we have a long position open and there's a buy order at fair value, but an ask at fair value to close the position
            elif bp == fv and self.initial_position > 0:

                # Flatten long inventory at fair value
                self.ask(bp, min(bv, self.initial_position), logging=False)

        # --- MARKET MAKING ---

        # Quote 1 tick better than current best bid and ask, checking that we're not crossing fair value; sizes limited by remaining capacity
        if self.best_bid is not None:
            self.bid(min(self.best_bid + 1, fv - 1), self.max_allowed_buy_volume)
        if self.best_ask is not None:
            self.ask(max(self.best_ask - 1, fv + 1), self.max_allowed_sell_volume)

        self.log("POS",  self.initial_position)
        self.log("WBID", self.worst_bid)
        self.log("WASK", self.worst_ask)

        return {self.name: self.orders}

# Class used for TOMATOES
class TomatoesTrader(ProductTrader):
    
    # Constructor, does the same things as the ProductTrader constructor using the super(), simply restricts to TOMATOES
    def __init__(self, state: TradingState, prints: dict, new_trader_data: dict):
        super().__init__(TOMATOES_SYMBOL, state, prints, new_trader_data)

    # Function which applies our strategy for Tomatoes trading, outputs a dictionary containing the product name and the orders as a list
    def get_orders(self) -> dict:
        '''
        Strategy for TOMATOES: Mean reversion using a 20-tick rolling Z-score.
        - Entry: sell when z > 2, buy when z < -2
        - Exit: close short when z < 0, close long when z > 0
        If nothing happens, do simple MM
        '''

        # If either price is 0 (no valid max-volume level found), skip trading this tick
        if self.max_vol_bid_price == 0 or self.max_vol_ask_price == 0:
            return {self.name: self.orders}

        # Here we're setting the fair value to (max vol bid + max vol ask) / 2
        fv = (self.max_vol_ask_price + self.max_vol_bid_price) / 2

        
        # Load price history from previous ticks, append current mid price, keep last 20
        history: list = self.last_traderData.get("TOM_prices", [])
        history.append(self.mid_price)
        if len(history) > 20:
            history = history[-20:]
        self.new_trader_data["TOM_prices"] = history

        # Need at least 20 data points to compute a meaningful z-score, if not just MM
        if len(history) < 20:

            if self.best_bid is not None and self.max_allowed_buy_volume > 0:
                self.bid(min(self.best_bid + 1, fv - 1), self.max_allowed_buy_volume)
            if self.best_ask is not None and self.max_allowed_sell_volume > 0:
                self.ask(max(self.best_ask - 1, fv + 1), self.max_allowed_sell_volume)

            return {self.name: self.orders}

        mean = sum(history) / len(history)
        std = (sum((x - mean) ** 2 for x in history) / (len(history)) ** 0.5)

        # Avoid division by zero if prices are flat, if it is just MM
        if std == 0:
            if self.best_bid is not None and self.max_allowed_buy_volume > 0:
                self.bid(min(self.best_bid + 1, fv - 1), self.max_allowed_buy_volume)
            if self.best_ask is not None and self.max_allowed_sell_volume > 0:
                self.ask(max(self.best_ask - 1, fv + 1), self.max_allowed_sell_volume)

            return {self.name: self.orders}

        z_score = (self.mid_price - mean) / std

        # Place a sell order at fair value when the z score is higher than 2, place a buy order at fv when the z score is lower than -2
        if z_score > 2:
            self.ask(fv, self.max_allowed_sell_volume, logging=False)
        elif z_score < -2:
            self.bid(fv, self.max_allowed_buy_volume, logging=False)

        
        # Exit short when z-score falls back below 0
        if z_score < 0 and self.initial_position < 0:
            self.bid(fv, abs(self.initial_position), logging=False)
        # Exit long when z-score rises back above 0
        elif z_score > 0 and self.initial_position > 0:
            self.ask(fv, abs(self.initial_position), logging=False)

        # Market Making if we still have inventory available
        if self.best_bid is not None and self.max_allowed_buy_volume > 0:
            self.bid(min(self.best_bid + 1, fv - 1), self.max_allowed_buy_volume)
        if self.best_ask is not None and self.max_allowed_sell_volume > 0:
            self.ask(max(self.best_ask - 1, fv + 1), self.max_allowed_sell_volume)


        self.log("POS",  self.initial_position)
        self.log("WBID", self.worst_bid)
        self.log("WASK", self.worst_ask)
        self.log("Z",    round(z_score, 3))

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

