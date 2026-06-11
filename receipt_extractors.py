"""
receipt_extractors.py
---------------------
Enthaelt die beiden Extraktions-Engines fuer die Kassenbon-Analyse:

1. Azure AI Document Intelligence (prebuilt-receipt)
   -> liefert direkt STRUKTURIERTE Felder (Datum, Haendler, Summe, Positionen ...)

2. Mistral Document AI / OCR (Azure AI Foundry)
   -> liefert reinen OCR-TEXT (Markdown). Die Felder werden anschliessend
      heuristisch aus dem Text geparst.

Der Vergleich beider Ansaetze (strukturierte Extraktion vs. OCR + Parsing).
"""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass, field as dc_field
from typing import Any, Optional

import requests


# ---------------------------------------------------------------------------
# Gemeinsames Ergebnis-Datenmodell
# ---------------------------------------------------------------------------
@dataclass
class ReceiptResult:
    """Normalisiertes Ergebnis, damit beide Modelle gleich dargestellt werden."""
    engine: str
    merchant: Optional[str] = None
    date: Optional[str] = None
    total: Optional[str] = None
    payment_method: Optional[str] = None
    items: list[dict[str, Any]] = dc_field(default_factory=list)
    raw_text: str = ""               # Roh-OCR-Text (v. a. bei Mistral)
    raw_payload: Any = None          # Roh-Antwort (dict) fuer Debug/Expander
    error: Optional[str] = None
    duration_s: Optional[float] = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "engine": self.engine,
            "merchant": self.merchant,
            "date": self.date,
            "total": self.total,
            "payment_method": self.payment_method,
            "items": self.items,
            "error": self.error,
            "duration_s": self.duration_s,
        }


# ===========================================================================
# 1) AZURE DOCUMENT INTELLIGENCE  (prebuilt-receipt)
# ===========================================================================
def _di_field_value(field: Any) -> Optional[str]:
    """
    Liest robust den Wert eines DocumentField aus, unabhaengig vom Feldtyp.
    Das neue SDK liefert je nach Feld value_string / value_date / value_currency ...
    """
    if field is None:
        return None

    # 1) Typische Skalarwerte (snake_case Attribute im neuen SDK)
    for attr in (
        "value_string", "value_date", "value_time", "value_number",
        "value_integer", "value_phone_number", "value_country_region",
        "value_selection_mark",
    ):
        val = getattr(field, attr, None)
        if val not in (None, ""):
            return str(val)

    # 2) Waehrungswert (CurrencyValue: amount + currency_symbol/code)
    currency = getattr(field, "value_currency", None)
    if currency is not None:
        amount = getattr(currency, "amount", None)
        symbol = (
            getattr(currency, "currency_symbol", None)
            or getattr(currency, "currency_code", None)
            or ""
        )
        if amount is not None:
            return f"{amount:.2f} {symbol}".strip()

    # 3) Fallback: Falls field ein dict ist (z. B. Roh-Antwort)
    if isinstance(field, dict):
        for key in ("valueString", "valueDate", "valueNumber", "content"):
            if field.get(key) not in (None, ""):
                return str(field[key])

    # 4) Letzter Fallback: der erkannte Rohtext des Feldes
    content = getattr(field, "content", None)
    return str(content) if content not in (None, "") else None


def _di_extract_items(items_field: Any) -> list[dict[str, Any]]:
    """Extrahiert die Positionsliste (Items) aus dem Receipt-Modell."""
    items: list[dict[str, Any]] = []
    if items_field is None:
        return items

    value_array = getattr(items_field, "value_array", None)
    if not value_array and isinstance(items_field, dict):
        value_array = items_field.get("valueArray")
    if not value_array:
        return items

    for entry in value_array:
        obj = getattr(entry, "value_object", None)
        if obj is None and isinstance(entry, dict):
            obj = entry.get("valueObject")
        if obj is None:
            continue

        def _f(name: str) -> Optional[str]:
            sub = obj.get(name) if hasattr(obj, "get") else getattr(obj, name, None)
            return _di_field_value(sub)

        items.append({
            "Beschreibung": _f("Description"),
            "Menge": _f("Quantity"),
            "Einzelpreis": _f("Price"),
            "Gesamtpreis": _f("TotalPrice"),
        })
    return items


