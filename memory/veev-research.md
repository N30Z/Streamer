# veev.to Extractor Research

## Test URLs
- Embed 1: `https://veev.to/e/27kYAOe9AbsIceAnuwJ36B2xKnlZdIfwhFzjjJc?rback=1`
  CDN: `https://s-eri-983105.veev.to/...` (domain: veev.to)
- Embed 2: `https://veev.to/e/2FN7EmDAu7xwVYC9MFUKizhuY7Nn14iJuVZjE7g?rback=1`
  CDN: `https://s-gb-441928.veevcdn.co/...` (domain: veevcdn.co)

## Page Loading Fix
- Must use `Accept-Encoding: gzip, deflate` (NOT `br`) — server sends brotli but
  requests can't decode it, resulting in 40K of garbled bytes.

## Page Structure (inline scripts)

**inline[2]:** `window._vvto = { vtl:0, fc:"Gujal00_loving_them_moves_buddy", rpp:1, as:0, ie:1, cc:3, boi:0 }`
**inline[3]:**
```javascript
var _5tk6cwegu1m4__ = { ..., fc: "411002014aC-...", asre: { e:1, z:"QiMQ...", s:"25" } }
window._vvto = _5tk6cwegu1m4__
window._vvto['fc'] = "411002013Ă1-9Ċ27kY...{vid_id}...{hash}"  // real_fc (LZW-compressed)
```

**inline[18]:** `Cookies.set('file_id', '70646', ...); Cookies.set('aff', '25', ...)`

Three fc values in page:
1. `window._vvto.fc` = short slug (e.g. `"Gujal00_loving_them_moves_buddy"`) — NOT used in API
2. intermediate fc = plain ASCII token (e.g. `"411002014aC-94-jblm6mjyhvdc-..."`) — NOT used in API
3. real_fc = LZW-compressed (Unicode chars > 255) = what becomes `ch=` after decoding

## Player JS String Table Decoding
JS file: `https://static.veevcdn.co/assets/videoplayer/434b479.js?v4` (125K)

Key decoded constants from `a2b()` string lookup (Xq = a2b6 = a2b):
- `Xq(0x51f)` = `"&r="` — separator in file_code URL
- `Xq(0x4bc)` = `"&ch="` — separator in file_code URL
- `Xq(0xb3)` = `"ref"` — property of window._vvto (referrer URL)
- `Xq(0x636)` = `"location"` — document.location
- `Xq(0x35c)` = `"search"` — document.location.search
- `Xq(0x476)` = `"replace"` — .replace('?','')
- `Xq(0x42e)` = `"concat"` — string concat
- `Xq(0x495)` = `"code"` — action payload key for file_code
- `Xq(0x612)` = `"$get"` — axios GET method
- `Xq(0x27b)` = `"$axios"` — axios instance
- `Xq(0x32d)` = `"/dl?op=player_api&cmd=ga&file_code="` — analytics endpoint
- `Xq(0x611)` = `"&ie="` — embed flag separator
- `Xq(0x184)` = `"$post"` — axios POST
- `Xq(0xda)`  = `"/dl"` — API base path
- `Xq(0x618)` = `"info"` — Vuex state key for file info
- `Xq(0x385)` = `"file"` — response field containing file data
- `Xq(0x539)` = `"success"` — success status string

## Variable Decoding
In the player module (at offset 113502):
```javascript
uL = Xq(0x22a).replaceAll(/[sfbyq]/gi, '')
   // "s_fvbvyytqo" → "_vvto"   → window["_vvto"] = window._vvto

uB = Xq(0x1c3).replace(/a|s|d|q|o|l/gi, '')
   // "asdqfolc"   → "fc"       → window._vvto["fc"]
```

So:
- `window[uL]` = `window._vvto` (the player config object)
- `window[uL][uB]` = `window._vvto.fc` = the real_fc value

Player initialization:
```javascript
window[uL] = Object.assign({}, uT, window[uL] || {})
window[uL][uB] = Object(Y['b'])(window[uL][uB])
```
→ `window._vvto.fc` is **LZW-decompressed** by `Y['b']` = `R()` function

## Y['b'] = R() = LZW Decompression
```python
def lzw_decompress(j):
    k = list(j)
    if not k: return ''
    D = {}; C = k[0]; M = C; U = [C]; y = 256
    for G in range(1, len(k)):
        Y = ord(k[G])
        I = k[G] if Y < 256 else (D[Y] if Y in D else M + C)
        U.append(I); C = I[0]; D[y] = M + C; y += 1; M = I
    return ''.join(U)
```
Characters with Unicode code > 255 in real_fc are LZW dictionary indices.

