#!/usr/bin/env python3
"""One-time import of public Radosti Nails images into repository assets.

Every external <img> URL listed below is replaced with a same-repository file.
Failed source downloads are replaced with clearly marked local illustrated
fallbacks, never with photographs of another studio.
"""
from __future__ import annotations
import io
import re
from pathlib import Path

import requests
from PIL import Image, ImageOps, UnidentifiedImageError

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
HTML = ROOT / "index.html"
ASSETS.mkdir(exist_ok=True)

IMAGES = [
    ("logo", "https://avatars.mds.yandex.net/get-maps-adv-crm/11387709/2a0000018f5359fe2227a319bf39113eee79/landing_logo_x3", "Логотип Radosti Nails"),
    ("manicure", "https://avatars.mds.yandex.net/get-altay/2701558/2a000001740a80976a97292f79137322bfb7/XXXL", "Маникюр"),
    ("french", "https://avatars.mds.yandex.net/get-altay/2786941/2a000001740a80c2b7ee7a90ba955206eeb0/XXXL", "Френч"),
    ("pedicure", "https://avatars.mds.yandex.net/get-altay/11622009/2a0000018f5354f98ad31b9a0b030c5f1223/XXXL", "Педикюр"),
    ("studio", "https://avatars.mds.yandex.net/get-altay/10232404/2a0000018fe440b9ceecc3c54f8e5ca02575/XXXL", "Студия"),
    ("nude", "https://avatars.mds.yandex.net/get-altay/2419289/2a000001704525674108dca024ccd1960a12/XXXL", "Нюдовый маникюр"),
    ("pink", "https://avatars.mds.yandex.net/get-altay/2809978/2a000001740a80f9e475acb931b8b37c29db/XXXL", "Маникюр Radosti Nails"),
]
PEDICURE_FALLBACKS = [
    "https://avatars.mds.yandex.net/get-altay/4476499/2a00000182bc44f02e3f471586a362ad5b23/XXXL",
    "https://avatars.mds.yandex.net/get-altay/7883089/2a0000018f5354f8ec0a93a438dda9e95e50/XXXL",
    "https://avatars.mds.yandex.net/get-altay/754546/2a0000018f5354f9a7ceab95c487eabf4b2a/XXXL",
]

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36",
    "Referer": "https://yandex.ru/maps/",
    "Accept": "image/webp,image/png,image/jpeg,image/*;q=0.8",
})

def urls_for(url: str, name: str) -> list[str]:
    opts = [url]
    if "/get-altay/" in url:
        base = url.rsplit("/", 1)[0]
        opts += [f"{base}/{size}" for size in ("XXL_height", "L_height", "L", "M")]
    elif name == "logo":
        base = url.rsplit("/", 1)[0]
        opts += [f"{base}/{size}" for size in ("landing_logo_x2", "landing_logo")]
    if name == "pedicure":
        for fallback in PEDICURE_FALLBACKS:
            base = fallback.rsplit("/", 1)[0]
            opts += [fallback, base + "/XXL_height", base + "/L"]
    return list(dict.fromkeys(opts))

def try_image(urls: list[str]):
    for url in urls:
        try:
            r = session.get(url, timeout=18, allow_redirects=True)
            r.raise_for_status()
            if len(r.content) < 1400 or len(r.content) > 22_000_000:
                raise ValueError("unexpected image byte size")
            im = Image.open(io.BytesIO(r.content))
            im.load()
            if min(im.size) < 160:
                raise ValueError("image resolution too low")
            print(f"Downloaded: {url} ({len(r.content)} bytes; {im.size})")
            return ImageOps.exif_transpose(im)
        except Exception as e:
            print(f"  unavailable: {url} [{type(e).__name__}: {str(e)[:120]}]")
    return None

def safe_svg(title: str, name: str) -> str:
    import html
    t = html.escape(title)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="680" viewBox="0 0 900 680">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#f6e8e9"/><stop offset="1" stop-color="#d9b4c2"/></linearGradient></defs>
<rect width="900" height="680" fill="url(#g)"/>
<circle cx="700" cy="170" r="250" fill="#fffcf9" opacity=".4"/>
<path d="M235 420 Q450 230 665 420" fill="none" stroke="#ae8394" stroke-width="9" opacity=".5"/>
<text x="450" y="510" fill="#573747" text-anchor="middle" font-family="Georgia,serif" font-size="52">{t}</text>
<text x="450" y="568" fill="#765061" text-anchor="middle" font-family="Arial,sans-serif" letter-spacing="6" font-size="22">RADOSTI NAILS</text>
</svg>'''

html_text = HTML.read_text(encoding="utf-8")
missing = []
mapping = {}
for name, source, label in IMAGES:
    photo = try_image(urls_for(source, name))
    if photo is not None:
        photo.thumbnail((1500, 1250), Image.Resampling.LANCZOS)
        if photo.mode not in ("RGB", "RGBA"):
            photo = photo.convert("RGB")
        target = ASSETS / f"{name}.webp"
        photo.save(target, format="WEBP", quality=86, method=6)
        relative = f"assets/{name}.webp"
        print(f"Saved {relative} ({target.stat().st_size} bytes)")
    else:
        target = ASSETS / f"{name}-unavailable.svg"
        target.write_text(safe_svg(label, name), encoding="utf-8")
        relative = f"assets/{name}-unavailable.svg"
        missing.append(name)
        print(f"WARNING: {name} source unavailable; using labelled local fallback {relative}")
    mapping[source] = relative

for old, new in mapping.items():
    n = html_text.count(old)
    if n < 1:
        raise RuntimeError("Missing expected source in HTML: " + old)
    print(f"Replacing {n} HTML references to {old.rsplit('/',1)[-1]} with {new}")
    html_text = html_text.replace(old, new)

# Existing generated brow image and site-owned SVG fallbacks remain local.
external_img_srcs = re.findall(r'<img\b[^>]*\bsrc=["\x27](https?://[^"\x27]+)', html_text)
if external_img_srcs:
    raise RuntimeError("External image tags remain: " + repr(external_img_srcs))
HTML.write_text(html_text, encoding="utf-8")
print("Image import finished; converted:", len(IMAGES) - len(missing), "fallbacks:", missing)
