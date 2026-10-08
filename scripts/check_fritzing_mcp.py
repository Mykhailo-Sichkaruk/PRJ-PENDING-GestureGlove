"""Exercise the configured Fritzing stdio MCP using an isolated sketch copy."""
import argparse
import asyncio
from datetime import timedelta
import json
from pathlib import Path
import shutil
import tomllib
import zipfile
import xml.etree.ElementTree as E
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

parser=argparse.ArgumentParser()
parser.add_argument('--open-gui',action='store_true')
args=parser.parse_args()

async def main():
    root=Path(__file__).resolve().parents[1]
    cfg=tomllib.loads((root/'.codex/config.toml').read_text())['mcp_servers']['fritzing']
    dest=root/'.local/fritzing/mcp-check';dest.mkdir(parents=True,exist_ok=True)
    f=dest/'check.fzz'
    shutil.copy2(root/'examples/poc/electronics/fritzing/gesture-glove.fzz',f)
    def geometry():
        with zipfile.ZipFile(f) as z: r=E.fromstring(z.read(next(n for n in z.namelist() if n.endswith('.fz'))))
        part=next(i for i in r.findall('instances/instance') if i.findtext('title')=='P1')
        return part.find('views/breadboardView/geometry').attrib
    params=StdioServerParameters(command=cfg['command'],args=cfg['args'],cwd=Path.cwd())
    async with stdio_client(params) as (rd,wr):
        async with ClientSession(rd,wr,read_timeout_seconds=timedelta(seconds=300)) as session:
            await session.initialize();ts=await session.list_tools()
            print(f'MCP initialized: {len(ts.tools)} tools',flush=True)
            async def call(name,args):
                r=await session.call_tool(name,args)
                assert not r.isError,r
                t='\n'.join(b.text for b in r.content if b.type=='text')
                print(name,t[:400],flush=True)
                return t
            await call('fritzing_search_parts',{'query':'MPU6050','limit':2})
            await call('fritzing_part_connectors',{'module_id':'MPU6050_GY521_782354e339f672575bb20992ece4ab1b_9'})
            # Exercise new sketch, place, wire and remove on a separate fixture.
            fixture=dest/'wire-check.fzz'
            await call('fritzing_new_sketch',{'path':str(fixture),'force':True})
            for ref,x in [('T1',20),('T2',160)]:
                await call('fritzing_place_part',{'file':str(fixture),'module_id':'smvit_resistor10k_v1','ref':ref,'x':x,'y':40,'view':'bb'})
            await call('fritzing_wire',{'file':str(fixture),'ref_a':'T1.connector1','ref_b':'T2.connector0','view':'bb'})
            with zipfile.ZipFile(fixture) as z:
                r=E.fromstring(z.read(next(n for n in z.namelist() if n.endswith('.fz'))))
            wire=next(i for i in r.findall('instances/instance') if i.get('moduleIdRef')=='WireModuleID')
            geo=wire.find('views/breadboardView/geometry')
            assert geo.get('wireFlags')=='64'
            assert abs(float(geo.get('x'))-66)<0.1 and abs(float(geo.get('x2'))-96)<0.1, geo.attrib
            await call('fritzing_remove_part',{'file':str(fixture),'ref':'T2'})
            await call('fritzing_check',{'file':str(fixture)})
            before=dict(geometry())
            await call('fritzing_move_part',{'file':str(f),'ref':'P1','x':float(before['x'])+10,'y':float(before['y'])})
            assert float(geometry()['x'])==float(before['x'])+10
            await call('fritzing_move_part',{'file':str(f),'ref':'P1','x':float(before['x']),'y':float(before['y'])})
            await call('fritzing_check',{'file':str(f)})
            await call('fritzing_render',{'target':str(f),'view':'bb','png':True})
            assert (dest/'check_breadboard.svg').stat().st_size>1000
            print('PASS: search, connectors, create/place/wire/remove, move/read-back/restore, validate and native rendering',flush=True)
            if args.open_gui:
                await call('fritzing_open_gui',{'files':[str(root/'examples/poc/electronics/fritzing/gesture-glove.fzz')]})

asyncio.run(main())
