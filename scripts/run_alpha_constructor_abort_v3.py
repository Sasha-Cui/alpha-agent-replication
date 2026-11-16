#!/usr/bin/env python3
from pathlib import Path
import sys,argparse
sys.path.insert(0,str(Path(__file__).resolve().parent))
from alpha_constructor_abort_v3 import diagnose,finalize,replay
p=argparse.ArgumentParser();p.add_argument('mode',choices=['diagnose','finalize','replay']);p.add_argument('--trial',type=int,choices=[14,15],required=True);a=p.parse_args()
{'diagnose':diagnose,'finalize':finalize,'replay':replay}[a.mode](a.trial)
