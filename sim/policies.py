"""Policy registry: one place that turns a name into a policy function.

Spec forms accepted by get():
  'hunter', 'sprint', 'rlock5' ...        a registered policy
  'rlock5[feed_min=8,feed_margin=3]'       a registered factory called with those parameters
  'module:function'                         any importable policy (module importable from sim/)

Specs are plain strings, so they can be sent to worker processes (experiments.py).
To plug in a new family of policies: give its module a FACTORIES dict (name -> factory(**params)) and/or a
POLICIES dict (name -> policy) and add the module name to POLICY_MODULES.
"""

import importlib

import bots
import cells_ref

POLICY_MODULES = ['rivals', 'cells_ref']

REGISTRY = dict(bots.BOTS)
REGISTRY['sprint'] = cells_ref.sprint
FACTORIES = {}
_cache = {}


def register(name, policy=None, factory=None):
    if factory is not None:
        FACTORIES[name] = factory
        if policy is None:
            policy = factory()
    if policy is not None:
        REGISTRY[name] = policy


def _load_modules():
    for modname in POLICY_MODULES:
        mod = importlib.import_module(modname)
        for name, fac in getattr(mod, 'FACTORIES', {}).items():
            register(name, getattr(mod, name, None), fac)
        for name, pol in getattr(mod, 'POLICIES', {}).items():
            register(name, pol)


_load_modules()


def _value(text):
    for conv in (int, float):
        try:
            return conv(text)
        except ValueError:
            pass
    if text in ('True', 'False'):
        return text == 'True'
    return text


def parse_params(text):
    kw = {}
    for part in text.split(','):
        part = part.strip()
        if part:
            k, v = part.split('=', 1)
            kw[k.strip()] = _value(v.strip())
    return kw


def get(spec):
    """Policy for a spec string; KeyError if unknown."""
    if spec in _cache:
        return _cache[spec]
    if '[' in spec:
        name, rest = spec.split('[', 1)
        if not rest.endswith(']') or name not in FACTORIES:
            raise KeyError(spec)
        pol = FACTORIES[name](**parse_params(rest[:-1]))
    elif spec in REGISTRY:
        pol = REGISTRY[spec]
    elif ':' in spec:
        mod, fn = spec.split(':', 1)
        pol = getattr(importlib.import_module(mod), fn)
    else:
        raise KeyError(spec)
    _cache[spec] = pol
    return pol


def split_specs(text):
    """'a,b[x=1,y=2],c' -> ['a', 'b[x=1,y=2]', 'c'] (commas inside brackets kept)."""
    out, cur, depth = [], '', 0
    for ch in text:
        if ch == ',' and depth == 0:
            out.append(cur)
            cur = ''
            continue
        depth += (ch == '[') - (ch == ']')
        cur += ch
    out.append(cur)
    return [s.strip() for s in out if s.strip()]


def known():
    return sorted(set(REGISTRY) | set(FACTORIES))
