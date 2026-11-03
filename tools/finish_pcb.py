"""Import the Freerouting session into the (zone-less) board, add GND pours, save."""
import sys, pcbnew
from pcbnew import FromMM
src, ses, dst = sys.argv[1:4]
from design import OX, OY, W, H
b = pcbnew.LoadBoard(src)
print("import ses:", pcbnew.ImportSpecctraSES(b, ses))
gnd = b.FindNet('GND')
for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
    z = pcbnew.ZONE(b); z.SetLayer(layer); z.SetNet(gnd)
    z.SetLocalClearance(FromMM(0.25)); z.SetMinThickness(FromMM(0.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL); z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    ol = z.Outline(); ol.NewOutline()
    for (x, y) in [(0.3, 0.3), (W - 0.3, 0.3), (W - 0.3, H - 0.3), (0.3, H - 0.3)]:
        ol.Append(FromMM(OX + x), FromMM(OY + y))
    b.Add(z)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.BuildConnectivity()
pcbnew.SaveBoard(dst, b)
print("tracks:", len(b.GetTracks()))
