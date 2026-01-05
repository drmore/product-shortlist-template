from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qsl, urlunparse

import requests

CONFIG_FILE = "site_config.json"

ASSETS_DIR = Path("assets")
IMG_DIR = ASSETS_DIR / "img"
PLACEHOLDER = "assets/placeholder.svg"

# If CACHE_IMAGES=1, we will download remote images during the GitHub Action build
CACHE_IMAGES = os.environ.get("CACHE_IMAGES", "0").strip() in {"1", "true", "TRUE", "yes", "YES"}


def esc(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;")
             .replace("'", "&#39;"))


def with_affiliate_tag(url: str, tag: str) -> str:
    """Ensure the Amazon URL contains ?tag=... while keeping existing params."""
    u = urlparse(url)
    q = dict(parse_qsl(u.query, keep_blank_values=True))
    q["tag"] = tag
    new_query = urlencode(q, doseq=True)
    return urlunparse((u.scheme, u.netloc, u.path, u.params, new_query, u.fragment))


def load_config(path: str = CONFIG_FILE) -> dict:
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    # required keys
    cfg.setdefault("title", "Product shortlist")
    cfg.setdefault("description", "A simple shortlist of products.")
    cfg.setdefault("intro_paragraphs", [])
    cfg.setdefault("meta_note", "")
    cfg.setdefault("products", [])
    return cfg


def normalize_products(items: list[dict]) -> list[dict]:
    out: list[dict] = []
    seen = set()
    for it in items:
        asin = (it.get("amazon_asin") or "").strip()
        if not asin or asin in seen:
            continue

        best_for = it.get("best_for") or []
        if isinstance(best_for, str):
            best_for = [best_for]
        if not isinstance(best_for, list):
            best_for = []

        out.append({
            "asin": asin,  # internal only
            "name": (it.get("product_name") or "").strip() or "Product",
            "description": (it.get("description") or "").strip(),
            "image_url": (it.get("image_url") or "").strip(),
            "amazon_url": (it.get("amazon_url") or f"https://www.amazon.com/dp/{asin}").strip(),
            "best_for": [str(x).strip() for x in best_for if str(x).strip()][:2],
        })
        seen.add(asin)
    return out


def _safe_ext(url: str, content_type: str | None) -> str:
    if content_type:
        ct = content_type.split(";")[0].strip().lower()
        if ct == "image/png":
            return ".png"
        if ct in {"image/jpeg", "image/jpg"}:
            return ".jpg"
        if ct == "image/webp":
            return ".webp"
        if ct == "image/avif":
            return ".avif"
        if ct == "image/gif":
            return ".gif"
    m = re.search(r"\.(png|jpe?g|webp|avif|gif)(?:\?|$)", url.lower())
    if m:
        ext = m.group(1).replace("jpeg", "jpg")
        return "." + ext
    return ".img"


def cache_image(asin: str, remote_url: str) -> str:
    """Download remote image to assets/img and return local path. If fails, return remote_url."""
    if not remote_url:
        return PLACEHOLDER

    IMG_DIR.mkdir(parents=True, exist_ok=True)

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; static-site-builder/1.0)",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }

    try:
        r = requests.get(remote_url, headers=headers, timeout=20, allow_redirects=True)
        if r.status_code != 200 or not r.content:
            return remote_url
        ext = _safe_ext(remote_url, r.headers.get("Content-Type"))
        local = IMG_DIR / f"{asin}{ext}"
        local.write_bytes(r.content)
        return str(local).replace("\\", "/")
    except Exception:
        return remote_url


HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <meta name="description" content="{desc}">
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; margin: 0; background:#fafafa; color:#111; }}
    header, main, footer {{ max-width: 1060px; margin: 0 auto; padding: 18px 16px; }}
    h1 {{ font-size: 28px; margin: 10px 0 8px; }}
    p {{ margin: 8px 0; line-height: 1.5; }}
    .meta {{ color:#444; font-size: 14px; }}
    .grid {{ display:grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }}
    .card {{ background:white; border-radius: 14px; overflow:hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.06); display:flex; flex-direction:column; }}
    .img {{ background:#f3f4f6; aspect-ratio: 4 / 3; overflow:hidden; }}
    .img img {{ width:100%; height:100%; object-fit:contain; display:block; background:#fff; }}
    .content {{ padding: 12px 14px 14px; display:flex; flex-direction:column; gap:8px; flex:1; }}
    .name {{ font-weight: 800; font-size: 16px; margin: 0; }}
    .desc {{ color:#333; font-size: 14px; margin:0; }}
    .tags {{ display:flex; flex-wrap:wrap; gap:6px; margin:2px 0 0; }}
    .tag {{ font-size: 12px; padding: 4px 8px; border: 1px solid #e5e7eb; background:#f9fafb; border-radius: 999px; color:#374151; }}
    .actions {{ margin-top:auto; display:flex; gap:10px; align-items:center; padding-top: 4px; }}
    .btn {{ display:inline-block; padding: 10px 12px; border:1px solid #ddd; border-radius: 12px; background:#fff; font-weight: 700; text-align:center; }}
    .btn:hover {{ background:#f7f7f7; text-decoration:none; }}
    a {{ color:#0b57d0; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    @media (max-width: 980px) {{
      .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
    @media (max-width: 640px) {{
      .grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>{h1}</h1>
    {intro}
    <p class="meta">Last updated: {updated}</p>
  </header>

  <main>
    <div class="grid">
      {cards}
    </div>
  </main>

  <footer>
    <p><strong>Affiliate disclosure:</strong> As an Amazon Associate, I earn from qualifying purchases.</p>
    <p><a href="privacy.html">Privacy</a> · <a href="disclosure.html">Disclosure</a></p>
  </footer>
</body>
</html>
"""


def tags_html(tags: list[str]) -> str:
    if not tags:
        return ""
    pills = "".join(f'<span class="tag">{esc(t)}</span>' for t in tags[:2])
    return f'<div class="tags">{pills}</div>'


def build_intro(intro_paragraphs: list[str], meta_note: str) -> str:
    parts = []
    for p in intro_paragraphs:
        p = str(p).strip()
        if p:
            parts.append(f"<p>{esc(p)}</p>")
    if meta_note and str(meta_note).strip():
        parts.append(f'<p class="meta">{esc(str(meta_note).strip())}</p>')
    return "\n".join(parts)


def card(p: dict, partner_tag: str) -> str:
    url = with_affiliate_tag(p["amazon_url"], partner_tag)

    src = p.get("image_url") or ""
    if CACHE_IMAGES:
        src = cache_image(p["asin"], src)

    if not src:
        src = PLACEHOLDER

    img_html = (
        f'<img src="{esc(src)}" alt="{esc(p["name"])}" loading="lazy" '
        f'referrerpolicy="no-referrer" onerror="this.onerror=null;this.src=\'{PLACEHOLDER}\';">'
    )

    return (
        '<div class="card">'
        f'  <div class="img">{img_html}</div>'
        '  <div class="content">'
        f'    <p class="name">{esc(p["name"])}</p>'
        f'    {tags_html(p.get("best_for") or [])}'
        f'    <p class="desc">{esc(p.get("description") or "")}</p>'
        '    <div class="actions">'
        f'      <a class="btn" href="{esc(url)}" rel="nofollow sponsored">Check price on Amazon</a>'
        '    </div>'
        '  </div>'
        '</div>'
    )


def main() -> None:
    partner_tag = os.environ.get("AMZ_PARTNER_TAG", "").strip()
    if not partner_tag:
        raise SystemExit("Missing AMZ_PARTNER_TAG (set as GitHub Actions secret).")

    cfg = load_config()
    products = normalize_products(cfg.get("products", []))

    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    cards = "\n".join(card(p, partner_tag) for p in products)
    intro = build_intro(cfg.get("intro_paragraphs", []), cfg.get("meta_note", ""))

    title = str(cfg.get("title") or "Product shortlist").strip()
    desc = str(cfg.get("description") or "").strip()

    html = HTML.format(
        title=esc(title),
        desc=esc(desc),
        h1=esc(title),
        intro=intro,
        updated=updated,
        cards=cards,
    )
    Path("index.html").write_text(html, encoding="utf-8")
    Path("products.json").write_text(json.dumps({"products": products, "updated": updated, "title": title}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
