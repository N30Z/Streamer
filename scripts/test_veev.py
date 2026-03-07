"""
veev.to extractor probe.

Usage:
    python scripts/test_veev.py [embed_url]

Default test URL:
    https://veev.to/e/27kYAOe9AbsIceAnuwJ36B2xKnlZdIfwhFzjjJc?rback=1

Steps performed:
  1  Page probe      – fetch the embed page, show status / redirect chain
  2  Extractor       – run get_direct_link_from_veev() and show result
  2b Diagnostics     – if extraction fails, dump page internals to aid debugging
  3  CDN reachability – HEAD + first-256-byte peek of the direct URL
  4  Download        – HLS segment download or direct MP4 download
"""

import re
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]

import tempfile
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urljoin

import requests

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logging.getLogger("urllib3").setLevel(logging.WARNING)

sys.path.insert(0, "src")

TEST_URL = "https://veev.to/e/27kYAOe9AbsIceAnuwJ36B2xKnlZdIfwhFzjjJc?rback=1"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

BROWSER_HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "iframe",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "cross-site",
}

OK   = "✓"
ERR  = "✗"
SKIP = "·"
W    = 68


# ── Formatting ────────────────────────────────────────────────────────────────

def header(title: str) -> None:
    print(f"\n{'─' * W}")
    print(f"  {title}")
    print(f"{'─' * W}")


def row(label: str, value: str, icon: str = " ") -> None:
    print(f"  {icon} {label:<22} {value}")


def ok(label: str, value: str = "")   -> None: row(label, value, OK)
def fail(label: str, value: str = "") -> None: row(label, value, ERR)
def info(label: str, value: str = "") -> None: row(label, value, " ")


# ── Step 1: Page probe ────────────────────────────────────────────────────────

def _make_session(scraper: bool = False):
    """Return a requests.Session (or cloudscraper session if scraper=True)."""
    if scraper:
        try:
            import cloudscraper  # type: ignore
            s = cloudscraper.create_scraper(
                browser={"browser": "chrome", "platform": "windows", "mobile": False}
            )
            return s, True
        except ImportError:
            pass
    s = requests.Session()
    s.headers.update(BROWSER_HEADERS)
    return s, False


def _detect_bot_wall(html: str) -> str | None:
    """Return a short description if the HTML looks like a bot-protection page."""
    l = html.lower()
    if "just a moment" in l and "cloudflare" in l:
        return "Cloudflare JS challenge"
    if "enable javascript" in l and len(html) < 10_000:
        return "JS-required page (bot wall)"
    if "cf-browser-verification" in l or "_cf_chl" in l:
        return "Cloudflare browser verification"
    if "please wait" in l and len(html) < 8_000:
        return "Generic wait/challenge page"
    if "<script" not in l and "<iframe" not in l and len(html) > 5_000:
        return "No scripts/iframes — likely SSR challenge or captcha"
    return None


