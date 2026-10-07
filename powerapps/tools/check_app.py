#!/usr/bin/env python3
"""Static checks on the generated app: balanced formulas, unique control names, references to controls that
exist, variables that are set somewhere, and screens that exist."""
import glob, re, sys, collections
from pathlib import Path
import yaml

PA = Path(__file__).resolve().parent.parent

def balanced(e):
    st = []; inq = False; i = 0; pairs = {')': '(', ']': '[', '}': '{'}
    while i < len(e):
        c = e[i]
        if inq:
            if c == '"':
                if i + 1 < len(e) and e[i + 1] == '"': i += 2; continue
                inq = False
        elif c == '"': inq = True
        elif c in '([{': st.append(c)
        elif c in ')]}':
            if not st or st[-1] != pairs[c]: return False
            st.pop()
        i += 1
    return not st and not inq

def strip_strings(e):
    return re.sub(r'"(?:[^"]|"")*"', '""', e)

names = collections.Counter(); formulas = []
def walk(node, where):
    if isinstance(node, list):
        for x in node: walk(x, where)
    elif isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, dict) and 'Control' in v:
                names[k] += 1
                for pk, pv in (v.get('Properties') or {}).items():
                    if isinstance(pv, str): formulas.append((where, k, pk, pv.lstrip('=')))
                walk(v.get('Children', []), where)
screens = []
for f in sorted(glob.glob(str(PA / 'screens' / '*.pa.yaml'))):
    screens.append(Path(f).name.split('.')[0]); walk(yaml.safe_load(open(f)), Path(f).name)
fx = {}
for f in ['App.Formulas.fx', 'App.OnStart.fx', 'Screens.OnVisible.fx']:
    fx[f] = '\n'.join(l for l in (PA / f).read_text().splitlines() if not l.strip().startswith('//'))
    formulas.append((f, '-', '-', fx[f]))

problems = []
dups = [k for k, c in names.items() if c > 1]
if dups: problems.append(f"duplicate control names: {dups}")
sets = set()
for _, _, _, e in formulas:
    sets |= set(re.findall(r'\bSet\(\s*(\w+)', e))
named = set(re.findall(r'^(\w+)\s*=', fx['App.Formulas.fx'], re.M))
for where, ctl, prop, e in formulas:
    if not balanced(e): problems.append(f"{where} {ctl}.{prop}: unbalanced")
    code = strip_strings(e)
    for ref in set(re.findall(r'\b((?:txt|lbl|cmb|dd|chk|rad|tgl|btn|gal|lnk|ico|rec|cnt|htm|html|tmr|hnt)[A-Z]\w*_\w+)\b', code)):
        if ref not in names: problems.append(f"{where} {ctl}.{prop}: unknown control {ref}")
    for var in set(re.findall(r'\b(var[A-Z]\w*)\b', code)):
        if var not in sets: problems.append(f"{where} {ctl}.{prop}: variable {var} is never Set")
    for scr in set(re.findall(r'Navigate\(\s*(\w+)', code)):
        if scr not in screens: problems.append(f"{where} {ctl}.{prop}: Navigate to missing screen {scr}")
    for g in set(re.findall(r'\b(g[A-Z]\w*)\b', code)):
        if g not in named: problems.append(f"{where} {ctl}.{prop}: unknown named formula {g}")
print(f"{sum(names.values())} controls, {len(formulas)} formulas, screens: {', '.join(screens)}")
print("\n".join(sorted(set(problems))) if problems else "no problems found")
sys.exit(1 if problems else 0)
