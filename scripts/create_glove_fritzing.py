"""Build a native, editable Fritzing breadboard-view harness with embedded parts."""
import argparse
import json
import os
from pathlib import Path
import shutil
import xml.etree.ElementTree as E
import zipfile
from xml.sax.saxutils import escape
from fzkit import model, partsdb
from fzkit.smvit import terminal, connect, route

root=Path(__file__).resolve().parents[1]
out=root/'examples/poc/electronics/fritzing'
parts=root/'hardware/parts/fritzing'
out.mkdir(parents=True,exist_ok=True)
p=argparse.ArgumentParser();p.add_argument('--replace-generated',action='store_true');args=p.parse_args()
path=out/'gesture-glove.fzz'
if path.exists() and not args.replace_generated: raise SystemExit('Refusing overwrite; use --replace-generated deliberately')
parts.mkdir(parents=True,exist_ok=True)
sketch=model.FzSketch.from_template(str(path),str(Path(model.__file__).resolve().parents[1]/'templates/sketch.fz'))
sketch.root.set('fritzingVersion','1.0.6')
for view in sketch.root.findall('views/view'):view.set('showGrid','0')


def install_bundle(bundle):
    z=zipfile.ZipFile(bundle)
    fzpname=next(n for n in z.namelist() if n.endswith('.fzp'))
    fzp=E.fromstring(z.read(fzpname)); mid=fzp.get('moduleId')
    dest=Path(partsdb.LOCAL_PARTS_DIR)/mid;dest.mkdir(parents=True,exist_ok=True)
    (dest/(mid+'.fzp')).write_bytes(z.read(fzpname))
    for n in z.namelist():
        data=z.read(n)
        # Adafruit's 2022 SVG lacks the named breadboard/icon layer groups.
        # Fritzing 1.0.6 otherwise loads the electrical part but paints it blank.
        if n.startswith(('svg.breadboard.', 'svg.icon.')):
            view=n.split('.')[1]; svg_root=E.fromstring(data)
            if not any(e.get('id')==view for e in svg_root.iter()):
                group=E.Element('{http://www.w3.org/2000/svg}g',id=view)
                for element in list(svg_root):
                    svg_root.remove(element); group.append(element)
                svg_root.append(group)
                E.register_namespace('', 'http://www.w3.org/2000/svg')
                data=E.tostring(svg_root,encoding='utf-8')
        sketch.other_entries[n]=data
        if n.startswith('svg.'):
            _,view,filename=n.split('.',2)
            d=dest/view;d.mkdir(exist_ok=True);(d/filename).write_bytes(data)
    return mid


def svg(width,height,body,layer='breadboard'):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width/90}in" height="{height/90}in" viewBox="0 0 {width} {height}"><g id="{layer}">{body}</g></svg>'


def make_part(key,title,width,height,body,connectors):
    mid='smvit_'+key+'_v1'
    fzp=E.Element('module',moduleId=mid,fritzingVersion='1.0.6')
    for name,value in [('version','1'),('author','SMVIT project'),('title',title),('label',key),('date','2026-09-29'),('description','Conceptual glove harness part. Dimensions and PCB view are illustrative.'),('taxonomy','part.smvit')]:E.SubElement(fzp,name).text=value
    props=E.SubElement(fzp,'properties');E.SubElement(props,'property',name='family').text='SMVIT glove'
    views=E.SubElement(fzp,'views');cs=E.SubElement(fzp,'connectors')
    for i,(name,x,y) in enumerate(connectors):
        c=E.SubElement(cs,'connector',id=f'connector{i}',name=name,type='male')
        E.SubElement(c,'description').text=name
        vs=E.SubElement(c,'views')
        for view,layer in [('breadboard','breadboard'),('schematic','schematic'),('pcb','copper0')]:
            E.SubElement(E.SubElement(vs,view+'View'),'p',layer=layer,svgId=f'connector{i}pin')
    assets={}
    for view,layer in [('breadboard','breadboard'),('icon','icon'),('schematic','schematic'),('pcb','copper0')]:
        filename=mid+'_'+view+'.svg'
        ls=E.SubElement(E.SubElement(views,view+'View'),'layers',image=view+'/'+filename)
        E.SubElement(ls,'layer',layerId=layer)
        dots=''.join(f'<circle id="connector{i}pin" cx="{x}" cy="{y}" r="2" fill="#c1a266" stroke="#6c5634" stroke-width="0.8"/>' for i,(_,x,y) in enumerate(connectors))
        graphic=body if view in ('breadboard','icon') else f'<rect x="2" y="2" width="{width-4}" height="{height-4}" fill="none" stroke="#444" stroke-width="1"/>'
        assets[f'svg.{view}.{filename}']=svg(width,height,graphic+dots,layer).encode()
    bundle=parts/(key+'.fzpz')
    with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('part.'+mid+'.fzp',E.tostring(fzp,encoding='utf-8'))
        for n,data in assets.items():z.writestr(n,data)
    return install_bundle(bundle)


