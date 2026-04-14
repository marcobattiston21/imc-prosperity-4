import numpy as np
import pandas as pd 



def compute_returns(price: pd.Series) -> pd.DataFrame :
    p = price.astype(float).dropna()
    out = pd.DataFrame(index=p.index)
    out["R_t"] = p.pct_change()       # simple return 
    out["r_t"] = np.log(p).diff()     # log returns
    out["p_t"] =np.log(p)
    return out.dropna()


