# CEDmate Analytics API

Die CEDmate Analytics API ist das Auswertungs-Backend der [CEDmate-Anwendung](https://github.com/ahmad-kalaf/CEDmate). CEDmate speichert Symptom-, Stuhlgang-, Ernährungs- und Stimmungseinträge in Cloud Firestore. Die API liest diese Daten benutzerbezogen aus, bereitet sie für Diagramme auf und erzeugt bei Bedarf einen PDF-Bericht. Dadurch bleiben die Datenanalyse und die PDF-Erstellung von der Flutter-Oberfläche getrennt.

Dieses Repository enthält **keine eigenständige Benutzeroberfläche**. Die API ist für die Integration in CEDmate gedacht; sie kann für Entwicklungszwecke auch direkt über HTTP oder die Python-Kommandozeile aufgerufen werden.

## Funktionsumfang

- Firestore-Daten aus vier benutzerbezogenen Subcollections laden.
- Zeitreihen und Häufigkeiten mit pandas aufbereiten.
- Diagramme mit matplotlib als PNG-Dateien erstellen.
- Einen PDF-Bericht mit Titelblatt, vorhandenen Diagrammen und Tabellen der Rohdaten erzeugen.
- Erzeugte Dateien über HTTP-URLs bereitstellen.

Der PDF-Export übernimmt pro Datenbereich höchstens die ersten 30 Rohdatensätze in die Tabelle. Die erzeugten Dateien werden im lokalen Verzeichnis `output/` gespeichert.

## Architektur und Datenfluss

```text
CEDmate (Flutter)
     |
     | HTTP: GET /analytics oder GET /export
     v
FastAPI (api.py)
     |
     +--> Firebase Admin SDK --> Cloud Firestore
     |                           users/{uid}/...
     |
     +--> cedmate_analytics.py --> pandas --> matplotlib --> PNG
     |
     +--> export_pdf.py -------------------------------> PDF
     |
     +--> output/ --> statische URLs unter /output/...
```

Die Anwendungslogik ist auf drei Module verteilt:

- [`api.py`](api.py): HTTP-Endpunkte, Header-Prüfungen, CORS-Konfiguration und Bereitstellung erzeugter Dateien.
- [`cedmate_analytics.py`](cedmate_analytics.py): Firebase-Initialisierung, Firestore-Abfragen, Spaltenerkennung und Diagrammerzeugung.
- [`export_pdf.py`](export_pdf.py): Zusammenstellung der Diagramme und Rohdaten in einem mehrseitigen PDF.

### Verwendete Firestore-Daten

| Firestore-Pfad | Auswertung |
| --- | --- |
| `users/{uid}/stuhlgaenge` | Streudiagramm zu zeitlich erfassten, numerisch auswertbaren Einträgen |
| `users/{uid}/stimmungen` | Liniendiagramm einer erkannten numerischen Größe über die Zeit |
| `users/{uid}/symptoms` | Streudiagramm der Symptomintensität über die Zeit |
| `users/{uid}/mahlzeiten` | Balkendiagramm mit der Anzahl der Mahlzeiten pro Tag |

Zeit- und Wertespalten werden anhand von Datentypen und Feldnamen erkannt. Können keine geeigneten Daten bestimmt werden, wird für den betreffenden Bereich kein Diagramm erzeugt. Bei mehreren numerischen Feldern kann die generische Erkennung derzeit eine fachlich nicht beabsichtigte Größe auswählen; die Diagramme sollten deshalb vor einer fachlichen Verwendung geprüft werden.

## API-Endpunkte

Die API stellt automatisch auch die interaktive FastAPI-Dokumentation unter `/docs` bereit.

| Methode | Pfad | Beschreibung |
| --- | --- | --- |
| `GET` | `/` | Einfacher Status-Endpunkt |
| `GET` | `/analytics?user={uid}` | PNG-Diagramme für die angegebene Firebase-UID erzeugen |
| `GET` | `/export?user={uid}` | PDF-Bericht für die angegebene Firebase-UID erstellen |
| `GET` | `/output/{filename}` | Erzeugte PNG- oder PDF-Datei abrufen |

`/analytics` und `/export` erwarten einen Header `x-api-key`. Zusätzlich prüft die aktuelle Implementierung den `Origin`-Header beziehungsweise bei Requests ohne Origin den `User-Agent`. Das sind technische Prüfungen des derzeitigen Prototyps und keine belastbare Authentifizierung eines Firebase-Benutzers.

Beispiel einer Antwort von `/analytics`:

```json
{
  "status": "ok",
  "user": "<firebase-uid>",
  "results": {
    "stuhlgang": "https://cedmate-analytics-api.onrender.com/output/stuhlgang_scatter_<firebase-uid>.png",
    "stimmung": null,
    "symptome": null,
    "mahlzeit": null
  }
}
```

Die Felder in `results` enthalten eine URL oder `null`, wenn kein entsprechendes Diagramm erzeugt werden konnte. `/export` liefert die Felder `status`, `user` und `pdf`, wobei `pdf` auf die erzeugte Datei verweist.

## Lokale Entwicklung

**Voraussetzungen**

- Python 3.11 oder 3.12
- Zugriff auf ein Firebase-Projekt mit Cloud Firestore und passenden CEDmate-Testdaten
- Ein Firebase-Service-Account mit den erforderlichen Berechtigungen

Repository klonen und virtuelle Umgebung erstellen:

```bash
git clone https://github.com/ahmad-kalaf/cedmate_analytics_api.git
cd cedmate_analytics_api
python -m venv .venv
```

Virtuelle Umgebung unter Linux oder macOS aktivieren:

```bash
source .venv/bin/activate
```

Unter Windows PowerShell stattdessen:

```powershell
.venv\Scripts\Activate.ps1
```

Abhängigkeiten installieren:

```bash
pip install -r requirements.txt
```

Anschließend den Firebase-Service-Account als `serviceAccount.json` im Projektverzeichnis ablegen oder seinen Speicherort über `SERVICE_ACCOUNT_PATH` festlegen. **Service-Account-Dateien dürfen nicht in Git eingecheckt oder öffentlich geteilt werden.** Für Tests sollte ein eigenes Firebase-Projekt mit fiktiven Daten verwendet werden.

Beispiel zum Setzen eines API-Schlüssels unter Linux oder macOS:

```bash
export API_KEY="<lokaler-testschluessel>"
export SERVICE_ACCOUNT_PATH="/absoluter/pfad/serviceAccount.json"
uvicorn api:app --host 127.0.0.1 --port 10000
```

Unter Windows PowerShell:

```powershell
$env:API_KEY="<lokaler-testschluessel>"
$env:SERVICE_ACCOUNT_PATH="C:\Pfad\zu\serviceAccount.json"
uvicorn api:app --host 127.0.0.1 --port 10000
```

### Endpunkte lokal testen

Ohne Firebase-Zugriff lässt sich zunächst nur der Status-Endpunkt prüfen:

```bash
curl http://127.0.0.1:10000/
```

Für eine Auswertung werden ein gültiger Testbenutzer in Firestore und der konfigurierte API-Schlüssel benötigt:

```bash
curl -H "x-api-key: <lokaler-testschluessel>" \
     -H "User-Agent: CEDmate" \
     "http://127.0.0.1:10000/analytics?user=<firebase-uid>"
```

Die erzeugten PNG-Dateien liegen anschließend in `output/`. Alternativ lässt sich die Diagrammerzeugung ohne HTTP-Server ausführen:

```bash
python cedmate_analytics.py --user <firebase-uid> --creds /pfad/serviceAccount.json
```

**Wichtig für lokale Tests:** Die Antwort-URLs werden in [`api.py`](api.py) derzeit fest mit der Render-Domain aufgebaut. Eine lokal gestartete Instanz erzeugt die Dateien zwar lokal, liefert aber weiterhin URLs zur entfernten Domain. Die lokal gespeicherten Dateien sind unter `http://127.0.0.1:10000/output/<dateiname>` erreichbar. Für eine eigenständige Bereitstellung muss die Basis-URL in `api.py` konfigurierbar gemacht werden.

## Tech-Stack und Deployment

| Bereich | Technologie |
| --- | --- |
| HTTP-API | FastAPI, Uvicorn |
| Firebase-Zugriff | Firebase Admin SDK, Cloud Firestore |
| Datenaufbereitung | pandas, NumPy |
| Diagramme | matplotlib |
| PDF-Export | matplotlib `PdfPages` |
| Deployment-Konfiguration | Render (`render.yaml`) |

Die Datei [`render.yaml`](render.yaml) definiert die Installation über `pip install -r requirements.txt` und den Start mit `uvicorn api:app --host 0.0.0.0 --port 10000`. Im Hosting müssen `API_KEY` sowie ein gültiger Service-Account-Pfad beziehungsweise eine sicher bereitgestellte Service-Account-Datei konfiguriert werden. Die im Code fest eingetragene öffentliche Render-Domain ist keine Voraussetzung für den lokalen Serverstart, beeinflusst aber die zurückgegebenen Datei-URLs.

## Sicherheit und bekannte Einschränkungen

**Die aktuelle Implementierung ist nicht ausreichend für den produktiven Umgang mit echten Gesundheitsdaten abgesichert.** Insbesondere:

- Die API akzeptiert eine frei angegebene Firebase-UID im Parameter `user`, verifiziert aber kein Firebase-ID-Token und prüft nicht, ob der Aufrufer zu dieser UID gehört.
- Der API-Schlüssel besitzt im Quellcode einen fest eingebauten Fallback-Wert; auch der zugehörige Flutter-Client enthält einen festen Schlüssel. Ein clientseitig bekannter Schlüssel ist keine Benutzerautorisierung.
- `Origin`- und `User-Agent`-Prüfungen lassen sich nicht als Identitätsnachweis verwenden.
- Dateien unter `/output/` sind ohne Benutzerautorisierung öffentlich abrufbar. Dateinamen enthalten die Benutzerkennung; bei erneuter Erstellung können Dateien überschrieben werden. Eine automatische Bereinigung ist nicht implementiert.
- Ein PDF-Export liest Firestore-Daten erneut ein und beschränkt die Tabellen auf 30 Zeilen je Collection. Es handelt sich daher nicht um einen vollständigen Rohdatenexport.
- Für die Auswertung werden Felder heuristisch ausgewählt. Insbesondere bei Stimmung und Stuhlgang ist die fachlich richtige Messgröße nicht in allen Datenkonstellationen sichergestellt.
- Es gibt derzeit keine automatisierten Tests im Repository.

Vor dem Einsatz mit echten Daten sind insbesondere eine tokenbasierte Benutzerauthentifizierung, die serverseitige Prüfung der Zugriffsberechtigung, geschützter Dateizugriff sowie eine sichere Verwaltung der Zugangsdaten erforderlich.

## Projektstruktur

```text
api.py                     # HTTP-Endpunkte, Zugriffsprüfungen, statische Dateien
cedmate_analytics.py       # Firestore-Zugriff und PNG-Diagramme
export_pdf.py              # PDF-Berichte
requirements.txt           # Python-Abhängigkeiten
render.yaml                # Render-Konfiguration
analytics_dokumentation.md # Ergänzende technische Dokumentation
output/                    # Zur Laufzeit erzeugte Dateien
```

## Weiterführende Dokumentation

- [Technische Analytics-Dokumentation](analytics_dokumentation.md)
- [CEDmate – Flutter-Anwendung](https://github.com/ahmad-kalaf/CEDmate)
