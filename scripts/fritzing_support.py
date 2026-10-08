"""Native SVG terminal positions and connected-wire editing for Fritzing 1.0.6.

Fritzing uses 90 px/in; Qt's SVG viewBox coordinates are transformed explicitly.
The upstream CLI uses part origins instead of terminals when drawing wires.
"""
import os
import re
from pathlib import Path
import xml.etree.ElementTree as E
from . import model, partsdb

_app = None


def part_data(sketch, inst):
    module = inst.get('moduleIdRef')
    for name, data in sketch.other_entries.items():
        if name.endswith('.fzp'):
            root=E.fromstring(data)
            if root.get('moduleId') == module:
                return root, lambda view,path: sketch.other_entries['svg.'+view+'.'+Path(path).name]
    path=partsdb.find_part_path(module)
    if path is None: raise ValueError(f'Unknown part: {module}')
    path=Path(path)
    if not path.is_absolute(): path=Path(partsdb.APP_ROOT)/'parts'/path
    root=E.parse(path).getroot()
    def svg(view, image):
        candidates=[path.parent/image, path.parent/f'svg.{view}.{Path(image).name}',
                    Path(partsdb.APP_ROOT)/'parts/svg'/path.parent.name/image]
        for candidate in candidates:
            if candidate.exists(): return candidate.read_bytes()
        raise FileNotFoundError(image)
    return root,svg


def inches(value):
    m=re.fullmatch(r'([0-9.+eE-]+)(in|mm|cm|px|pt)?',value)
    if not m: raise ValueError(f'Unsupported SVG dimension {value!r}')
    return float(m[1])*{'in':1,'mm':1/25.4,'cm':1/2.54,'px':1/90,'pt':1/72,None:1/90}[m[2]]


def terminal(sketch, inst, connector, view='bb'):
    global _app
    token=model.VIEW_TOKENS[view]
    geo=inst.find(f'views/{token["view"]}/geometry')
    if geo is None: raise ValueError(f'Missing {view} placement')
    x,y=float(geo.get('x','0')),float(geo.get('y','0'))
    if inst.get('moduleIdRef') == model.WIRE_MODULE_ID:
        return (x,y) if connector == 'connector0' else (x+float(geo.get('x2','0'))-float(geo.get('x1','0')),y+float(geo.get('y2','0'))-float(geo.get('y1','0')))
    from PySide6.QtCore import QByteArray,QPointF
    from PySide6.QtGui import QTransform
    from PySide6.QtWidgets import QApplication
    from PySide6.QtSvg import QSvgRenderer
    if _app is None:
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        _app=QApplication.instance() or QApplication([])
    root,read_svg=part_data(sketch,inst)
    con=root.find(f'connectors/connector[@id="{connector}"]/views/{token["view"]}/p')
    if con is None: raise ValueError(f'No {view} terminal {connector}')
    layer=root.find(f'views/{token["view"]}/layers')
    data=read_svg({'bb':'breadboard','sc':'schematic','pcb':'pcb'}[view],layer.get('image'))
    renderer=QSvgRenderer(QByteArray(data))
    svg_id=con.get('terminalId') or con.get('svgId')
    if not renderer.elementExists(svg_id): svg_id=con.get('svgId')
    if not renderer.elementExists(svg_id): raise ValueError(f'SVG terminal missing: {svg_id}')
    point=renderer.transformForElement(svg_id).map(renderer.boundsOnElement(svg_id).center())
    svg_root=E.fromstring(data); box=renderer.viewBoxF()
    point=QPointF((point.x()-box.x())*inches(svg_root.get('width'))*90/box.width(),
                 (point.y()-box.y())*inches(svg_root.get('height'))*90/box.height())
    transform=geo.find('transform')
    if transform is not None:
        point=QTransform(*(float(transform.get(k,'0')) for k in ('m11','m12','m21','m22','dx','dy'))).map(point)
    return x+point.x(),y+point.y()


def connect(a,ac,b,bc,view='bb'):
    tok=model.VIEW_TOKENS[view]
    def layer(inst):
        return tok['wire_conn'] if inst.get('moduleIdRef') == model.WIRE_MODULE_ID else tok['part_conn']
    for inst,conn,other,otherconn in [(a,ac,b,bc),(b,bc,a,ac)]:
        v=inst.find(f'views/{tok["view"]}')
        cs=v.find('connectors')
        if cs is None: cs=E.SubElement(v,'connectors')
        c=cs.find(f'connector[@connectorId="{conn}"]')
        if c is None:
            c=E.SubElement(cs,'connector',connectorId=conn,layer=layer(inst))
            E.SubElement(c,'geometry',x='0',y='0')
            E.SubElement(c,'connects')
        targets=c.find('connects')
        if not any(t.get('modelIndex')==other.get('modelIndex') and t.get('connectorId')==otherconn for t in targets):
            E.SubElement(targets,'connect',modelIndex=other.get('modelIndex'),connectorId=otherconn,layer=layer(other))