def analyze_with_document_intelligence(
    image_bytes: bytes,
    endpoint: str,
    key: str,
) -> ReceiptResult:
    """Analysiert einen Kassenbon mit Azure Document Intelligence (prebuilt-receipt)."""
    import time

    result = ReceiptResult(engine="Azure Document Intelligence")
    if not endpoint or not key:
        result.error = "AZURE_DI_ENDPOINT oder AZURE_DI_KEY fehlt in der .env-Datei."
        return result

    try:
        from azure.core.credentials import AzureKeyCredential
        from azure.ai.documentintelligence import DocumentIntelligenceClient
        from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
    except ImportError as exc:
        result.error = (
            "Paket 'azure-ai-documentintelligence' nicht installiert. "
            f"Bitte requirements.txt installieren. ({exc})"
        )
        return result

    try:
        start = time.perf_counter()
        client = DocumentIntelligenceClient(
            endpoint=endpoint.rstrip("/"),
            credential=AzureKeyCredential(key),
        )
        poller = client.begin_analyze_document(
            "prebuilt-receipt",
            AnalyzeDocumentRequest(bytes_source=image_bytes),
        )
        analyze_result = poller.result()
        result.duration_s = round(time.perf_counter() - start, 2)

        # Roh-Antwort fuer Debug-Expander (als dict, falls moeglich)
        try:
            result.raw_payload = analyze_result.as_dict()
        except Exception:
            result.raw_payload = str(analyze_result)

        documents = getattr(analyze_result, "documents", None) or []
        if not documents:
            result.error = "Kein Kassenbon-Dokument erkannt."
            result.raw_text = getattr(analyze_result, "content", "") or ""
            return result

        fields = documents[0].fields or {}

        def _get(name: str) -> Any:
            return fields.get(name) if hasattr(fields, "get") else getattr(fields, name, None)

        result.merchant = _di_field_value(_get("MerchantName"))
        result.date = _di_field_value(_get("TransactionDate"))
        result.total = _di_field_value(_get("Total"))
        # Receipt-Modell hat kein dediziertes Feld "Zahlungsmethode" ->
        # aus dem Volltext heuristisch ermitteln.
        result.raw_text = getattr(analyze_result, "content", "") or ""
        result.payment_method = _guess_payment_method(result.raw_text)
        result.items = _di_extract_items(_get("Items"))

    except Exception as exc:  # noqa: BLE001
        result.error = f"Document Intelligence Fehler: {exc}"

    return result


# ===========================================================================
# 2) MISTRAL DOCUMENT AI / OCR  (Azure AI Foundry)
# ===========================================================================
def _detect_mime(image_bytes: bytes) -> str:
    """Erkennt den MIME-Typ anhand der Magic Bytes (PNG / JPEG / PDF)."""
    if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if image_bytes[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if image_bytes[:4] == b"%PDF":
        return "application/pdf"
    return "image/jpeg"


def analyze_with_mistral_ocr(
    image_bytes: bytes,
    endpoint: str,
    key: str,
    model: str = "mistral-document-ai-2512",
    api_version: str = "",
) -> ReceiptResult:
    """
    Schickt das Bild an den Mistral-Document-AI-OCR-Endpoint in Azure Foundry.
    Erwartet eine base64-Data-URL und liefert Markdown-Text pro Seite zurueck,
    der anschliessend heuristisch zu Feldern geparst wird.
    """
    import time

    result = ReceiptResult(engine="Mistral Document AI (OCR)")
    if not endpoint or not key:
        result.error = "AZURE_MISTRAL_ENDPOINT oder AZURE_MISTRAL_KEY fehlt in der .env-Datei."
        return result

    mime = _detect_mime(image_bytes)
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:{mime};base64,{b64}"

    # Bei PDFs erwartet die API document_url, bei Bildern image_url.
    if mime == "application/pdf":
        document = {"type": "document_url", "document_url": data_url}
    else:
        document = {"type": "image_url", "image_url": data_url}

    payload = {"model": model, "document": document, "include_image_base64": False}

    url = endpoint
    if api_version:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}api-version={api_version}"

    # Foundry akzeptiert je nach Deployment Bearer- ODER api-key-Header -> beide senden.
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
        "api-key": key,
    }

    try:
        start = time.perf_counter()
        response = requests.post(url, json=payload, headers=headers, timeout=90)
        result.duration_s = round(time.perf_counter() - start, 2)

        if response.status_code != 200:
            snippet = response.text[:500]
            result.error = f"Mistral OCR HTTP {response.status_code}: {snippet}"
            return result

        data = response.json()
        result.raw_payload = data

        # Markdown-Text aller Seiten zusammenfuehren
        pages = data.get("pages", []) if isinstance(data, dict) else []
        text_parts = []
        for page in pages:
            text_parts.append(page.get("markdown") or page.get("text") or "")
        ocr_text = "\n".join(tp for tp in text_parts if tp).strip()

        # Fallback, falls Antwortstruktur abweicht
        if not ocr_text and isinstance(data, dict):
            ocr_text = str(data.get("content") or data.get("text") or "")

        result.raw_text = ocr_text

        # Felder heuristisch aus dem OCR-Text parsen
        parsed = parse_receipt_text(ocr_text)
        result.merchant = parsed["merchant"]
        result.date = parsed["date"]
        result.total = parsed["total"]
        result.payment_method = parsed["payment_method"]
        result.items = parsed["items"]

    except requests.exceptions.RequestException as exc:
        result.error = f"Netzwerk-/Anfragefehler bei Mistral OCR: {exc}"
    except Exception as exc:  # noqa: BLE001
        result.error = f"Mistral OCR Fehler: {exc}"

    return result


