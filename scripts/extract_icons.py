import re
from pathlib import Path

storage_path = Path(r"C:\Users\Administrator\Documents\Zapret-Zen\src\zapret_zen\services\storage.py")
content = storage_path.read_text(encoding="utf-8")

start = content.find('icon_map: dict[str, str] = {')
end = content.find("}", content.find('"window_close.svg"', start))
icon_block = content[start:end+1]

icons = {}
for match in re.finditer(r'"([^"]+\.svg)": \'(<svg[^\']+)\'', icon_block):
    icons[match.group(1)] = match.group(2)

icons_dir = Path(r"C:\Users\Administrator\Documents\Zapret-Zen\src\zapret_zen\assets\icons")
icons_dir.mkdir(parents=True, exist_ok=True)

for filename, svg_content in sorted(icons.items()):
    (icons_dir / filename).write_text(svg_content, encoding="utf-8")
    print(f"  {filename} ({len(svg_content)} bytes)")

print(f"Extracted {len(icons)} SVG icons")
