# Collaborator Result Index

`strategy_result_index.csv` is the compact starting dataframe for a new
collaborator. It has one row per retained strategy mapping: 50 strategies from
40 papers.

The table combines:

- paper identity and candidate formula;
- mapping fidelity and implementation basis;
- source support, omissions, favorable choices, and negative-evidence boundary;
- CAPM, FF3, FF5+momentum, and broad JKP132 alpha diagnostics;
- strongest surviving benchmark flags and alpha attenuation; and
- the closest derived JKP factor diagnostic.

It does not contain monthly returns, security-level observations, the factor
panel, or third-party repository contents. The 50 rows partition into one
released-code component adaptation, 12 source-grounded paper components, and
37 in-spirit reconstructions. There are zero native-agent replications.

Regenerate it from tracked aggregate inputs:

```bash
python scripts/build_collaborator_handoff.py
```

`manifest.json` records scope, exclusions, input hashes, output dimensions,
and the output hash. The builder fails if the 50-strategy/40-paper denominator,
the 1/12/37 provenance partition, required fields, or one-to-one joins change.
