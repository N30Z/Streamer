# Parallele Downloads

Das AniWorld Downloader System unterstützt jetzt **echte parallele Episode-Downloads**! Dies ermöglicht es, mehrere Anime-Episoden gleichzeitig herunterzuladen, wodurch die Gesamtdownloadzeit erheblich reduziert wird.

## Funktionsweise

### Episode-Level Parallelisierung

Im Gegensatz zu früheren Implementierungen werden **jede Episode als separater Download-Job** behandelt:

- **Jede ausgewählte Episode** wird als eigener Job in die Download-Queue eingefügt
- **Standard: Bis zu 3 parallele Downloads** gleichzeitig
- Downloads starten automatisch in der Reihenfolge, in der Platz verfügbar ist
- Jeder Download läuft in einem separaten Thread

**Beispiel:** Wenn Sie 12 Episoden auswählen und 3 Slots verfügbar sind:
- Episodes 1, 2, 3 → starten sofort parallel
- Episode 1 komplett → Episode 4 startet automatisch
- Episode 2 komplett → Episode 5 startet automatisch
- usw.

### Threading-Pool-Architektur

Die parallele Download-Verarbeitung nutzt einen `ThreadPoolExecutor` mit konfigurierbaren Worker-Threads:

- **Standard: 3 gleichzeitige Downloads**
- Jeder Download läuft in einem separaten Thread
- Die Download-Queue wird kontinuierlich überwacht und neue Downloads automatisch gestartet
- Downloads können während des Herunterladens pausiert oder gestoppt werden

### Komponenten

#### 1. **DownloadQueueManager** (`download_manager.py`)

```python
class DownloadQueueManager:
    def __init__(self, database=None, max_concurrent_downloads=3):
        # ThreadPool für parallele Downloads
        self.thread_pool = ThreadPoolExecutor(max_workers=max_concurrent_downloads)
        # Track aktive Worker
        self.active_workers = set()
```

**Schlüsselfunktionen:**

- `add_download()`: **NEU** - Erstellt einen separaten Job für **jede Episode**
- `start_queue_processor()`: Startet den Queue-Prozessor mit Thread-Pool
- `_process_queue()`: Verwaltet die parallele Verarbeitung
  - Prüft verfügbare Worker-Slots
  - Startet neue Downloads, wenn Kapazität verfügbar ist
  - Benutzt Callbacks um Worker zu trackieren
- `_process_download_job()`: Verarbeitet einen **einzelnen Episode-Download**

#### 2. **Konfiguration** (`config.py`)

```python
# Standardmäßig 3 parallele Downloads
DEFAULT_MAX_CONCURRENT_DOWNLOADS = 5  # (aktuell auf 5 konfiguriert)
```

#### 3. **API Responses** (`app.py`)

```json
{
  "success": true,
  "message": "Download added to queue: 12 episode(s) will download in parallel",
  "episode_count": 12,
  "queue_ids": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
  "max_concurrent": 3
}
```

## Verwendung

### Web-Interface

1. **Mehrere Episoden auswählen:**
   - Wählen Sie z.B. 12 Episoden aus

2. **Download starten:**
   - System zeigt an: "Download started for 12 episodes (3 parallel downloads)"
   - 3 werden sofort gestartet, die anderen warten

3. **Queue-Status ansehen:**
   - Das Frontend zeigt alle aktiven Downloads an
   - Fortschritt wird für jeden Episode-Download einzeln angezeigt
   - Abgeschlossene Downloads werden separat angezeigt

4. **Parallel Downloads Anpassungen:**
   - Bearbeiten Sie `DEFAULT_MAX_CONCURRENT_DOWNLOADS` in `config.py` um die Anzahl anzupassen

### Python-Code

```python
from aniworld.web.download_manager import get_download_manager

# Mit Standard 3 parallelen Downloads
manager = get_download_manager()

# Oder mit benutzerdefinierter Anzahl
manager = get_download_manager(max_concurrent_downloads=5)

# Downloads hinzufügen (erstellt einen Job pro Episode!)
queue_ids = manager.add_download(
    anime_title="Beispiel Anime",
    episode_urls=["url1", "url2", "url3", "url4"],  # 4 Episoden
    language="German Sub",
    provider="VOE",
    total_episodes=4
)
# queue_ids = [1, 2, 3, 4]  # Eine ID pro Episode!

# Queue starten
manager.start_queue_processor()

# Status abrufen
status = manager.get_queue_status()
print(f"Aktive Downloads: {len(status['active'])}")
# Könnte z.B. 3 aktive sein (die ersten 3 Episoden)
```

## Fortschritt-Tracking

### Frontend-Display

