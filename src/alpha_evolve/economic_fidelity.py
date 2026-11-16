"""Source-guided EFS v1 numerical factors and causal daily accounting.

This module does not claim to recover the author's unreleased implementation.
All choices beyond the published mechanism belong in the frozen run recipe.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
import re
import signal
from types import SimpleNamespace

import numpy as np
import pandas as pd


class InvalidFactor(ValueError):
    pass


SAFE_NUMPY = {
    'array', 'asarray', 'abs', 'mean', 'std', 'sum', 'min', 'max', 'median',
    'nanmean', 'nanstd', 'nansum', 'nanmin', 'nanmax', 'nanmedian',
    'log', 'log1p', 'exp', 'sqrt', 'sign', 'tanh', 'clip', 'diff', 'where',
    'maximum', 'minimum', 'isfinite', 'isnan', 'isinf', 'all', 'any',
    'percentile', 'nanpercentile', 'quantile', 'power', 'cumsum', 'cumprod',
    'dot', 'average', 'argmax', 'argmin', 'nan_to_num', 'arange',
}
SAFE_METHODS = {'mean', 'std', 'sum', 'min', 'max', 'copy', 'astype'}
SAFE_BUILTINS = {'len': len, 'float': float, 'int': int, 'abs': abs,
                 'min': min, 'max': max}
ALLOWED_NODES = {
    ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Return, ast.Assign,
    ast.AugAssign, ast.If, ast.Expr, ast.Constant, ast.Name, ast.Load, ast.Store,
    ast.Call, ast.Attribute, ast.keyword, ast.BinOp, ast.UnaryOp, ast.BoolOp,
    ast.Compare, ast.IfExp, ast.Subscript, ast.Slice, ast.Tuple, ast.List,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    ast.USub, ast.UAdd, ast.Not, ast.And, ast.Or, ast.Eq, ast.NotEq, ast.Lt,
    ast.LtE, ast.Gt, ast.GtE, ast.BitAnd, ast.BitOr, ast.Invert,
}


def bounded_arange(*args, **kwargs):
    if any(not np.isfinite(x) or abs(x) > 1000 for x in args):
        raise InvalidFactor('arange exceeds bounded price window')
    out = np.arange(*args, **kwargs)
    if out.size > 1000:
        raise InvalidFactor('arange allocation too large')
    return out


def compile_factor(code: str):
    if len(code) > 8000:
        raise InvalidFactor('factor too long')
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise InvalidFactor('syntax error') from exc
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        raise InvalidFactor('exactly one function is required')
    func = tree.body[0]
    if func.decorator_list or func.returns or func.type_comment:
        raise InvalidFactor('decorators and annotations are not allowed')
    if [arg.arg for arg in func.args.args] != ['prices', 'window'] or func.args.vararg or func.args.kwarg or func.args.kwonlyargs or func.args.posonlyargs:
        raise InvalidFactor('signature must be (prices, window=...)')
    if any(arg.annotation for arg in func.args.args):
        raise InvalidFactor('argument annotations are not allowed')
    if len(func.args.defaults) > 1 or any(not isinstance(x, ast.Constant) or not isinstance(x.value, (int, float)) for x in func.args.defaults):
        raise InvalidFactor('only a numeric window default is allowed')
    match = re.fullmatch(r'([a-z][a-z0-9_]*?)_(3|7|14|21|1)(?:_v([1-9][0-9]*))?', func.name)
    if not match:
        raise InvalidFactor('source-style factor name/window required')
    nodes = list(ast.walk(tree))
    if len(nodes) > 500:
        raise InvalidFactor('factor AST too large')
    for node in nodes:
        if type(node) not in ALLOWED_NODES:
            raise InvalidFactor('disallowed syntax: ' + type(node).__name__)
        if isinstance(node, ast.Name) and (node.id.startswith('_') or node.id in {'eval', 'exec', 'open', 'globals', 'locals', 'getattr', 'setattr', 'compile'}):
            raise InvalidFactor('disallowed name')
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and abs(node.value) > 10000:
            raise InvalidFactor('numeric constant too large')
        if isinstance(node, ast.Attribute):
            if node.attr.startswith('_'):
                raise InvalidFactor('private attributes are forbidden')
            if isinstance(node.value, ast.Name) and node.value.id == 'np':
                if node.attr not in SAFE_NUMPY | {'nan', 'inf', 'float64'}:
                    raise InvalidFactor('numpy function not allowed: ' + node.attr)
            elif isinstance(node.value, ast.Attribute) and isinstance(node.value.value, ast.Name) and node.value.value.id == 'np' and node.value.attr == 'maximum' and node.attr == 'accumulate':
                pass
            elif node.attr not in SAFE_METHODS:
                raise InvalidFactor('array attribute not allowed: ' + node.attr)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id not in SAFE_BUILTINS:
            raise InvalidFactor('call not allowed: ' + node.func.id)
        if isinstance(node, ast.Assign):
            if any(not isinstance(target, ast.Name) or target.id in {'np', 'prices', 'window'} for target in node.targets):
                raise InvalidFactor('only local scalar/array assignments are allowed')
        if isinstance(node, ast.AugAssign) and (not isinstance(node.target, ast.Name) or node.target.id in {'np', 'prices', 'window'}):
            raise InvalidFactor('input mutation is forbidden')
    proxy = SimpleNamespace(**{name: getattr(np, name) for name in SAFE_NUMPY}, nan=np.nan, inf=np.inf, float64=np.float64)
    proxy.arange = bounded_arange
    namespace = {'__builtins__': SAFE_BUILTINS, 'np': proxy}
    exec(compile(tree, '<restricted-price-factor>', 'exec'), namespace)
    return func.name, int(match.group(2)), namespace[func.name]


@dataclass
class Factor:
    code: str
    origin: str = 'paper_seed_family'
    created_index: int = -1

    def __post_init__(self):
        self.created_index = int(self.created_index)
        self.name, self.window, self.function = compile_factor(self.code)
        self.sha256 = hashlib.sha256(self.code.encode()).hexdigest()
        self.base = re.sub(r'_v\d+$', '', self.name)
        self.version = int(re.search(r'_v(\d+)$', self.name).group(1)) if re.search(r'_v(\d+)$', self.name) else 0

    def score(self, history: np.ndarray) -> np.ndarray:
        if history.ndim != 2 or history.shape[0] != 30:
            raise ValueError('EFS requires 30 completed daily closes')
        eligible = np.isfinite(history).all(axis=0) & (history > 0).all(axis=0)
        scores = np.full(history.shape[1], np.nan)
        def timeout(_signum, _frame):
            raise InvalidFactor('factor execution exceeded time budget')
        prior = signal.signal(signal.SIGALRM, timeout)
        signal.setitimer(signal.ITIMER_REAL, 3.0)
        try:
            for i in np.flatnonzero(eligible):
                prices = history[:, i].copy()
                prices.flags.writeable = False
                with np.errstate(all='ignore'):
                    value = self.function(prices, self.window)
                if np.ndim(value) != 0:
                    raise InvalidFactor('factor must return one score per stock')
                scores[i] = float(value)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, prior)
        return scores


def seed_factors() -> list[Factor]:
    bodies = {
        'mean_return': 'r = prices[-window:] / prices[-window-1:-1] - 1\nreturn np.mean(r)',
        'std_return': 'r = prices[-window:] / prices[-window-1:-1] - 1\nreturn np.std(r)',
        'momentum': 'return prices[-1] / prices[-window-1] - 1',
        'max_drawdown': 'p = prices[-window-1:]\nreturn np.min(p / np.maximum.accumulate(p) - 1)',
        'sharpe_ratio': 'r = prices[-window:] / prices[-window-1:-1] - 1\nreturn np.mean(r) / (np.std(r) + 1e-8)',
        'volatility': 'return np.std(np.log(prices[-window:] / prices[-window-1:-1]))',
        'price_position': 'p = prices[-window:]\nreturn (p[-1] - np.min(p)) / (np.max(p) - np.min(p) + 1e-8)',
        'ma': 'return np.mean(prices[-window:])',
        'bb_width': 'p = prices[-window:]\nreturn 2 * np.std(p) / (np.mean(p) + 1e-8)',
        'ema_ratio': 'p = prices[-window:]\na = 2 / (window + 1)\nw = np.power(1-a, np.arange(window-1, -1, -1))\nema = p[0] * w[0] + a * np.sum(p[1:] * w[1:])\nreturn p[-1] / (ema + 1e-8)',
    }
    factors = []
    for name, body in bodies.items():
        for window in (3, 7, 14, 21):
            code = f'def {name}_{window}_v1(prices, window={window}):\n' + '\n'.join('    ' + s for s in body.splitlines()) + '\n'
            factors.append(Factor(code))
    factors.append(Factor('def log_return_1_v1(prices, window=1):\n    return np.log(prices[-1] / prices[-2])\n'))
    factors.append(Factor('def rsi_14_v1(prices, window=14):\n    r = np.diff(prices[-window-1:])\n    gain = np.mean(np.maximum(r, 0))\n    loss = np.mean(np.maximum(-r, 0))\n    return 100 - 100 / (1 + gain / (loss + 1e-8))\n'))
    return factors


def normalize(scores: np.ndarray) -> np.ndarray:
    out = np.full(scores.shape, np.nan)
    finite = np.isfinite(scores)
    if finite.any():
        low, high = scores[finite].min(), scores[finite].max()
        out[finite] = 0.0 if high - low <= 1e-12 else 2 * (scores[finite] - low) / (high - low) - 1
    return out


def top_weights(scores: np.ndarray, m: int) -> np.ndarray:
    valid = np.flatnonzero(np.isfinite(scores))
    if len(valid) < m:
        raise ValueError('fewer than m formation-eligible stocks')
    # Input columns are sorted by ticker; stable sort supplies declared tie breaks.
    chosen = valid[np.argsort(-scores[valid], kind='stable')[:m]]
    weights = np.zeros(len(scores))
    weights[chosen] = 1 / m
    return weights


def daily_account(targets: np.ndarray, returns: np.ndarray, costs_bps: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Targets at row t execute after earning row t's return; fees charged at t close.

A signal dated t-1 supplies target[t]. The position earns close[t] -> close[t+1].
Fees reduce all post-trade capital proportionally; traded notional solves the
self-financing fee equation rather than charging pre-fee target turnover.
"""
    if targets.shape != returns.shape or targets.ndim != 2:
        raise ValueError('unaligned account arrays')
    fee = costs_bps / 10000
    if not 0 <= fee < 1 or not np.isfinite(targets).all() or (targets < 0).any() or not np.allclose(targets.sum(axis=1), 1):
        raise ValueError('invalid long-only targets or costs')
    nav = 1.0
    dollars = np.zeros(targets.shape[1])
    cash = 1.0
    paths, turnover, fees = [], [], []
    for w, r in zip(targets, returns):
        held = dollars > 1e-14
        if not np.isfinite(r[held]).all() or (r[held] < -1).any():
            raise ValueError('missing or invalid realized return on a held stock')
        marked = dollars * (1 + np.where(held, r, 0))
        gross = cash + marked.sum()
        if gross <= 0:
            raise ValueError('nonpositive portfolio NAV')
        after = gross
        for _ in range(30):
            updated = gross - fee * np.abs(after * w - marked).sum()
            if abs(updated - after) < 1e-13 * gross:
                after = updated
                break
            after = updated
        traded = np.abs(after * w - marked).sum()
        paths.append(after / nav - 1)
        turnover.append(traded / gross)
        fees.append((gross - after) / gross)
        dollars = after * w
        cash, nav = 0.0, after
    return np.asarray(paths), np.asarray(turnover), np.asarray(fees)


def monthly_compound(dates, returns: np.ndarray) -> pd.Series:
    series = pd.Series(returns, index=pd.DatetimeIndex(dates))
    if not series.index.is_monotonic_increasing or series.index.has_duplicates or not np.isfinite(series).all() or (series < -1).any():
        raise ValueError('invalid daily return series')
    return (1 + series).groupby(series.index.to_period('M')).prod() - 1
