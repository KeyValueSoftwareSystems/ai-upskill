"""Regenerate assets/tidal_photo.png (a stand-in product photo)."""
from pathlib import Path

from PIL import Image, ImageDraw

out = Path(__file__).resolve().parents[1] / "assets" / "tidal_photo.png"
img = Image.new("RGB", (800, 800), (239, 230, 216))
d = ImageDraw.Draw(img)
d.rounded_rectangle([330, 150, 470, 650], radius=40, fill=(111, 169, 160))
d.rounded_rectangle([345, 110, 455, 170], radius=14, fill=(31, 58, 95))
d.text((20, 770), "Harbor Flask Trail 750, Tidal (stand-in product photo)", fill=(31, 58, 95))
img.save(out)
print(out)
