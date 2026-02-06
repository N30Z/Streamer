import sys
sys.path.insert(0, 'src')
from aniworld.sites.movie4k import Movie

m = Movie(url='https://movie4k.sx/watch/mission-impossible-fallout/6195193358607cdfb9fad5c8')
print('title:', m.title)
print('available_languages:', getattr(m, 'available_languages', None))
print('providers:')
for prov, d in (m.providers or {}).items():
    print(' ', prov, '->', d)

print('\nstreams sample:')
for s in (m.streams or [])[:20]:
    print(' ', s)