def txt(x,y,text,size=11,color='#334155',weight='normal'):
    return f'<text x="{x}" y="{y}" font-family="DejaVu Sans" font-size="{size}" fill="{color}" font-weight="{weight}">{escape(text)}</text>'


feather=install_bundle(parts/'Adafruit ESP32-S3 Feather.fzpz')
flex=make_part('flex','DIY Velostat flex strip',24,155,
    '<rect x="2" y="0" width="20" height="137" rx="5" fill="#b8772d"/>'
    '<rect x="6" y="7" width="12" height="121" rx="3" fill="#363b3c"/>'
    '<path d="M7 135 V152 M17 135 V152" stroke="#b89050" stroke-width="4"/>',
    [('3V3',7,152),('Signal',17,152)])
res=make_part('resistor10k','10 kohm divider resistor',48,16,
    '<path d="M2 8 H46" stroke="#92989c" stroke-width="2"/>'
    '<rect x="10" y="3" width="28" height="10" rx="4" fill="#dfc298"/>'
    '<path d="M15 3 V13" stroke="#714020" stroke-width="3"/>'
    '<path d="M20 3 V13" stroke="#181818" stroke-width="3"/>'
    '<path d="M25 3 V13" stroke="#e57125" stroke-width="3"/>'
    '<path d="M33 3 V13" stroke="#b99a39" stroke-width="2"/>', [('Signal',2,8),('GND',46,8)])
cap=make_part('capacitor100n','100 nF filter capacitor',23,30,
    '<path d="M6 12 V28 M17 12 V28" stroke="#949a9d" stroke-width="1.8"/>'
    '<circle cx="11.5" cy="10" r="10" fill="#c48a3d"/>'+txt(4,13,'104',7,'#3b2d1c'),
    [('Signal',6,28),('GND',17,28)])
pad=make_part('contact','Conductive fingertip pad',30,32,
    '<circle cx="15" cy="17" r="13" fill="#b97243" stroke="#855032" stroke-width="1.5"/>'
    '<circle cx="15" cy="17" r="9" fill="#c78c62"/>',[('Contact',15,4)])
palm=make_part('palm','Common conductive palm fabric',100,55,
    '<rect x="3" y="3" width="94" height="49" rx="8" fill="#92999b" stroke="#5b666a"/>'
    +''.join(f'<path d="M{x} 6 V49" stroke="#aeb4b4" stroke-width="0.6"/>' for x in range(8,96,5))
    +txt(17,31,'PALM / GND',10,'#263136'),[('GND',5,27.5)])
battery=make_part('lipo500','LiPo 3.7V 500mAh',105,66,
    '<rect x="0" y="0" width="96" height="65" rx="5" fill="#d9dcdf" stroke="#878c91"/>'
    '<rect x="0" y="0" width="14" height="65" fill="#d5a234"/>'
    '<path d="M94 16 H103" stroke="#c83737" stroke-width="2"/>'
    '<path d="M94 49 H103" stroke="#242424" stroke-width="2"/>'
    +txt(24,26,'LiPo',13)+txt(24,43,'3.7V  500mAh',8),[('VBAT',103,16),('GND',103,49)])
switch=make_part('slide','Slide switch: EN to GND',42,28,
    '<rect x="1" y="0" width="40" height="19" rx="2" fill="#62676b"/>'
    '<rect x="8" y="2" width="26" height="14" fill="#222"/>'
    '<rect x="9" y="3" width="11" height="12" fill="#aaa"/>'
    '<path d="M7 18 V26 M21 18 V26 M35 18 V26" stroke="#969a9d" stroke-width="2"/>',
    [('GND',7,26),('EN',21,26),('Unused',35,26)])

parts_inst={}

