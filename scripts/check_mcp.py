"""Exercise the same stdio command configured for Codex, optionally building the PoC."""
import argparse
import asyncio
import base64
import json
from datetime import timedelta
from pathlib import Path
import tomllib

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main(build_poc, capture):
    root = Path(__file__).resolve().parents[1]
    config = tomllib.loads((root / ".codex/config.toml").read_text())["mcp_servers"]["freecad"]
    params = StdioServerParameters(command=config["command"], args=config["args"], cwd=Path.cwd())
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer, read_timeout_seconds=timedelta(seconds=120)) as session:
            initialized = await session.initialize()
            tools = await session.list_tools()
            print(f"MCP initialized: {initialized.serverInfo.name}; {len(tools.tools)} tools", flush=True)

            async def call(name, arguments=None):
                response = await session.call_tool(name, arguments or {})
                messages = [part.text for part in response.content if part.type == "text"]
                for message in messages:
                    print(f"{name}: {message}", flush=True)
                    if message.startswith(("Failed to ", "Error ", "Error:")):
                        raise RuntimeError(message)
                if response.isError:
                    raise RuntimeError(f"{name} failed")
                # The upstream server also reports failures in text JSON payloads.
                for message in messages:
                    try:
                        payload = json.loads(message)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(payload, dict) and payload.get("success") is False:
                        raise RuntimeError(f"{name} failed: {payload}")
                return response

            def json_payload(response):
                for part in response.content:
                    if part.type == "text":
                        try:
                            return json.loads(part.text)
                        except json.JSONDecodeError:
                            pass
                raise RuntimeError("Expected a JSON tool response")

            status = json_payload(await call("get_rpc_status"))
            if not status.get("success") or status.get("gui_dispatch", {}).get("state") != "healthy":
                raise RuntimeError(f"FreeCAD is not healthy: {status}")
            if not (build_poc or capture):
                await call("list_documents")
                return

            if build_poc:
                code = "project_root = " + repr(str(root)) + "\n"
                code += (root / "examples/poc/cad/glove_poc.py").read_text()
                await call("execute_code", {"code": code, "include_screenshot": False})
            # FreeCAD derives a new internal document name from the filename on
            # reopen, so discover it rather than assuming it remains GlovePoC.
            documents = json_payload(await call("list_documents"))
            matches = []
            for document_name in documents:
                board = json_payload(await call("get_object", {
                    "doc_name": document_name, "obj_name": "ESP32Board", "include_screenshot": False,
                }))
                if board is not None:
                    matches.append(document_name)
            if len(matches) != 1:
                raise RuntimeError("Open exactly one glove PoC document before capturing")
            await call("execute_code", {
                "code": (
                    f"App.setActiveDocument({matches[0]!r})\n"
                    "doc = App.ActiveDocument\n"
                    "assert len(doc.FlexSensors.Group) == 5\n"
                    "assert len(doc.Contacts.Group) == 6\n"
                    "assert abs(doc.ESP32Board.Length.Value - 50.8) < 0.001\n"
                    "assert abs(doc.ESP32Board.Width.Value - 22.86) < 0.001\n"
                    "assert all(o.Shape.isValid() for o in doc.Objects if hasattr(o, 'Shape'))\n"
                    "print('Verified board dimensions, five flex strips, five fingertip pads, palm contact, and valid geometry.')"
                ),
                "include_screenshot": False,
            })
            for view, filename in [("Isometric", "glove-poc.png"), ("Bottom", "glove-poc-palm.png")]:
                result = await call("get_view", {"view_name": view, "width": 1400, "height": 1100})
                images = [part for part in result.content if part.type == "image"]
                if not images:
                    raise RuntimeError(f"No screenshot returned for {view}")
                path = root / "examples/poc/cad" / filename
                path.write_bytes(base64.b64decode(images[0].data))
                print(f"Saved {path}")
            await call("execute_code", {
                "code": "Gui.activeDocument().activeView().viewAxonometric(); Gui.activeDocument().activeView().fitAll(); App.ActiveDocument.save()",
                "include_screenshot": False,
            })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-poc", action="store_true", help="Create and save the glove placement model")
    parser.add_argument("--capture", action="store_true", help="Capture views of the open GlovePoC document")
    args = parser.parse_args()
    asyncio.run(main(args.build_poc, args.capture))
