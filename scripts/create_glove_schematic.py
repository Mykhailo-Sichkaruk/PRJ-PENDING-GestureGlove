"""Generate the annotated revision-2 module wiring schematic (not a custom PCB).

Uses KiCad's standard symbol library and two project-local module symbols.
Refuses to overwrite a drawing unless --replace-generated is explicit.
"""
import argparse
import copy
import json
import math
import os
from pathlib import Path
import uuid
import sexpdata as sx

root = Path(__file__).resolve().parents[1]
out = root / 'examples/poc/electronics/glove'
name = 'gesture-glove-v2'
p = argparse.ArgumentParser()
p.add_argument('--replace-generated', action='store_true')
args = p.parse_args()
path = out / f'{name}.kicad_sch'
if path.exists() and not args.replace_generated:
    raise SystemExit(f'Refusing to overwrite {path}; use --replace-generated deliberately.')
out.mkdir(parents=True, exist_ok=True)
q = json.dumps
uid = lambda: str(uuid.uuid4())
sheet_id = uid()
objects, libraries, pins = [], {}, {}


def tag(x, name):
    return isinstance(x, list) and x and str(x[0]) == name


def child(x, name):
    return next((v for v in x if tag(v, name)), None)


def standard(lib_id):
    lib, symbol = lib_id.split(':')
    ast = sx.load(open(Path(os.environ['KICAD_SYMBOL_DIR']) / f'{lib}.kicad_sym'))
    s = copy.deepcopy(next(v for v in ast if tag(v, 'symbol') and v[1] == symbol))
    s[1] = lib_id
    return s


def module_symbol(lib_id, width, height, entries):
    short = lib_id.split(':')[1]
    result = f'''(symbol {q(lib_id)} (pin_names (offset 0.8)) (pin_numbers hide)
      (in_bom yes) (on_board yes)
      (property "Reference" "U" (at 0 {height/2+4} 0) (effects (font (size 1.27 1.27))))
      (property "Value" {q(short)} (at 0 {-height/2-4} 0) (effects (font (size 1.27 1.27))))
      (symbol "{short}_0_1" (rectangle (start {-width/2} {height/2}) (end {width/2} {-height/2})
        (stroke (width 0.254) (type default)) (fill (type background))))
      (symbol "{short}_1_1"'''
    for num, label, side, offset, kind in entries:
        x, angle = (-width/2-5.08, 0) if side == 'L' else (width/2+5.08, 180)
        result += f'''(pin {kind} line (at {x} {-offset} {angle}) (length 5.08)
            (name {q(label)} (effects (font (size 1.1 1.1))))
            (number {q(num)} (effects (font (size 1 1)))))'''
    return sx.loads(result + '))')


feather_pins = [
 ('A5','A5/GPIO8','L',-25.4,'input'), ('D5','D5/GPIO5','L',-20.32,'input'),
 ('D6','D6/GPIO6','L',-15.24,'input'), ('D9','D9/GPIO9','L',-10.16,'input'),
 ('D10','D10/GPIO10','L',-5.08,'input'),
 ('A0','A0/GPIO18','L',5.08,'input'), ('A1','A1/GPIO17','L',10.16,'input'),
 ('A2','A2/GPIO16','L',15.24,'input'), ('A3','A3/GPIO15','L',20.32,'input'),
 ('A4','A4/GPIO14','L',25.4,'input'),
 ('3V3','3V3','R',-25.4,'power_out'), ('GND','GND','R',-15.24,'power_in'),
 ('SCL','SCL/GPIO4','R',-5.08,'output'), ('SDA','SDA/GPIO3','R',5.08,'bidirectional'),
 ('EN','EN','R',15.24,'input'), ('BAT','BAT+','R',25.4,'power_in')]
libraries['Glove:Feather_ESP32_S3'] = module_symbol('Glove:Feather_ESP32_S3',45.72,66.04,feather_pins)
libraries['Glove:GY521'] = module_symbol('Glove:GY521',25.4,25.4,[
 ('1','VCC','L',-7.62,'power_in'),('2','GND','L',7.62,'power_in'),
 ('3','SCL','R',-7.62,'input'),('4','SDA','R',0,'bidirectional'),('7','AD0','R',7.62,'input')])


