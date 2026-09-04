# M069: automated strategy finding PriceMomentum on monthly U.S./JKP data

Status: **completed partial monthly U.S./JKP evaluation**, not the integrated automated strategy.

The first Table 3 selected alpha, `PriceMomentum = CLOSE - DELAY(CLOSE, 14)`, is evaluated with its literal price-difference formula and positive author-workbook IC direction. One source day becomes one month, and the common U.S. top-1,000 value-weighted deciles replace the unreleased 12-alpha DNN and top-13/drop-5 portfolio. Prior outcomes were seen, so inference is exploratory.

At 10 bp one-way costs, the 305-month path has CAGR 3.20%, annualized Sharpe 0.256, and maximum drawdown -39.11%. Mean monthly traded notional is 1.033; minimum signal coverage is 834 stocks.

Across the 185-month rolling attribution window, the JKP133 residual mean is 2.11% annually (HAC t=0.924, p=0.3557, 95% interval [-2.37%, 6.60%]; descriptive 69-test bound=1.0000).

This result applies only to one materially cadence-adapted selected factor. It does not reproduce GPT-4o comparison, the complete SAF, learned weights, DNN prediction, top-13/drop-5 execution, or the paper's integrated return.