def step1_page_probe(url: str):
    header("1 · Page probe")
    info("URL", url)

    # Try plain requests first, then cloudscraper as fallback
    session, used_scraper = _make_session(scraper=False)
    r = session.get(url, timeout=20, allow_redirects=True)

    row("Status", str(r.status_code), OK if r.status_code == 200 else ERR)
    info("Content-Type", r.headers.get("Content-Type", "?"))
    info("Body size", f"{len(r.text):,} chars")
    info("Via", "cloudscraper" if used_scraper else "requests")

    if r.history:
        for h in r.history:
            info("  redirect →", f"HTTP {h.status_code}  {h.headers.get('Location', '?')}")
    else:
        info("Redirects", "none")

    # ── Bot-wall detection ────────────────────────────────────────────────
    wall = _detect_bot_wall(r.text)
    if wall:
        row("Bot protection", wall, ERR)
        print()
        info("Trying cloudscraper …", "")
        cs, ok_cs = _make_session(scraper=True)
        if ok_cs:
            try:
                r2 = cs.get(url, timeout=25, allow_redirects=True)
                wall2 = _detect_bot_wall(r2.text)
                if not wall2:
                    ok("cloudscraper", f"bypassed  ({len(r2.text):,} chars)")
                    session, r = cs, r2
                else:
                    row("cloudscraper", f"still blocked: {wall2}", ERR)
            except Exception as exc:
                fail("cloudscraper", str(exc)[:80])
        else:
            row("cloudscraper", "not installed  (pip install cloudscraper)", SKIP)
    else:
        ok("Bot protection", "none detected")

    # ── HTML preview (first 600 chars) ────────────────────────────────────
    print()
    info("HTML preview", "")
    snippet = " ".join(r.text[:800].split())
    for part in [snippet[i:i+110] for i in range(0, min(len(snippet), 660), 110)]:
        print(f"    {part}")

    # ── Script / iframe summary ───────────────────────────────────────────
    print()
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(r.text, "html.parser")
    ext_scripts = [s.get("src") for s in soup.find_all("script") if s.get("src")]
    inline_scripts = [s for s in soup.find_all("script") if not s.get("src") and s.string]
    iframes = soup.find_all("iframe")
    info("External scripts", str(len(ext_scripts)))
    for s in ext_scripts[:6]:
        info("  src", str(s)[:100])
    info("Inline scripts",   str(len(inline_scripts)))
    info("Iframes",          str(len(iframes)))

    # ── Quick look at fc tokens in page ──────────────────────────────────
    print()
    fc_matches = re.findall(r"""['\"]?fc['\"]?\s*:\s*['"]([^'"]{10,})['"]""", r.text)
    if fc_matches:
        ok("fc tokens found", str(len(fc_matches)))
        for i, tok in enumerate(fc_matches[:3]):
            info(f"  fc[{i}]", tok[:60])
    else:
        row("fc tokens", "none found", SKIP)

    api_uri_m = re.search(r"""apiUri\s*:\s*['"]([^'"]+)['"]""", r.text)
    if api_uri_m:
        ok("apiUri", api_uri_m.group(1)[:60])
    else:
        row("apiUri", "not found", SKIP)

    return session, r


# ── Step 2: Extractor ─────────────────────────────────────────────────────────

def step2_extract(url: str) -> str | None:
    header("2 · Extractor (get_direct_link_from_veev)")

    try:
        from aniworld.extractors.provider.veev import get_direct_link_from_veev
        result = get_direct_link_from_veev(url)
        if result:
            ok("Direct URL", result[:90])
            return result
        fail("Extractor", "returned None")
    except Exception as exc:
        fail("Extractor", str(exc)[:120])

    return None


# ── Step 2b: Diagnostics ──────────────────────────────────────────────────────