Das Web-Interface zeigt für jeden Episode-Download an:
- **Gesamt-Fortschritt:** 0% oder 100% (einzelne Episode)
- **Aktuelle Episode Fortschritt:** Detaillierter Fortschrittsbalken (0-100%)
- **Status:** queued, downloading, completed, failed
- **Details:** Anime-Name und Episode-Nummer

**Beispiel mit 3 parallelen Downloads:**
```
Episode 1: ████░░░░░░ 40%
Episode 2: ██░░░░░░░░ 20%
Episode 3: ██████░░░░ 60%
Episode 4: Queued
Episode 5: Queued
...
```

### API-Endpunkt

```
GET /api/queue-status
```

Beispiel-Response:
```json
{
  "success": true,
  "queue": {
    "active": [
      {
        "id": 1,
        "anime_title": "Anime A",
        "status": "downloading",
        "completed_episodes": 1,  # 1 = fertig, da 1 Episode pro Job
        "total_episodes": 1,
        "progress_percentage": 40.0,
        "current_episode_progress": 40.0,
        "current_episode": "Downloading Anime A - Episode 1 (Season 1) - 40.0%"
      },
      {
        "id": 2,
        "anime_title": "Anime A",
        "status": "downloading",
        "completed_episodes": 0,
        "total_episodes": 1,
        "progress_percentage": 20.0,
        "current_episode_progress": 20.0,
        "current_episode": "Downloading Anime A - Episode 2 (Season 1) - 20.0%"
      },
      {
        "id": 3,
        "anime_title": "Anime A",
        "status": "downloading",
        "completed_episodes": 0,
        "total_episodes": 1,
        "progress_percentage": 60.0,
        "current_episode_progress": 60.0,
        "current_episode": "Downloading Anime A - Episode 3 (Season 1) - 60.0%"
      }
    ],
    "completed": [...]
  }
}
```

## Performance-Tipps

### Optimale Worker-Anzahl

```python
# Empfohlene Einstellungen:
# - Langsame Internetverbindung: 1-2 Worker
# - Standard-Internet: 3-4 Worker  ← EMPFOHLEN
# - Schnelle Internetverbindung: 5-6 Worker
DEFAULT_MAX_CONCURRENT_DOWNLOADS = 3
```

### Ressourcen-Management

- Jeder Worker-Thread verbraucht ~10-20 MB Speicher
- Die Bandbreitenbegrenzung kommt von Ihrer Internetverbindung, nicht vom Downloader
- Bei zu vielen parallelen Downloads kann die CPU-Auslastung durch Netzwerk-I/O steigen

### Geschwindigkeit

Mit parallelen Downloads können Sie die Gesamtdownloadzeit um den Faktor der parallelen Slots reduzieren:
- 12 Episoden à 500 MB = 6 GB
- **Sequenziell** (1 Download): ~2 Stunden
- **Parallel (3 Downloads)**: ~40 Minuten
- **Parallel (5 Downloads)**: ~25 Minuten

## Implementierungsdetails

### Thread-Sicherheit

Alle freigegebenen Ressourcen sind mit `threading.Lock` geschützt:

```python
with self._queue_lock:
    # Sichere Datenbank-Operationen
    download = self._active_downloads[queue_id]
```

### Worker Lifecycle

1. **Neue Downloads starten:** `_process_queue()` prüft verfügbare Slots
2. **Job einreichen:** `thread_pool.submit(self._process_download_job, job)`
3. **Callback hinzufügen:** `worker_future.add_done_callback(...)`
4. **Cleanup:** Automatisches Entfernen aus `active_workers` nach Completion

### Fehlerbehandlung

- Einzelne Episode-Fehler stoppen nicht andere Downloads
- Fehler werden in den Download-Job-Status aufgezeichnet
- Fehlgeschlagene Downloads können später manuell erneut gestartet werden

## Änderungen von vorheriger Version

### Vorher (Monolithischer Download)
```
12 ausgewählte Episoden → 1 Download-Job → alle Episoden sequenziell
Gesamtdauer: ~2 Stunden
```

### Nachher (Parallele Episode-Downloads)
```
12 ausgewählte Episoden → 12 separate Download-Jobs → 3 parallel
Gesamtdauer: ~40 Minuten
```

## Bekannte Einschränkungen

- Die Anzahl paralleler Downloads ist zur Laufzeit nicht änderbar (wird beim Start gesetzt)
- Windows kann Probleme mit zu vielen parallelen Dateisystem-Operationen haben (empfohlen: ≤5)
- Einige ISPs drosseln aggressive parallele Verbindungen

## Zukünftige Verbesserungen

- [ ] Dynamische Worker-Skalierung basierend auf Systemressourcen
- [ ] Bandbreitenbegrenzung pro Worker
- [ ] Priorisierung von Downloads
- [ ] Pause/Resume für individuelle Episode-Downloads
- [ ] WebSocket-Updates statt Polling
- [ ] Bessere Fehlerbehandlung mit Retry-Logik
