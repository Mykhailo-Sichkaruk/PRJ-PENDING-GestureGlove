"""Initialize configured CAD servers from root and a nested cwd; no GUI required."""
import asyncio
from datetime import timedelta
from pathlib import Path
import tomllib
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    root = Path(__file__).resolve().parents[1]
    servers = tomllib.loads((root / '.codex/config.toml').read_text())['mcp_servers']
    for cwd in [root, root / 'hardware']:
        for name, cfg in servers.items():
            if not cfg.get('enabled', True):
                continue
            params = StdioServerParameters(command=cfg['command'], args=cfg['args'], cwd=cwd)
            async with stdio_client(params) as (r, w):
                async with ClientSession(r, w, read_timeout_seconds=timedelta(seconds=120)) as session:
                    info = await session.initialize()
                    result = await session.list_tools()
                    assert result.tools, (name, 'empty tool list')
                    print(f'{cwd.relative_to(root)}: {name}: {info.serverInfo.name}, {len(result.tools)} tools', flush=True)

if __name__ == '__main__':
    asyncio.run(main())
