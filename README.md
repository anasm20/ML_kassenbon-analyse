# Kassenbon-Analyse

Streamlit-Anwendung, die Kassenbons einliest und relevante Informationen
(**Datum, Händlername, Gesamtsumme, einzelne Positionen, Zahlungsmethode**)
mit zwei Modellen extrahiert und gegenüberstellt:

1. **Azure AI Document Intelligence** (`prebuilt-receipt`) – liefert direkt
   **strukturierte Felder**.
2. **Mistral Document AI / OCR** (Azure AI Foundry) – liefert reinen
   **OCR-Text**, aus dem die Felder anschließend heuristisch geparst werden.

> **Hinweis zur Modellwahl:** Die Aufgabenstellung nennt *Document Intelligence
> + **Mistral Document AI** wird als günstiger
> Bild-zu-Text-Ersatz eingesetzt. Die App vergleicht damit weiterhin zwei
> Modelle unter identischen Bedingungen – die Grundlage für das Testprotokoll.

---

## 1. Voraussetzungen

- Python **3.9–3.11** empfohlen (funktioniert ab 3.8).
- Zwei Azure-Ressourcen, bereits angelegt:
  - Azure AI Document Intelligence (`NAME-receipt-di`)
  - Mistral Document AI / OCR in Azure AI Foundry (`mistral-document-ai-2512`)

## 2. Installation

```bash
# 1) virtuelle Umgebung anlegen (optional, empfohlen)
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 2) Abhängigkeiten installieren
pip install -r requirements.txt
```

## 3. Zugangsdaten eintragen

Die Datei `.env.example` nach `.env` kopieren und die echten Werte eintragen:

```bash
# Windows:
copy .env.example .env
# macOS/Linux:
cp .env.example .env
```

Inhalt der `.env`:

```env
AZURE_DI_ENDPOINT=https://NAME.azure.com/
AZURE_DI_KEY=DEIN_DOCUMENT_INTELLIGENCE_KEY

AZURE_MISTRAL_ENDPOINT=https://NAME-foundry.services.ai.azure.com/providers/mistral/azure/ocr
AZURE_MISTRAL_KEY=DEIN_MISTRAL_KEY
AZURE_MISTRAL_MODEL=mistral-document-ai-2512
```

> Die `.env` mit den echten Schlüsseln **nicht** in die Abgabe-ZIP legen –
> es genügt `.env.example`.

## 4. App starten

```bash
streamlit run app.py
```

Der Browser öffnet sich automatisch (sonst `http://localhost:8501`).

## 5. Bedienung

1. **Bildaufnahme:** Tab *Bild hochladen* (JPG/PNG/PDF) **oder** Tab *Webcam*.
2. **Analyse:** Auf **„Kassenbon analysieren“** klicken.
3. **Visualisierung:** Beide Modelle laufen parallel; die App zeigt
   - eine kompakte **Vergleichstabelle**,
   - je Modell die extrahierten Felder und die Positionsliste,
   - den Roh-OCR-Text und die Roh-JSON-Antwort (einklappbar).
4. **Export:** Ergebnisse können als JSON heruntergeladen werden (praktisch
   fürs Testprotokoll).

In der **Seitenleiste** lässt sich der Status der Zugangsdaten prüfen und
einzelne Modelle an-/abschalten.

---

## 6. Projektstruktur

```
kassenbon-analyse/
├── app.py                 # Streamlit-UI (Upload, Webcam, Visualisierung, Vergleich)
├── receipt_extractors.py  # Beide Extraktoren + Heuristik-Parser
├── requirements.txt       # Abhängigkeiten
├── .env.example           # Vorlage für Zugangsdaten
├── README.md              # diese Datei
├── TESTPROTOKOLL.md       # Testplan + Protokoll-Vorlage (als PDF exportieren)
└── testbilder/            # Kassenbon-Bilder der 6 Testszenarien
```

## 7. Funktionsweise (Kurzüberblick)

| Schritt              | Document Intelligence            | Mistral Document AI            |
|----------------------|----------------------------------|-------------------------------|
| Eingabe              | Bild-Bytes                       | base64-Data-URL               |
| Modell               | `prebuilt-receipt`               | `mistral-document-ai-2512`    |
| Ausgabe              | strukturierte Felder             | OCR-Markdown                  |
| Feld-Extraktion      | direkt aus dem Modell            | Heuristik-Parser (Regex)      |
| Zahlungsmethode      | aus Volltext (Heuristik)         | aus OCR-Text (Heuristik)      |

Das Mistral-Modell liefert nur Text; die Felder werden in
`parse_receipt_text()` über deutsche Schlüsselwörter (`SUMME`, `ZU ZAHLEN`,
`BAR`, `EC-KARTE`, …) und Beträge/Daten per Regex erkannt. Die bewussten
Grenzen dieses Ansatzes werden im Testprotokoll dokumentiert.

## 8. Bewertungslogik des Testprotokolls

Für jedes der sechs Szenarien wird je Modell und je Feld notiert, ob die
Extraktion **korrekt / teilweise / falsch** war. Siehe `TESTPROTOKOLL.md`.

## 9. Bekannte Fehlerquellen / Troubleshooting

- **`HTTP 401/403` bei Mistral:** Schlüssel falsch oder Header-Stil.
  Die App sendet `Authorization: Bearer` **und** `api-key`. Falls dein
  Deployment eine `api-version` verlangt, in der `.env`
  `AZURE_MISTRAL_API_VERSION=...` setzen.
- **`InvalidContent` bei Document Intelligence:** Bilddatei beschädigt oder
  Format nicht unterstützt (JPG/PNG/PDF verwenden).
- **Keine Positionen erkannt:** bei sehr schlechter Bildqualität normal –
  genau das soll im Testprotokoll dokumentiert werden.
