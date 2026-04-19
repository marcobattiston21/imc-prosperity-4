from datamodel import OrderDepth, TradingState, Order
import json
from typing import List


ROOT_SYMBOL  = "INTARIAN_PEPPER_ROOT"

POS_LIMITS = {
    ROOT_SYMBOL:   80,
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
 

class RootTrader(ProductTrader):


    # Linear model parameters (from analysis)
    SLOPE = 0.001           # price units per timestamp
    DOWNSIDE_INVENTORY_LIMIT = 70

    def __init__(self, state: TradingState, prints: dict, new_trader_data: dict):
        super().__init__(ROOT_SYMBOL, state, prints, new_trader_data)
        
        self.INTERCEPT = self._get_intercept()

    # setting intercept 
    def _get_intercept(self) -> float:

        INTERCEPT = self.last_traderData.get("intercept", None)
        
        if INTERCEPT is None and self.spread is not None and self.spread >= 12:
            INTERCEPT = self.mid_price - self.SLOPE * self.state.timestamp

        self.new_trader_data["intercept"] = INTERCEPT
        
        return INTERCEPT  


    def _fair_value(self) -> float:

        # Rolling fair value: intercept + slope × current timestamp
        fv = self.INTERCEPT + self.SLOPE * self.state.timestamp if self.INTERCEPT is not None else None
        
        return fv


    def get_orders(self) -> dict:
        
        # Get the START signal from past iteration
        START = self.last_traderData.get("START", False)

        # Compute the fair value as intercept + slope * timestamp
        fv = self._fair_value()

        # If the fair value is None (Missing bids or asks or particular situation, skip the turn)
        if fv is None:
            self.new_trader_data["START"] = START
            return {self.name: self.orders} 
        
        # If the fair value is not none
        elif fv is not None:
           
            # If our initial position is equal to 80 (full long), switch the START signal to True such that we don't buy at best ask
            if self.initial_position == 80:
                START=True
            
            # If we are not yet at 80 longs, buy at best ask for that amount and place resting orders at best bid + 1 or fv - 7
            if START == False: # starting cycle

                # If there's a best ask, fill that order
                if self.best_ask is not None:
                    self.bid(self.best_ask, min(self.max_allowed_buy_volume, self.mkt_sell_orders[self.best_ask]))
                
                # Place resting orders at best bid or fv - 7
                if self.best_bid is not None and self.best_bid < int(fv):
                    self.bid(self.best_bid + 1, self.max_allowed_buy_volume)
                
                else:
                    self.bid(fv - 7, self.max_allowed_buy_volume)
                
                return {self.name: self.orders}
            
            # If the START is True (we got to 80 inventory)
            elif START == True:
                
                # If we're 80 contracts long, look for opportunities to sell either at best ask - 1 or at fv + 7 if best ask is not present.
                # Use misplaced bids (above fv) to get fills
                if self.initial_position == 80:
                    
                    # Check for mispriced bids (above fv)
                    if self.best_bid is not None and self.best_bid >= int(fv + 3):
                        
                        # Cycle through all bid orders and check if they are above fv and above last buy price
                        for bid_price, bid_volume in self.mkt_buy_orders.items():
                            if bid_price >= int(fv + 3):
                                self.ask(bid_price, bid_volume, logging = True)

                        # Position a resting bid to get back to 80 inventory either at second best + 1 or fv - 7
                        if self.second_best_bid is not None and self.second_best_bid < int(fv - 1):
                            self.bid(self.second_best_bid + 1 , self.max_allowed_buy_volume)
                        else:
                            self.bid(fv - 7, self.max_allowed_buy_volume)

                    # If the best ask exists, place a resting ask below it (floored at last_buy_price+1), otherwise place at fv + 8
                    if self.best_ask is not None:
                        self.ask(self.best_ask - 1, self.max_allowed_sell_volume)
                    else:
                        self.ask(fv + 8, self.max_allowed_sell_volume)

                # If we are below 80 inventory, it means we shorted something and we must get back to 80 inventory. 
                # To do that we check for mispriced asks and place bid orders at best bid + 1 or fv - 7, on top of picking mispriced bids to sell.
                if self.initial_position < 80:
                    
                    # First we look for mispriced asks to fill them and get back to max inventory
                    if self.best_ask is not None and self.best_ask <= int(fv):

                        # Cycle through all ask orders and check if they are below fv; track last buy price
                        for ask_price, ask_volume in self.mkt_sell_orders.items():
                            if ask_price <= int(fv):
                                self.bid(ask_price, ask_volume, logging = True)
                                
                        
                    # Secondly, we check for mispriced bids (above fv) to get free sells and to make space for more opportunities
                    # We put int(fv + 2) to be more selective and limit this to when we are above 65 inventory, so that we don't drop too low with our long inventory
                    elif self.best_bid is not None and self.best_bid >= int(fv + 3) and self.DOWNSIDE_INVENTORY_LIMIT < self.initial_position < 80:
                        
                        # Cycle through all bid orders above fv and above fv + 2
                        for bid_price, bid_volume in self.mkt_buy_orders.items():
                            if bid_price >= int(fv + 3):
                                self.ask(bid_price, bid_volume, logging = True)

                        # Position a resting bid to get back to 80 inventory either at second best + 1 or fv - 7
                        if self.second_best_bid is not None and self.second_best_bid < int(fv - 1):
                            self.bid(self.second_best_bid + 1 , self.max_allowed_buy_volume)
                        else:
                            self.bid(fv - 7, self.max_allowed_buy_volume)
                    
                    # If we are here it means that the orders are far from the fv, in which case we just place resting bids to get back to 80 inventory
                    # If the best bid exists, place a resting bid below it, otherwise place at fv - 8 to get back to 80 inventory. 
                    # We only place bids because we want to get back to max inventory. Once at 80 we start placing asks once again
                    # We also check if best bid < fv because it's possible that it's above fv, but we didn't sell into it because we are low on inventory, so we skipped that if
                    elif self.best_bid is not None and self.best_bid < fv:
                        self.bid(self.best_bid + 1, self.max_allowed_buy_volume)
                    else:
                        self.bid(fv - 7, self.max_allowed_buy_volume)
        
        # We keep passing the START signal from one iteration to the following one to not get back to the starting buying rally
        self.new_trader_data["START"] = START


        # Logging
        self.log("POS",    self.initial_position)
        self.log("FV",     round(fv, 2))
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