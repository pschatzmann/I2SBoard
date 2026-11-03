"""Export the JLCPCB package: Gerbers + drill (zip), BOM.csv, CPL.csv."""
import csv, os, subprocess, shutil, zipfile, collections
from design import PARTS, LCSC, NOT_ASSEMBLED
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
pcb = f'{root}/kicad/I2SBoard.kicad_pcb'
out = f'{root}/fab'; g = f'{out}/gerber'
shutil.rmtree(out, ignore_errors=True); os.makedirs(g)
run = lambda *a: subprocess.run(a, check=True, capture_output=True)
run('kicad-cli', 'pcb', 'export', 'gerbers', '--layers', 'F.Cu,B.Cu,F.Paste,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts',
    '--no-protel-ext', '-o', g, pcb)
run('kicad-cli', 'pcb', 'export', 'drill', '--format', 'excellon', '--drill-origin', 'absolute',
    '--excellon-units', 'mm', '--generate-map', '--map-format', 'gerberx2', '-o', g + '/', pcb)
run('kicad-cli', 'pcb', 'export', 'pos', '--format', 'csv', '--units', 'mm', '--side', 'front',
    '--exclude-dnp', '-o', f'{out}/pos_kicad.csv', pcb)
with zipfile.ZipFile(f'{out}/I2SBoard_gerber.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for f in sorted(os.listdir(g)):
        z.write(f'{g}/{f}', f)

# ---- BOM (grouped by LCSC number) ----
fp_short = lambda fp: fp.split(':')[1]
groups = collections.OrderedDict()
for ref, lib, sym, value, fp, nets in PARTS:
    if ref in NOT_ASSEMBLED: continue
    key = (LCSC[ref], value, fp_short(fp))
    groups.setdefault(key, []).append(ref)
natkey = lambda r: (r.rstrip('0123456789'), int(r[len(r.rstrip('0123456789')):]))
with open(f'{out}/BOM.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part #'])
    for (lcsc, value, fp), refs in groups.items():
        w.writerow([value, ','.join(sorted(refs, key=natkey)), fp, lcsc])

# ---- CPL ----
with open(f'{out}/pos_kicad.csv') as f, open(f'{out}/CPL.csv', 'w', newline='') as o:
    r = csv.DictReader(f); w = csv.writer(o)
    w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
    for row in r:
        if row['Ref'] in NOT_ASSEMBLED or row['Ref'] not in LCSC: continue
        w.writerow([row['Ref'], row['PosX'] + 'mm', row['PosY'] + 'mm', 'Top', row['Rot']])
os.remove(f'{out}/pos_kicad.csv')
print(open(f'{out}/BOM.csv').read()); print(open(f'{out}/CPL.csv').read()); print(os.listdir(out), os.listdir(g))
