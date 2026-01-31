import sys
sys.path.insert(0,'src')
import requests
from aniworld.config import RANDOM_USER_AGENT

url = 'https://filemoon.sx/d/w5clfextaz08'
print('Fetching', url)
resp = requests.get(url, headers={'User-Agent': RANDOM_USER_AGENT}, timeout=30)
print('Status:', resp.status_code)
text = resp.text
print('len:', len(text))
print('--- snippet ---')
print(text[:8000])

# Save to temporary file for inspection
open('tmp_filemoon_page.html','w', encoding='utf-8').write(text)
print('Saved to tmp_filemoon_page.html')
