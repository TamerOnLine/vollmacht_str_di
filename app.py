import os
import io
import json
from io import BytesIO

import numpy as np
from PIL import Image as PILImage
import streamlit as st
from streamlit_drawable_canvas import st_canvas

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    Image as RLImage, Indenter, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet


# ============ Helpers ============
def load_json(path: str, default: dict | None = None) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default or {}


# ============ Load Configuration and i18n ============
APP_DIR = os.path.dirname(__file__)
cfg = load_json(os.path.join(APP_DIR, "setup-config.json"), {})
schema = load_json(os.path.join(APP_DIR, "form_schema.json"), {})

i18n_de = load_json(os.path.join(APP_DIR, "i18n.de.json"), {})
i18n_ar = load_json(os.path.join(APP_DIR, "i18n.ar.json"), {})
i18n_en = load_json(os.path.join(APP_DIR, "i18n.en.json"), {})
I18N_PDF = i18n_de

LANGS = {
    "Deutsch": i18n_de,
    "العربية": i18n_ar,
    "English": i18n_en
}


def tr(key: str, i18n: dict, fallback: str | None = None) -> str:
    return i18n.get(key, fallback or key)


# ============ Signature Session State ============
if "signature_bytes" not in st.session_state:
    st.session_state["signature_bytes"] = None


def set_signature(signature: bytes | None) -> None:
    st.session_state["signature_bytes"] = signature


# ============ PDF Builder ============
def build_vollmacht_pdf_bytes(
    data: dict,
    signature_bytes: bytes | None = None,
    *,
    i18n: dict,
    pdf_options: dict
) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=pdf_options.get("leftMargin", 40),
        rightMargin=pdf_options.get("rightMargin", 40),
        topMargin=pdf_options.get("topMargin", 36),
        bottomMargin=pdf_options.get("bottomMargin", 36),
    )
    styles = getSampleStyleSheet()
    normal_style = styles["Normal"]

    elems = [
        Paragraph(f"<b>{tr(pdf_options.get('title_i18n', 'app.title'), i18n, 'Vollmacht')}</b>", styles["Title"]),
        Paragraph("zur Abholung und Beantragung des Aufenthaltstitels/Reiseausweises", normal_style),
        Spacer(1, 12),
        Paragraph("Ich:", normal_style),
        Paragraph("Vollmachtgeber", normal_style),
    ]

    table_style = TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ])

    tbl1 = Table([
        ["Name:", data.get("vg_name", "")],
        ["Vorname:", data.get("vg_vorname", "")],
        ["Geburtsdatum:", data.get("vg_geb", "")],
        ["Anschrift:", data.get("vg_addr", "")],
    ], colWidths=[100, 350])
    tbl1.setStyle(table_style)

    elems += [tbl1, Spacer(1, 12), Paragraph("bevollmächtige", normal_style), Paragraph("Bevollmächtigter/-r", normal_style)]

    tbl2 = Table([
        ["Name:", data.get("b_name", "")],
        ["Vorname:", data.get("b_vorname", "")],
        ["Geburtsdatum:", data.get("b_geb", "")],
        ["Anschrift:", data.get("b_addr", "")],
    ], colWidths=[100, 350])
    tbl2.setStyle(table_style)

    elems += [tbl2, Spacer(1, 12)]

    elems.append(Paragraph(
        "den Aufenthaltstitel und Reiseausweis zu beantragen/abzuholen, unter Vorlage <u>meines</u> Personaldokuments (Pass/Reiseausweises).",
        normal_style
    ))
    elems.append(Paragraph(
        "<b>Hinweis:</b> Der Bevollmächtigte muss sich bei Vorsprache zur Abholung durch Vorlage eines eigenen Personaldokuments ausweisen.",
        normal_style
    ))
    elems.append(Spacer(1, 24))

    elems.append(Paragraph(f"{data.get('stadt', '')}, den {data.get('datum', '')}", normal_style))
    elems.append(Spacer(1, 18))

    target_w = float(pdf_options.get("signature_width_pt", 180))
    max_h = float(pdf_options.get("signature_max_height_pt", 80))
    sig_block = []

    if signature_bytes:
        try:
            pil = PILImage.open(BytesIO(signature_bytes)).convert("RGBA")
            w, h = pil.size
            aspect = h / w if w else 1.0
            out_w = target_w
            out_h = min(max_h, out_w * aspect)
            sig_img = RLImage(BytesIO(signature_bytes), width=out_w, height=out_h, hAlign="LEFT")
            sig_block += [sig_img, Spacer(1, -12)]
        except Exception:
            pass

    sig_block += [
        Paragraph("_________________________", normal_style),
        Paragraph("Unterschrift des Vollmachtgebers", normal_style),
    ]

    elems += [Indenter(left=0), KeepTogether(sig_block), Indenter(left=0)]

    doc.build(elems)
    buf.seek(0)
    return buf.read()


# Streamlit and other logic will continue in the next update.

# The following content continues formatting the rest of the Streamlit application

# ============ Streamlit UI ============
lang_choice = st.sidebar.selectbox("Language / اللغة", list(LANGS.keys()), index=0)
i18n = LANGS[lang_choice]

st.title(tr("app.title", i18n, "Vollmacht – PDF Generator"))

