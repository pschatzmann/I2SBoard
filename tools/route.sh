#!/bin/bash
# regenerate the board, autoroute with Freerouting, import result, add pours
set -e
cd "$(dirname "$0")/../kicad"
NOZONE=1 /usr/bin/python3 ../tools/gen_pcb.py /tmp/nozone.kicad_pcb
/usr/bin/python3 -c "
import pcbnew
b=pcbnew.LoadBoard('/tmp/nozone.kicad_pcb'); assert pcbnew.ExportSpecctraDSN(b,'I2SBoard.dsn')"
rm -f I2SBoard.ses
java -jar ~/tools/freerouting/freerouting.jar -de I2SBoard.dsn -do I2SBoard.ses -mp 40 -mt 1 > /tmp/fr.log 2>&1
/usr/bin/python3 ../tools/finish_pcb.py /tmp/nozone.kicad_pcb I2SBoard.ses I2SBoard.kicad_pcb
kicad-cli pcb drc --severity-all --all-track-errors -o /tmp/drc.rpt I2SBoard.kicad_pcb | tail -2
grep -E "^\[" /tmp/drc.rpt | sort | uniq -c
