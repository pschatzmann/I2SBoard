import uuid, sys
from sexp import *
from design import PARTS, PWR_FLAGS, NOT_ASSEMBLED, NC_PARTS
import os

SYM = '/usr/share/kicad/symbols/'
PROJECT = "I2SBoard"
POWER = {"GND", "+5V", "+3V3"}
root = str(uuid.uuid4())
U = lambda: str(uuid.uuid4())

def num(x):
    return f"{x:.4f}".rstrip('0').rstrip('.')

libsyms = {}   # "Lib:Name" -> node
def getsym(lib, name):
    key = f"{lib}:{name}"
    if key not in libsyms:
        s = load_symbol((os.path.dirname(os.path.abspath(__file__)) + '/' if lib == 'Local' else SYM) + lib + '.kicad_sym', name)
        s = [s[0], Str(key)] + s[2:]
        # sub-symbol names must stay "<name>_u_s" (without the library prefix)
        libsyms[key] = s
    return libsyms[key]

def pins_of(sym, unit):
    """[(number, name, x, y, angle)] for given unit (unit 0 = all)."""
    out = []
    for sub in find(sym, 'symbol'):
        parts = sub[1].rsplit('_', 2)
        u = int(parts[1]); 
        if unit and u not in (0, unit):
            continue
        for p in find(sub, 'pin'):
            at = find(p, 'at')[0]
            out.append((str(find(p, 'number')[0][1]), str(find(p, 'name')[0][1]),
                        float(at[1]), float(at[2]), float(at[3])))
    # top-level pins (no units)
    for p in find(sym, 'pin'):
        at = find(p, 'at')[0]
        out.append((str(find(p, 'number')[0][1]), str(find(p, 'name')[0][1]),
                    float(at[1]), float(at[2]), float(at[3])))
    return out

DIRS = {0: (-1, 0), 90: (0, 1), 180: (1, 0), 270: (0, -1)}  # outward in schematic coords

body = []
def eff(size=1.27, hide=False, just=None):
    e = ['effects', ['font', ['size', num(size), num(size)]]]
    if just: e.append(['justify'] + just.split())
    if hide: e.append(['hide', 'yes'])
    return e

def wire(x1, y1, x2, y2):
    body.append(['wire', ['pts', ['xy', num(x1), num(y1)], ['xy', num(x2), num(y2)]],
                 ['stroke', ['width', '0'], ['type', 'default']], ['uuid', Str(U())]])

def label(net, x, y, outdir):
    ang = {(-1, 0): 180, (1, 0): 0, (0, 1): 270, (0, -1): 90}[outdir]
    just = 'right bottom' if ang in (180, 270) else 'left bottom'
    if ang == 270: just = 'right bottom'
    body.append(['label', Str(net), ['at', num(x), num(y), str(ang)], eff(1.27, just=just), ['uuid', Str(U())]])

power_count = [0]
def place_symbol(libname, name, ref, value, fp, x, y, unit=1, hidepins=None, pinmap=None, fixed_ref=None):
    sym = getsym(libname, name)
    props = []
    lib_props = {p[1]: p for p in find(sym, 'property')}
    def prop(k, v, dy, hide=False):
        props.append(['property', Str(k), Str(v), ['at', num(x), num(y + dy), '0'], eff(1.27, hide=hide)])
    prop('Reference', ref, -6.35, hide=ref.startswith('#'))
    prop('Value', value, 6.35, hide=ref.startswith('#'))
    prop('Footprint', fp, 0, True)
    prop('Datasheet', '', 0, True)
    entry = ['symbol', ['lib_id', Str(f"{libname}:{name}")], ['at', num(x), num(y), '0'], ['unit', str(unit)],
             ['exclude_from_sim', 'no'], ['in_bom', 'no' if (ref.startswith('#') or ref in NOT_ASSEMBLED) else 'yes'],
             ['on_board', 'no' if ref.startswith('#') else 'yes'], ['dnp', 'yes' if ref in NOT_ASSEMBLED else 'no'], ['uuid', Str(U())]] + props
    return sym, entry

