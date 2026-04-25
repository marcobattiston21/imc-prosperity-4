from datamodel import OrderDepth, TradingState, Order
import json
import math
import numpy as np
from typing import List

HYDROGEL_SYMBOL = "HYDROGEL_PACK"
VELVET_SYMBOL = "VELVETFRUIT_EXTRACT"

OPTION_SYMBOLS = [
    "VEV_5000",
    "VEV_5100",
    "VEV_5200",
    "VEV_5300",
    "VEV_5400"
]

MM_OPTIONS_SYMBOLS = [
    "VEV_4000",
    "VEV_4500"
]

USELESS_OPTIONS_SYMBOLS = [
    "VEV_5500",
    "VEV_6000",
    "VEV_6500"
]

POS_LIMITS = {
    HYDROGEL_SYMBOL: 200,
    VELVET_SYMBOL: 200,
    **{sym: 300 for sym in OPTION_SYMBOLS},
    **{sym: 300 for sym in MM_OPTIONS_SYMBOLS},
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



class HydrogelTrader(ProductTrader):

    MEAN = 9990

    SOFT_THRESHOLD = 20
    HARD_THRESHOLD = 60
    TAKE_THRESHOLD = 3
    HALF_SPREAD = 7

    '''
    FV Estimation: Mid Point between max vol bid and max vol ask
    Order placement: - If we are in the zone MEAN - SOFT_THRESHOLD < FV < MEAN + SOFT_THRESHOLD --> Normal Market Making and use misplaced orders to manage inventory
                     ---- WAY HIGH ----
                     - If we are in the zone MEAN + SOFT_THRESHOLD < FV < MEAN + HARD_THRESHOLD --> Only place resting sell orders at best ask - 1 and get mispriced orders
                     - If we are above the MEAN + HARD_THRESHOLD --> Sell aggressively at best bid

                     ---- WAY BELOW ----
                     - If we are in the zone MEAN - HARD_THRESHOLD < FV < MEAN - SOFT_THRESHOLD --> Only place resting bids at best bid + 1 and get mispriced orders
                     - If we are below MEAN - HARD_THRESHOLD --> Buy aggressively at best ask
    '''

    def __init__(self, state: TradingState, prints: dict, new_trader_data: dict):
        super().__init__(HYDROGEL_SYMBOL, state, prints, new_trader_data)

    def get_orders(self) -> dict:

        if self.best_bid is None or self.best_ask is None or self.spread is None:
            return {self.name: self.orders}

        fv = self.fv

        aggressive_selling = fv >= self.MEAN + self.HARD_THRESHOLD
        soft_selling = self.MEAN + self.SOFT_THRESHOLD < fv < self.MEAN + self.HARD_THRESHOLD
        normal_mm = self.MEAN - self.SOFT_THRESHOLD <= fv <= self.MEAN + self.SOFT_THRESHOLD
        soft_buying = self.MEAN - self.HARD_THRESHOLD < fv < self.MEAN - self.SOFT_THRESHOLD
        aggressive_buying = fv <= self.MEAN - self.HARD_THRESHOLD

        # NORMAL REGIME
        if normal_mm is True:

            # Mispriced bids --> sell into them, then place a resting buy at fv - HALF_SPREAD and ask inside spread
            if self.best_bid >= (fv - self.TAKE_THRESHOLD):

                for bid_price, bid_volume in self.mkt_buy_orders.items():
                    if bid_price >= (fv - self.TAKE_THRESHOLD):
                        self.ask(bid_price, bid_volume)

                self.bid(fv - self.HALF_SPREAD, self.max_allowed_buy_volume)
                self.ask(self.best_ask - 1, self.max_allowed_sell_volume)

            # Mispriced asks --> buy into them, then place a resting ask at fv + HALF_SPREAD and bid inside spread
            elif self.best_ask <= (fv + self.TAKE_THRESHOLD):

                for ask_price, ask_volume in self.mkt_sell_orders.items():
                    if ask_price <= (fv + self.TAKE_THRESHOLD):
                        self.bid(ask_price, ask_volume)

                self.bid(self.best_bid + 1, self.max_allowed_buy_volume)
                self.ask(fv + self.HALF_SPREAD, self.max_allowed_sell_volume)

            # No mispriced orders: post inside the spread
            else:
                self.bid(self.best_bid + 1, self.max_allowed_buy_volume)
                self.ask(self.best_ask - 1, self.max_allowed_sell_volume)

        # SOFT SELLING REGIME
        elif soft_selling is True:

            if self.best_bid >= (fv - self.TAKE_THRESHOLD):
                for bid_price, bid_volume in self.mkt_buy_orders.items():
                    if bid_price >= (fv - self.TAKE_THRESHOLD):
                        self.ask(bid_price, bid_volume)

            # If already short and there's a cheap ask, reduce inventory
            if self.initial_position < 0 and self.best_ask <= (fv + self.TAKE_THRESHOLD):
                self.bid(self.best_ask, self.mkt_sell_orders[self.best_ask])
                self.ask(fv + self.HALF_SPREAD, self.max_allowed_sell_volume)
            else:
                self.ask(self.best_ask - 1, self.max_allowed_sell_volume)

        # SOFT BUYING REGIME
        elif soft_buying is True:

            if self.best_ask <= (fv + self.TAKE_THRESHOLD):
                for ask_price, ask_volume in self.mkt_sell_orders.items():
                    if ask_price <= (fv + self.TAKE_THRESHOLD):
                        self.bid(ask_price, ask_volume)

            # If already long and there's a rich bid, reduce inventory
            if self.initial_position > 0 and self.best_bid >= (fv - self.TAKE_THRESHOLD):
                self.ask(self.best_bid, self.mkt_buy_orders[self.best_bid])
                self.bid(fv - self.HALF_SPREAD, self.max_allowed_buy_volume)
            else:
                self.bid(self.best_bid + 1, self.max_allowed_buy_volume)

        # AGGRESSIVE SELLING REGIME
        elif aggressive_selling is True:
            self.ask(self.best_bid, self.mkt_buy_orders[self.best_bid])
            self.ask(self.best_ask - 1, self.max_allowed_sell_volume)

        # AGGRESSIVE BUYING REGIME
        elif aggressive_buying is True:
            self.bid(self.best_ask, self.mkt_sell_orders[self.best_ask])
            self.bid(self.best_bid + 1, self.max_allowed_buy_volume)

        self.log("FV", fv)
        self.log("POS", self.initial_position)
        self.log("Aggressive Selling", aggressive_selling)
        self.log("Aggressive Buying", aggressive_buying)
        self.log("Soft Selling", soft_selling)
        self.log("Soft Buying", soft_buying)
        self.log("Normal Regime", normal_mm)
        self.log("BASK", self.best_ask)
        self.log("BBID", self.best_bid)

        return {self.name: self.orders}



class OptionTrader:
    """
    Vol-smile market-taking on VEV options + mean reversion on VELVETFRUIT_EXTRACT.

    Each tick:
      1. Compute mid-price IV for every option with a two-sided market.
      2. Fit a degree-2 parabola (polyfit) on log-moneyness vs IV.
      3. Re-evaluate each option's fair value using the smoothed smile IV.
      4. Sell into bids above FV, buy into asks below FV.
      5. For the underlying, run a z-score mean-reversion (SMA-100, threshold 2).
    """

    TTE = 5 / 365         # 5 calendar days, annualised
    SMA_WINDOW = 200
    ZSCORE_THRESHOLD = 3.0

    def __init__(self, state: TradingState, prints: dict, new_trader_data: dict):
        self.state = state
        self.prints = prints
        self.new_trader_data = new_trader_data

        self.options = [
            ProductTrader(sym, state, prints, new_trader_data, product_group="OPTION")
            for sym in OPTION_SYMBOLS
        ]
        self.underlying = ProductTrader(
            VELVET_SYMBOL, state, prints, new_trader_data, product_group="VELVET"
        )
        self.mm_options = [
            ProductTrader(opt, state, prints, new_trader_data, product_group="OPTION")
            for opt in MM_OPTIONS_SYMBOLS
        ]
        self.useless_options = [
            ProductTrader(opt, state, prints, new_trader_data, product_group="OPTION")
            for opt in USELESS_OPTIONS_SYMBOLS
        ]

        # Reuse the already-parsed trader data from the underlying trader
        self.last_traderData: dict = self.underlying.last_traderData

    # ------------------------------------------------------------------
    # Black-Scholes helpers (r = 0)
    # ------------------------------------------------------------------

    @staticmethod
    def _norm_cdf(x: float) -> float:
        return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

    @staticmethod
    def _norm_pdf(x: float) -> float:
        return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)

    def _bs_call(self, S: float, K: float, sigma: float) -> float:
        
        if sigma <= 0 or S <= 0 or K <= 0:
            return max(S - K, 0.0)
        
        sqrt_T = math.sqrt(self.TTE)
        d1 = (math.log(S / K) + 0.5 * sigma ** 2 * self.TTE) / (sigma * sqrt_T)
        d2 = d1 - sigma * sqrt_T
        return S * self._norm_cdf(d1) - K * self._norm_cdf(d2)

    def _implied_vol(self, price: float, S: float, K: float) -> float | None:
        """Newton-Raphson IV solver. Returns None if price <= intrinsic."""
        intrinsic = max(S - K, 0.0)
        if price <= intrinsic + 1e-6:
            return None
        
        sigma = 0.5
        
        sqrt_T = math.sqrt(self.TTE)
        
        for _ in range(100):
            d1 = (math.log(S / K) + 0.5 * sigma ** 2 * self.TTE) / (sigma * sqrt_T)
            d2 = d1 - sigma * sqrt_T
            bs = S * self._norm_cdf(d1) - K * self._norm_cdf(d2)
            vega = S * self._norm_pdf(d1) * sqrt_T
            
            diff = bs - price
            
            if abs(diff) < 1e-6:
                break
            
            if vega < 1e-10:
                break
            
            sigma -= diff / vega
            sigma = max(0.001, min(sigma, 10.0))
        
        return sigma

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def get_orders(self) -> dict:
        result: dict = {}

        S = self.underlying.fv
        
        if S is None or S <= 0:
            for option in self.options:
                result[option.name] = option.orders
            result[self.underlying.name] = self.underlying.orders
            return result

        # --- Step 1 & 2: collect IV / log-moneyness, fit smile parabola ---
        # Use all options (including MM ones) that have a two-sided market
        log_moneyness_list: list[float] = []
        iv_list: list[float] = []

        for option in self.options + self.mm_options + self.useless_options:
            if option.best_bid is None or option.best_ask is None:
                continue
            K = int(option.name.split("_")[-1])
            iv = self._implied_vol(option.fv, S, K)
            if iv is None:
                continue
            log_moneyness_list.append(math.log(K / S))
            iv_list.append(iv)

        fitted_coeffs = None
        if len(log_moneyness_list) >= 3:
            try:
                fitted_coeffs = np.polyfit(log_moneyness_list, iv_list, 2)
                self.new_trader_data["vol_smile_coeffs"] = fitted_coeffs.tolist()
            except Exception:
                pass

        # --- Step 3 & 4: fair-value each option and take mispriced orders ---
        for option in self.options:
            K = int(option.name.split("_")[-1])

            if fitted_coeffs is not None:
                lm = math.log(K / S)
                smooth_iv = float(np.polyval(fitted_coeffs, lm))
                smooth_iv = max(0.001, smooth_iv)
            else:
                # No smile available — fall back to raw IV for this option
                if option.best_bid is None or option.best_ask is None:
                    result[option.name] = option.orders
                    continue
                smooth_iv = self._implied_vol(option.mid_price, S, K)
                if smooth_iv is None:
                    result[option.name] = option.orders
                    continue

            theo_price = self._bs_call(S, K, smooth_iv)

            # Sell into bids above fair value
            if option.best_bid is not None and option.best_bid > theo_price:
                for bid_price, bid_vol in option.mkt_buy_orders.items():
                    if bid_price > theo_price:
                        option.ask(bid_price, bid_vol)

            # Buy into asks below fair value
            if option.best_ask is not None and option.best_ask < theo_price:
                for ask_price, ask_vol in option.mkt_sell_orders.items():
                    if ask_price < theo_price:
                        option.bid(ask_price, ask_vol)

            option.log("Theo Price", round(theo_price, 2))
            option.log("IV", round(smooth_iv, 4))
            result[option.name] = option.orders

        # --- Step 5: MM options ---
        result.update(self._get_mm_option_orders(fitted_coeffs, S))

        # --- Step 6: underlying mean reversion ---
        result.update(self._get_underlying_orders(S))

        return result

    def _get_mm_option_orders(self, fitted_coeffs, S: float) -> dict:
        result: dict = {}

        for option in self.mm_options:
            K = int(option.name.split("_")[-1])

            if option.best_bid is None or option.best_ask is None:
                result[option.name] = option.orders
                continue

            fv = option.fv

            # Use mispriced orders to offload inventory before posting quotes
            # Bids above FV: sell into them (reduces long / builds short)
            if option.best_bid >= (fv - 2):
                
                for bid_price, bid_vol in option.mkt_buy_orders.items():
                    if bid_price >= (fv - 2):
                        option.ask(bid_price, bid_vol)

                option.bid(option.second_best_bid + 1, option.max_allowed_buy_volume)
                option.ask(option.best_ask - 1, option.max_allowed_sell_volume)

            # Asks below FV: buy into them (reduces short / builds long)
            elif option.best_ask <= (fv + 2):
                
                for ask_price, ask_vol in option.mkt_sell_orders.items():
                    if ask_price <= (fv + 2):
                        option.bid(ask_price, ask_vol)
                
                option.ask(option.second_best_ask - 1, option.max_allowed_sell_volume)
                option.bid(option.best_bid + 1, option.max_allowed_buy_volume)
            
            else:
                # Resting MM quotes inside the spread
                option.bid(option.best_bid + 1, option.max_allowed_buy_volume)
                option.ask(option.best_ask - 1, option.max_allowed_sell_volume)


            result[option.name] = option.orders

        return result

    def _get_underlying_orders(self, S: float) -> dict:
        
        history: list = self.last_traderData.get("velvet_prices", [])
        history.append(S)
        
        if len(history) >= self.SMA_WINDOW:
            history = history[-self.SMA_WINDOW :]
        self.new_trader_data["velvet_prices"] = history

        if len(history) < self.SMA_WINDOW:
            return {self.underlying.name: self.underlying.orders}

        arr = np.array(history, dtype=float)
        sma = arr.mean()
        std = arr.std()

        if std < 1e-10:
            return {self.underlying.name: self.underlying.orders}

        zscore = (S - sma) / std

        self.underlying.log("ZSCORE", round(zscore, 4))
        self.underlying.log("SMA", round(sma, 2))

        if self.underlying.best_bid is None or self.underlying.best_ask is None:
            return {self.underlying.name: self.underlying.orders}
        
        if zscore >= self.ZSCORE_THRESHOLD:
            self.underlying.ask(self.underlying.best_bid, self.underlying.mkt_buy_orders[self.underlying.best_bid])
            self.underlying.ask(self.underlying.best_ask - 1, self.underlying.max_allowed_sell_volume)

        elif zscore <= -self.ZSCORE_THRESHOLD:
            self.underlying.bid(self.underlying.best_ask, self.underlying.mkt_sell_orders[self.underlying.best_ask])
            self.underlying.bid(self.underlying.best_bid + 1, self.underlying.max_allowed_buy_volume)
        



        return {self.underlying.name: self.underlying.orders}


class Trader:

    def run(self, state: TradingState):

        new_trader_data: dict = {}
        prints: dict = {
            "GENERAL": {"t": state.timestamp, "pos": state.position},
        }

        product_traders = {
            HYDROGEL_SYMBOL: HydrogelTrader,
            VELVET_SYMBOL: OptionTrader,
        }

        result: dict = {}
        conversions: int = 0

        for symbol, TraderClass in product_traders.items():
            if symbol in state.order_depths:
                try:
                    trader = TraderClass(state, prints, new_trader_data)
                    result.update(trader.get_orders())
                except Exception as e:
                    prints[symbol] = {"ERROR": str(e)}

        try:
            final_trader_data = json.dumps(new_trader_data)
        except Exception:
            final_trader_data = ""

        try:
            print(json.dumps(prints))
        except Exception:
            pass

        return result, conversions, final_trader_data
