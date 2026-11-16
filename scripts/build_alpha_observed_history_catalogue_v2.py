#!/usr/bin/env python3
"""Freeze all20 verified observed source outcomes; never admit a completed subset."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from alpha_evolve.openrouter_budget import atomic_json
from alpha_observed_history_evidence_v2 import complete_catalogue

def main():
    out=ROOT/'artifacts/fidelity_completion_v2/alpha_observed_history_catalogue'
    if out.exists():raise ValueError('Preserve the existing catalogue attempt')
    catalogue=complete_catalogue(ROOT)
    out.mkdir()
    atomic_json(out/'manifest.json',catalogue)
    print('ALL20_OBSERVED_SOURCE_CATALOGUE_READY_NOT_AN_ECONOMIC_RESULT')
if __name__=='__main__':main()
