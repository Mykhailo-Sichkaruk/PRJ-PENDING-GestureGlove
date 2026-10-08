"""Populate the MCP's project-local part library from the checked-in bundles."""
import hashlib
import os
from pathlib import Path
import xml.etree.ElementTree as E
import zipfile

root=Path(os.environ['SMVIT_PROJECT_ROOT'])
library=Path(os.environ['FRITZING_LOCAL_PARTS'])
E.register_namespace('', 'http://www.w3.org/2000/svg')
for bundle in (root/'hardware/parts/fritzing').glob('*.fzpz'):
    digest=hashlib.sha256(bundle.read_bytes()).hexdigest()+'-layer-repair-v1'
    with zipfile.ZipFile(bundle) as z:
        name=next(n for n in z.namelist() if n.endswith('.fzp'))
        fzp=E.fromstring(z.read(name));mid=fzp.get('moduleId')
        if not mid or Path(mid).name!=mid:raise ValueError('Invalid module ID')
        dest=library/mid
        stamp=dest/'.source-sha256'
        if stamp.exists() and stamp.read_text()==digest:continue
        dest.mkdir(parents=True,exist_ok=True)
        (dest/(mid+'.fzp')).write_bytes(z.read(name))
        for name in z.namelist():
            if not name.startswith('svg.'):continue
            _,view,filename=name.split('.',2)
            if view not in ('breadboard','icon','schematic','pcb') or Path(filename).name!=filename:
                raise ValueError('Unexpected part asset path')
            data=z.read(name)
            if view in ('breadboard','icon'):
                svg=E.fromstring(data)
                if not any(e.get('id')==view for e in svg.iter()):
                    group=E.Element('{http://www.w3.org/2000/svg}g',id=view)
                    for element in list(svg):svg.remove(element);group.append(element)
                    svg.append(group);data=E.tostring(svg,encoding='utf-8')
            folder=dest/view;folder.mkdir(exist_ok=True);(folder/filename).write_bytes(data)
        stamp.write_text(digest)
