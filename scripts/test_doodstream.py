import sys
sys.path.insert(0, 'src')
import logging
from aniworld.extractors.provider.doodstream import get_direct_link_from_doodstream

logging.basicConfig(level=logging.DEBUG)

links = [
    'https://dood.to/e/sbsy06yix5pn',
    'https://doodstream.com/d/jfdk3yf3x6hz',
]

for link in links:
    print('\nTesting:', link)
    try:
        direct = get_direct_link_from_doodstream(link)
        print('Direct link:', direct)
    except Exception as e:
        print('Error:', type(e).__name__, e)
