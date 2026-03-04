"""
Provider extractor probe — works with any supported provider.

Usage:
    python scripts/test_voe_custom_domain.py [url]

Supported providers: VOE, Filemoon, Doodstream, Streamtape, Vidoza,
                     Vidmoly, Luluvdo, SpeedFiles, LoadX
"""

import re
import sys
import time

# Ensure UTF-8 output on Windows (box-drawing and block chars)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
import tempfile
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse, urljoin

import requests

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logging.getLogger("urllib3").setLevel(logging.WARNING)

sys.path.insert(0, "src")

TEST_URL = "https://lancewhosedifficult.com/keqifuhr1d5q"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"

# Domain → provider name (extend as needed)
PROVIDER_DOMAINS: dict[str, str] = {
    "voe.sx":           "VOE",
    "filemoon.to":      "Filemoon",
    "filemoon.sx":      "Filemoon",
    "moonplayer.to":    "Filemoon",
    "myvidplay.com":    "Doodstream",
    "dood.so":          "Doodstream",
    "dood.li":          "Doodstream",
    "dood.to":          "Doodstream",
    "dood.yt":          "Doodstream",
    "dood.cx":          "Doodstream",
    "doodstream.com":   "Doodstream",
    "ds2play.com":      "Doodstream",
    "streamtape.com":   "Streamtape",
    "streamtape.to":    "Streamtape",
    "vidoza.net":       "Vidoza",
    "vidmoly.to":       "Vidmoly",
    "vidmoly.net":      "Vidmoly",
    "luluvdo.com":      "Luluvdo",
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


# ── Provider helpers ──────────────────────────────────────────────────────────

def detect_provider(url: str) -> str | None:
    """Return provider name from URL domain, or None if unknown."""
    domain = urlparse(url).netloc.lower().removeprefix("www.")
    return PROVIDER_DOMAINS.get(domain)


def call_extractor(provider: str, embed_url: str) -> str | None:
    """Call get_direct_link_from_<provider>(embed_url) and return the result."""
    from aniworld import extractors
    func_name = f"get_direct_link_from_{provider.lower()}"
    func = getattr(extractors, func_name, None)
    if func is None:
        return None
    return func(**{f"embeded_{provider.lower()}_link": embed_url})


def is_hls(url: str) -> bool:
    """Return True if the URL points to an HLS playlist."""
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


# ── Step 1: Page probe ────────────────────────────────────────────────────────

def step1_page_probe(url: str) -> requests.Response:
    header("1 · Page probe")
    info("URL", url)

    r = requests.get(url, headers={"User-Agent": UA}, timeout=15, allow_redirects=True)

    row("Status", str(r.status_code), OK if r.status_code == 200 else ERR)
    info("Content-Type", r.headers.get("Content-Type", "?"))
    info("Body size", f"{len(r.text):,} chars")

    provider = detect_provider(url)
    row("Provider", provider or "unknown (custom domain?)",
        OK if provider else SKIP)

    if r.history:
        for h in r.history:
            info("  redirect →", f"HTTP {h.status_code}  {h.headers.get('Location', '?')}")
    else:
        info("Redirects", "none")

    return r


# ── Step 2: Extractor dispatch ────────────────────────────────────────────────

def step2_extract(url: str) -> str | None:
    """
    Try to get a direct URL from the embed URL.
    - Known provider → call its extractor directly.
    - Unknown domain → try VOE's script-tag extraction first (custom domains),
      then fall back to trying every registered extractor.
    """
    header("2 · Extractor dispatch")

    provider = detect_provider(url)

    if provider:
        info("Trying extractor", provider)
        try:
            result = call_extractor(provider, url)
            if result:
                ok(provider, result[:90])
                return result
            fail(provider, "returned None")
        except Exception as err:
            fail(provider, str(err)[:90])
        return None

    # Unknown domain — try VOE script extraction first (VOE rotates custom domains)
    info("Unknown domain", "probing VOE script extraction…")
    try:
        from aniworld.extractors.provider.voe import extract_voe_from_script
        r = requests.get(url, headers={"User-Agent": UA}, timeout=15)
        r.raise_for_status()
        source = extract_voe_from_script(r.text)
        if source:
            ok("VOE (custom domain)", source[:90])
            return source
        row("VOE (custom domain)", "no script tag match", SKIP)
    except Exception as err:
        row("VOE (custom domain)", str(err)[:80], SKIP)

    # Fall back: try every registered extractor
    from aniworld import extractors as _ext
    all_providers = [
        name.replace("get_direct_link_from_", "").title()
        for name in dir(_ext)
        if name.startswith("get_direct_link_from_")
    ]
    info("Trying all extractors", ", ".join(all_providers))
    for p in all_providers:
        try:
            result = call_extractor(p, url)
            if result:
                ok(f"  {p}", result[:80])
                return result
        except Exception:
            pass
        row(f"  {p}", "failed", SKIP)

    fail("All extractors", "none succeeded")

    # ── Diagnostic dump to help identify the provider ──────────────────────
    header("2b · Page diagnostic (unknown provider)")
    from bs4 import BeautifulSoup

    try:
        page = requests.get(url, headers={"User-Agent": UA}, timeout=15)
        html = page.text
        soup = BeautifulSoup(html, "html.parser")

        # Iframes
        iframes = soup.find_all("iframe")
        for i, fr in enumerate(iframes[:5]):
            src = fr.get("src") or fr.get("data-src") or "no src"
            info(f"iframe[{i}]", str(src)[:100])
        if not iframes:
            row("iframes", "none found", SKIP)

        # Script srcs
        scripts = [s.get("src") for s in soup.find_all("script") if s.get("src")]
        for s in scripts[:5]:
            info("script src", str(s)[:100])

        # Interesting patterns in HTML
        patterns = {
            "file: '...'":      re.search(r"file:\s*['\"]([^'\"]{10,})['\"]", html),
            "sources: [...]":   re.search(r"sources\s*:\s*\[\s*\{[^}]*?file[^}]*?\}", html),
            "m3u8 URL":         re.search(r"https?://[^\s'\"<>]+\.m3u8[^\s'\"<>]*", html),
            "mp4 URL":          re.search(r"https?://[^\s'\"<>]+\.mp4[^\s'\"<>]*", html),
            "jwplayer setup":   re.search(r"jwplayer\s*\(", html),
            "videojs":          re.search(r"videojs\s*\(", html),
            "eval(atob":        re.search(r"eval\s*\(\s*atob\s*\(", html),
            "eval(function(p":  re.search(r"eval\s*\(\s*function\s*\(p", html),
        }
        for label, match in patterns.items():
            if match:
                ok(label, match.group(0)[:90] if match.lastindex else "found")
            else:
                row(label, "not found", SKIP)

        # Inline script content (non-empty, no src)
        print()
        inline_scripts = [s for s in soup.find_all("script") if not s.get("src") and s.string]
        info("Inline scripts", str(len(inline_scripts)))
        for i, s in enumerate(inline_scripts[:5]):
            snippet = " ".join((s.string or "").split())[:120]
            info(f"  inline[{i}]", snippet)

        # data- attributes that might carry video IDs / tokens
        data_attrs = {}
        for tag in soup.find_all(True):
            for attr, val in tag.attrs.items():
                if attr.startswith("data-") and isinstance(val, str) and len(val) > 3:
                    data_attrs[attr] = val
        if data_attrs:
            for attr, val in list(data_attrs.items())[:8]:
                info(f"  {attr}", str(val)[:100])
        else:
            row("data- attributes", "none found", SKIP)

        # Any URL pointing to the same domain's API
        domain = urlparse(url).netloc
        api_urls = re.findall(rf"https?://{re.escape(domain)}/[^\s'\"<>]+", html)
        for u in list(dict.fromkeys(api_urls))[:5]:
            info("same-domain URL", u[:100])

        # ── Veev-specific: extract fc (file code) and probe API ──────────
        fc_matches = re.findall(r"['\"]?fc['\"]?\s*:\s*['\"]([^'\"]{10,})['\"]", html)
        fc_short = fc_matches[0] if fc_matches else None
        fc_long  = fc_matches[1] if len(fc_matches) > 1 else None

        if fc_short or fc_long:
            ok("Veev fc (short)", str(fc_short)[:80])
            ok("Veev fc (long)",  str(fc_long)[:80])

            # Also look for apiUri in __VEEVPLAYER__ config
            api_uri_m = re.search(r"apiUri\s*:\s*['\"]([^'\"]+)['\"]", html)
            api_uri = api_uri_m.group(1) if api_uri_m else None
            if api_uri:
                ok("apiUri", api_uri[:80])

            vid_id = urlparse(url).path.split("/")[-1]
            base_domain = f"https://{domain}"

            hdrs = {"User-Agent": UA, "Referer": url,
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json"}

            # Build candidate (method, url, body) triples
            candidates = []
            fc_key = fc_long or fc_short
            fc_vid = fc_short or fc_long
            if fc_vid and fc_key:
                candidates += [
                    # /api/video/{short_fc} with key param
                    ("GET",  f"{base_domain}/api/video/{fc_vid}?key={fc_key}", None),
                    ("POST", f"{base_domain}/api/video/{fc_vid}",
                     {"key": fc_key, "r": url}),
                    # /api/source with key
                    ("POST", f"{base_domain}/api/source/{vid_id}",
                     {"r": url, "d": domain, "key": fc_key}),
                    ("POST", f"{base_domain}/api/source/{vid_id}",
                     {"r": url, "d": domain, "key": fc_vid}),
                    # /api/source with fc directly
                    ("POST", f"{base_domain}/api/source/{fc_vid}",
                     {"r": url, "d": domain}),
                    # GET endpoints
                    ("GET",  f"{base_domain}/api/stream?fc={fc_vid}&vid={vid_id}", None),
                    ("GET",  f"{base_domain}/api/video/{fc_vid}", None),
                    ("GET",  f"{base_domain}/api/embed/{vid_id}?key={fc_key}", None),
                ]
            if api_uri:
                candidates += [
                    ("POST", f"{api_uri.rstrip('/')}/api/source/{vid_id}",
                     {"r": url, "d": domain, "key": fc_key}),
                ]

            print()
            info("Probing Veev API", f"{len(candidates)} candidates")
            for method, api_url, body in candidates:
                try:
                    if method == "POST":
                        resp = requests.post(api_url, json=body, headers=hdrs, timeout=8)
                    else:
                        resp = requests.get(api_url, headers=hdrs, timeout=8)
                    snippet = resp.text[:160].replace("\n", " ")
                    icon = OK if resp.status_code == 200 and "url" in resp.text.lower() else SKIP
                    short_url = api_url.replace(base_domain, "").replace("https://veev.to", "")
                    row(f"  {method} {short_url[:45]}", f"{resp.status_code}  {snippet[:80]}", icon)
                except Exception as e:
                    short_url = api_url.replace(base_domain, "")
                    row(f"  {method} {short_url[:45]}", str(e)[:60], ERR)

            # Fetch one JS file and look for API call patterns
            js_srcs = [str(s["src"]) for s in soup.find_all("script")
                       if s.get("src") and "veevcdn" in str(s.get("src"))]
            if js_srcs:
                print()
                for js_src in js_srcs[:4]:
                    info("Fetching player JS", js_src[:80])
                    try:
                        js_resp = requests.get(js_src, headers={"User-Agent": UA}, timeout=15)
                        js_text = js_resp.text
                        info("  JS size", f"{len(js_text):,} chars")

                        if len(js_text) < 8000:
                            # Small file — dump it entirely
                            print(f"\n    --- JS content ---")
                            for part in [js_text[i:i+120] for i in range(0, len(js_text), 120)]:
                                print(f"    {part}")
                            print()
                        else:
                            # Large bundle — targeted searches
                            patterns_found = False
                            for pat_label, pattern in [
                                ("api path",    r'["\`]/api/[^"\'`\s]{2,60}'),
                                ("apiKey",      r'apiKey[\'"\s:]+[\'"]([^\'"]{4,})[\'"]'),
                                ("Bearer",      r'Bearer[^\'"]{0,60}'),
                                ("key param",   r'[?&]key=[^"\'&\s]{4,40}'),
                                ("axios.post",  r'axios\.(?:post|get)\([^)]{5,80}'),
                                ("fetch(",      r'fetch\([^)]{5,80}\)'),
                            ]:
                                hits = re.findall(pattern, js_text)
                                unique = list(dict.fromkeys(hits))[:6]
                                if unique:
                                    patterns_found = True
                                    for h in unique:
                                        info(f"  {pat_label}", str(h)[:100])
                            if not patterns_found:
                                info("  (no API patterns found)", "")
                    except Exception as e:
                        fail("  JS fetch", str(e)[:60])

    except Exception as err:
        fail("Diagnostic", str(err)[:80])

    return None


# ── Step 3: CDN reachability ──────────────────────────────────────────────────

def step3_cdn_check(direct_url: str) -> None:
    header("3 · CDN reachability")
    try:
        head = requests.head(direct_url, headers={"User-Agent": UA},
                             timeout=10, allow_redirects=True)
        row("Status", str(head.status_code), OK if head.status_code == 200 else ERR)
        info("Content-Type",   head.headers.get("Content-Type", "?"))
        info("Content-Length", head.headers.get("Content-Length", "N/A"))
    except Exception as err:
        fail("HEAD request", str(err)[:80])
        return

    try:
        r = requests.get(direct_url, headers={"User-Agent": UA,
                         "Range": "bytes=0-255"}, timeout=10)
        ok("First 200 bytes", "")
        print(f"    {r.content[:200]}")
    except Exception as err:
        fail("Stream peek", str(err)[:80])


# ── Step 4a: HLS parallel segment download ────────────────────────────────────

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
    filled = int(bar_w * done / total) if total else 0
    bar    = "█" * filled + "░" * (bar_w - filled)
    pct    = done * 100 // total if total else 0
    mb     = total_b / 1_048_576
    speed  = mb / elapsed if elapsed > 0 else 0
    err_s  = f"  {ERR} {errors}" if errors else ""
    w      = len(str(total))
    return (f"  [{bar}] {done:>{w}}/{total}  {pct:>3}%  "
            f"{mb:>6.1f} MB  {speed:>5.1f} MB/s  +{elapsed:>5.1f}s{err_s}")


def step4a_hls_download(master_url: str, workers: int = 20) -> None:
    header(f"4a · HLS segment download  ({workers} workers)")

    # Fetch master playlist
    try:
        m = requests.get(master_url, headers={"User-Agent": UA}, timeout=15)
        m.raise_for_status()
        master_text = m.text
    except Exception as err:
        fail("Master playlist", str(err))
        return

    # Pick best quality variant
    quality_url, best_bw = None, 0
    lines = master_text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("#EXT-X-STREAM-INF"):
            bw_m = re.search(r"BANDWIDTH=(\d+)", line)
            bw = int(bw_m.group(1)) if bw_m else 0
            if bw >= best_bw and i + 1 < len(lines):
                best_bw = bw
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
        except Exception as err:
            fail("Quality playlist", str(err))
            return

    seg_urls = [
        urljoin(quality_url, line.strip())
        for line in quality_text.splitlines()
        if line.strip() and not line.startswith("#")
    ]
    total_segs = len(seg_urls)
    info("Segments", str(total_segs))

    tmp_dir = Path(tempfile.mkdtemp(prefix="provider_segments_"))
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

    # Concatenate segments in order
    out_file = tmp_dir.parent / "output.ts"
    with out_file.open("wb") as fout:
        for sf in sorted(tmp_dir.glob("*.ts")):
            fout.write(sf.read_bytes())
    ok("Output file", str(out_file))
    info("File size", f"{out_file.stat().st_size / 1_048_576:.1f} MB")


# ── Step 4b: Direct video download ───────────────────────────────────────────

def step4b_direct_download(video_url: str) -> None:
    header("4b · Direct video download")

    out_file = Path(tempfile.gettempdir()) / "output.mp4"
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

    except Exception as err:
        print()
        fail("Download", str(err))


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else TEST_URL

    print(f"\n{'═' * W}")
    print(f"  Provider Extractor Probe")
    print(f"  {url}")
    print(f"{'═' * W}")

    step1_page_probe(url)
    direct_url = step2_extract(url)

    if not direct_url:
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
