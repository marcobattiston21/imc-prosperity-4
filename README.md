# IMC Prosperity 4 - Stochastic Bulls

> **IMC Prosperity 4** is IMC Trading's annual global algorithmic and manual trading competition for STEM students, running from April 14 to April 30, 2026. Teams of up to five compete across five rounds — each consisting of one algorithmic challenge and one manual challenge — maximising profit in the competition's virtual currency, **XIRECs**.

---

## The Team

| [<img src="https://media.licdn.com/dms/image/v2/D4D03AQFV2pB_oC_yvg/profile-displayphoto-scale_400_400/B4DZh24CaAHAAg-/0/1754341060294?e=1779926400&v=beta&t=usKoCyYszECpoC7lSYx6HoPPWW5RxC52LvDjDBP5xpQ" width="150" alt="Marco Battiston">](https://www.linkedin.com/in/marcobattiston/) | [<img src="https://media.licdn.com/dms/image/v2/D4D03AQFCvIwMC6eK0w/profile-displayphoto-scale_400_400/B4DZgsMb6oHAAo-/0/1753088115012?e=1779926400&v=beta&t=w3aVcF5sP_uhdkEfuh19lHZAQsdh_l9lbAVYeEv_T-g" width="150" alt="Michele Beltrame">](https://www.linkedin.com/in/michele-beltrame-625066292/) | [<img src="https://media.licdn.com/dms/image/v2/D4D03AQGSKbzTZxu03w/profile-displayphoto-shrink_400_400/B4DZawUUUSHEAg-/0/1746714839226?e=1779926400&v=beta&t=BjRLeosU1VXAAXpdZqepdmbjsZlY6eawimhXF67biro" width="150" alt="Claudia Rocas Corrons">](https://www.linkedin.com/in/claudia-rocas-corrons-370a1a364/) | [<img src="https://media.licdn.com/dms/image/v2/D4D03AQHwEAaALgjDDQ/profile-displayphoto-shrink_400_400/profile-displayphoto-shrink_400_400/0/1704570136616?e=1779926400&v=beta&t=cLzKOwYIERXH29gTiTXDtI7grnZSyS9f6dAFF9n7qoc" width="150" alt="Davide Tonini">](https://www.linkedin.com/in/davide-tonini/) | [<img src="https://media.licdn.com/dms/image/v2/D4E03AQEsETpmyIYrFg/profile-displayphoto-shrink_400_400/B4EZOh4_HiGQAk-/0/1733587891269?e=1779926400&v=beta&t=BtjJqL-vj3KWDXzLqUoTnmUmXQ1K1y50CjaV05NNkHk" width="150" alt="Leonardo Zamprotta">](https://www.linkedin.com/in/leonardo-zamprotta/) |
|:---:|:---:|:---:|:---:|:---:|
| [Marco Battiston](https://www.linkedin.com/in/marcobattiston/) | [Michele Beltrame](https://www.linkedin.com/in/michele-beltrame-625066292/) | [Claudia Rocas Corrons](https://www.linkedin.com/in/claudia-rocas-corrons-370a1a364/) | [Davide Tonini](https://www.linkedin.com/in/davide-tonini/) | [Leonardo Zamprotta](https://www.linkedin.com/in/leonardo-zamprotta/) |

## Results

The 2026 edition saw:
- Number of competing players: 30,703
- Number of competing teams: 18,803
- Number of universities represented: 1,549 universities
- Number of countries represented: 117 countries

Our placement among all teams: 

| Phase | Round | Algorithmic | Manual | XIRECs | Global rank |
|-------|-------|-------------|--------|--------|-------------|
| Phase 1 | Round 1 | 98,319 (921st) | 87,995 (1st) | 186,314 | **703 (top 3.5%)** |
| Phase 1 | Round 2 | 99,931 (186th) | 183,999 (139th) | 470,244 | **569 (top 3.0%)** |
| Phase 2 | Round 3 | 29,929 (1019th) | 68,640 (510th) | 98,569 | **1102 (top 6.0%)** |
| Phase 2 | Round 4 |  103,735  (460th) | 3,223 (885th) | 205,527 | **715 (top 4.0%)** | 
| Phase 2 | Round 5 |  33,091 (542nd) | -32,909 (1936th) | 205,709 | **1077 (top 6.0%)** |

Phase 1 (Round 1 & 2):
- (Globally) Ranked **569th** overall.
- Gained access to phase 2 by accumulating more than 200,000 XIRECs in the first two rounds.

Phase 2  (Round 3, 4 & 5):
- (Globally) Ranked **494th** for Algorithmic trading, **2496th** for Manual trading and **1077th** overall.

## Our Journey & Spirit
As first-year Computational Finance students at the University of Padua, we approached IMC Prosperity 4 primarily as a learning opportunity.
Being at the beginning of our academic path, many of the tools and methodologies required by the challenge were new to us; we chose to dive in anyway to test our skills and bridge the gap between theory and practice.

The second half of the competition coincided with a demanding period of university exams and projects. While this required us to prioritize our academic commitments during Phase 2, we remained dedicated to completing the challenges, valuing the hands-on experience and the steep learning curve over our final global ranking.

---

## Table of Contents

- [Competition structure](#competition-structure)
- [Repository structure](#repository-structure)
- [Algorithmic Trading](#algorithmic-trading)
  - [Round Tutorial - Market-Making Fundamentals](#algo-round-tutorial)
  - [Round 1 - Stationary MM + Trend Following](#algo-round-1)
  - [Round 2 - Stationary MM + Trend Following (Additional Volume)](#algo-round-2)
  - [Round 3 - Options Pricing](#algo-round-3)
  - [Round 4 - Informed Traders](#algo-round-4)
  - [Round 5 - Pairs Trading, Zero-Sum Baskets, Correlations](#algo-round-5)
- [Manual Challenges](#manual-challenges)
  - [Round 1 — Exchange Auction](#manual-round-1)
  - [Round 2 — Capital Allocation](#manual-round-2)
  - [Round 3 — Invest & Expand](#manual-round-3)
  - [Round 4 — Exotic Derivatives](#manual-round-4)
  - [Round 5 — News-Based Trading](#manual-round-5)
- [Reproducibility](#reproducibility)

---

## <a id="competition-structure"></a>[Competition structure](#competition-structure)

Five rounds of ~2 days each. Every round introduces new tradeable products and increases market complexity. 

Algorithmic challenges:

| Round | Products | Core theme |
|-------|----------|------------|
| Tutorial | `EMERALDS`, `TOMATOES` | MM fundamentals |
| Round 1 | `ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT` | Stationary MM + Trend Following |
| Round 2 | `ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT` | Stationary MM + Trend Following (Additional Volume) |
| Round 3 | `VELVETFRUIT_EXTRACT`, `HYDROGEL_PACK` | Options Pricing |
| Round 4 | `VELVETFRUIT_EXTRACT`, `HYDROGEL_PACK` | Informed Traders |
| Round 5 | `50` assets divided in `10` categories | Pairs Trading, Zero-Sum Baskets, Correlations |

Manual challenges:

| Round | Products | Core theme |
|-------|----------|------------|
| Round 1 | `DRYLAND FLAX`, `EMBER MUSHROOM` | Auction |
| Round 2 | `SCALE`, `RESEARCH` & `SPEED` | Investment, Optimization, Game Theory |
| Round 3 | `ORNAMENTAL BIO-POD` | Auction, Game Theory |
| Round 4 | 12 `AETHER CRYSTAL` Options | Exotic Options, Optimization & Delta Hedging |
| Round 5 | 9 Tradable Goods on `IGNITH MARKET` | News Trading |


---

## <a id="repository-structure"></a>[Repository structure](#repository-structure)

```
imc-prosperity-4/
│
├── prosperity4/
│   ├── round_/
│   │   ├── data/               # contains challenge data
│   │   ├── manual/             # contains manual trading analysis (notebooks)
│   │   ├── notebooks/          # contains algo trading analysis (notebooks)
│   │   └── Trader.py           # contains algorithmic trading strategies
├── .gitignore
├── .python-version
├── uv.lock
├── pyproject.toml
└── README.md
```

---

## <a id="algorithmic-trading"></a>[Algorithmic trading](#algorithmic-trading)


### <a id="algo-round-tutorial"></a>[Round Tutorial - Market-Making Fundamentals](#algo-round-tutorial)

The tutorial served as a soft introduction to IMC Prosperity 4's custom trading engine. It required trading two basic assets: `EMERALDS` (a stationary asset with a fixed true value) and `TOMATOES` (an asset with slight price drift). Our solution implemented basic market-making: providing liquidity around the mid-price to capture the spread, while utilizing inventory management to avoid breaching the position limits.

### <a id="algo-round-1"></a>[Round 1 - Stationary MM + Trend Following](#algo-round-1)

The first official round introduced `ASH_COATED_OSMIUM` and `INTARIAN_PEPPER_ROOT`, testing both mean-reversion and trend-following capabilities. 
*   **INTARIAN_PEPPER_ROOT:** Data analysis revealed a perfect linear trend (R²=0.9999) with fast mean-reverting residuals. Our solution split the position limit: we dedicated a "Trend Leg" (48 units) to buy immediately and hold as a permanent long, and an "MM Leg" (32 units) to market-make around a rolling fair value computed from the linear regression intercept and slope. We dynamically skewed our quotes based on inventory to remain neutral.
*   **ASH_COATED_OSMIUM:** We used a Kalman Filter to track the fair value (FV) and smooth out market noise. We combined this with a 100-period Simple Moving Average (SMA) Z-Score. When the Z-Score was within normal bounds, we provided liquidity. When prices stretched beyond a Z-Score of ±2, we aggressively accumulated inventory in anticipation of mean reversion, sniping mispriced liquidity in the order book.

PnL curve:

<img src="prosperity4/docs/round-1-algo-results.png" width="900">

### <a id="algo-round-2"></a>[Round 2 - Stationary MM + Trend Following (Additional Volume)](#algo-round-2)

Round 2 featured the exact same assets as Round 1, but with significantly increased market volume and depth. Due to our strong performance in Round 1 and the manual challenge, we realized we were only ~10K XIRECs short of the advancement threshold. As a tactical decision to secure our spot in Phase 2 without taking unnecessary risks, we submitted an empty algorithmic trader (taking 0 risk) and relied entirely on a guaranteed minimax strategy in the manual challenge to bank a safe profit.

PnL curve:

<img src="prosperity4/docs/round-2-algo-results.png" width="900">

### <a id="algo-round-3"></a>[Round 3 - Options Pricing](#algo-round-3)

This round introduced `HYDROGEL_PACK` and options on `VELVETFRUIT_EXTRACT`, shifting the focus to derivatives pricing and volatility modelling.
*   **HYDROGEL_PACK:** We implemented a regime-based market maker. By tracking the Fair Value (FV) using volume imbalances, we categorized the market into Normal, Soft, and Aggressive regimes. In normal conditions, we provided liquidity; in aggressive regimes, we crossed the spread to quickly dump or accumulate inventory based on hard thresholds.
*   **VELVETFRUIT_EXTRACT (Options):** We built a full Volatility Smile and Black-Scholes pricing engine. The algorithm backed out Implied Volatilities (IV) using a Newton-Raphson solver for all options with two-sided markets. It then fit a degree-2 parabola (polyfit) on the log-moneyness vs. IV curve to create a smooth volatility surface. Using this fitted volatility, we generated theoretical prices for all option contracts, systematically selling into bids above our fair value and buying into asks below it.

PnL curve:

<img src="prosperity4/docs/round-3-algo-results.png" width="900">

### <a id="algo-round-4"></a>[Round 4 - Informed Traders](#algo-round-4)

Round 4 retained the assets from Round 3 but introduced "Informed Traders"—hidden market participants with superior knowledge who distorted prices. To combat this adverse selection, our solution completely abandoned pure Black-Scholes theoretical pricing in favor of statistical arbitrage and mean-reversion. For `VELVETFRUIT_EXTRACT` and its ATM options, we implemented a rolling Z-score mean reversion model (300-tick lookback). Instead of providing passive liquidity and getting run over by informed flow, we aggressively accumulated long or short positions when the price stretched beyond a Z-score threshold of 3.0, anticipating a fast reversion to the moving average once the informed flow subsided. 

PnL curve:

<img src="prosperity4/docs/round-4-algo-results.png" width="900">

### <a id="algo-round-5"></a>[Round 5 - Pairs Trading, Zero-Sum Baskets, Correlations](#algo-round-5)

The final algorithmic round was a massive scale-up, featuring 50 distinct assets divided into 10 categories (e.g., Sounds Recorders, Sleeping Pods, Organic Microchips). The challenge conceptually tested pairs trading, zero-sum baskets, and correlation modeling across the diverse asset classes. Given the complexity and our existing ranking, our final submission (`ROUND5_Final.py`) deployed a broad, naive market-maker (`AllTrader`) across all 50 assets simultaneously. It computed a simple fair value for every asset based on bid/ask volume imbalances and continuously quoted 1 tick inside the spread to collect passive spread capture across the entire market ecosystem.

PnL curve:

<img src="prosperity4/docs/round-5-algo-results.png" width="900">

## <a id="manual-challenges"></a>[Manual Challenges](#manual-challenges)


### <a id="manual-round-1"></a>[Round 1: Exchange Auction](#manual-round-1)

Round 1 presented two opening auctions  **Dryland Flax** and **Ember Mushrooms** where we had to submit a single limit order (price, quantity) for each product to maximise profit, knowing that any inventory acquired would be immediately bought back by the Merchant Guild at a fixed price.

The key insight was that profit per unit depended entirely on the spread between the auction clearing price and the guaranteed buyback price, net of any fees. This meant we needed to:

1. **Identify the clearing price**  the price that maximises total traded volume under the auction rules
2. **Bid aggressively enough** to ensure execution, without pushing the clearing price above the buyback price
3. **Size our order** to absorb as much profitable volume as possible, accounting for our last-in-line priority at any price level we joined

We built a simulator (`analysis.ipynb`) to sweep candidate clearing prices across the full order book for both products, computing executed volume and our resulting PnL at each level.

**Dryland Flax**: Bid 9999 units @31, clearing price @29, buyback @30, no fees:

<img src="prosperity4/docs/round-1-manual-orderbook-dryland.png" width="900">

**Ember Mushrooms**: Bid 19999 units @18, clearing price @16, buyback @20, fee of 0.10/unit:

<img src="prosperity4/docs/round-1-manual-orderbook-ember.png" width="900">


This analysis yielded the **optimal manual submission**, securing **1st place in the manual rankings** for this round.

Manual results:

<img src="prosperity4/docs/round-1-manual-results.png" width="900">

### <a id="manual-round-2"></a>[Round 2: Capital Allocation](#manual-round-2)

In Round 2, we were given a capital allocation challenge where we had to distribute a budget of 50,000 XIRECs across three interdependent pillars **Research**, **Scale**, and **Speed** to maximise a nonlinear PnL function:

$$
\text{PnL} = \text{Research}(x_r) \times \text{Scale}(x_s) \times \text{Speed}(x_{sp}) - \text{Budget\_Used}
$$

$$
\begin{aligned}
\text{Research}(x_r) &= 200{,}000 \cdot \frac{\ln(1 + x_r)}{\ln(101)} \\[6pt]
\text{Scale}(x_s) &= \frac{7}{100} \cdot x_s \\[6pt]
\text{Speed}(x_{sp}) &= 0.9 - 0.8 \cdot \frac{\text{Rank}(x_{sp}) - 1}{R_{\text{max}} - 1}
\end{aligned}
$$

The core difficulty was that each pillar followed a different return structure: Research scaled logarithmically, Scale linearly, and Speed was rank-determined relative to all competing teams, making it the most uncertain and strategically sensitive variable.

Our approach was to tackle the problem in two stages. We first focused on **Speed**, since its multiplier depended entirely on the behaviour of other teams rather than a fixed formula. We analysed the rank-based scoring mechanism and reasoned about likely competitor distributions to arrive at a Speed allocation we were confident would secure a strong relative rank. With that anchor fixed, we then ran a **numerical optimisation** (via `optimizer.html` and `analysis.ipynb`) over the remaining budget to find the Research/Scale split that maximised the product of the two analytically-defined pillars given the leftover capital.

We invested the full budget, landing on a final allocation of **34% Speed, 50% Scale, and 16% Research**, a distribution that prioritised broad market deployment and competitive rank while accepting a modest edge, reflecting the classic market-maker trade-off between reach, speed, and depth of insight.

Manual results:

<img src="prosperity4/docs/round-2-manual-results.png" width="900">

### <a id="manual-round-3"></a>[Round 3  Invest & Expand](#manual-round-3)

Round 3 required submitting two bids against counterparties with uniformly distributed reserve prices between 670 and 920 (in increments of 5), with any acquired inventory sellable the next day at the fair price of 920.

The profit per unit on any trade was simply `920 − bid`, so the lower we bid, the higher the margin, but the fewer counterparties we would trade with. The real strategic tension lived in the **second bid**, which introduced a rank-based penalty: if our second bid fell below the mean second bid of all players, our PnL on those trades was penalised by a steep cubic factor, making an aggressive-but-below-average second bid potentially worse than not trading at all.

The penalization factor was defined as follows:
$$ \left(\frac{920 - \text{avg\_b2}}{920 - b2}\right)^3 $$

**A note on bid precision:** since all reserve prices are multiples of 5, any bid ending in 1 or 6 is functionally equivalent to the nearest lower multiple of 5, a counterparty with reserve price 795 accepts a bid of 796, same as a bid of 799. We therefore deliberately chose values ending in **6** (e.g. 796, 906) to sit just above a clean multiple of 5, capturing every counterparty at that threshold without leaving margin on the table.

**First bid 796:** This was intentionally conservative, targeting only counterparties with reserve prices at or below 795 (roughly the lower 26% of the distribution). The margin per unit was a comfortable 124. We were not trying to maximise volume here. The first bid carries no competitive penalty, so we prioritised a reliable, high-margin trade over breadth.

**Second bid 906:** This is where the design of the challenge demanded the most careful reasoning. The cubic penalty for finishing below the mean second bid is severe enough that a slightly-below-average bid can actively destroy value. Our thinking was: if most teams reasoned similarly and clustered their second bids in the 880–910 range out of caution, submitting 906 would likely land at or above the mean, avoiding the penalty entirely while still capturing a thin but positive margin of 14/unit across a large share of the distribution. We accepted that this might be overly conservative, a team willing to bid 850 and trust the field would gain significantly more margin, but the asymmetric downside of the penalty made us reluctant to anchor below what we estimated the crowd would do.

In hindsight, our allocation was **risk-averse by design**: we prioritised penalty avoidance and margin certainty over volume maximisation, reflecting our belief that in a competitive setting with an opaque penalty structure, staying above the crowd's average was worth more than chasing extra units at lower prices.

Manual results:

<img src="prosperity4/docs/round-3-manual-results.png" width="900">

### <a id="manual-round-4"></a>[Round 4: Exotic Derivatives](#manual-round-4)

Round 4 introduced a rich derivatives universe written on `AETHER_CRYSTAL` vanilla calls and puts at 2 and 3 week expiries, alongside three exotic structures (a Chooser, a Binary Put, and a Knock-Out Put) with the objective of constructing a position that maximised expected PnL across 100 simulations of the underlying, held to expiry.

The most immediate signal was the underlying's annualised volatility of **251%**, an extremely high figure that made any unhedged directional exposure dangerous. A naked long or short in the underlying, or an unbalanced options book, could easily see simulated paths swing wildly enough to overwhelm any edge extracted from mispricing. Our primary concern was therefore not just finding positive expected value, but ensuring that delta exposure, our first-order sensitivity to the underlying's moves, was kept tightly controlled.

**Modelling the exotics:** We built a dedicated simulation framework in `analysis.ipynb`, implementing Python classes for each product with their precise payoff logic. This was essential for the path-dependent products in particular:
- The **Knock-Out Put** required tracking whether the barrier was breached at any discrete step before expiry
- The **Chooser Option** required simulating the underlying at the 2-week mark to determine which flavour (call or put) the holder would rationally select, then continuing to expiry
- The **Binary Put** had a simple terminal payoff but its delta profile is highly nonlinear near the strike, requiring careful treatment

**Portfolio construction as an integer program:** We formulated the position-sizing problem as an **integer program**: maximise total expected PnL across simulations subject to the constraint that the net portfolio delta remained within a tight neutrality tolerance. Integer constraints were necessary because contract quantities had to be whole numbers bounded by the displayed volume limits. This allowed us to search over the full feasible combination space while respecting both the delta-hedge requirement and the position size caps.

Manual results:

<img src="prosperity4/docs/round-4-manual-results.png" width="900">

Distribution by Derivative:

<table>
  <tr>
    <td><img src="prosperity4/docs/round-4-manual-results-ac.png" width="100%" height="400" style="object-fit: cover;"><br>AC</td>
    <td><img src="prosperity4/docs/round-4-manual-results-ac35p.png" width="100%" height="400" style="object-fit: cover;"><br>AC 35P</td>
    <td><img src="prosperity4/docs/round-4-manual-results-ac40bp.png" width="100%" height="400" style="object-fit: cover;"><br>AC 40BP</td>
  </tr>
  <tr>
    <td><img src="prosperity4/docs/round-4-manual-results-ac40p.png" width="100%" height="400" style="object-fit: cover;"><br>AC 40P</td>
    <td><img src="prosperity4/docs/round-4-manual-results-ac45ko.png" width="100%" height="400" style="object-fit: cover;"><br>AC 45KO</td>
    <td><img src="prosperity4/docs/round-4-manual-results-ac45p.png" width="100%" height="400" style="object-fit: cover;"><br>AC 45P</td>
  </tr>
  <tr>
    <td><img src="prosperity4/docs/round-4-manual-results-ac50c.png" width="100%" height="400" style="object-fit: cover;"><br>AC 50C</td>
    <td><img src="prosperity4/docs/round-4-manual-results-ac50c2.png" width="100%" height="400" style="object-fit: cover;"><br>AC 50C2</td>
    <td><img src="prosperity4/docs/round-4-manual-results-ac50co.png" width="100%" height="400" style="object-fit: cover;"><br>AC 50CO</td>
  </tr>
  <tr>
    <td><img src="prosperity4/docs/round-4-manual-results-ac50p.png" width="100%" height="400" style="object-fit: cover;"><br>AC 50P</td>
    <td><img src="prosperity4/docs/round-4-manual-results-ac50p2.png" width="100%" height="400" style="object-fit: cover;"><br>AC 50P2</td>
    <td><img src="prosperity4/docs/round-4-manual-results-ac60c.png" width="100%" height="400" style="object-fit: cover;"><br>AC 60C</td>
  </tr>
</table>

### <a id="manual-round-5"></a>[Round 5: News-Based Trading](#manual-round-5)

Round 5 provided a fictional newspaper: **Ashflow Alpha** and required us to construct a one-day portfolio based on qualitative news interpretation, with a quadratic fee structure that penalised heavy concentration in any single instrument.

Our approach was to read each article and classify the signal as bullish, bearish, or ambiguous, then size positions proportionally to our conviction while keeping an eye on the fee drag that would erode returns on large allocations.

---

**Position-by-position rationale:**

**Magma Ink, BUY 35%:** The largest allocation, driven by the front-page story about the merger between Stip Stationery Enterprises and Splatter Inc. and the launch of the limited-edition Lava Fountain Pen. The crowd queuing for six hours and the "hot drop" framing read as a strong demand signal for Magma Ink as the ink supplier. In hindsight, this was our most costly mistake: the news was likely **already priced in** given how widely the event had been promoted beforehand, and the 35% allocation triggered a fee of 122,500; making the position nearly impossible to profit from even with a positive underlying return. We over-weighted a sentiment story that the market had already absorbed.

**Thermalite Core, BUY 19%:** The quarterly forecast report showed projected active users nearly doubling next quarter (1.42M to 3.09M) with significantly extended daily usage times, a strong forward-looking demand signal. The position returned modestly (+6,004), likely because the optimistic forecast was partially anticipated by the market already.

**Lava Cake, SELL 14%:** Health authorities confirming traces of actual lava in Lava Cakes, an immediate sales halt, civil lawsuits, and vendors returning stock all pointed clearly to a sharp negative move. This was our strongest and cleanest signal, unambiguously bad news with direct commercial impact and it paid off as our most profitable trade (+69,095).

**Pyroflex Cells, SELL 10%:** The abrupt end to the Pyroflex Cell Tax Cut, effectively doubling the levy overnight, was a clear demand headwind. Higher consumer prices would suppress upgrade cycles and slow new purchases. We shorted this and captured a positive return (+9,534), though in hindsight we could have sized this more aggressively given the clarity of the signal.

**Sulfur Reactor, BUY 7%:** Index inclusion is a textbook mechanical buy signal, funds tracking Elemental Index 118 would be forced to purchase Sulfur Reactor upon rebalance. We sized this conservatively given the uncertainty around timing, and it returned a small positive (+7,297).

**Volcanic Incense, BUY 5%:** This was a misjudgement. Whiff Nostralico openly calling his followers to buy Volcanic Incense reads more as a manipulation red flag than a genuine fundamental signal, the buying was concentrated in narrow windows around his appearances, a classic pump pattern. We should have either shorted this or avoided it entirely. Instead we went long and lost (-9,786).

**Scoria Paste, BUY 3%:** Lava D. Ray's call to stockpile Scoria Paste was a weak, influencer-driven signal from a self-proclaimed "market medium" with no credible fundamental backing. We sized it minimally out of caution, and the near-zero result (-500) confirmed there was little real signal here.

**Obsidian Cutlery, no position:** The manufacturing halt story was genuinely negative, but the signal was muddied, the contamination was self-inflicted and the company declined to comment, making the magnitude of impact hard to gauge. We opted out, which in hindsight may have been a missed short opportunity.

---

**What went wrong:**

The overall loss of -32,909 was driven almost entirely by the **Magma Ink** position. The core error was conflating *exciting news* with *new information*, the Lava Fountain Pen launch had been widely promoted beforehand, meaning the demand enthusiasm for Magma Ink was already reflected in prices by the time we traded. Combined with the quadratic fee structure, a 35% allocation to a story that was largely priced in was very costly. A more disciplined approach would have capped single-position sizes to control fee drag, reserved the largest allocations for the clearest and most *unexpected* signals (Lava Cake and Pyroflex Cells), and treated heavily promoted consumer events with more scepticism.

Manual results:

<img src="prosperity4/docs/round-5-manual-results.png" width="900">

## <a id="reproducibility"></a>[Reproducibility](#reproducibility)

We used **uv** to manage Python and all dependencies.
 
---
 
### 1. Install uv
 
**Windows** — open PowerShell and run:
 
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
 
**macOS** — open Terminal and run:
 
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
 
Close and reopen your terminal after it finishes. Verify it worked:
 
```bash
uv --version
```
 
You should see something like `uv 0.x.x`. If the command isn't found, restart your terminal and rerun it.
 
---
 
### 2. Clone the repo
 
```bash
git clone https://github.com/marcobattiston21/imc-prosperity-4.git
cd imc-prosperity-4
```
 
---
 
### 3. Create the environment and install dependencies
 
Because we already have a `pyproject.toml` and `uv.lock`, this is a single command. uv will automatically download the right Python version and install every dependency at the exact pinned versions:
 
```bash
uv sync
```
 
That's it. uv creates a `.venv` folder in the project root — you don't need to activate it for most things (uv handles it transparently), but if you need to activate it manually:
 
**Windows:**
```powershell
.venv\Scripts\activate
```
 
**macOS:**
```bash
source .venv/bin/activate
```
 