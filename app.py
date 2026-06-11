"""
app.py
------
Streamlit-Anwendung zur Kassenbon-Analyse.

Die App nimmt einen Kassenbon (Upload oder Webcam) entgegen und extrahiert
relevante Informationen (Datum, Haendler, Gesamtsumme, Positionen,
Zahlungsmethode) mit ZWEI Modellen parallel:

  * Azure AI Document Intelligence (prebuilt-receipt)  -> strukturierte Felder
  * Mistral Document AI / OCR (Azure AI Foundry)        -> OCR + Heuristik-Parser

Die Ergebnisse werden nebeneinander dargestellt, damit man Robustheit und
Genauigkeit beider Modelle direkt vergleichen kann (Grundlage Testprotokoll).

Start:  streamlit run app.py
"""

import json
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from receipt_extractors import (
    analyze_with_document_intelligence,
    analyze_with_mistral_ocr,
    ReceiptResult,
)

# ---------------------------------------------------------------------------
# Konfiguration aus .env laden
# ---------------------------------------------------------------------------
load_dotenv()

DI_ENDPOINT = os.getenv("AZURE_DI_ENDPOINT", "")
DI_KEY = os.getenv("AZURE_DI_KEY", "")
MISTRAL_ENDPOINT = os.getenv("AZURE_MISTRAL_ENDPOINT", "")
MISTRAL_KEY = os.getenv("AZURE_MISTRAL_KEY", "")
MISTRAL_MODEL = os.getenv("AZURE_MISTRAL_MODEL", "mistral-document-ai-2512")
MISTRAL_API_VERSION = os.getenv("AZURE_MISTRAL_API_VERSION", "")

st.set_page_config(page_title="Kassenbon-Analyse", page_icon="🧾", layout="wide")


# ---------------------------------------------------------------------------
# Hilfsfunktionen fuer die Darstellung
# ---------------------------------------------------------------------------
def render_result(result: ReceiptResult) -> None:
    """Zeigt ein Modell-Ergebnis strukturiert an."""
    st.subheader(result.engine)

    if result.error:
        st.error(result.error)

    if result.duration_s is not None:
        st.caption(f"Laufzeit: {result.duration_s} s")

    # Kennzahlen als Metriken
    c1, c2 = st.columns(2)
    c1.metric("Händler", result.merchant or "—")
    c2.metric("Datum", result.date or "—")
    c3, c4 = st.columns(2)
    c3.metric("Gesamtsumme", result.total or "—")
    c4.metric("Zahlungsmethode", result.payment_method or "—")

    # Positionen als Tabelle
    st.markdown("**Positionen**")
    if result.items:
        df = pd.DataFrame(result.items)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Keine Positionen erkannt.")

    # Rohdaten in einklappbaren Bereichen
    if result.raw_text:
        with st.expander("Erkannter Rohtext (OCR / content)"):
            st.text(result.raw_text)
    if result.raw_payload is not None:
        with st.expander("Roh-Antwort (JSON)"):
            try:
                st.json(result.raw_payload)
            except Exception:
                st.text(str(result.raw_payload))


def build_comparison_table(di: ReceiptResult, mistral: ReceiptResult) -> pd.DataFrame:
    """Erzeugt eine kompakte Vergleichstabelle der wichtigsten Felder."""
    rows = [
        ("Händler", di.merchant, mistral.merchant),
        ("Datum", di.date, mistral.date),
        ("Gesamtsumme", di.total, mistral.total),
        ("Zahlungsmethode", di.payment_method, mistral.payment_method),
        ("Anzahl Positionen", len(di.items), len(mistral.items)),
        ("Laufzeit (s)", di.duration_s, mistral.duration_s),
    ]
    return pd.DataFrame(rows, columns=["Feld", "Document Intelligence", "Mistral OCR"])


def results_to_json(di: ReceiptResult, mistral: ReceiptResult) -> str:
    return json.dumps(
        {"document_intelligence": di.as_dict(), "mistral_ocr": mistral.as_dict()},
        ensure_ascii=False,
        indent=2,
    )


