"""Check the configured MCP against the open, disposable integration-test board."""
import asyncio
import json
import tomllib
from datetime import timedelta
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    root = Path(__file__).resolve().parents[1]
    config = tomllib.loads((root / ".codex/config.toml").read_text())["mcp_servers"]["kicad"]
    params = StdioServerParameters(command=config["command"], args=config["args"], cwd=Path.cwd())
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer, read_timeout_seconds=timedelta(seconds=60)) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(f"MCP initialized: {len(tools.tools)} tools", flush=True)

            async def call(name, args=None):
                response = await session.call_tool(name, args or {})
                assert not response.isError, response
                payload = json.loads(next(p.text for p in response.content if p.type == "text"))
                print(name, json.dumps(payload), flush=True)
                assert not payload.get("error"), payload
                assert payload.get("success") is not False, payload
                return payload

            connection = await call("connect_to_kicad")
            assert connection.get("connected"), connection
            # Never run the edit test against a user's actual design.
            assert "integration-test.kicad_pcb" in connection["message"], connection
            await call("get_kicad_version")
            await call("get_layers")
            before = await call("get_tracks")
            transaction = await call("begin_commit")
            assert transaction.get("commit_id"), transaction
            created = None
            committed = False
            try:
                created = await call("place_track", {
                    "start_x_mm": 110, "start_y_mm": 115,
                    "end_x_mm": 130, "end_y_mm": 115,
                    "width_mm": 0.5, "layer": "F.Cu", "net_code": 0,
                })
                await call("end_commit", {"commit_id": transaction["commit_id"], "action": "commit",
                                          "message": "MCP integration check"})
                committed = True
                tracks = await call("get_tracks")
                assert tracks["count"] == before["count"] + 1
                assert any(t["id"] == created["track_id"] for t in tracks["tracks"])
            finally:
                if committed and created:
                    await call("delete_item", {"item_id": created["track_id"]})
                else:
                    await call("end_commit", {"commit_id": transaction["commit_id"], "action": "drop"})
            after = await call("get_tracks")
            assert after == before, "Cleanup did not restore the original tracks"
            print("Verified live read, track creation, and removal.", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