def step2b_diagnostics(url: str, session: requests.Session, html: str) -> None:
    header("2b · Diagnostics (page internals)")

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    # CDN URLs
    cdn_matches = re.findall(r"https://s-[A-Za-z0-9]+-\d+\.veev\.to/[A-Za-z0-9_\-]{20,}", html)
    for u in cdn_matches[:4]:
        ok("CDN URL", u[:100])
    if not cdn_matches:
        row("CDN URLs", "none found", SKIP)

    # m3u8 / mp4
    for label, pat in [("m3u8", r"https?://[^\s'\"<>]+\.m3u8[^\s'\"<>]*"),
                        ("mp4",  r"https?://[^\s'\"<>]+\.mp4[^\s'\"<>]*")]:
        hits = re.findall(pat, html)
        for h in hits[:2]:
            ok(label, h[:100])
        if not hits:
            row(label, "not found", SKIP)

    # Iframes
    iframes = soup.find_all("iframe")
    for i, fr in enumerate(iframes[:4]):
        src = fr.get("src") or fr.get("data-src") or "no src"
        info(f"iframe[{i}]", str(src)[:100])
    if not iframes:
        row("iframes", "none", SKIP)

    # Script srcs
    scripts = [s.get("src") for s in soup.find_all("script") if s.get("src")]
    for s in scripts[:5]:
        info("script src", str(s)[:100])

    # Inline scripts
    inline = [s for s in soup.find_all("script") if not s.get("src") and s.string]
    info("Inline scripts", str(len(inline)))
    for i, s in enumerate(inline[:4]):
        snippet = " ".join((s.string or "").split())[:140]
        info(f"  inline[{i}]", snippet)

    # data- attributes
    data_attrs: dict[str, str] = {}
    for tag in soup.find_all(True):
        for attr, val in tag.attrs.items():
            if attr.startswith("data-") and isinstance(val, str) and len(val) > 3:
                data_attrs[attr] = val
    for attr, val in list(data_attrs.items())[:8]:
        info(f"  {attr}", str(val)[:100])

    # ── All inline scripts (full content) ────────────────────────────────
    print()
    info("All inline scripts", str(len(inline)))
    for i, s in enumerate(inline):
        raw = (s.string or "").strip()
        # Always show full content for scripts ≤ 600 chars; first 800 chars otherwise
        limit = len(raw) if len(raw) <= 600 else 800
        snippet = " ".join(raw[:limit].split())
        print(f"\n    [inline {i}]  ({len(raw)} chars)")
        for part in [snippet[j:j+110] for j in range(0, len(snippet), 110)]:
            print(f"    {part}")

    # ── API probe ──────────────────────────────────────────────────────────
    print()
    # Real fc: the FINAL override written to window._vvto.fc — this is the actual API key
    real_fc_m = re.search(r'window\._vvto\[[^\]]+\]\s*=\s*"([^"]+)"', html)
    real_fc   = real_fc_m.group(1) if real_fc_m else ""
    if real_fc:
        ok("real fc (final key)", real_fc[:80])
    else:
        row("real fc", "pattern not found", ERR)

    fc_tokens = re.findall(r"""['\"]?fc['\"]?\s*:\s*['"]([^'"]{10,})['"]""", html)
    api_uri_m = re.search(r"""apiUri\s*:\s*['"]([^'"]+)['"]""", html)
    raw_api   = api_uri_m.group(1) if api_uri_m else ""
    api_uri   = raw_api if raw_api else "https://veev.to"

    vid_id = url.split("/")[-1].split("?")[0]
    base   = api_uri.rstrip("/")

    fc_short = fc_tokens[0] if fc_tokens else ""
    fc_long  = fc_tokens[1] if len(fc_tokens) > 1 else fc_short

    api_hdrs = {
        "User-Agent": UA,
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": url,
        "Origin": "https://veev.to",
    }

    candidates: list[tuple] = []
    if real_fc or fc_short:
        key = real_fc or fc_long
        candidates += [
            # Primary: real fc as key, short slug as video id
            ("GET",  f"{base}/api/video/{fc_short}?key={key}", None),
            ("GET",  f"{base}/api/video/{fc_short}?k={key}", None),
            ("GET",  f"{base}/api/video/{vid_id}?key={key}", None),
            # POST variants
            ("POST", f"{base}/api/source/{vid_id}",
             {"r": url, "d": "veev.to", "key": key}),
            ("POST", f"{base}/api/source/{fc_short}",
             {"r": url, "d": "veev.to", "key": key}),
            # Fallbacks with intermediate long token
            ("GET",  f"{base}/api/video/{fc_short}?key={fc_long}", None),
            ("GET",  f"{base}/api/video/{fc_short}", None),
            ("GET",  f"{base}/api/embed/{vid_id}?key={key}", None),
        ]

    if candidates:
        info("Probing veev API", f"{len(candidates)} candidates  api_uri={api_uri}")
        for method, api_url, body in candidates:
            try:
                if method == "POST":
                    resp = session.post(api_url, json=body, headers=api_hdrs, timeout=10)
                else:
                    resp = session.get(api_url, headers=api_hdrs, timeout=10)
                snippet = resp.text[:200].replace("\n", " ")
                has_url = any(k in resp.text.lower() for k in ("veev.to", ".m3u8", ".mp4", "stream", '"url"'))
                icon = OK if resp.status_code == 200 and has_url else SKIP
                short = api_url.replace(base, "")[:55]
                row(f"  {method} {short}", f"{resp.status_code}  {snippet[:90]}", icon)
            except Exception as exc:
                short = api_url.replace(base, "")[:55]
                row(f"  {method} {short}", str(exc)[:60], ERR)

    # ── Fetch veev player JS files ─────────────────────────────────────────
    js_srcs = [str(s["src"]) for s in soup.find_all("script")
               if s.get("src") and "veev" in str(s.get("src", "")).lower()]
    if js_srcs:
        print()
        for js_src in js_srcs[:3]:
            info("Fetching player JS", js_src[:80])
            try:
                js_resp = session.get(js_src, timeout=15)
                js_text = js_resp.text
                info("  JS size", f"{len(js_text):,} chars")

                if len(js_text) < 8000:
                    print("\n    --- JS content ---")
                    for part in [js_text[i:i+120] for i in range(0, len(js_text), 120)]:
                        print(f"    {part}")
                    print()
                else:
                    for pat_label, pattern in [
                        ("api path",   r'["\`]/api/[^"\'`\s]{2,60}'),
                        ("apiKey",     r'apiKey[\'"\s:]+[\'"]([^\'"]{4,})[\'"]'),
                        ("key param",  r'[?&]key=[^"\'&\s]{4,40}'),
                        ("fetch(",     r'fetch\([^)]{5,80}\)'),
                        ("axios.post", r'axios\.(?:post|get)\([^)]{5,80}'),
                    ]:
                        hits = re.findall(pattern, js_text)
                        for h in list(dict.fromkeys(hits))[:4]:
                            info(f"  {pat_label}", str(h)[:100])
            except Exception as exc:
                fail("  JS fetch", str(exc)[:60])