# Dynamic form from schema
with st.form("vollmacht_form"):
    values: dict[str, str] = {}

    for section in schema.get("sections", []):
        st.subheader(tr(section.get("title_i18n", section.get("key", "")), i18n, section.get("key", "")))
        for fld in section.get("fields", []):
            label = tr(fld.get("label_i18n", fld.get("key", "")), i18n, fld.get("key", ""))
            placeholder = fld.get("placeholder", "")
            key = f'{section["key"]}_{fld["key"]}'
            if fld.get("type") == "textarea":
                values[key] = st.text_area(label, placeholder=placeholder)
            else:
                values[key] = st.text_input(label, placeholder=placeholder)

    cols = st.columns(2)
    with cols[0]:
        stadt = st.text_input(
            tr("field.ort", i18n, "Ort"),
            value=schema.get("misc", {}).get("stadt_default", "Berlin"),
        )
    with cols[1]:
        datum = st.text_input(
            tr("field.datum", i18n, "Datum"),
            placeholder=schema.get("misc", {}).get("date_placeholder", ""),
        )

    submitted = st.form_submit_button(tr("btn.create", i18n, "PDF erstellen"))

# Signature input section
st.subheader(tr("signature.title", i18n, "Unterschrift"))
draw_label = tr("signature.mode.draw", i18n, "Mouse drawing")
upload_label = tr("signature.mode.upload", i18n, "Upload image")

sig_mode = st.radio("", [draw_label, upload_label], horizontal=True)

if sig_mode == draw_label:
    st.caption(draw_label)
    canvas_result = st_canvas(
        fill_color="rgba(0, 0, 0, 0)",
        stroke_width=2,
        stroke_color="black",
        background_color="white",
        height=120,
        width=400,
        drawing_mode="freedraw",
        key="signature_canvas",
        update_streamlit=True,
        display_toolbar=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button(tr("btn.accept_drawn", i18n, "Accept drawn signature")):
            if canvas_result.image_data is not None:
                rgba = canvas_result.image_data.astype(np.uint8)
                pil_img = PILImage.fromarray(rgba)
                out = io.BytesIO()
                pil_img.save(out, format="PNG")
                set_signature(out.getvalue())
                st.success("OK")
            else:
                st.warning("No drawing.")
    with c2:
        if st.button(tr("btn.clear", i18n, "Clear")):
            set_signature(None)
            st.info("Cleared.")
else:
    uploaded = st.file_uploader(upload_label, type=["png", "jpg", "jpeg"])
    c1, c2 = st.columns(2)
    with c1:
        if uploaded:
            set_signature(uploaded.read())
            st.success("OK")
    with c2:
        if st.button(tr("btn.clear", i18n, "Clear")):
            set_signature(None)
            st.info("Cleared.")

if st.session_state["signature_bytes"]:
    st.image(st.session_state["signature_bytes"], caption="Signature preview", width=260)

st.divider()


# ============ Validation & PDF Creation ============
def validate_required(vals: dict, sc: dict, i18n_dict: dict) -> list[str]:
    errors: list[str] = []
    for section in sc.get("sections", []):
        for fld in section.get("fields", []):
            if fld.get("required"):
                k = f'{section["key"]}_{fld["key"]}'
                label = tr(fld.get("label_i18n", fld.get("key", "")), i18n_dict, fld.get("key", ""))
                if not vals.get(k, "").strip():
                    errors.append(label)
    return errors


def v(sec: str, key: str) -> str:
    return (values.get(f"{sec}_{key}", "") or "").strip()


if submitted:
    errs = validate_required(values, schema, i18n)
    if errs:
        st.error(tr("validation.required", i18n, "Bitte Pflichtfelder ausfüllen.") + "\n- " + "\n- ".join(errs))
    else:
        form_data = {
            "vg_name": v("vg", "name"),
            "vg_vorname": v("vg", "vorname"),
            "vg_geb": v("vg", "geb"),
            "vg_addr": v("vg", "addr"),
            "b_name": v("b", "name"),
            "b_vorname": v("b", "vorname"),
            "b_geb": v("b", "geb"),
            "b_addr": v("b", "addr"),
            "stadt": stadt.strip(),
            "datum": datum.strip(),
        }

        signature_data = st.session_state.get("signature_bytes")
        pdf_bytes = build_vollmacht_pdf_bytes(
            form_data,
            signature_bytes=signature_data,
            i18n=I18N_PDF,
            pdf_options=cfg.get("pdf_options", {}),
        )
        st.success(tr("msg.created", I18N_PDF, "PDF created."))
        st.download_button(
            tr("btn.download", I18N_PDF, "Download Vollmacht.pdf"),
            data=pdf_bytes,
            file_name="vollmacht_formular.pdf",
            mime="application/pdf",
        )


# ============ Safe auto-run Streamlit when executed directly ============
if __name__ == "__main__":
    import sys

    if os.environ.get("APP_BOOTSTRAPPED") != "1":
        os.environ["APP_BOOTSTRAPPED"] = "1"
        port = os.environ.get("STREAMLIT_PORT", "8501")

        os.execv(
            sys.executable,
            [
                sys.executable,
                "-m", "streamlit", "run",
                __file__,
                "--server.port", port,
            ],
        )
