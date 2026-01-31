from pathlib import Path
import sys
sys.path.insert(0, r'c:\Users\buttl\Projects\Streamer\src')
from aniworld import models
from requests.models import Response
p = Path(r'c:\Users\buttl\Projects\Streamer\tests\sto_fallout.html')
content = p.read_bytes()
r = Response()
r._content = content
r.status_code = 200
print('Extracted title:', models.get_anime_title_from_html(r, site='s.to'))
