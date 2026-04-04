from datamodel import OrderDepth, TradingState, Order
import json
from typing import List


# ── Constants ──────────────────────────────────────────────────────────────────

EMERALD_SYMBOL = "EMERALDS"

POS_LIMITS = {
    EMERALD_SYMBOL: 80,
}


# ── Base class ─────────────────────────────────────────────────────────────────

class ProductTrader:
    """
    Shared utilities for a single-product trader.

    On construction, parses the order book and position state once so every
    subclass method can rely on clean, pre-computed attributes:

        mkt_buy_orders   – {price: abs_volume}, sorted high → low (best bid first)
        mkt_sell_orders  – {price: abs_volume}, sorted low  → high (best ask first)

        bid_wall / ask_wall – outermost (worst) prices on each side
        wall_mid            – midpoint of the two walls  →  used as fair value
        best_bid / best_ask – innermost (best) prices on each side

        max_allowed_buy_volume  – units we can still buy before hitting +pos_limit
        max_allowed_sell_volume – units we can still sell before hitting -pos_limit
                                  (both are decremented by bid() / ask())

    Subclasses only need to override get_orders().
    """

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
        self.expected_position: int = self.initial_position

        self.mkt_buy_orders, self.mkt_sell_orders = self._parse_order_depth()
        self.bid_wall, self.wall_mid, self.ask_wall = self._get_walls()
        self.best_bid, self.best_ask = self._get_best_bid_ask()
        self.max_allowed_buy_volume, self.max_allowed_sell_volume = self._get_max_volumes()

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _load_trader_data(self) -> dict:
        try:
            if self.state.traderData:
                return json.loads(self.state.traderData)
        except:
            pass
        return {}

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

    def _get_walls(self) -> tuple:
        """
        bid_wall = lowest (outermost) bid price
        ask_wall = highest (outermost) ask price
        wall_mid = their midpoint  →  effective fair value
        """
        bid_wall = ask_wall = wall_mid = None
        try: bid_wall = min(self.mkt_buy_orders)
        except: pass
        try: ask_wall = max(self.mkt_sell_orders)
        except: pass
        try: wall_mid = (bid_wall + ask_wall) / 2
        except: pass
        return bid_wall, wall_mid, ask_wall

    def _get_best_bid_ask(self) -> tuple:
        best_bid = max(self.mkt_buy_orders, default=None)
        best_ask = min(self.mkt_sell_orders, default=None)
        return best_bid, best_ask

    def _get_max_volumes(self) -> tuple[int, int]:
        return (
            self.position_limit - self.initial_position,
            self.position_limit + self.initial_position,
        )

    # ── Order submission ───────────────────────────────────────────────────────

    def bid(self, price: float, volume: float, logging: bool = True) -> None:
        """Submit a buy order, clamped to remaining buy capacity."""
        qty = min(abs(int(volume)), self.max_allowed_buy_volume)
        if qty <= 0:
            return
        self.orders.append(Order(self.name, int(price), qty))
        if logging:
            self.log("BUY", {"p": int(price), "v": qty})
        self.max_allowed_buy_volume -= qty

    def ask(self, price: float, volume: float, logging: bool = True) -> None:
        """Submit a sell order, clamped to remaining sell capacity."""
        qty = min(abs(int(volume)), self.max_allowed_sell_volume)
        if qty <= 0:
            return
        self.orders.append(Order(self.name, int(price), -qty))
        if logging:
            self.log("SELL", {"p": int(price), "v": qty})
        self.max_allowed_sell_volume -= qty

    # ── Logging ────────────────────────────────────────────────────────────────

    def log(self, kind: str, message, product_group: str | None = None) -> None:
        group_key = product_group or self.product_group
        group = self.prints.get(group_key, {})
        group[kind] = message
        self.prints[group_key] = group

    # ── Override in subclasses ─────────────────────────────────────────────────

    def get_orders(self) -> dict:
        return {}


# ── EMERALDS ───────────────────────────────────────────────────────────────────

class EmeraldsTrader(ProductTrader):
    """
    Market making for EMERALDS (fixed fair value = 10 000).

    The order book always has its midpoint exactly at 10 000:
        bids: 9992 / 9990   asks: 10008 / 10010
        → bid_wall = 9990, ask_wall = 10010, wall_mid = 10000

    Strategy (two phases per tick):

    1. TAKING — free edge
       • Buy every ask strictly below wall_mid  (price < 10 000)
       • Sell every bid strictly above wall_mid (price > 10 000)
       • If we carry inventory, also close it at exactly wall_mid.

    2. MAKING — collect the spread
       • Post a bid  at best_bid + 1  (9 993)   ← best bid in the book
       • Post an ask at best_ask - 1  (10 007)   ← best ask in the book
       • Size = full remaining position capacity on each side, so we always
         absorb as much order flow as possible without exceeding limits.
    """

    def __init__(self, state: TradingState, prints: dict, new_trader_data: dict):
        super().__init__(EMERALD_SYMBOL, state, prints, new_trader_data)

    def get_orders(self) -> dict:

        if self.wall_mid is None:
            return {}
        
        # Here we're setting the fair value to 10000
        fv = self.wall_mid  # 10 000 for EMERALDS

        # ── 1. TAKING ─────────────────────────────────────────────────────────

        # Lift every ask that is below fair value
        for sp, sv in self.mkt_sell_orders.items():
            
            # If there's an order below fv, bid and fill that order
            if sp < fv:
                self.bid(sp, sv, logging=False)
            
            # If we have short positions open, put a bid at fair value to close the position
            elif sp == fv and self.initial_position < 0:
                # Flatten short inventory at fair value (no edge, but reduces risk)
                self.bid(sp, min(sv, abs(self.initial_position)), logging=False)

        # Hit every bid that is above fair value
        for bp, bv in self.mkt_buy_orders.items():
            if bp > fv:
                self.ask(bp, bv, logging=False)
            elif bp == fv and self.initial_position > 0:
                # Flatten long inventory at fair value
                self.ask(bp, min(bv, self.initial_position), logging=False)

        # ── 2. MAKING ─────────────────────────────────────────────────────────

        # Quote 7 ticks inside fair value; sizes limited by remaining capacity
        self.bid(self.best_bid + 1, self.max_allowed_buy_volume)
        self.ask(self.best_ask - 1, self.max_allowed_sell_volume)

        self.log("POS",  self.initial_position)
        self.log("BWALL", self.bid_wall)
        self.log("AWALL", self.ask_wall)

        return {self.name: self.orders}


# ── Trader ─────────────────────────────────────────────────────────────────────

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