# ---------------------------------------------------------------------------
# Sidebar: Konfigurations-Status
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Konfiguration")
    st.markdown("Status der Azure-Zugangsdaten (aus `.env`):")

    def status(label: str, ok: bool) -> None:
        st.write(("✅ " if ok else "❌ ") + label)

    status("Document Intelligence Endpoint", bool(DI_ENDPOINT))
    status("Document Intelligence Key", bool(DI_KEY))
    status("Mistral Endpoint", bool(MISTRAL_ENDPOINT))
    status("Mistral Key", bool(MISTRAL_KEY))
    st.caption(f"Mistral-Modell: `{MISTRAL_MODEL}`")

    st.divider()
    st.subheader("Aktive Modelle")
    use_di = st.checkbox("Azure Document Intelligence", value=True)
    use_mistral = st.checkbox("Mistral Document AI (OCR)", value=True)

    st.divider()
    st.caption(
        "Kassenbon-Analyse\n\n"
    )


# ---------------------------------------------------------------------------
# Hauptbereich
# ---------------------------------------------------------------------------
st.title("🧾 Kassenbon-Analyse")
st.markdown(
    "Lade einen Kassenbon hoch oder nimm ihn per Webcam auf. "
    "Die App extrahiert **Datum, Händler, Gesamtsumme, Positionen** und "
    "**Zahlungsmethode** mit zwei Modellen und stellt die Ergebnisse gegenüber."
)

tab_upload, tab_webcam = st.tabs(["📁 Bild hochladen", "📷 Webcam"])

image_bytes: bytes | None = None
source_name = "kassenbon"

with tab_upload:
    uploaded = st.file_uploader(
        "Kassenbon-Bild auswählen (JPG, PNG oder PDF)",
        type=["jpg", "jpeg", "png", "pdf"],
    )
    if uploaded is not None:
        image_bytes = uploaded.getvalue()
        source_name = os.path.splitext(uploaded.name)[0]
        if uploaded.type != "application/pdf":
            st.image(image_bytes, caption=uploaded.name, width=350)
        else:
            st.info(f"PDF geladen: {uploaded.name}")

with tab_webcam:
    cam = st.camera_input("Kassenbon fotografieren")
    if cam is not None:
        image_bytes = cam.getvalue()
        source_name = "webcam_aufnahme"

st.divider()

# ---------------------------------------------------------------------------
# Analyse ausloesen
# ---------------------------------------------------------------------------
analyze_clicked = st.button(
    "🔍 Kassenbon analysieren",
    type="primary",
    disabled=image_bytes is None,
    use_container_width=True,
)

if image_bytes is None:
    st.info("Bitte zuerst ein Bild hochladen oder per Webcam aufnehmen.")

if analyze_clicked and image_bytes is not None:
    if not use_di and not use_mistral:
        st.warning("Bitte in der Seitenleiste mindestens ein Modell aktivieren.")
        st.stop()

    di_result = ReceiptResult(engine="Azure Document Intelligence")
    mistral_result = ReceiptResult(engine="Mistral Document AI (OCR)")

    if use_di:
        with st.spinner("Document Intelligence analysiert den Kassenbon ..."):
            di_result = analyze_with_document_intelligence(image_bytes, DI_ENDPOINT, DI_KEY)
    if use_mistral:
        with st.spinner("Mistral Document AI (OCR) analysiert den Kassenbon ..."):
            mistral_result = analyze_with_mistral_ocr(
                image_bytes, MISTRAL_ENDPOINT, MISTRAL_KEY,
                model=MISTRAL_MODEL, api_version=MISTRAL_API_VERSION,
            )

    # Vergleichstabelle
    if use_di and use_mistral:
        st.markdown("### 📊 Modellvergleich")
        st.dataframe(
            build_comparison_table(di_result, mistral_result),
            use_container_width=True,
            hide_index=True,
        )
        st.divider()

    # Detailansicht nebeneinander
    col_left, col_right = st.columns(2)
    if use_di:
        with col_left:
            render_result(di_result)
    if use_mistral:
        with col_right:
            render_result(mistral_result)

    # Ergebnis-Download (praktisch fuer das Testprotokoll)
    st.divider()
    st.download_button(
        "⬇️ Ergebnisse als JSON speichern",
        data=results_to_json(di_result, mistral_result),
        file_name=f"ergebnis_{source_name}.json",
        mime="application/json",
    )
