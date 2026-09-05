# M039: FinPos in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not a native GPT-4o FinPos replication.

The reconstruction preserves shallow news, middle technical, and deep fundamental memory; a separate Direction Agent; a Quantity/Risk Agent; continuous carried positions; delayed multi-timescale reflection; and 95% lower-tail CVaR exposure caps. Every month the Direction Agent reliability-weights memory layers using only 60 reward months ending six months earlier. The Quantity/Risk Agent moves each carried stock position by at most 0.25 times confidence and clips it to a risk-budget/CVaR cap. Aggregate directions were {'buy': 102341, 'hold': 101305, 'sell': 101354}; mean absolute carried position was 0.275 and mean trade quantity was 0.023. Missing prompts, integer-share conversion, and native account history are not recreated.

At 10 bp one-way costs, the 305-month path has CAGR -0.33%, annualized Sharpe 0.025, and maximum drawdown -52.26%. Mean monthly traded notional is 0.392, and minimum signal coverage is 1000 stocks.

Across the 185-month rolling JKP attribution window, residual mean return is -1.16% annually (HAC t=-0.653, p=0.5135, 95% interval [-4.62%, 2.31%]).

This result answers how one transparent FinPos-inspired stateful dual-agent policy transfers to the common monthly U.S. universe. It does not reproduce the paper's GPT-4o decisions, integer quantities, daily account ledger, five-stock experiment, or native claims.