def place(module,ref,x,y,props=None):
    inst=sketch.add_part_instance(module,ref,['bb','sc','pcb'],x,y,partsdb.find_part_path(module) or '',props)
    parts_inst[ref]=inst
    return inst


def pt(ref,pin):return terminal(sketch,parts_inst[ref],pin)

def link(a,ac,b,bc,way=None,color='#c39124'):
    return route(sketch,parts_inst[a],ac,parts_inst[b],bc,way,color)


names=['Thumb','Index','Middle','Ring','Little'];xs=[120,270,420,570,720]
for i,x in enumerate(xs,1):
    place(flex,f'RF{i}',x,72)
    place(res,f'R{i}',x-20,307,{'resistance':'10k'})
    place(cap,f'C{i}',x+54,307,{'capacitance':'100nF'})
place(feather,'U1',395,505)
gy='MPU6050_GY521_782354e339f672575bb20992ece4ab1b_9'
place(gy,'U2',755,500)
place(battery,'BT1',84,509)
place(switch,'SW6',250,526)
for i,x in enumerate([405,510,615,720,825],1):place(pad,f'P{i}',x,735)
place(palm,'PALM',165,736)

# Shared power conductors. They are real connected wire segments, not graphics.
def bus(xs,y,color):
    wires=[]
    for left,right in zip(xs,xs[1:]):
        w=sketch.add_wire([],['bb'],(left,y),((0,0),(right-left,0)),color)
        w.find('title').text=f'W{w.get("modelIndex")}'
        if wires:connect(wires[-1],'connector1',w,'connector0')
        wires.append(w)
    return [(wires[0],'connector0')]+[(w,'connector1') for w in wires]
red,black='#c63e3e','#343d42'
powerbus=bus([x+7 for x in xs],266,red)
groundbus=bus([x+26 for x in xs],389,black)
for i,x in enumerate(xs,1):
    w,c=powerbus[i-1];route(sketch,parts_inst[f'RF{i}'],'connector0',w,c,color=red)
    w,c=groundbus[i-1];route(sketch,parts_inst[f'R{i}'],'connector1',w,c,color=black)
    a=pt(f'RF{i}','connector1');b=pt(f'R{i}','connector0')
    link(f'RF{i}','connector1',f'R{i}','connector0',[(a[0],290),(b[0],290)])
    a=pt(f'C{i}','connector0');b=pt(f'R{i}','connector0')
    link(f'C{i}','connector0',f'R{i}','connector0',[(a[0],353),(b[0],353)])
    a=pt(f'C{i}','connector1')
    route(sketch,parts_inst[f'C{i}'],'connector1',w,c,[(a[0],389)],black)

# Board supply to the two shared rails; use the actual header holes.
w,c=powerbus[0];a=pt('U1','connector61')
route(sketch,parts_inst['U1'],'connector61',w,c,[(a[0],610),(53,610),(53,266)],red)
w,c=groundbus[0];a=pt('U1','connector60')
route(sketch,parts_inst['U1'],'connector60',w,c,[(a[0],600),(65,600),(65,389)],black)
colors=['#278055','#ad7931','#8b5aa8','#367cba','#ca6a36']
for i,connector in enumerate(['connector54','connector73','connector72','connector71','connector70'],1):
    a=pt(f'R{i}','connector0');b=pt('U1',connector)
    if i==1:way=[(a[0],425),(330,425),(330,595),(b[0],595)]
    else:way=[(a[0],420+12*i),(b[0],420+12*i)]
    link(f'R{i}','connector0','U1',connector,way,colors[i-1])
for i,connector in enumerate(['connector59','connector58','connector57','connector56','connector55'],1):
    a=pt('U1',connector);b=pt(f'P{i}','connector0');y=646+(i-1)*14
    link('U1',connector,f'P{i}','connector0',[(a[0],y),(b[0],y)],colors[i-1])
a=pt('PALM','connector0');b=pt('U1','connector60')
link('PALM','connector0','U1','connector60',[(a[0]-20,a[1]),(a[0]-20,620),(b[0],620)],black)

# GY-521 header labels are the source of truth for the connector IDs.
gy_conns={n:c for c,n,_ in partsdb.connectors(gy)}
print('GY-521 connector map:',gy_conns)
for idx,(pin,fc,color) in enumerate([('VCC','connector61',red),('GND','connector60',black),('SCL','connector74','#b39922'),('SDA','connector75','#3988a8')]):
    a=pt('U1',fc);b=pt('U2',gy_conns[pin]);lane=450-idx*9
    if fc in ('connector61','connector60'):
        way=[(a[0],630+idx*8),(900+idx*10,630+idx*8),(900+idx*10,lane),(b[0],lane)]
    else:way=[(a[0],lane),(b[0],lane)]
    link('U1',fc,'U2',gy_conns[pin],way,color)
