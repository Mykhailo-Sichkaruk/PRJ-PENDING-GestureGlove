"""Adapt upstream's developer-machine paths to the project-local Nix launchers."""
from pathlib import Path
import sys

root = Path(sys.argv[1])
for name in ("partsdb.py", "partgen.py"):
    path = root / "fzkit" / name
    text = path.read_text()
    text = text.replace('os.path.expanduser(\n    "~/.local/share/Fritzing/Fritzing/local_parts")',
                        'os.environ["FRITZING_LOCAL_PARTS"]')
    path.write_text(text)

path = root / "fzkit" / "cli.py"
text = path.read_text().replace('LAUNCHER = os.path.join(_FZ_BASE, "run-fritzing.sh")',
                               'LAUNCHER = os.environ["FRITZING_APP"]')
# Do not keep the MCP subprocess pipes open for the lifetime of a GUI window.
text = text.replace('subprocess.Popen([LAUNCHER] + [os.path.abspath(f) for f in args.files])',
                    'subprocess.Popen([LAUNCHER] + [os.path.abspath(f) for f in args.files], '
                    'stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, '
                    'stderr=subprocess.DEVNULL, start_new_session=True)')
path.write_text(text)
path = root / "fzkit" / "render.py"
text = path.read_text()
start = text.index('    env["LD_LIBRARY_PATH"]')
end = text.index('    return env', start)
text = text[:start] + '    env["QT_QPA_PLATFORM"] = "offscreen"\n' + text[end:]
path.write_text(text)
# Fix native wire terminal placement and maintain connections after edits.
path = root / 'fzkit' / 'cli.py'
text = path.read_text().replace('if __name__ == "__main__":',
    'from .smvit import cmd_wire, cmd_move, cmd_remove\n\nif __name__ == "__main__":')
path.write_text(text)
# 128 means schematic trace, not breadboard wire; breadboard uses NormalFlag=64.
path = root / 'fzkit' / 'model.py'
text = path.read_text().replace('geo.set("wireFlags", "128")',
    'geo.set("wireFlags", str({"bb": 64, "sc": 128, "pcb": 4}[v]))')
path.write_text(text)
# Preserve custom parts when creating sketches through MCP, not just generators.
path = root / 'fzkit' / 'cli.py'
text = path.read_text().replace('from .smvit import cmd_wire, cmd_move, cmd_remove',
    'from .smvit import cmd_wire, cmd_move, cmd_remove, embed_local')
text = text.replace('props=props)\n    sketch.save()', 'props=props)\n    embed_local(sketch, inst)\n    sketch.save()')
path.write_text(text)
# Native -svg scans a directory. A request for one file must not render other
# sketches in that directory or hit a modal dialog caused by an unrelated file.
path = root / 'fzkit' / 'render.py'
text = path.read_text().replace('def render(target:', 'def _render_directory(target:')
text += '''\n\ndef render(target, png=False, density=150, view="all"):
    import tempfile, shutil, io, contextlib
    target = os.path.abspath(target)
    if not os.path.isfile(target):
        return _render_directory(target, png, density, view)
    with tempfile.TemporaryDirectory(prefix="smvit-fritzing-render-") as scratch:
        shutil.copy2(target, scratch)
        with contextlib.redirect_stdout(io.StringIO()) as log:
            result = _render_directory(scratch, png, density, view)
        if result:
            print(log.getvalue())
            return result
        from .model import resolve_view_token
        for token in resolve_view_token(view):
            for extension in (("svg", "png") if png else ("svg",)):
                name = os.path.splitext(os.path.basename(target))[0] + "_" + VIEW_SUFFIX[token] + "." + extension
                src = os.path.join(scratch, name)
                if os.path.exists(src):
                    dst = os.path.join(os.path.dirname(target), name)
                    shutil.copy2(src, dst)
                    print(extension + "  " + dst)
    return 0
'''
path.write_text(text)
