import sys
sys.path.insert(0,'src')
import requests
from aniworld.config import RANDOM_USER_AGENT

url = 'https://streamtape.com/e/GpPbrZqw48fV0o'
print('Fetching', url)
resp = requests.get(url, headers={'User-Agent': RANDOM_USER_AGENT}, timeout=30)
print('Status:', resp.status_code)
text = resp.text
print('len:', len(text))
print('--- snippet ---')
print(text[:8000])
open('tmp_streamtape.html','w', encoding='utf-8').write(text)
print('Saved to tmp_streamtape.html')
