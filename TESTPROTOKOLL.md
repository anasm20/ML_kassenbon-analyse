# Testprotokoll – Kassenbon-Analyse

**Autor:in:** _[Name eintragen]_
**Datum der Durchführung:** _[TT.MM.JJJJ]_
**Verglichene Modelle:**
1. Azure AI Document Intelligence (`prebuilt-receipt`) – strukturierte Extraktion
2. Mistral Document AI / OCR (`mistral-document-ai-2512`) – OCR + Heuristik-Parser

> **Hinweis:** Diese Datei ist die ausfüllbare Vorlage. Nach dem Durchführen der
> Tests als **PDF** exportieren (z. B. in VS Code per Markdown-PDF-Extension, mit
> `pandoc TESTPROTOKOLL.md -o testprotokoll.pdf` oder über „Drucken → PDF“) und
> als `testprotokoll.pdf` der Abgabe-ZIP beilegen.

---

## 1. Zielsetzung

Bewertet werden **Robustheit** und **Genauigkeit** beider Modelle bei der
Extraktion der fünf Zielfelder
**Datum, Händlername, Gesamtsumme, Positionen, Zahlungsmethode**
unter sechs erschwerten Aufnahmebedingungen.

## 2. Testumgebung

| Punkt                | Wert                                            |
|----------------------|-------------------------------------------------|
| Betriebssystem       | _[z. B. Windows 11]_                            |
| Python-Version       | _[z. B. 3.11]_                                  |
| Streamlit-Version    | _[`streamlit --version`]_                        |
| Azure-Region (DI)    | _[z. B. West Europe]_                           |
| Foundry-Region       | _[z. B. Sweden Central]_                        |
| Aufnahmegerät        | _[Webcam / Smartphone-Kamera / Scan]_           |

## 3. Testmethodik

1. Pro Szenario wird **dasselbe Motiv** verwendet, nur die Aufnahmebedingung
   variiert (z. B. derselbe Bon zerknittert/dunkel/verwischt).
2. Jedes Bild wird einmal mit beiden Modellen analysiert.
3. Für jedes Zielfeld wird die Erkennung bewertet:

   | Bewertung      | Bedeutung                                              |
   |----------------|--------------------------------------------------------|
   | ✅ korrekt      | Wert exakt korrekt erkannt                              |
   | 🟡 teilweise   | Wert teilweise korrekt (Tippfehler, Format, unvollständig) |
   | ❌ falsch       | Wert falsch oder gar nicht erkannt                      |

4. **Feld-Genauigkeit je Modell/Szenario** = Anteil korrekter Felder
   (✅ = 1, 🟡 = 0,5, ❌ = 0) an den 5 Zielfeldern.
5. **Positionen** werden gesondert bewertet (Anzahl korrekt erkannter
   Positionen / tatsächliche Anzahl).
6. Die JSON-Exporte der App werden je Testfall gespeichert (Nachvollziehbarkeit).

## 4. Testszenarien

| Nr. | Szenario                | Beschreibung                                | Testbild               |
|-----|-------------------------|---------------------------------------------|------------------------|
| 1   | Standardkassenbon       | Deutlich lesbar, heller Hintergrund, klar   | `01_standard.jpg`      |
| 2   | Zerknitterter Kassenbon | Papier mit Falten und Unebenheiten          | `02_zerknittert.jpg`   |
| 3   | Dunkler Hintergrund     | Geringer Kontrast                           | `03_dunkel.jpg`        |
| 4   | Verwischte Schrift      | Teilweise unleserliche Tinte                | `04_verwischt.jpg`     |
| 5   | Handschriftl. Ergänzung | Handschriftliche Markierungen/Notizen       | `05_handschrift.jpg`   |
| 6   | Teilweise verdeckt      | Informationen teilweise nicht sichtbar      | `06_verdeckt.jpg`      |

---

## 5. Ergebnisse je Testfall

> Für jedes Szenario die folgende Tabelle ausfüllen (Werte aus der App / dem
> JSON-Export eintragen) und die beobachteten Probleme notieren.

### 5.1 Szenario 1 – Standardkassenbon

**Erwartete Werte (Ground Truth):** Datum `___` · Händler `___` · Summe `___` · Zahlungsart `___` · #Positionen `___`

