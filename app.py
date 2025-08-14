import os
import io
import numpy as np
from io import BytesIO
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

# ---------------- Session state for signature ----------------
if "signature_bytes" not in st.session_state:
    st.session_state["signature_bytes"] = None

def set_signature(signature: bytes | None) -> None:
    """Set the signature bytes in the session state.

    Args:
        signature (bytes | None): Signature image bytes or None to clear.
    """
    st.session_state["signature_bytes"] = signature

def build_vollmacht_pdf_bytes(data: dict, signature_bytes: bytes | None = None) -> bytes:
    """Build a Vollmacht PDF in memory and return it as bytes.

    Args:
        data (dict): Dictionary containing the fields:
            'vg_name', 'vg_vorname', 'vg_geb', 'vg_addr',
            'b_name', 'b_vorname', 'b_geb', 'b_addr',
            'stadt', 'datum'.
        signature_bytes (bytes | None): Signature image bytes (PNG/JPG) to insert into PDF.

    Returns:
        bytes: PDF document as bytes.
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=40, rightMargin=40, topMargin=36, bottomMargin=36
    )
    styles = getSampleStyleSheet()
    normal_style = styles["Normal"]

    elems = [
        Paragraph("<b>Vollmacht</b>", styles["Title"]),
        Paragraph(
            "zur Abholung und Beantragung des Aufenthaltstitels/Reiseausweises",
            normal_style
        ),
        Spacer(1, 12),
        Paragraph("Ich:", normal_style),
        Paragraph("Vollmachtgeber", normal_style)
    ]

    # Vollmachtgeber table
    tbl1 = Table([
        ["Name:", data.get("vg_name", "")],
        ["Vorname:", data.get("vg_vorname", "")],
        ["Geburtsdatum:", data.get("vg_geb", "")],
        ["Anschrift:", data.get("vg_addr", "")],
    ], colWidths=[100, 350])
    tbl1.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elems += [tbl1, Spacer(1, 12),
              Paragraph("bevollmächtige", normal_style),
              Paragraph("Bevollmächtigter/-r", normal_style)]

    # Bevollmächtigter table
    tbl2 = Table([
        ["Name:", data.get("b_name", "")],
        ["Vorname:", data.get("b_vorname", "")],
        ["Geburtsdatum:", data.get("b_geb", "")],
        ["Anschrift:", data.get("b_addr", "")],
    ], colWidths=[100, 350])
    tbl2.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elems += [tbl2, Spacer(1, 12)]

    # Additional text
    elems.append(Paragraph(
        "den Aufenthaltstitel und Reiseausweis zu beantragen/abzuholen, "
        "unter Vorlage <u>meines</u> Personaldokuments (Pass/Reiseausweises).",
        normal_style
    ))
    elems.append(Paragraph(
        "<b>Hinweis:</b> Der Bevollmächtigte muss sich bei Vorsprache zur Abholung "
        "durch Vorlage eines eigenen Personaldokuments ausweisen.",
        normal_style
    ))
    elems.append(Spacer(1, 24))

    # Date and location
    elems.append(Paragraph(f"{data.get('stadt', '')}, den {data.get('datum', '')}",
                           normal_style))
    elems.append(Spacer(1, 18))

    # Signature block
    cm_to_pt = 28.3465
    shift_cm = 0.0
    shift_pt = shift_cm * cm_to_pt
    sig_w, sig_h = 160, 60
    sig_offset = -12

    sig_block = []
    if signature_bytes:
        sig_img = RLImage(BytesIO(signature_bytes),
                          width=sig_w, height=sig_h, hAlign="LEFT")
        sig_block += [sig_img, Spacer(1, sig_offset)]

    sig_block += [
        Paragraph("_________________________", normal_style),
        Paragraph("Unterschrift des Vollmachtgebers", normal_style)
    ]

    elems += [
        Indenter(left=-shift_pt),
        KeepTogether(sig_block),
        Indenter(left=shift_pt)
    ]

    doc.build(elems)
    buf.seek(0)
    return buf.read()

# ---------------- Streamlit UI ----------------
st.title("Vollmacht – PDF Generator (internal)")

with st.form("vollmacht_form"):
    st.subheader("Vollmachtgeber")
    vg_name = st.text_input("Name (Vollmachtgeber)")
    vg_vorname = st.text_input("Vorname (Vollmachtgeber)")
    vg_geb = st.text_input("Geburtsdatum (Vollmachtgeber)  e.g. 01.01.1990")
    vg_addr = st.text_area("Anschrift (Vollmachtgeber)")

    st.subheader("Bevollmächtigter")
    b_name = st.text_input("Name (Bevollmächtigter)")
    b_vorname = st.text_input("Vorname (Bevollmächtigter)")
    b_geb = st.text_input("Geburtsdatum (Bevollmächtigter)")
    b_addr = st.text_area("Anschrift (Bevollmächtigter)")

    cols = st.columns(2)
    with cols[0]:
        stadt = st.text_input("Ort", value="Berlin")
    with cols[1]:
        datum = st.text_input("Datum", placeholder="TT.MM.JJJJ")

    submitted = st.form_submit_button("PDF erstellen")

# Signature area outside the form
st.subheader("Signature")
sig_mode = st.radio("Choose signature method:",
                   ["Mouse drawing", "Upload image"],
                   horizontal=True)

if sig_mode == "Mouse drawing":
    st.caption("Draw your signature inside the box, then click 'Accept drawn signature'.")
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
    cols_sig = st.columns([1, 1, 2])
    with cols_sig[0]:
        if st.button("Accept drawn signature"):
            if canvas_result.image_data is not None:
                rgba = canvas_result.image_data.astype(np.uint8)
                pil_img = PILImage.fromarray(rgba)
                out = io.BytesIO()
                pil_img.save(out, format="PNG")
                set_signature(out.getvalue())
                st.success("Signature accepted.")
            else:
                st.warning("No drawing to accept.")
    with cols_sig[1]:
        if st.button("Clear signature"):
            set_signature(None)
            st.info("Signature cleared.")
else:
    uploaded_file = st.file_uploader("Upload signature image (PNG/JPG)",
                                     type=["png", "jpg", "jpeg"])
    if uploaded_file is not None:
        set_signature(uploaded_file.read())
        st.success("Signature image accepted.")
    if st.button("Clear signature"):
        set_signature(None)
        st.info("Signature cleared.")

# Optional signature preview
if st.session_state["signature_bytes"]:
    st.image(st.session_state["signature_bytes"], caption="Signature preview", width=260)

st.divider()

# PDF creation
if submitted:
    form_data = {
        "vg_name": vg_name,
        "vg_vorname": vg_vorname,
        "vg_geb": vg_geb,
        "vg_addr": vg_addr,
        "b_name": b_name,
        "b_vorname": b_vorname,
        "b_geb": b_geb,
        "b_addr": b_addr,
        "stadt": stadt,
        "datum": datum
    }
    signature_data = st.session_state.get("signature_bytes")
    pdf_bytes = build_vollmacht_pdf_bytes(form_data, signature_bytes=signature_data)
    st.success("PDF created.")
    st.download_button(
        "Download Vollmacht.pdf",
        data=pdf_bytes,
        file_name="vollmacht_formular.pdf",
        mime="application/pdf",
    )

"""
Auto-run Streamlit application when executed directly as a script.
This script ensures Streamlit runs only once by using an environment
variable as a bootstrap flag.

Environment Variables:
    APP_BOOTSTRAPPED (str): Internal flag to prevent re-execution loop.
    STREAMLIT_PORT (str): Port number for Streamlit to use. Defaults to "8501".
"""

if __name__ == "__main__":
    import os
    import sys

    # Prevent infinite re-execution: execute only once
    if os.environ.get("APP_BOOTSTRAPPED") != "1":
        os.environ["APP_BOOTSTRAPPED"] = "1"
        port = os.environ.get("STREAMLIT_PORT", "8501")

        os.execv(
            sys.executable,
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                __file__,
                "--server.port",
                port,
            ],
        )

    # If already running under Streamlit (APP_BOOTSTRAPPED=1), do nothing