def instance(entry, ref, unit, pinnums):
    for pn in pinnums:
        entry.append(['pin', Str(pn), ['uuid', Str(U())]])
    entry.append(['instances', ['project', Str(PROJECT),
                  ['path', Str('/' + root), ['reference', Str(ref)], ['unit', str(unit)]]]])
    body.append(entry)

def connect_net(net, px, py, outdir, stub=2.54):
    """wire stub from pin end + label or power symbol."""
    ex, ey = px + outdir[0] * stub, py + outdir[1] * stub
    wire(px, py, ex, ey)
    if net in POWER:
        power_count[0] += 1
        ref = f"#PWR{power_count[0]:02d}"
        sym, e = place_symbol('power', net, ref, net, '', ex, ey)
        instance(e, ref, 1, ['1'])
    else:
        label(net, ex, ey, outdir)

# ---- layout ----
COLS, DX, DY, X0, Y0 = 6, 63.5, 50.8, 50.8, 50.8
refpos = {}
for i, (ref, lib, name, value, fp, nets) in enumerate(PARTS):
    cx, cy = X0 + (i % COLS) * DX, Y0 + (i // COLS) * DY
    sym = getsym(lib, name)
    units = sorted({int(s[1].rsplit('_', 2)[1]) for s in find(sym, 'symbol')} - {0})
    if len(units) <= 1:
        units = [1]
    for k, unit in enumerate(units):
        ux, uy = cx, cy + (k * 25.4 if len(units) > 1 else 0)
        pins = [p for p in pins_of(sym, unit)]
        used = [p for p in pins if p[0] in nets]
        if not used and len(units) > 1:
            continue
        _, entry = place_symbol(lib, name, ref, value, fp, ux, uy, unit)
        instance(entry, ref, unit, [p[0] for p in pins if True and (p[0] in nets or name in ('ME6211C33M5',) or ref in NC_PARTS)])
        for (pn, pname, lx, ly, ang) in pins:
            px, py = ux + lx, uy - ly
            refpos[(ref, pn)] = (px, py, DIRS[int(ang)])
            if pn in nets:
                connect_net(nets[pn], px, py, DIRS[int(ang)])
            elif (name == 'ME6211C33M5' and pn == '4') or ref in NC_PARTS:
                body.append(['no_connect', ['at', num(px), num(py)], ['uuid', Str(U())]])

# PWR_FLAGs
for k, (net, ref, pn) in enumerate(PWR_FLAGS):
    px, py, d = refpos[(ref, pn)]
    ex, ey = px + d[0] * 7.62, py + d[1] * 7.62
    wire(px, py, ex, ey)
    power_count[0] += 1
    fref = f"#FLG{k+1:02d}"
    sym, e = place_symbol('power', 'PWR_FLAG', fref, 'PWR_FLAG', '', ex, ey)
    instance(e, fref, 1, ['1'])

out = ['kicad_sch', ['version', '20250114'], ['generator', Str('eeschema')], ['generator_version', Str('9.0')],
       ['uuid', Str(root)], ['paper', Str('A3')],
       ['title_block', ['title', Str('I2SBoard: stereo I2S ADC for Guitar/Piezo preamps')], ['rev', Str('1')],
        ['comment', '1', Str('PCM1808, USB-C powered')]],
       ['lib_symbols'] + list(libsyms.values())] + body + \
      [['sheet_instances', ['path', Str('/'), ['page', Str('1')]]], ['embedded_fonts', 'no']]

def pretty(n, ind=0):
    """one top-level child per line for readability"""
    if not isinstance(n, list) or not n:
        return dump(n)
    s = dump(n)
    if len(s) < 100 or n[0] in ('property',):
        return s
    return '(' + dump(n[0]) + ''.join('\n' + '  ' * (ind + 1) + pretty(c, ind + 1) for c in n[1:]) + ')'

open(sys.argv[1], 'w').write(pretty(out) + '\n')
print("parts placed, power symbols:", power_count[0])
