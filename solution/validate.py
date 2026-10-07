#!/usr/bin/env python3
"""Static checks on the generated flow definitions (src/Workflows/*.json)."""
import json, re, sys, glob

def balance(e):
    out = []; inq = False; i = 0
    while i < len(e):
        c = e[i]
        if inq:
            if c == "'":
                if i + 1 < len(e) and e[i + 1] == "'": i += 2; continue
                inq = False
        elif c == "'": inq = True
        else: out.append(c)
        i += 1
    if inq: return "unterminated quote"
    st = []; pairs = {')': '(', ']': '[', '}': '{'}
    for c in out:
        if c in '([{': st.append(c)
        elif c in ')]}':
            if not st or st[-1] != pairs[c]: return f"unbalanced {c}"
            st.pop()
    return "unclosed " + ''.join(st) if st else None

def expressions(v):
    """Yield every expression in a WDL value: '@expr' strings and '@{...}' fragments."""
    if isinstance(v, dict):
        for x in v.values(): yield from expressions(x)
    elif isinstance(v, list):
        for x in v: yield from expressions(x)
    elif isinstance(v, str):
        if v.startswith('@') and not v.startswith('@{') and not v.startswith('@@'):
            yield v[1:]
        else:
            i = 0
            while True:
                j = v.find('@{', i)
                if j < 0: break
                depth = 0; k = j + 1; inq = False
                while k < len(v):
                    c = v[k]
                    if inq:
                        if c == "'": inq = False
                    elif c == "'": inq = True
                    elif c == '{': depth += 1
                    elif c == '}':
                        depth -= 1
                        if depth == 0: break
                    k += 1
                yield v[j + 2:k]; i = k + 1

errors = []
for f in sorted(glob.glob('src/Workflows/*.json')):
    d = json.load(open(f)); defn = d['properties']['definition']
    flow = f.split('/')[-1].split('-')[0]
    all_actions = {}; loops = {}
    def collect(acts, parents):
        for k, a in acts.items():
            all_actions[k] = (a, parents)
            if a['type'] in ('Foreach',): loops[k] = parents
            for sub in [a.get('actions', {}), a.get('else', {}).get('actions', {})] + [c['actions'] for c in a.get('cases', {}).values()] + [a.get('default', {}).get('actions', {})]:
                collect(sub, parents + [k])
            # runAfter must reference siblings
        names = set(acts)
        for k, a in acts.items():
            for ra in a.get('runAfter', {}):
                if ra not in names: errors.append(f"{flow}: {k} runAfter {ra} is not a sibling")
            if len([x for x in acts.values() if not x.get('runAfter')]) > 1:
                pass
    collect(defn['actions'], [])
    for k in all_actions:
        if set(k) & set('?<>%&\\/:*#"\''):
            errors.append(f"{flow}: action name {k!r} contains a character Power Automate rejects")
    roots = [k for k, a in defn['actions'].items() if not a.get('runAfter')]
    if len(roots) != 1: errors.append(f"{flow}: top level has {len(roots)} start actions {roots}")
    init_vars = set()
    for k, (a, _) in all_actions.items():
        if a['type'] == 'InitializeVariable':
            init_vars |= {v['name'] for v in a['inputs']['variables']}
    triggers = set(defn['triggers'])
    for k, (a, parents) in list(all_actions.items()) + [(t, (defn['triggers'][t], [])) for t in triggers]:
        own = {x: y for x, y in a.items() if x not in ('actions', 'else', 'cases', 'default')} if isinstance(a, dict) else a
        for e in expressions(own):
            b = balance(e)
            if b: errors.append(f"{flow}: {k}: {b}: {e[:100]}")
            for fn, ref in re.findall(r"\b(body|outputs|actions|result|items)\('([^']+)'\)", e):
                if fn == 'items':
                    if ref not in loops: errors.append(f"{flow}: {k}: items('{ref}') is not a loop")
                    elif ref not in parents: errors.append(f"{flow}: {k}: items('{ref}') used outside the loop")
                elif ref not in all_actions: errors.append(f"{flow}: {k}: {fn}('{ref}') unknown action")
            for v in re.findall(r"variables\('([^']+)'\)", e):
                if v not in init_vars: errors.append(f"{flow}: {k}: variable {v} not initialized")
            for p in re.findall(r"parameters\('([^']+)'\)", e):
                if p not in defn['parameters']: errors.append(f"{flow}: {k}: parameter {p} unknown")
        if a.get('type') in ('SetVariable', 'AppendToArrayVariable') and a['inputs']['name'] not in init_vars:
            errors.append(f"{flow}: {k}: sets unknown variable {a['inputs']['name']}")
        host = a.get('inputs', {}).get('host') if isinstance(a.get('inputs'), dict) else None
        if host and host['connectionName'] not in d['properties']['connectionReferences']:
            errors.append(f"{flow}: {k}: connection {host['connectionName']} not referenced")
    print(f"{flow}: {len(all_actions)} actions checked")
print("\n".join(errors) if errors else "no problems found")
sys.exit(1 if errors else 0)
