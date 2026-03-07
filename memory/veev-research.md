# veev.to Extractor Research

## Test URLs
- Embed 1: `https://veev.to/e/27kYAOe9AbsIceAnuwJ36B2xKnlZdIfwhFzjjJc?rback=1`
  CDN: `https://s-eri-983105.veev.to/kkk1a7e...` (domain: veev.to)
- Embed 2: `https://veev.to/e/2FN7EmDAu7xwVYC9MFUKizhuY7Nn14iJuVZjE7g?rback=1`
  CDN: `https://s-gb-441928.veevcdn.co/FhQBwA...` (domain: veevcdn.co)

## Page Loading Fix
- Must use `Accept-Encoding: gzip, deflate` (NOT `br`) — server sends brotli but
  requests can't decode it, resulting in 40K of garbled bytes.

## Page Structure (inline scripts)
Three fc tokens in the page HTML:
1. `window._vvto = { ..., fc: "Gujal00_loving_them_moves_buddy", ... }` — video slug
2. `var _RAND__ = { ..., fc: "411002014aC-94-jblm6mjyhvdc-...", ... }` — intermediate
3. `window._vvto[__pqrsww] = "30104Ă...{vid_id}...{hash}"` — REAL API key (changes per request)
   Pattern: `window._vvto\[[^\]]+\]\s*=\s*"([^"]+)"`
   Includes video ID embedded + partial hash + Unicode noise chars

Also contains:
- `asre: { e:1, z: "base64token", s: "25" }` — anti-bot token in the _RAND__ object
- `window.__VEEVPLAYER__=function(a,e){...}("","veev.to")` — apiUri is empty string
- `window._vvto.ie = 1` — embed flag

## API Endpoints Discovered (JS4 = 434b479.js, 125K)
From reverse-engineering `434b479.js?v4`:

### cmd=gv (POST with FormData, tracking call)
```
POST /dl?op=player_api
FormData: { op: 'player_api', cmd: 'gv', file_code: <fc>, h: <h>,
            embed: <ie>, adb: '0'/'1', r: <ref>, ff: ..., _a: <prev_val> }
```
Returns `{"status":"success"}` — just a tracking/visit call. No useful data.

### cmd=gi (GET, the actual video info call)
URL pattern from JS source:
```
/dl?op=player_api&cmd=gi&file_code={uC}{Kz(0x51f)}{encodeURIComponent(uS)}{Kz(0x4bc)}{uU}&{page_path}&ie={uG}
```
Where:
- `uC` = file_code (passed to getInfo — probably the short fc slug)
- `uS` = `window[uL][Kz(0xb3)]` = some property of `window._vvto`
- `uU` = `window[uL][uB]` = another property of `window._vvto`
- `page_path` = `/e/27kYAOe9AbsIceAnuwJ36B2xKnlZdIfwhFzjjJc` (no query string)
- `uG` = `window._vvto.ie` = 1
- `Kz(0x51f)` and `Kz(0x4bc)` = obfuscated separator strings (UNKNOWN)

On success returns JSON with `info` field containing CDN stream URL(s).

## What Didn't Work
- `/api/video/{fc_short}?key={any_fc}` → "Invalid key" (wrong endpoint entirely)
- All variants of the old API probe → "Invalid key"

## Next Steps (choose one)
### Option A: Decode JS constants with Node.js
Deobfuscate `Kz(0x51f)` and `Kz(0x4bc)` from `434b479.js?v4`:
- Load the JS in Node.js, redefine `Xq` = `Kz` lookup fn, print `Kz(0x51f)` and `Kz(0x4bc)`
- This gives us the separator chars needed to build the cmd=gi URL

### Option B: Headless browser (Playwright) — user suggested
- Use Playwright to open the embed page, wait for the network request to the CDN
- Intercept it and extract the URL
- This is the most reliable approach given heavy JS obfuscation

```python
from playwright.async_api import async_playwright
async with async_playwright() as p:
    browser = await p.chromium.launch()
    page = await browser.new_page()
    cdnUrls = []
    page.on('request', lambda req: cdnUrls.append(req.url)
            if 'veevcdn' in req.url or ('veev.to' in req.url and req.url.count('/') > 3) else None)
    await page.goto(embed_url)
    await page.wait_for_timeout(5000)
    print(cdnUrls)
```

### Option C: Dump full inline[3] and look for h value
The `h` parameter in the gv call might equal `window._vvto.cc` or similar known field.

## Files Created
- `src/aniworld/extractors/provider/veev.py` — extractor (needs API fix)
- `scripts/test_veev.py` — test probe script
- `src/aniworld/config.py` — added "Veev" to SUPPORTED_PROVIDERS
