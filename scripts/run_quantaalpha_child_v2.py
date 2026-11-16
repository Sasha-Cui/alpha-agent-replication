#!/usr/bin/env python3
"""Invoke the installed native Qlib CLI without unrelated Git metadata collection."""

import sys
import importlib.metadata
from qlib.workflow.recorder import MLflowRecorder

if hasattr(MLflowRecorder, "_log_uncommitted_code"):
    MLflowRecorder._log_uncommitted_code = lambda *args, **kwargs: None
entry = next(e for e in importlib.metadata.distribution("pyqlib").entry_points if e.name == "qrun")
sys.argv = ["qrun", *sys.argv[1:]]
entry.load()()