# ── Step 3: CDN reachability ──────────────────────────────────────────────────

def step3_cdn_check(direct_url: str) -> None:
    header("3 · CDN reachability")
    try:
        head = requests.head(direct_url, headers={"User-Agent": UA},
                             timeout=10, allow_redirects=True)
        row("Status", str(head.status_code), OK if head.status_code == 200 else ERR)
        info("Content-Type",   head.headers.get("Content-Type", "?"))
        info("Content-Length", head.headers.get("Content-Length", "N/A"))
    except Exception as exc:
        fail("HEAD request", str(exc)[:80])
        return

    try:
        r = requests.get(direct_url, headers={"User-Agent": UA,
                         "Range": "bytes=0-255"}, timeout=10)
        ok("First 256 bytes", "")
        print(f"    {r.content[:256]}")
    except Exception as exc:
        fail("Stream peek", str(exc)[:80])


def is_hls(url: str) -> bool:
    clean = url.split("?")[0].lower()
    if clean.endswith(".m3u8"):
        return True
    try:
        head = requests.head(url, headers={"User-Agent": UA}, timeout=8,
                             allow_redirects=True)
        ct = head.headers.get("Content-Type", "")
        return "mpegurl" in ct or "m3u8" in ct
    except Exception:
        return False


# ── Step 4a: HLS segment download ─────────────────────────────────────────────

def _fetch_segment(args: tuple) -> tuple:
    _, seg_url, headers, out_path = args
    try:
        r = requests.get(seg_url, headers=headers, timeout=15)
        r.raise_for_status()
        out_path.write_bytes(r.content)
        return len(r.content), True
    except Exception:
        return 0, False


def _progress_bar(done: int, total: int, total_b: int, t0: float,
                  errors: int, bar_w: int = 32) -> str:
    elapsed = time.time() - t0
    filled  = int(bar_w * done / total) if total else 0
    bar     = "█" * filled + "░" * (bar_w - filled)
    pct     = done * 100 // total if total else 0
    mb      = total_b / 1_048_576
    speed   = mb / elapsed if elapsed > 0 else 0
    err_s   = f"  {ERR} {errors}" if errors else ""
    w       = len(str(total))
    return (f"  [{bar}] {done:>{w}}/{total}  {pct:>3}%  "
            f"{mb:>6.1f} MB  {speed:>5.1f} MB/s  +{elapsed:>5.1f}s{err_s}")


