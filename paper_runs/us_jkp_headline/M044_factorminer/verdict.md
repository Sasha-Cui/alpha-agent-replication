# M044: FactorMiner Top-40 IC-weighted library on monthly U.S./JKP data

Status: **completed central partial adaptation**, not a reproduction of the FactorMiner agent or native 10-minute study.

The current v2 paper releases 110 formulas and makes the frozen Top-40 IC-weighted ensemble its strongest simple headline strategy. All 110 v2 strings are byte-lineage checked against the tracked formula ledger and evaluated before selection. The first 12 formation months determine absolute-IC ranking, signs, and normalized IC weights; those choices remain fixed for the following 293 months. No factor was selected on its later return.

At the common 10 bp one-way cost, the 305-month path has CAGR -3.84%, annualized Sharpe -0.278, and maximum drawdown -67.40%. The 185-month JKP133 residual mean is -2.36% annually (HAC t=-0.914, p=0.3606; descriptive 69-test bound=1.0000).

The paper releases no author-native runtime, selection IDs, weights, signals, or portfolio. Exact printed formulas therefore use the pinned independent interpreter's declared NumPy semantics, including the ambiguous Factor 001 `Min/Max(...,48)` parse. JKP fields, monthly periods, first-year selection, and common value-weighted deciles are disclosed adaptations. This does not reproduce the Gemini/memory mining process, 10-minute data, paper IC/ICIR, or a paper trading return.

Selected factor IDs: 029, 016, 012, 109, 030, 054, 011, 026, 102, 027, 071, 039, 097, 007, 045, 049, 053, 078, 041, 079, 062, 014, 070, 019, 024, 081, 061, 092, 002, 099, 021, 051, 090, 009, 031, 025, 085, 008, 100, 093.
