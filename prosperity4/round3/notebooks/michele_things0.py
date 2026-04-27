from datamodel import OrderDepth, TradingState, Order
import json
import math
from typing import List

# ============================================================
#  CONSTANTS
# ============================================================
UNDERLYING  = "VELVETFRUIT_EXTRACT"
VOUCHER_PFX = "VEV_"
STRIKES     = [4000, 4500, 5000, 5100, 5200, 5300, 5400, 5500, 6000, 6500]

POS_LIMITS = {
    UNDERLYING: 200,
    **{f"{VOUCHER_PFX}{K}": 300 for K in STRIKES},
}

TRADING_DAYS_PER_YEAR = 252
TICKS_PER_DAY         = 1000
TTE_START_DAYS        = 5.0
VOL_WINDOW            = 60
VOL_FALLBACK          = 0.20

# ── MM sul sottostante ───────────────────────────────────────
MM_HALF_SPREAD  = 1.0    # spread che postiamo intorno al mid
MM_VOLUME       = 10     # lotti per lato
MM_MAX_SKEW     = 15.0   # skew massimo per gestire posizione

# ── Breakout ─────────────────────────────────────────────────
BREAKOUT_WINDOW    = 40   # tick finestra high/low
BREAKOUT_VOLUME    = 20   # lotti per segnale
BREAKOUT_COOLDOWN  = 25   # tick di pausa dopo segnale
# Se il range high-low degli ultimi N tick è sotto questa soglia
# il mercato è "piatto" → MM. Sopra → breakout.
BREAKOUT_THRESHOLD = 8.0  # punti di range per distinguere piatto vs trend

# ── Delta hedge ──────────────────────────────────────────────
DELTA_MAX_SKEW = 5.0  # Max skew derivante dal delta globale

# ── Opzioni ──────────────────────────────────────────────────
OPT_HALF_SPREAD = 0.8    # Spread passivo
OPT_VOLUME      = 15     # Trade più sostanziosi dato che c'è un solo asset
OPT_MAX_SKEW    = 3.0    # Skew proporzionale
OPT_POS_LIMIT   = 300    # Possiamo usare l'intero limite su questa singola opzione


# ============================================================
#  BLACK-SCHOLES HELPERS
# ============================================================
def _norm_cdf(x: float) -> float:
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)

def bs_call_price(S: float, K: float, T: float, sigma: float) -> float:
    if T <= 0 or sigma <= 0:
        return max(0.0, S - K)
    sq = sigma * math.sqrt(T)
    d1 = (math.log(S / K) + 0.5 * sigma ** 2 * T) / sq
    d2 = d1 - sq
    return S * _norm_cdf(d1) - K * _norm_cdf(d2)

def bs_delta(S: float, K: float, T: float, sigma: float) -> float:
    if T <= 0 or sigma <= 0:
        return 1.0 if S > K else 0.0
    d1 = (math.log(S / K) + 0.5 * sigma ** 2 * T) / (sigma * math.sqrt(T))
    return _norm_cdf(d1)

def bs_vega(S: float, K: float, T: float, sigma: float) -> float:
    if T <= 0 or sigma <= 0:
        return 0.0
    sq = math.sqrt(T)
    d1 = (math.log(S / K) + 0.5 * sigma ** 2 * T) / (sigma * sq)
    return S * _norm_pdf(d1) * sq

# ============================================================
#  FAST GREEKS & PORTFOLIO EVALUATION
# ============================================================
INV_SQRT_2 = 1.0 / math.sqrt(2.0)
INV_SQRT_2PI = 1.0 / math.sqrt(2.0 * math.pi)

def get_call_greeks_r0(S: float, K: float, T: float, sigma: float) -> tuple[float, float, float, float]:
    """
    Calcola Delta, Gamma, Vega e Theta (Call, r=0) in una singola passata.
    """
    if T <= 0.0 or sigma <= 0.0:
        return (1.0 if S > K else 0.0), 0.0, 0.0, 0.0
        
    sqrt_T = math.sqrt(T)
    sigma_sqrt_T = sigma * sqrt_T
    d1 = (math.log(S / K) + 0.5 * sigma * sigma * T) / sigma_sqrt_T
    
    phi_d1 = INV_SQRT_2PI * math.exp(-0.5 * d1 * d1)
    Phi_d1 = 0.5 * (1.0 + math.erf(d1 * INV_SQRT_2))
    
    delta = Phi_d1
    s_phi_d1 = S * phi_d1
    gamma = phi_d1 / (S * sigma_sqrt_T)
    vega = s_phi_d1 * sqrt_T
    theta = -(s_phi_d1 * sigma) / (2.0 * sqrt_T)
    
    return delta, gamma, vega, theta