def step4a_hls_download(master_url: str, workers: int = 20) -> None:
    header(f"4a · HLS segment download  ({workers} workers)")

    try:
        m = requests.get(master_url, headers={"User-Agent": UA}, timeout=15)
        m.raise_for_status()
        master_text = m.text
    except Exception as exc:
        fail("Master playlist", str(exc))
        return

    quality_url, best_bw = None, 0
    lines = master_text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("#EXT-X-STREAM-INF"):
            bw_m = re.search(r"BANDWIDTH=(\d+)", line)
            bw = int(bw_m.group(1)) if bw_m else 0
            if bw >= best_bw and i + 1 < len(lines):
                best_bw   = bw
                quality_url = urljoin(master_url, lines[i + 1].strip())

    if not quality_url:
        quality_url, quality_text = master_url, master_text
        info("Playlist", "single-level (no variants)")
    else:
        info("Best quality", f"{best_bw // 1000} kbps")
        try:
            q = requests.get(quality_url, headers={"User-Agent": UA}, timeout=15)
            q.raise_for_status()
            quality_text = q.text
        except Exception as exc:
            fail("Quality playlist", str(exc))
            return

    seg_urls = [
        urljoin(quality_url, line.strip())
        for line in quality_text.splitlines()
        if line.strip() and not line.startswith("#")
    ]
    total_segs = len(seg_urls)
    info("Segments", str(total_segs))

    tmp_dir = Path(tempfile.mkdtemp(prefix="veev_segments_"))
    info("Saving to", str(tmp_dir))
    print()

    seg_hdrs = {"User-Agent": UA, "Referer": master_url}
    tasks = [(i, u, seg_hdrs, tmp_dir / f"{i:05d}.ts") for i, u in enumerate(seg_urls)]

    t0 = time.time()
    total_bytes = ok_count = error_count = 0

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_fetch_segment, t): t[0] for t in tasks}
        for f in as_completed(futures):
            nbytes, status_ok = f.result()
            total_bytes  += nbytes
            ok_count     += status_ok
            error_count  += not status_ok
            print(_progress_bar(ok_count + error_count, total_segs,
                                total_bytes, t0, error_count),
                  end="\r", flush=True)

    elapsed = time.time() - t0
    print(_progress_bar(total_segs, total_segs, total_bytes, t0, error_count))
    print()
    row("Result", f"{ok_count}/{total_segs} segments  ·  "
        f"{total_bytes / 1_048_576:.1f} MB  ·  {elapsed:.1f}s",
        OK if error_count == 0 else ERR)

    out_file = tmp_dir.parent / "veev_output.ts"
    with out_file.open("wb") as fout:
        for sf in sorted(tmp_dir.glob("*.ts")):
            fout.write(sf.read_bytes())
    ok("Output file", str(out_file))
    info("File size", f"{out_file.stat().st_size / 1_048_576:.1f} MB")


# ── Step 4b: Direct video download ───────────────────────────────────────────

def step4b_direct_download(video_url: str) -> None:
    header("4b · Direct video download")

    out_file = Path(tempfile.gettempdir()) / "veev_output.mp4"
    info("Saving to", str(out_file))
    print()

    BAR = 32
    try:
        with requests.get(video_url, headers={"User-Agent": UA},
                          stream=True, timeout=30) as r:
            r.raise_for_status()
            total = int(r.headers.get("Content-Length", 0))
            done  = 0
            t0    = time.time()

            with out_file.open("wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        done += len(chunk)
                        elapsed = time.time() - t0
                        mb      = done / 1_048_576
                        speed   = mb / elapsed if elapsed > 0 else 0
                        if total:
                            pct    = done * 100 // total
                            filled = int(BAR * done / total)
                            bar    = "█" * filled + "░" * (BAR - filled)
                            line   = (f"  [{bar}] {pct:>3}%  {mb:>6.1f} MB  "
                                      f"{speed:>5.1f} MB/s  +{elapsed:>5.1f}s")
                        else:
                            line   = (f"  {'█' * BAR}  {mb:>6.1f} MB  "
                                      f"{speed:>5.1f} MB/s  +{elapsed:>5.1f}s")
                        print(line, end="\r", flush=True)

        elapsed = time.time() - t0
        size    = out_file.stat().st_size
        print()
        ok("Output file", str(out_file))
        info("File size", f"{size / 1_048_576:.1f} MB  ·  {elapsed:.1f}s")

    except Exception as exc:
        print()
        fail("Download", str(exc))


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else TEST_URL

    print(f"\n{'═' * W}")
    print(f"  Veev.to Extractor Probe")
    print(f"  {url}")
    print(f"{'═' * W}")

    session, page_resp = step1_page_probe(url)
    direct_url = step2_extract(url)

    if not direct_url:
        step2b_diagnostics(url, session, page_resp.text)
        print(f"\n  {ERR}  No direct URL extracted — cannot continue.")
        print(f"{'═' * W}\n")
        return

    step3_cdn_check(direct_url)

    if is_hls(direct_url):
        info("Stream type", "HLS (M3U8)")
        step4a_hls_download(direct_url)
    else:
        info("Stream type", "direct video")
        step4b_direct_download(direct_url)

    print(f"\n{'═' * W}\n")


if __name__ == "__main__":
    main()
