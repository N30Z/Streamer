# Parallele Downloads

Das AniWorld Downloader System unterstützt jetzt **parallele Downloads**! Dies ermöglicht es, mehrere Anime-Episoden gleichzeitig herunterzuladen, wodurch die Gesamtdownloadzeit erheblich reduziert wird.

## Funktionsweise

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

- `start_queue_processor()`: Startet den Queue-Prozessor mit Thread-Pool
- `_process_queue()`: Verwaltet die parallele Verarbeitung
  - Prüft verfügbare Worker-Slots
  - Startet neue Downloads, wenn Kapazität verfügbar ist
  - Benutzt Callbacks um Worker zu trackieren
- `_process_download_job()`: Verarbeitet einen einzelnen Download

#### 2. **Konfiguration** (`config.py`)

```python
# Standardmäßig 3 parallele Downloads
DEFAULT_MAX_CONCURRENT_DOWNLOADS = 3
```

## Verwendung

### Web-Interface

1. **Mehrere Downloads starten:**
   - Sie können mehrere Download-Anfragen hintereinander starten
   - Diese werden in die Queue eingefügt und automatisch parallel verarbeitet

2. **Queue-Status ansehen:**
   - Das Frontend zeigt alle aktiven Downloads an
   - Fortschritt wird für jeden Download einzeln angezeigt
   - Abgeschlossene Downloads werden separat angezeigt

3. **Parallel Downloads Anpassungen:**
   - Bearbeiten Sie `DEFAULT_MAX_CONCURRENT_DOWNLOADS` in `config.py` um die Anzahl anzupassen

### Python-Code

```python
from aniworld.web.download_manager import get_download_manager

# Mit Standard 3 parallelen Downloads
manager = get_download_manager()

# Oder mit benutzerdefinierter Anzahl
manager = get_download_manager(max_concurrent_downloads=5)

# Downloads hinzufügen
queue_id = manager.add_download(
    anime_title="Beispiel Anime",
    episode_urls=[...],
    language="German Sub",
    provider="VOE",
    total_episodes=12
)

# Queue starten
manager.start_queue_processor()

# Status abrufen
status = manager.get_queue_status()
print(f"Aktive Downloads: {len(status['active'])}")
```

## Fortschritt-Tracking

### Frontend-Display

Das Web-Interface zeigt für jeden Download an:
- **Gesamt-Fortschritt:** Prozentsatz + Episoden-Zähler (3/12)
- **Aktuelle Episode Fortschritt:** Seperater Fortschrittsbalken für die gerade downloadete Episode
- **Status:** queued, downloading, completed, failed
- **Details:** Aktuelle Episode und Speed/ETA

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
        "completed_episodes": 3,
        "total_episodes": 12,
        "progress_percentage": 27.5,
        "current_episode_progress": 50.0,
        "current_episode": "Downloading Anime A - Episode 4 (Season 1) - 50.0%"
      },
      {
        "id": 2,
        "anime_title": "Anime B",
        "status": "downloading",
        "completed_episodes": 1,
        "total_episodes": 13,
        "progress_percentage": 10.2,
        "current_episode_progress": 30.0,
        "current_episode": "Downloading Anime B - Episode 2 (Season 1) - 30.0%"
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
# - Standard-Internet: 3-4 Worker
# - Schnelle Internetverbindung: 5-6 Worker
DEFAULT_MAX_CONCURRENT_DOWNLOADS = 3  # Default ist ein guter Kompromiss
```

### Ressourcen-Management

- Jeder Worker-Thread verbraucht ~10-20 MB Speicher
- Die Bandbreitenbegrenzung kommt von Ihrer Internetverbindung, nicht vom Downloader
- Bei zu vielen parallelen Downloads kann die CPU-Auslastung durch Netzwerk-I/O steigen

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

- Einzelne Download-Fehler stoppenat nicht andere Downloads
- Fehler werden in den Download-Job-Status aufgezeichnet
- Fehlgeschlagene Downloads können später manuell erneut gestartet werden

## Bekannte Einschränkungen

- Die Anzahl paralleler Downloads ist zur Laufzeit nicht änderbar (wird beim Start gesetzt)
- Windows kann Probleme mit zu vielen parallelen Dateisystem-Operationen haben (empfohlen: ≤5)
- Einige ISPs drosseln aggressive parallele Verbindungen

## Zukünftige Verbesserungen

- [ ] Dynamische Worker-Skalierung basierend auf Systemressourcen
- [ ] Bandbreitenbegrenzung pro Worker
- [ ] Priorisierung von Downloads
- [ ] Pause/Resume für individuelle Downloads
- [ ] WebSocket-Updates statt Polling