# Portafoglio di esempio (Butterfly Spread)
my_portfolio = {
    "VEV_5200": 10,
    "VEV_5300": -20,
    "VEV_5400": 10,
    "VELVETFRUIT_EXTRACT": 0
}

def get_portfolio_greeks(portfolio: dict, S: float, T: float, sigma: float) -> tuple[float, float, float, float]:
    """
    Calcola le Greche di portafoglio, escludendo gli strike >= 6000.
    """
    port_delta, port_gamma, port_vega, port_theta = 0.0, 0.0, 0.0, 0.0
    
    for asset, quantity in portfolio.items():
        if quantity == 0:
            continue
            
        if asset == "VELVETFRUIT_EXTRACT":
            port_delta += quantity * 1.0
            continue
            
        if asset.startswith("VEV_"):
            strike = float(asset.split("_")[1])
            # Esclude gli ultimi 2 strike altissimi (6000 e 6500)
            if strike >= 6000:
                continue
            
            d, g, v, t = get_call_greeks_r0(S, strike, T, sigma)
            port_delta += quantity * d
            port_gamma += quantity * g
            port_vega  += quantity * v
            port_theta += quantity * t
            
    return port_delta, port_gamma, port_vega, port_theta


# ============================================================
#  BASE CLASS
# ============================================================
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
        self.name             = name
        self.state            = state
        self.prints           = prints
        self.new_trader_data  = new_trader_data
        self.product_group    = name if product_group is None else product_group

        self.last_traderData: dict = self._load_trader_data()

        self.position_limit:   int = POS_LIMITS.get(self.name, 0)
        self.initial_position: int = self.state.position.get(self.name, 0)

        self.mkt_buy_orders, self.mkt_sell_orders = self._parse_order_depth()

        self.worst_bid, self.worst_ask               = self._get_worst_bid_ask()
        self.best_bid, self.mid_price, self.best_ask = self._get_best_bid_ask()
        self.second_best_bid, self.second_best_ask   = self._get_second_best_bid_ask()

        self.max_allowed_buy_volume, self.max_allowed_sell_volume = self._get_max_volumes()

        self.spread = (
            self.best_ask - self.best_bid
            if self.best_ask is not None and self.best_bid is not None
            else None
        )

    def _load_trader_data(self) -> dict:
        try:
            if self.state.traderData:
                return json.loads(self.state.traderData)
        except:
            pass
        return {}

    def _parse_order_depth(self) -> tuple[dict, dict]:
        buy_orders:  dict = {}
        sell_orders: dict = {}
        try:
            od: OrderDepth = self.state.order_depths[self.name]
            buy_orders  = {p: abs(v) for p, v in sorted(od.buy_orders.items(),  reverse=True)}
            sell_orders = {p: abs(v) for p, v in sorted(od.sell_orders.items())}
        except:
            pass
        return buy_orders, sell_orders

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
        return (bids[1] if len(bids) >= 2 else None,
                asks[1] if len(asks) >= 2 else None)

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

    def ask(self, price, volume, logging=True):
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