def route(sketch,a,ac,b,bc,points=None,color='#328856',view='bb'):
    start=terminal(sketch,a,ac,view); end=terminal(sketch,b,bc,view)
    points=[start]+(points or [])+[end]
    points=[p for i,p in enumerate(points) if i==0 or p!=points[i-1]]
    prev,prevconn=a,ac
    wires=[]
    for p1,p2 in zip(points,points[1:]):
        wire=sketch.add_wire([], [view], p1, ((0,0),(p2[0]-p1[0],p2[1]-p1[1])),color)
        wire.find('title').text=f'W{wire.get("modelIndex")}'
        connect(prev,prevconn,wire,'connector0',view)
        prev,prevconn=wire,'connector1'; wires.append(wire)
    connect(prev,prevconn,b,bc,view)
    return wires


def cmd_wire(args):
    sketch=model.FzSketch(args.file)
    ra,ca=args.ref_a.split('.',1); rb,cb=args.ref_b.split('.',1)
    a,b=sketch.find_instance(ra),sketch.find_instance(rb)
    if a is None or b is None: raise ValueError('Unknown part reference')
    for view in model.resolve_view_token(args.view or 'bb'):
        route(sketch,a,ca,b,cb,color=args.color or '#328856',view=view)
    sketch.save(); print(f'Wired {args.ref_a} to {args.ref_b} at SVG terminals')
    return 0


def cmd_move(args):
    sketch=model.FzSketch(args.file); inst=sketch.find_instance(args.ref)
    if inst is None: raise ValueError('Unknown part reference')
    for view,tok in model.VIEW_TOKENS.items():
        geo=inst.find(f'views/{tok["view"]}/geometry')
        if geo is None: continue
        dx=0 if args.x is None else args.x-float(geo.get('x','0'))
        dy=0 if args.y is None else args.y-float(geo.get('y','0'))
        geo.set('x',str(float(geo.get('x','0'))+dx)); geo.set('y',str(float(geo.get('y','0'))+dy))
        for wire in sketch.instances():
            if wire.get('moduleIdRef')!=model.WIRE_MODULE_ID: continue
            wv=wire.find(f'views/{tok["view"]}')
            if wv is None: continue
            wg=wv.find('geometry'); ox,oy=float(wg.get('x')),float(wg.get('y'))
            ex,ey=ox+float(wg.get('x2')),oy+float(wg.get('y2'))
            for c in wv.findall('connectors/connector'):
                if any(t.get('modelIndex')==inst.get('modelIndex') for t in c.findall('connects/connect')):
                    if c.get('connectorId')=='connector0': ox+=dx;oy+=dy
                    else: ex+=dx;ey+=dy
            for k,v in dict(x=ox,y=oy,x1=0,y1=0,x2=ex-ox,y2=ey-oy).items(): wg.set(k,str(v))
    sketch.save();print(f'Moved {args.ref}; attached wire endpoints updated')
    return 0


def cmd_remove(args):
    sketch=model.FzSketch(args.file); inst=sketch.find_instance(args.ref)
    if inst is None: raise ValueError('Unknown part reference')
    doomed={inst.get('modelIndex')}
    # Remove complete attached wire chains, preserving other parts and branches.
    changed=True
    while changed:
        changed=False
        for wire in sketch.instances():
            if wire.get('moduleIdRef')!=model.WIRE_MODULE_ID or wire.get('modelIndex') in doomed: continue
            if any(c.get('modelIndex') in doomed for c in wire.findall('views/*/connectors/connector/connects/connect')):
                doomed.add(wire.get('modelIndex'));changed=True
    for item in list(sketch.instances()):
        if item.get('modelIndex') in doomed: sketch._instances_el().remove(item);continue
        for connects in item.findall('views/*/connectors/connector/connects'):
            for c in list(connects):
                if c.get('modelIndex') in doomed: connects.remove(c)
    sketch.save(); print(f'Removed {args.ref} and {len(doomed)-1} attached wire segments')
    return 0


def embed_local(sketch, inst):
    """A local part must travel in the .fzz for the real app to load it."""
    path=partsdb.find_part_path(inst.get('moduleIdRef'))
    if not path or not Path(path).is_absolute(): return
    root,read_svg=part_data(sketch,inst)
    sketch.other_entries['part.'+inst.get('moduleIdRef')+'.fzp']=E.tostring(root,encoding='utf-8')
    for view in root.findall('views/*'):
        layer=view.find('layers')
        if layer is None: continue
        name=view.tag.removesuffix('View')
        filename=Path(layer.get('image')).name
        sketch.other_entries[f'svg.{name}.{filename}']=read_svg(name,layer.get('image'))
