from pathlib import Path
import sys
data = Path(sys.argv[1] if len(sys.argv) > 1 else "replay_data.json").read_text(encoding="utf-8")
assert "</script" not in data
html = Path("replay_template.html").read_text(encoding="utf-8").replace("/*DATA*/", data)
Path("rtis_replay.html").write_text(html, encoding="utf-8")
print(f"rtis_replay.html {len(html)/1e6:.2f} MB")