# ============================================================
#  UNDERLYING TRADER  —  MM + breakout adattivo
# ============================================================
class UnderlyingTrader(ProductTrader):

    def __init__(self, state: TradingState, prints: dict,
                 new_trader_data: dict, last_data: dict):
        super().__init__(UNDERLYING, state, prints, new_trader_data)

        # Storico prezzi per breakout e regime detection
        self.price_history: list = last_data.get("price_history", [])
        if self.mid_price is not None:
            self.price_history.append(self.mid_price)
        self.price_history = self.price_history[-(BREAKOUT_WINDOW + 1):]
        new_trader_data["price_history"] = self.price_history

        # Cooldown breakout
        self.cooldown: int = max(0, last_data.get("cooldown", 0) - 1)
        new_trader_data["cooldown"] = self.cooldown

    def _market_regime(self) -> str:
        """
        Ritorna 'flat' o 'trending' in base al range degli ultimi N tick.
        Se il range high-low è stretto → mercato piatto → MM.
        Se il range è ampio → mercato in trend → breakout.
        """
        if len(self.price_history) < BREAKOUT_WINDOW:
            return "flat"  # non abbastanza storia, default a MM
        window = self.price_history[-BREAKOUT_WINDOW:]
        price_range = max(window) - min(window)
        return "trending" if price_range > BREAKOUT_THRESHOLD else "flat"

    def _breakout_signal(self) -> int:
        """
        +1 compra, -1 vendi, 0 nessun segnale.
        Segnale solo se siamo in regime trending e senza cooldown.
        """
        if len(self.price_history) < BREAKOUT_WINDOW + 1:
            return 0
        if self.cooldown > 0:
            return 0

        current = self.price_history[-1]
        window  = self.price_history[-(BREAKOUT_WINDOW + 1):-1]
        high    = max(window)
        low     = min(window)

        if current > high:
            return 1
        if current < low:
            return -1
        return 0

    def trade(self, global_delta: float = 0.0) -> None:
        """
        Decide il regime e applica la strategia giusta.
        """
        if self.best_bid is None or self.best_ask is None:
            return

        regime = self._market_regime()
        self.log("REGIME", regime)

        if regime == "flat":
            self._do_market_make(global_delta)
        else:
            self._do_breakout()

    def _do_market_make(self, global_delta: float) -> None:
        """MM passivo: quota bid/ask intorno al mid, skew su posizione e DELTA."""
        fv   = self.mid_price
        
        # Skew posizione
        pos_skew = (self.initial_position / self.position_limit) * MM_MAX_SKEW
        
        # Skew Delta Globale (se delta > 0 voglio vendere, quindi alzo lo skew -> abbasso prezzi)
        delta_skew = max(-DELTA_MAX_SKEW, min(DELTA_MAX_SKEW, (global_delta / 100.0) * DELTA_MAX_SKEW))
        
        total_skew = pos_skew + delta_skew

        my_bid = round(fv - MM_HALF_SPREAD - total_skew)
        my_ask = round(fv + MM_HALF_SPREAD - total_skew)

        # PREVENZIONE ASSOLUTA ORDINI A MERCATO SUL SOTTOSTANTE (STOP BLEEDING)
        if self.best_ask is not None:
            my_bid = min(my_bid, self.best_ask - 1)
        if self.best_bid is not None:
            my_ask = max(my_ask, self.best_bid + 1)

        if self.max_allowed_buy_volume > 0:
            self.bid(my_bid, MM_VOLUME)
        if self.max_allowed_sell_volume > 0:
            self.ask(my_ask, MM_VOLUME)

        self.log("MM_BID", my_bid)
        self.log("MM_ASK", my_ask)
        self.log("G_DELTA", round(global_delta, 1))

    def _do_breakout(self) -> None:
        """Breakout: ordine aggressivo nella direzione del movimento."""
        signal = self._breakout_signal()

        if signal == 1:
            qty = min(BREAKOUT_VOLUME, self.max_allowed_buy_volume)
            if qty > 0:
                self.bid(self.best_ask, qty)
                self.new_trader_data["cooldown"] = BREAKOUT_COOLDOWN
                self.log("BREAKOUT", "BUY")

        elif signal == -1:
            qty = min(BREAKOUT_VOLUME, self.max_allowed_sell_volume)
            if qty > 0:
                self.ask(self.best_bid, qty)
                self.new_trader_data["cooldown"] = BREAKOUT_COOLDOWN
                self.log("BREAKOUT", "SELL")

        else:
            # Siamo in trend ma nessun nuovo breakout → MM leggero
            # per non stare fermi mentre aspettiamo il segnale
            self._do_market_make()


    def get_orders(self) -> dict:
        self.log("POS",  self.initial_position)
        self.log("BBID", self.best_bid)
        self.log("BASK", self.best_ask)
        return {self.name: self.orders}


# ============================================================
#  VOUCHER TRADER  —  solo long, compra con edge, vendi per profit
# ============================================================
class VoucherTrader(ProductTrader):

    def __init__(
        self,
        strike: int,
        state: TradingState,
        prints: dict,
        new_trader_data: dict,
        mid_und: float,
        T_years: float,
        sigma: float,
    ):
        ticker = f"{VOUCHER_PFX}{strike}"
        super().__init__(ticker, state, prints, new_trader_data, product_group="OPTIONS")

        self.strike     = strike
        self.mid_und    = mid_und
        self.T_years    = T_years
        self.sigma      = sigma
        self.fair_value = bs_call_price(mid_und, strike, T_years, sigma)
        self.delta      = bs_delta(mid_und, strike, T_years, sigma)

        # Sovrascriviamo il limite di rischio con quello conservativo
        self.position_limit = min(self.position_limit, OPT_POS_LIMIT)
        self.max_allowed_buy_volume, self.max_allowed_sell_volume = self._get_max_volumes()

    def get_orders(self) -> dict:
        fv = self.fair_value
        intrinsic = max(0.0, self.mid_und - self.strike)
        
        # --- A: ARBITRAGGIO PURO (INTRINSIC VALUE) ---
        # Se un'opzione quota a meno del suo valore intrinseco, compriamo a mercato!
        if self.best_ask is not None and self.best_ask < intrinsic - 0.5:
            if self.max_allowed_buy_volume > 0:
                self.bid(self.best_ask, min(OPT_VOLUME, self.max_allowed_buy_volume))
                return {self.name: self.orders}
        
        # --- B: PASSIVE MM ---
        skew = (self.initial_position / self.position_limit) * OPT_MAX_SKEW
        
        my_bid = math.floor(fv - OPT_HALF_SPREAD - skew)
        my_ask = math.ceil(fv + OPT_HALF_SPREAD - skew)
        
        # Safety: evita che il MM passivo diventi aggressivo se il fair value è "sballato"
        if self.best_ask is not None:
            my_bid = min(my_bid, self.best_ask - 1)
        if self.best_bid is not None:
            my_ask = max(my_ask, self.best_bid + 1)
        
        # Quotazione passiva bid/ask
        if self.max_allowed_buy_volume > 0:
            self.bid(my_bid, OPT_VOLUME)
        if self.max_allowed_sell_volume > 0:
            self.ask(my_ask, OPT_VOLUME)

        self.log("FV",   round(fv, 2))
        self.log("DELT", round(self.delta, 3))
        self.log("POS",  self.initial_position)

        return {self.name: self.orders}

    def net_delta_contribution(self) -> float:
        net_qty = sum(o.quantity for o in self.orders)
        return net_qty * self.delta