a=pt('U2',gy_conns['AD0']);b=pt('U2',gy_conns['GND'])
link('U2',gy_conns['AD0'],'U2',gy_conns['GND'],[(a[0],480),(b[0],480)],black)

# Battery connects to the JST contacts supplied in Adafruit's part, not VBUS.
for bc,fc,color,lane in [('connector0','connector218',red,483),('connector1','connector217',black,492)]:
    a=pt('BT1',bc);b=pt('U1',fc)
    link('BT1',bc,'U1',fc,[(a[0]+25,a[1]),(a[0]+25,lane),(b[0],lane)],color)
a=pt('SW6','connector1');b=pt('U1','connector65')
link('SW6','connector1','U1','connector65',[(a[0],576),(370,576),(370,472),(b[0],472)],'#93619c')
a=pt('SW6','connector0');b=pt('U1','connector60')
link('SW6','connector0','U1','connector60',[(a[0],587),(b[0],587)],black)

# A background annotation part travels with the sketch; all electronics above
# remain separate selectable parts and every colored conductor is a native wire.
body='<rect x="0" y="0" width="970" height="855" fill="#ffffff"/>'
body+=txt(28,30,'GESTURE GLOVE',22,'#162d3b','bold')+txt(28,52,'Wearable wiring prototype  /  ESP32-S3 Feather  /  revision 2',12)
for i,x in enumerate(xs,1):
    body+=txt(x-8,66,f'{i}  {names[i-1]}',12,'#162d3b','bold')
    body+=txt(x+33,174,f'RF{i}',11)+txt(x+33,189,'DIY flex',10)
    body+=txt(x-12,303,f'R{i}  10k',10)+txt(x+45,303,f'C{i}  100nF',10)
body+=txt(770,268,'3.3 V',11,red)+txt(805,379,'GND',11,black)
body+=txt(87,501,'BT1  BATTERY',11,'#162d3b','bold')+txt(240,518,'SW6  ON / OFF',10)
body+=txt(596,550,'U1  ESP32-S3',11,'#162d3b','bold')+txt(596,566,'FEATHER',11,'#162d3b','bold')
body+=txt(820,529,'U2  GY-521',11,'#162d3b','bold')+txt(820,547,'MPU6050',10)
body+=txt(747,592,'GY-521 supply:',10)+txt(747,608,'verify 3.3 V VIN',10)
body+=txt(181,727,'PALM CONTACT',11,'#162d3b','bold')
for i,x in enumerate([405,510,615,720,825],1):body+=txt(x-4,785,f'P{i} {names[i-1]}',10)
body+=txt(384,808,'Touch a fingertip pad to the palm fabric to close that input.',11)
body+=txt(28,828,'Red: 3.3 V or battery +    Black: GND    Colored: signals    Pads have one lead each.',11)
body+=txt(28,846,'Breadboard view is arranged. Schematic and PCB tabs are not a manufacturing design.',10)
legend=make_part('legend','Glove diagram annotations',970,855,body,[])
inst=place(legend,'NOTES',0,0)
for geo in inst.findall('views/*/geometry'):geo.set('z','-10')
sketch.save()
# Expose exact connections as a reviewable sidecar as well as the native model.
netmap={
 'controller':'Adafruit ESP32-S3 Feather #5323',
 'flex':dict(zip(names,['A5 / GPIO8','D5 / GPIO5','D6 / GPIO6','D9 / GPIO9','D10 / GPIO10'])),
 'contacts':dict(zip(names,['A0 / GPIO18','A1 / GPIO17','A2 / GPIO16','A3 / GPIO15','A4 / GPIO14'])),
 'imu':{'SDA':'GPIO3','SCL':'GPIO4','AD0':'GND','VCC':'3V3 (verify GY-521 variant)'},
 'power':'Battery to onboard JST; USB-C charging; slide switch pulls EN to GND for OFF',
}
(out/'pin-map.json').write_text(json.dumps(netmap,indent=2)+'\n')
print(f'Created {path}: {len(sketch.instances())} parts and wire segments')