| Feld            | Document Intelligence | Bewertung | Mistral OCR | Bewertung |
|-----------------|-----------------------|-----------|-------------|-----------|
| Datum           |                       |           |             |           |
| Händlername     |                       |           |             |           |
| Gesamtsumme     |                       |           |             |           |
| Zahlungsmethode |                       |           |             |           |
| Positionen (#)  |                       |           |             |           |

- **Feld-Genauigkeit:** DI = ___ %  ·  Mistral = ___ %
- **Beobachtungen / Probleme:** _[…]_

### 5.2 Szenario 2 – Zerknitterter Kassenbon

**Erwartete Werte:** Datum `___` · Händler `___` · Summe `___` · Zahlungsart `___` · #Positionen `___`

| Feld            | Document Intelligence | Bewertung | Mistral OCR | Bewertung |
|-----------------|-----------------------|-----------|-------------|-----------|
| Datum           |                       |           |             |           |
| Händlername     |                       |           |             |           |
| Gesamtsumme     |                       |           |             |           |
| Zahlungsmethode |                       |           |             |           |
| Positionen (#)  |                       |           |             |           |

- **Feld-Genauigkeit:** DI = ___ %  ·  Mistral = ___ %
- **Beobachtungen / Probleme:** _[…]_

### 5.3 Szenario 3 – Dunkler Hintergrund

**Erwartete Werte:** Datum `___` · Händler `___` · Summe `___` · Zahlungsart `___` · #Positionen `___`

| Feld            | Document Intelligence | Bewertung | Mistral OCR | Bewertung |
|-----------------|-----------------------|-----------|-------------|-----------|
| Datum           |                       |           |             |           |
| Händlername     |                       |           |             |           |
| Gesamtsumme     |                       |           |             |           |
| Zahlungsmethode |                       |           |             |           |
| Positionen (#)  |                       |           |             |           |

- **Feld-Genauigkeit:** DI = ___ %  ·  Mistral = ___ %
- **Beobachtungen / Probleme:** _[…]_

### 5.4 Szenario 4 – Verwischte Schrift

**Erwartete Werte:** Datum `___` · Händler `___` · Summe `___` · Zahlungsart `___` · #Positionen `___`

| Feld            | Document Intelligence | Bewertung | Mistral OCR | Bewertung |
|-----------------|-----------------------|-----------|-------------|-----------|
| Datum           |                       |           |             |           |
| Händlername     |                       |           |             |           |
| Gesamtsumme     |                       |           |             |           |
| Zahlungsmethode |                       |           |             |           |
| Positionen (#)  |                       |           |             |           |

- **Feld-Genauigkeit:** DI = ___ %  ·  Mistral = ___ %
- **Beobachtungen / Probleme:** _[…]_

### 5.5 Szenario 5 – Handschriftliche Ergänzungen

**Erwartete Werte:** Datum `___` · Händler `___` · Summe `___` · Zahlungsart `___` · #Positionen `___`

| Feld            | Document Intelligence | Bewertung | Mistral OCR | Bewertung |
|-----------------|-----------------------|-----------|-------------|-----------|
| Datum           |                       |           |             |           |
| Händlername     |                       |           |             |           |
| Gesamtsumme     |                       |           |             |           |
| Zahlungsmethode |                       |           |             |           |
| Positionen (#)  |                       |           |             |           |

- **Feld-Genauigkeit:** DI = ___ %  ·  Mistral = ___ %
- **Beobachtungen / Probleme:** _[…]_

### 5.6 Szenario 6 – Teilweise verdeckt oder zerrissen

**Erwartete Werte:** Datum `___` · Händler `___` · Summe `___` · Zahlungsart `___` · #Positionen `___`

| Feld            | Document Intelligence | Bewertung | Mistral OCR | Bewertung |
|-----------------|-----------------------|-----------|-------------|-----------|
| Datum           |                       |           |             |           |
| Händlername     |                       |           |             |           |
| Gesamtsumme     |                       |           |             |           |
| Zahlungsmethode |                       |           |             |           |
| Positionen (#)  |                       |           |             |           |

- **Feld-Genauigkeit:** DI = ___ %  ·  Mistral = ___ %
- **Beobachtungen / Probleme:** _[…]_

---

## 6. Gesamtauswertung

| Szenario                | Feld-Genauigkeit DI | Feld-Genauigkeit Mistral |
|-------------------------|---------------------|--------------------------|
| 1 Standard              |                     |                          |
| 2 Zerknittert           |                     |                          |
| 3 Dunkler Hintergrund   |                     |                          |
| 4 Verwischte Schrift    |                     |                          |
| 5 Handschrift           |                     |                          |
| 6 Teilweise verdeckt    |                     |                          |
| **Durchschnitt**        |                     |                          |

## 7. Beispiele korrekt / falsch erkannter Informationen

- **Korrekt erkannt:** _[z. B. „Document Intelligence erkannte die Summe 6,38 € im Standardfall exakt."]_
- **Falsch erkannt:** _[z. B. „Mistral interpretierte bei verwischter Schrift '8' als '3' → Summe falsch."]_
- _(je 2–3 konkrete Beispiele mit Screenshot/JSON-Auszug)_

## 8. Fazit

_[Zusammenfassende Bewertung: Welches Modell ist robuster bei welchem Szenario?
Wo liegen die Grenzen des OCR+Heuristik-Ansatzes (Mistral) gegenüber der
strukturierten Extraktion (Document Intelligence)? Empfehlung.]_
