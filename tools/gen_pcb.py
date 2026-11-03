import sys, pcbnew
from pcbnew import VECTOR2I, FromMM
from design import PARTS

from design import OX, OY, W, H, SX, SY, POS, HOLES, NOT_ASSEMBLED, SILK
FP = '/usr/share/kicad/footprints/'
mm = lambda x, y: VECTOR2I(FromMM(OX + x), FromMM(OY + y))

b = pcbnew.NewBoard(sys.argv[1])
ds = b.GetDesignSettings()
ds.m_TrackMinWidth = FromMM(0.15)
ds.m_MinClearance = FromMM(0.15)
ds.m_ViasMinSize = FromMM(0.5)
ds.m_MinThroughDrill = FromMM(0.3)
ds.m_CopperEdgeClearance = FromMM(0.3)
nc = ds.m_NetSettings.GetDefaultNetclass()
nc.SetClearance(FromMM(0.15)); nc.SetTrackWidth(FromMM(0.25))
nc.SetViaDiameter(FromMM(0.6)); nc.SetViaDrill(FromMM(0.3))

nets = {}
def net(name):
    if name not in nets:
        n = pcbnew.NETINFO_ITEM(b, name); b.Add(n); nets[name] = n
    return nets[name]

for ref, lib, sym, value, fp, pinnets in PARTS:
    libname, fpname = fp.split(':')
    m = pcbnew.FootprintLoad(FP + libname + '.pretty', fpname)
    m.SetReference(ref); m.SetValue(value)
    x, y, rot = POS[ref]
    m.SetPosition(mm(x + SX, y + SY)); m.SetOrientationDegrees(rot)
    for pad in m.Pads():
        n = pinnets.get(pad.GetNumber())
        if n: pad.SetNet(net(n))
    m.Reference().SetVisible(ref not in ('J1', 'J2', 'J3', 'J5', 'J4'))
    if ref in NOT_ASSEMBLED:
        m.SetAttributes(m.GetAttributes() | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_DNP)
    b.Add(m)

# board outline with rounded-ish simple rectangle
for (x1, y1, x2, y2) in [(0, 0, W, 0), (W, 0, W, H), (W, H, 0, H), (0, H, 0, 0)]:
    s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.Edge_Cuts)
    s.SetStart(mm(x1, y1)); s.SetEnd(mm(x2, y2)); s.SetWidth(FromMM(0.1)); b.Add(s)

# mounting holes M3
for hi, (x, y) in enumerate(HOLES, 1):
    m = pcbnew.FootprintLoad(FP + 'MountingHole.pretty', 'MountingHole_2.7mm_M2.5')
    m.SetPosition(mm(x, y)); m.SetReference(f'H{hi}'); m.Reference().SetVisible(False); b.Add(m)

# GND pours on both layers
import os
for layer in (() if os.environ.get('NOZONE') else (pcbnew.F_Cu, pcbnew.B_Cu)):
    z = pcbnew.ZONE(b); z.SetLayer(layer); z.SetNet(net('GND'))
    z.SetLocalClearance(FromMM(0.25)); z.SetMinThickness(FromMM(0.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    ol = z.Outline(); ol.NewOutline()
    for (x, y) in [(0.3, 0.3), (W - 0.3, 0.3), (W - 0.3, H - 0.3), (0.3, H - 0.3)]:
        ol.Append(FromMM(OX + x), FromMM(OY + y))
    b.Add(z)

# silkscreen
def text(s, x, y, size=0.8, layer=pcbnew.F_SilkS):
    t = pcbnew.PCB_TEXT(b);
    if layer == pcbnew.B_SilkS: t.SetMirrored(True)
    t.SetText(s); t.SetPosition(mm(x + SX, y + SY)); t.SetLayer(layer)
    t.SetTextSize(VECTOR2I(FromMM(size), FromMM(size))); t.SetTextThickness(FromMM(size * 0.15)); b.Add(t)
for (t,x,y,sz) in SILK: text(t,x,y,sz)

b.BuildConnectivity()
pcbnew.SaveBoard(sys.argv[1], b)
print("saved", sys.argv[1])