# ===========================================================================
# Heuristischer Parser fuer OCR-Text (deutsche Kassenbons)
# ===========================================================================
_AMOUNT_RE = re.compile(r"(\d{1,4}[.,]\d{2})")
_DATE_RE = re.compile(r"\b(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4})\b")

_TOTAL_KEYWORDS = (
    "zu zahlen", "summe", "gesamtsumme", "gesamt", "total",
    "zahlbetrag", "betrag", "endbetrag",
)
_PAYMENT_PATTERNS = {
    "Bar": r"\bbar\b|\bbargeld\b",
    "EC-/Girocard": r"\bec[\s\-]?karte\b|\bgirocard\b|\bgiro\b|\bmaestro\b",
    "Kreditkarte": r"\bkreditkarte\b|\bvisa\b|\bmastercard\b|\bamex\b",
    "Kontaktlos": r"\bkontaktlos\b|\bcontactless\b|\bnfc\b",
    "PayPal": r"\bpaypal\b",
    "Karte (allg.)": r"\bkarte\b|\bkartenzahlung\b|\bcard\b",
}


def _to_amount(value: str) -> Optional[float]:
    try:
        return float(value.replace(".", "").replace(",", ".")) if value.count(",") == 1 \
            else float(value.replace(",", "."))
    except ValueError:
        return None


def _guess_payment_method(text: str) -> Optional[str]:
    if not text:
        return None
    low = text.lower()
    for label, pattern in _PAYMENT_PATTERNS.items():
        if re.search(pattern, low):
            return label
    return None


def parse_receipt_text(text: str) -> dict[str, Any]:
    """
    Extrahiert Datum, Haendler, Summe, Zahlungsmethode und Positionen
    heuristisch aus reinem OCR-Text. Bewusst einfach gehalten -> die
    Schwaechen dieses Ansatzes werden im Testprotokoll dokumentiert.
    """
    out: dict[str, Any] = {
        "merchant": None, "date": None, "total": None,
        "payment_method": None, "items": [],
    }
    if not text:
        return out

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    low_text = text.lower()

    # --- Datum: erstes plausibles Datum im Text ---
    date_match = _DATE_RE.search(text)
    if date_match:
        out["date"] = date_match.group(1)

    # --- Haendler: erste sinnvolle Textzeile (ohne Markdown-/Trennzeichen) ---
    for ln in lines:
        clean = ln.lstrip("#* >-|").strip()
        if len(clean) >= 3 and re.search(r"[A-Za-zÄÖÜäöü]", clean) \
                and not _DATE_RE.search(clean):
            out["merchant"] = clean
            break

    # --- Summe: Betrag in der Naehe eines Summen-Schluesselwortes ---
    best_total: Optional[str] = None
    for ln in lines:
        low = ln.lower()
        if any(kw in low for kw in _TOTAL_KEYWORDS):
            amounts = _AMOUNT_RE.findall(ln)
            if amounts:
                best_total = amounts[-1]  # letzter Betrag in der Zeile
    if best_total is None:
        # Fallback: groesster Betrag im gesamten Beleg
        all_amounts = _AMOUNT_RE.findall(text)
        numeric = [(a, _to_amount(a)) for a in all_amounts]
        numeric = [(a, v) for a, v in numeric if v is not None]
        if numeric:
            best_total = max(numeric, key=lambda t: t[1])[0]
    out["total"] = best_total

    # --- Zahlungsmethode ---
    out["payment_method"] = _guess_payment_method(low_text)

    # --- Positionen: Zeilen mit Text + Preis (ohne Summen-/Steuerzeilen) ---
    items: list[dict[str, Any]] = []
    skip_kw = _TOTAL_KEYWORDS + ("mwst", "ust", "steuer", "netto", "brutto", "rückgeld", "rueckgeld")
    for ln in lines:
        low = ln.lower()
        if any(kw in low for kw in skip_kw):
            continue
        # Datums- und Prozent-/Steuersatz-Zeilen sind keine Positionen
        if _DATE_RE.search(ln) or "%" in ln:
            continue
        # Datum entfernen, damit es nicht als Betrag fehlinterpretiert wird
        ln_no_date = _DATE_RE.sub("", ln)
        amounts = _AMOUNT_RE.findall(ln_no_date)
        if not amounts:
            continue
        description = _AMOUNT_RE.sub("", ln_no_date).strip(" .-|x*€eur")
        if len(description) >= 2:
            items.append({
                "Beschreibung": description,
                "Menge": None,
                "Einzelpreis": None,
                "Gesamtpreis": amounts[-1],
            })
    out["items"] = items[:30]  # Schutz gegen Ausreisser
    return out