# ============================================================
#  VOLATILITY ESTIMATOR
# ============================================================
class VolEstimator:

    def __init__(self, window: int = VOL_WINDOW, fallback: float = VOL_FALLBACK):
        self._prices:  list = []
        self._window   = window
        self._fallback = fallback

    @classmethod
    def from_state(cls, last_data: dict, new_data: dict,
                   mid: float, window: int = VOL_WINDOW) -> "VolEstimator":
        est = cls(window=window)
        est._prices = last_data.get("vol_prices", [])
        est._prices.append(mid)
        est._prices = est._prices[-(window + 1):]
        new_data["vol_prices"] = est._prices
        return est

    def estimate(self) -> float:
        prices = self._prices
        if len(prices) < 5:
            return self._fallback
        log_returns = [
            math.log(prices[i] / prices[i - 1])
            for i in range(1, len(prices))
        ]
        mean     = sum(log_returns) / len(log_returns)
        variance = sum((r - mean) ** 2 for r in log_returns) / (len(log_returns) - 1)
        return math.sqrt(variance * TICKS_PER_DAY * TRADING_DAYS_PER_YEAR)


# ============================================================
#  MAIN TRADER
# ============================================================
class Trader:

    def run(self, state: TradingState):

        new_trader_data: dict = {}
        prints: dict = {
            "GENERAL": {"t": state.timestamp, "pos": state.position},
        }

        result:      dict = {}
        conversions: int  = 0

        if UNDERLYING not in state.order_depths:
            return result, conversions, ""

        # ── Carica stato precedente ──────────────────────────────
        try:
            last_data = json.loads(state.traderData) if state.traderData else {}
        except:
            last_data = {}

        # ── Underlying trader ────────────────────────────────────
        und_trader = UnderlyingTrader(state, prints, new_trader_data, last_data)
        if und_trader.best_bid is None or und_trader.best_ask is None:
            return result, conversions, ""

        mid_und = und_trader.mid_price

        # ── Volatility + TTE ─────────────────────────────────────
        vol_est = VolEstimator.from_state(last_data, new_trader_data, mid_und)
        sigma   = vol_est.estimate()

        tick = last_data.get("tick", 0) + 1
        new_trader_data["tick"] = tick
        T_years = max(
            (TTE_START_DAYS - tick / TICKS_PER_DAY) / TRADING_DAYS_PER_YEAR,
            0.5 / TRADING_DAYS_PER_YEAR,
        )

        # ── 1. Calcolo Delta Globale (Sottostante + Deep ITM) ────
        portfolio = {UNDERLYING: float(und_trader.initial_position)}
        
        # Filtriamo tutto il resto, tradando solo la Call più ITM
        ITM_STRIKE = STRIKES[0] # VEV_4000
        ticker_itm = f"{VOUCHER_PFX}{ITM_STRIKE}"
        
        portfolio[ticker_itm] = float(state.position.get(ticker_itm, 0))
            
        port_delta, port_gamma, port_vega, port_theta = get_portfolio_greeks(
            portfolio, mid_und, T_years, sigma
        )
        global_delta = port_delta

        # ── 2. Trade Sottostante (MM Passivo Hedged) ─────────────
        und_trader.trade(global_delta)
        result.update(und_trader.get_orders())

        # ── 3. Trade Opzione Deep ITM (MM Passivo Hedged) ────────
        if ticker_itm in state.order_depths:
            try:
                vt = VoucherTrader(ITM_STRIKE, state, prints, new_trader_data,
                                   mid_und, T_years, sigma)
                result.update(vt.get_orders())
            except Exception as e:
                prints.setdefault("ERRORS", []).append(f"{ticker_itm}: {e}")

        # ── 5. Serialise ─────────────────────────────────────────
        try:
            final_trader_data = json.dumps(new_trader_data)
        except:
            final_trader_data = ""

        try:
            print(json.dumps(prints))
        except:
            pass

        return result, conversions, final_trader_data