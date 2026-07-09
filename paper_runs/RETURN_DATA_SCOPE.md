# Return Data Scope Policy

Current user constraint: all candidate and benchmark returns must be constructed only from read-only inputs under:

- `${ALPHA_EVOLVE_JKP_ROOT}`
- `${ALPHA_EVOLVE_RETURN_DATA_ROOT}`

Those two folders are read-only inputs. Generated scripts and artifacts should stay under the active alpha-agent replication checkout.

Earlier diagnostics that used paper-shipped return streams or official French factors remain on disk for auditability but are legacy/non-counting under this scope.

Runtime guardrail: legacy scripts that read paper-shipped returns, official Kenneth French factors, or the older external-factor-data `performance_analysis` panel now refuse to run unless `ALLOW_LEGACY_NON_JKP_RETURNS=1` is set. That opt-in is only for explicit non-counting audit reproduction; valid experiments should use `scripts/build_jkp_long_short_returns.py`, `scripts/run_quantevolver_jkp_seed_proxies.py`, and `scripts/evaluate_candidate_returns_jkp.py`.