def comp(lib_id, ref, value, x, y, rot=0, fields=None, hide_value=False):
    s = libraries.setdefault(lib_id, standard(lib_id) if not lib_id.startswith('Glove:') else libraries[lib_id])
    sid = uid()
    props = ''
    fields = fields or [(x+4,y-2),(x+4,y+2)]
    for k, v, pos in zip(('Reference','Value'), (ref,value), fields):
        hidden = ref.startswith('#') and k == 'Reference' or hide_value and k == 'Value'
        props += f'(property {q(k)} {q(v)} (at {pos[0]} {pos[1]} 0) (effects (font (size 1.1 1.1)) (justify left){" (hide yes)" if hidden else ""}))'
    objects.append(f'''(symbol (lib_id {q(lib_id)}) (at {x} {y} {rot}) (unit 1)
      (in_bom {"no" if ref.startswith('#') else "yes"}) (on_board yes) (dnp no) (uuid {q(sid)}) {props}
      (instances (project {q(name)} (path "/{sheet_id}" (reference {q(ref)}) (unit 1)))))''')
    for unit in s:
        if tag(unit,'symbol'):
            for pin in unit:
                if not tag(pin,'pin'): continue
                a = child(pin,'at'); n = child(pin,'number')[1]
                r = math.radians(rot)
                pins[ref,str(n)] = (round(x + float(a[1])*math.cos(r) - float(a[2])*math.sin(r),5),
                                   round(y - float(a[1])*math.sin(r) - float(a[2])*math.cos(r),5))
    return ref


def wire(a,b):
    if a == b: return
    objects.append(f'(wire (pts (xy {a[0]} {a[1]}) (xy {b[0]} {b[1]})) (stroke (width 0) (type default)) (uuid "{uid()}"))')


def join(pos):
    objects.append(f'(junction (at {pos[0]} {pos[1]}) (diameter 0) (color 0 0 0 0) (uuid "{uid()}"))')


def label(text,pos,rot=0):
    objects.append(f'(label {q(text)} (at {pos[0]} {pos[1]} {rot}) (effects (font (size 1.1 1.1)) (justify left bottom)) (uuid "{uid()}"))')


def text(s,x,y,size=1.15,bold=False):
    objects.append(f'(text {q(s)} (at {x} {y} 0) (effects (font (size {size} {size}) {"(bold yes)" if bold else ""}) (justify left)) (uuid "{uid()}"))')


power_count=0

def power(kind,x,y):
    global power_count
    power_count += 1
    fields=[(x,y),(x-2,y-3 if kind=='+3V3' else y+4)]
    comp('power:'+kind, f'#PWR{power_count:03}',kind,x,y,fields=fields)


def stub(ref,pin,net,dx=-12.7):
    a=pins[ref,str(pin)]; b=(a[0]+dx,a[1]); wire(a,b)
    label(net,b,0 if dx < 0 else 180)


text('GESTURE GLOVE  /  module wiring',12,17,2.3,True)
text('Revision 2  |  ESP32-S3 Feather #5323  |  conceptual prototype, no custom PCB',12,22)
text('1  FINGER BEND SENSORS',12,26,1.7,True)
fingers=['Thumb','Index','Middle','Ring','Little']
flex_nets=['FLEX_T','FLEX_I','FLEX_M','FLEX_R','FLEX_L']
contact_nets=['TOUCH_T','TOUCH_I','TOUCH_M','TOUCH_R','TOUCH_L']
for i,finger in enumerate(fingers):
    x=22.86+i*25.4
    text(finger,x-4,32,1.2,True)
    comp('Device:R_Variable',f'RF{i+1}','DIY flex',x,48.26,fields=[(x+4,46),(x+4,50)])
    power('+3V3',x,38.1); wire((x,38.1),pins[f'RF{i+1}','1'])
    node=(x,60.96)
    wire(pins[f'RF{i+1}','2'],node); join(node)
    label(flex_nets[i],node)
    comp('Device:R',f'R{i+1}','10k',x,76.2)
    comp('Device:C',f'C{i+1}','100n',x+12.7,76.2)
    wire(node,pins[f'R{i+1}','1'])
    wire(node,(x+12.7,node[1])); wire((x+12.7,node[1]),pins[f'C{i+1}','1'])
    ground=(x,88.9)
    wire(pins[f'R{i+1}','2'],ground)
    wire(pins[f'C{i+1}','2'],(x+12.7,88.9)); wire((x+12.7,88.9),ground)
    join(ground); power('GND',*ground)
text('RF1-RF5 = handmade resistive strips. Values require calibration.',12,103,1.05)

text('2  CONTROLLER',159,26,1.7,True)
comp('Glove:Feather_ESP32_S3','U1','Feather ESP32-S3',219.71,66.04,
     fields=[(238,30),(203,102)])