## Y['a'] = W() = Referrer/URL Getter
NOT a UUID generator. Returns `document.URL` or `document.referrer` or `window.frames.top.document.URL`.
In headless/direct-embed context returns empty string.

## Correct cmd=gi API Call (VERIFIED WORKING)

### Step 1: GET gvnp (tracking, no params)
```
GET /dl?op=player_api&cmd=gvnp
```
Returns `{"status":"success","data":0}` — just primes server session.

### Step 2: GET gi (actual video info)
URL construction (decoded from JS):
```
/dl?op=player_api&cmd=gi
  &file_code={vid_id}           ← URL path ID, e.g. "27kYAOe9AbsIceAnuwJ36B2xKnlZdIfwhFzjjJc"
  &r=                           ← EMPTY (referrer; empty in direct/headless context)
  &ch={lzw_decoded_real_fc}     ← LZW-decoded real_fc (ASCII, all-hyphen-and-alphanumeric)
  &{location.search.replace('?','')}  ← e.g. "rback=1"
  &ie=1                         ← embed flag
```

Confirmed by Playwright browser interception:
```
GET /dl?op=player_api&cmd=gi&file_code=27kYAOe9AbsIceAnuwJ36B2xKnlZdIfwhFzjjJc&r=&ch=2014010040011-91-27kYAOe9AbsIceAnuwJ36B2xKnlZdIfwhFzjjJc-106-1772899601-cd2dcd33216eebf3a2e21d46875ad3c8&rback=1&ie=1
```

### Step 3: Parse Response
```json
{
  "status": "success",
  "file": {
    "file_code": "27kYAOe9AbsIceAnuwJ36B2xKnlZdIfwhFzjjJc",
    "file_h": "70646-91-106-1772900396-77c03a4d6be67b19a33fa2e0bab9912d",
    "file_mime_type": "video/x-matroska",
    "vid_container": "mp4",
    "dv": [{"s": "<LZW-compressed-URL>", "t": "<type>", "sz": "<size>"}],
    "captions_list": [{"label":"German","language":"ger","src":"https://s-eri-983105.veev.to/vtt/..."}],
    "download_link": "https://veev.to/d/{vid_id}",
    "player_img": "https://s-eri-983105.veev.to/...",
    ...
  },
  "mm": "<md5>"
}
```

The `ch` value structure (after LZW decode): `{prefix}-{seg}-{vid_id}-{seg}-{unix_timestamp}-{md5_hash}`
Timestamps change each page load — token is time-limited.

## dv Array — Stream URL Encoding (UNSOLVED)
`dv[0].s` is multi-layer encoded:
1. In page response: LZW-compressed Unicode string
2. LZW decompress → long hex string (1696 chars = 848 bytes of ASCII)
3. Hex-decode → ASCII text starting with `dXRmOA==` (base64 of "utf8") + more data
4. Full base64-decode → `b'utf8'` (4 bytes only — not the URL)

**Status: encoding of dv[0].s not yet fully reversed.**

### Possible approaches:
- A: Inspect player JS (d5fc656.js or 141ccb4.js) for how dv[0].s is decoded/used
- B: Use Playwright with longer wait + click-to-play to intercept actual HLS/MP4 request
- C: Use `file_h` + `file_code` to construct stream URL directly (common pattern)
- D: Try `https://veev.to/dl?op=download&file_code={vid_id}&h={file_h}` or similar

## Extractor Python Code (Summary)
```python
# 1. Fetch embed page
session.get(embed_url)  # Accept-Encoding: gzip, deflate

# 2. Extract real_fc
real_fc_m = re.search(r'window\._vvto\[[^\]]+\]\s*=\s*"([^"]+)"', html)
ch = lzw_decompress(real_fc_m.group(1))

# 3. Get vid_id from URL
vid_id = embed_url.split('/e/')[-1].split('?')[0]

# 4. Parse query string for uy param
uy = embed_url.split('?', 1)[1] if '?' in embed_url else ''

# 5. gvnp tracking call
session.get("https://veev.to/dl?op=player_api&cmd=gvnp")

# 6. gi info call
gi_url = f"https://veev.to/dl?op=player_api&cmd=gi&file_code={vid_id}&r=&ch={ch}&{uy}&ie=1"
resp = session.get(gi_url)
file_data = resp.json()['file']
file_h = file_data['file_h']
# dv = file_data['dv']  # stream URLs — still need to decode
```

## Files Created
- `src/aniworld/extractors/provider/veev.py` — extractor (needs dv decoding fix)
- `scripts/test_veev.py` — test probe script
- `src/aniworld/config.py` — added "Veev" to SUPPORTED_PROVIDERS
