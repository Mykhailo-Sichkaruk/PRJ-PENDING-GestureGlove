"""Compare the 16 intended electrical nets across KiCad and Fritzing exports.

ERC alone cannot prove signal assignment. This checks actual native connections,
including the Feather part's internal buses and all wire-chain junctions.
"""
from collections import defaultdict
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as E
import zipfile

root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as tmp:
    export=Path(tmp)/'glove.net'
    subprocess.run(['kicad-cli','sch','export','netlist','--format','kicadxml',
                    str(root/'examples/poc/electronics/glove/gesture-glove-v2.kicad_sch'),'-o',str(export)],check=True)
    sch=E.parse(export).getroot()
expected={}
for net in sch.findall('nets/net'):
    nodes=set()
    for node in net:
        ref,pin=node.get('ref'),node.get('pin')
        if ref in ['SW1','SW2','SW3','SW4','SW5'] and pin=='2': ref,pin='PALM','1'
        nodes.add((ref,pin))
    expected[net.get('name')]=frozenset(nodes)

with zipfile.ZipFile(root/'examples/poc/electronics/fritzing/gesture-glove.fzz') as z:
    fz=E.fromstring(z.read(next(n for n in z.namelist() if n.endswith('.fz'))))
    definitions={r.get('moduleId'):r for n in z.namelist() if n.endswith('.fzp') for r in [E.fromstring(z.read(n))]}
instances={i.get('modelIndex'):i for i in fz.findall('instances/instance')}
parent={}
def find(n):
    parent.setdefault(n,n)
    if parent[n]!=n:parent[n]=find(parent[n])
    return parent[n]
def union(a,b):parent[find(a)]=find(b)
for index,inst in instances.items():
    if inst.get('moduleIdRef')=='WireModuleID':
        union((index,'connector0'),(index,'connector1'))
        assert inst.find('views/breadboardView/geometry').get('wireFlags')=='64', 'Non-breadboard wire flag'
    for con in inst.findall('views/breadboardView/connectors/connector'):
        for target in con.findall('connects/connect'):
            assert target.get('modelIndex') in instances,'Dangling wire reference'
            union((index,con.get('connectorId')),(target.get('modelIndex'),target.get('connectorId')))
    definition=definitions.get(inst.get('moduleIdRef'))
    if definition is not None:
        for bus in definition.findall('buses/bus'):
            ids=[(index,n.get('connectorId')) for n in bus]
            for a,b in zip(ids,ids[1:]):union(a,b)

feather={'connector54':'A5','connector73':'D5','connector72':'D6','connector71':'D9','connector70':'D10',
 'connector59':'A0','connector58':'A1','connector57':'A2','connector56':'A3','connector55':'A4',
 'connector61':'3V3','connector60':'GND','connector74':'SCL','connector75':'SDA','connector65':'EN','connector218':'BAT'}
groups=defaultdict(set)
for index,inst in instances.items():
    ref=inst.findtext('title')
    mapping={}
    if ref=='U1':mapping={c:('U1',p) for c,p in feather.items()}
    elif ref=='U2':mapping={f'connector{c}':('U2',p) for c,p in [(0,'1'),(1,'2'),(2,'3'),(3,'4'),(6,'7')]}
    elif ref.startswith(('RF','R','C')) or ref=='BT1': mapping={f'connector{i}':(ref,str(i+1)) for i in range(2)}
    elif ref.startswith('P') and ref!='PALM':mapping={'connector0':('SW'+ref[1:],'1')}
    elif ref=='PALM':mapping={'connector0':('PALM','1')}
    elif ref=='SW6':mapping={'connector0':('SW6','2'),'connector1':('SW6','1')}
    for c,n in mapping.items():groups[find((index,c))].add(n)
actual={frozenset(nodes) for nodes in groups.values()}
assert len(expected)==16
assert set(expected.values())==actual, {'missing':set(expected.values())-actual,'unexpected':actual-set(expected.values())}
print('PASS: all 16 KiCad/Fritzing nets match; five flex inputs, five pad inputs, I2C, EN and power remain separate.')