for pin,net in zip(['A5','D5','D6','D9','D10','A0','A1','A2','A3','A4'], flex_nets+contact_nets):
    stub('U1',pin,net,-22.86)
for pin,net in [('3V3','+3V3'),('GND','GND'),('SCL','I2C_SCL'),('SDA','I2C_SDA'),('EN','EN'),('BAT','VBAT')]:
    stub('U1',pin,net,20.32)
text('Board pin labels shown; unused headers omitted.',159,107,1.05)

text('3  FINGERTIP / PALM CONTACTS',12,115,1.7,True)
for i,finger in enumerate(fingers):
    x=25.4+i*25.4
    text(finger,x-5,123,1.15)
    comp('Switch:SW_SPST',f'SW{i+1}','Pad contact',x,137.16,
         fields=[(x-3,129),(x-3,146)],hide_value=True)
    a=pins[f'SW{i+1}','1']; b=pins[f'SW{i+1}','2']
    wire(a,(a[0]-2.54,a[1])); wire((a[0]-2.54,a[1]),(a[0]-2.54,132.08))
    label(contact_nets[i],(a[0]-2.54,132.08))
    wire(b,(b[0],152.4))
    if i: wire((25.4+(i-1)*25.4+5.08,152.4),(b[0],152.4))
    if i not in (0,4): join((b[0],152.4))
power('GND',pins['SW5','2'][0],152.4)
text('Switch symbols represent pads touching the common palm fabric.',12,164,1.05)
text('Enable INPUT_PULLUP on A0-A4. Touch = LOW. No physical buttons.',12,169,1.05)

text('4  MOTION / I2C',158,117,1.6,True)
comp('Glove:GY521','U2','GY-521 / MPU6050',177.8,135.89,
     fields=[(190,123),(165,153)])
for pin,net,dx in [('1','+3V3',-5.08),('2','GND',-5.08),('3','I2C_SCL',8.89),('4','I2C_SDA',8.89),('7','GND',8.89)]:
    stub('U2',pin,net,dx)
text('AD0 to GND: address 0x68.',156,158,1)
text('Check chosen GY-521 accepts 3.3V.',156,163,1)

text('5  POWER',231,117,1.6,True)
comp('Device:Battery_Cell','BT1','LiPo 3.7V',237.49,137.16,fields=[(242,134),(242,138)])
a=pins['BT1','1']; wire(a,(a[0],125.73)); label('VBAT',(a[0],125.73))
b=pins['BT1','2']; wire(b,(b[0],144.78)); power('GND',b[0],144.78)
comp('power:PWR_FLAG','#FLG01','PWR_FLAG',237.49,125.73,hide_value=True)
comp('power:PWR_FLAG','#FLG02','PWR_FLAG',237.49,144.78,hide_value=True)
comp('Switch:SW_SPST','SW6','Disable regulator',267.97,148.59,fields=[(263,143),(254,159)])
stub('SW6','1','EN',-5.08)
a=pins['SW6','2']; wire(a,(a[0],152.4)); power('GND',a[0],152.4)
text('Battery plugs into onboard JST.',230,123,1)
text('USB-C powers / charges Feather.',230,164,1)


text('READING THE DRAWING',12,180,1.35,True)
text('Green lines are wires. Dots join wires. Identical labels are electrically connected.',12,185,1.05)
text('3V3 and GND are shared. Five flex readings + five contact states + one IMU.',12,189,1.05)
text('Module wiring only. Verify DIY sensor range, battery polarity and GY-521 variant before assembly.',12,194,1.0)

custom=[v for k,v in libraries.items() if k.startswith('Glove:')]
libcopy=[]
for s in custom:
    s=copy.deepcopy(s); s[1]=s[1].split(':')[1]; libcopy.append(sx.dumps(s))
(out/'Glove.kicad_sym').write_text('(kicad_symbol_lib (version 20231120) (generator "glove")\n'+'\n'.join(libcopy)+')\n')
(out/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "Glove") (type "KiCad") (uri "${KIPRJMOD}/Glove.kicad_sym") (options "") (descr "Glove module interfaces")))\n')
header=f'''(kicad_sch (version 20250114) (generator "glove") (uuid "{sheet_id}") (paper "A4")
  (title_block (title "Gesture glove - module wiring") (rev "0.2") (company "SMVIT"))
  (lib_symbols {' '.join(sx.dumps(v) for v in libraries.values())})'''
path.write_text(header+'\n'+'\n'.join(objects)+'\n)\n')
project=out/f'{name}.kicad_pro'
if not project.exists(): project.write_text('{}\n')
print(f'Created {path}')
