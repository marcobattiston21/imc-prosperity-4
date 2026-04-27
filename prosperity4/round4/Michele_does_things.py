import json
from typing import List, Dict, Any
from datamodel import OrderDepth, TradingState, Order, Trade

VOUCHER_SYMBOLS = [
    "VELVETFRUIT_EXTRACT_VOUCHER_1",
    "VELVETFRUIT_EXTRACT_VOUCHER_2",
    "VELVETFRUIT_EXTRACT_VOUCHER_3",
    "VELVETFRUIT_EXTRACT_VOUCHER_4",
    "VELVETFRUIT_EXTRACT_VOUCHER_5",
    "VELVETFRUIT_EXTRACT_VOUCHER_6",
    "VELVETFRUIT_EXTRACT_VOUCHER_7",
    "VELVETFRUIT_EXTRACT_VOUCHER_8",
    "VELVETFRUIT_EXTRACT_VOUCHER_9",
    "VELVETFRUIT_EXTRACT_VOUCHER_10",
]

class Trader:

    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:

        result: Dict[str, List[Order]] = {}
        conversions: int = 0

        # ── 1. Load previous state ─────────────────────────────────────────────
        try:
            last_data = json.loads(state.traderData) if state.traderData else {}
        except:
            last_data = {}

        mark38_pos = last_data.get("mark38_pos", 0)
        mark55_pos = last_data.get("mark55_pos", 0)

        # ── 2. Track Mark 38 and Mark 55 inventory from market trades ──────────
        for symbol, trades in state.market_trades.items():
            for trade in trades:
                if symbol == "HYDROGEL_PACK":
                    if trade.buyer == "Mark 38":
                        mark38_pos += trade.quantity
                    elif trade.seller == "Mark 38":
                        mark38_pos -= trade.quantity

                elif symbol == "VELVETFRUIT_EXTRACT":
                    if trade.buyer == "Mark 55":
                        mark55_pos += trade.quantity
                    elif trade.seller == "Mark 55":
                        mark55_pos -= trade.quantity

        # Slow decay to avoid stale tracking
        mark38_pos = round(mark38_pos * 0.95)
        mark55_pos = round(mark55_pos * 0.95)

        # ── Helper: best bid/ask ───────────────────────────────────────────────
        def get_best_prices(order_depth: OrderDepth):
            best_bid = max(order_depth.buy_orders.keys()) if order_depth.buy_orders else None
            best_ask = min(order_depth.sell_orders.keys()) if order_depth.sell_orders else None
            return best_bid, best_ask

        # ── Helper: aggressively hit the book to flatten position ──────────────
        def panic_flatten(order_depth: OrderDepth, symbol: str, my_pos: int, target: int) -> List[Order]:
            """
            If my_pos > target: sell aggressively by hitting bids.
            If my_pos < -target: buy aggressively by lifting asks.
            """
            orders = []
            remaining = my_pos - target if my_pos > target else my_pos + target

            if my_pos > target:
                # Need to sell: hit bids from best down
                for bid_price in sorted(order_depth.buy_orders.keys(), reverse=True):
                    if remaining <= 0:
                        break
                    vol = min(order_depth.buy_orders[bid_price], remaining)
                    orders.append(Order(symbol, bid_price, -vol))
                    remaining -= vol

            elif my_pos < -target:
                # Need to buy: lift asks from best up
                for ask_price in sorted(order_depth.sell_orders.keys()):
                    if remaining <= 0:
                        break
                    vol = min(abs(order_depth.sell_orders[ask_price]), remaining)
                    orders.append(Order(symbol, ask_price, vol))
                    remaining -= vol

            return orders

        # ── 3. Generic market-making strategy ─────────────────────────────────
        def market_make(
            symbol: str,
            pos_limit: int,
            counterparty_pos: int,
            cp_skew_threshold: int = 15,
            panic_hard: int = 150,
            panic_soft: int = 80,
        ) -> List[Order]:

            if symbol not in state.order_depths:
                return []

            order_depth = state.order_depths[symbol]
            best_bid, best_ask = get_best_prices(order_depth)

            if best_bid is None or best_ask is None:
                return []

            spread = best_ask - best_bid
            my_pos = state.position.get(symbol, 0)

            # ── HARD PANIC: flatten now by taking liquidity ────────────────────
            if my_pos > panic_hard:
                return panic_flatten(order_depth, symbol, my_pos, panic_soft)
            if my_pos < -panic_hard:
                return panic_flatten(order_depth, symbol, my_pos, -panic_soft)

            # ── No spread to profit from: skip posting ─────────────────────────
            if spread <= 2:
                return []

            # ── Normal zone: post inside the spread ───────────────────────────
            my_bid_price = best_bid + 1
            my_ask_price = best_ask - 1

            bid_capacity = pos_limit - my_pos
            ask_capacity = -(pos_limit + my_pos)   # negative quantity for sells

            # ── SOFT ALARM: reduce size and skew prices away from risk ─────────
            if my_pos > panic_soft:
                bid_capacity = min(bid_capacity, 10)
                my_bid_price = best_bid - 2         # buy cheaper
                my_ask_price = best_ask - 2         # sell more aggressively

            elif my_pos < -panic_soft:
                ask_capacity = max(ask_capacity, -10)
                my_ask_price = best_ask + 2         # sell higher
                my_bid_price = best_bid + 2         # buy more aggressively

            # ── COUNTERPARTY SKEW (only in safe zone) ─────────────────────────
            elif -panic_soft <= my_pos <= panic_soft:
                if counterparty_pos > cp_skew_threshold:
                    # Counterparty is long → likely to sell soon → lean short
                    my_bid_price -= 2
                    my_ask_price = max(best_ask - 1, my_bid_price + 1)
                elif counterparty_pos < -cp_skew_threshold:
                    # Counterparty is short → likely to buy soon → lean long
                    my_ask_price += 2
                    my_bid_price = min(best_bid + 1, my_ask_price - 1)

            orders: List[Order] = []
            if bid_capacity > 0:
                orders.append(Order(symbol, my_bid_price, bid_capacity))
            if ask_capacity < 0:
                orders.append(Order(symbol, my_ask_price, ask_capacity))

            return orders

        # ── 4. HYDROGEL_PACK ──────────────────────────────────────────────────
        result["HYDROGEL_PACK"] = market_make(
            symbol="HYDROGEL_PACK",
            pos_limit=200,
            counterparty_pos=mark38_pos,
        )

        # ── 5. VELVETFRUIT_EXTRACT ────────────────────────────────────────────
        result["VELVETFRUIT_EXTRACT"] = market_make(
            symbol="VELVETFRUIT_EXTRACT",
            pos_limit=200,
            counterparty_pos=mark55_pos,
        )

        # ── 6. VELVETFRUIT_EXTRACT_VOUCHERs ───────────────────────────────────
        # Each voucher is an option: we market-make on it if the spread is wide.
        # Position limit is 300 per voucher.
        for vsymbol in VOUCHER_SYMBOLS:
            if vsymbol not in state.order_depths:
                continue

            order_depth = state.order_depths[vsymbol]
            best_bid, best_ask = get_best_prices(order_depth)

            if best_bid is None or best_ask is None:
                continue

            spread = best_ask - best_bid
            if spread <= 2:
                continue

            my_pos = state.position.get(vsymbol, 0)
            pos_limit = 300
            panic_hard = 270
            panic_soft = 180

            if my_pos > panic_hard:
                result[vsymbol] = panic_flatten(order_depth, vsymbol, my_pos, panic_soft)
                continue
            if my_pos < -panic_hard:
                result[vsymbol] = panic_flatten(order_depth, vsymbol, my_pos, -panic_soft)
                continue

            my_bid_price = best_bid + 1
            my_ask_price = best_ask - 1
            bid_capacity = pos_limit - my_pos
            ask_capacity = -(pos_limit + my_pos)

            if my_pos > panic_soft:
                bid_capacity = min(bid_capacity, 20)
                my_bid_price = best_bid - 2
                my_ask_price = best_ask - 2
            elif my_pos < -panic_soft:
                ask_capacity = max(ask_capacity, -20)
                my_ask_price = best_ask + 2
                my_bid_price = best_bid + 2

            orders: List[Order] = []
            if bid_capacity > 0:
                orders.append(Order(vsymbol, my_bid_price, bid_capacity))
            if ask_capacity < 0:
                orders.append(Order(vsymbol, my_ask_price, ask_capacity))
            result[vsymbol] = orders

        # ── 7. Save state for next tick ───────────────────────────────────────
        new_data = {
            "mark38_pos": mark38_pos,
            "mark55_pos": mark55_pos,
        }

        return result, conversions, json.dumps(new_data)