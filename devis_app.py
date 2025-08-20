
import streamlit as st
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
import base64

LOGO_BASE64 = """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"""

def draw_logo(canvas_obj, x=160*mm, y=270*mm, width=30*mm):
    logo_data = base64.b64decode(LOGO_BASE64)
    logo_image = BytesIO(logo_data)
    canvas_obj.drawImage(logo_image, x, y, width=width, preserveAspectRatio=True, mask='auto')

def build_pdf_goodnotes(line_items, totals, tva_choice):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    draw_logo(c)

    c.setFont("Helvetica-Bold", 14)
    c.drawString(20*mm, height - 20*mm, "Devis – Isolation mousse polyuréthane")
    c.setFont("Helvetica", 10)
    c.drawString(20*mm, height - 30*mm, "contact@isol59.fr • 06 98 96 18 80")

    c.setFont("Helvetica-Bold", 12)
    y = height - 50*mm
    for item in line_items:
        if y < 50*mm:
            c.showPage()
            draw_logo(c)
            y = height - 30*mm
        c.drawString(20*mm, y, "- {}".format(item))
        y -= 10*mm

    y -= 10*mm
    c.setFont("Helvetica", 10)
    total_materiel, total_options, deplacement, extras, total_ht = totals
    c.drawString(20*mm, y, "Total HT : {:.2f} €".format(total_ht))
    y -= 8*mm
    taux_tva = float(tva_choice.replace('%','')) / 100
    montant_tva = total_ht * taux_tva
    total_ttc = total_ht + montant_tva
    c.drawString(20*mm, y, "TVA ({}) : {:.2f} €".format(tva_choice, montant_tva))
    y -= 8*mm
    c.drawString(20*mm, y, "Total TTC : {:.2f} €".format(total_ttc))

    y -= 20*mm
    c.rect(20*mm, y - 25*mm, 170*mm, 25*mm)
    c.drawString(22*mm, y - 10*mm, "Signature client :")
    c.drawString(140*mm, y - 10*mm, "Date : ____ / ____ / ______")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()

st.title("Assistant Devis Isol'59")

st.subheader("Intervention diverse")
desc_diverse = st.text_input("Description de l'intervention")
montant_diverse = st.number_input("Montant HT (€)", min_value=0.0, step=1.0)

items = []
if desc_diverse and montant_diverse > 0:
    items.append(f"{desc_diverse} : {montant_diverse:.2f} €")

totaux_fictifs = (0, 0, 0, montant_diverse, montant_diverse)

tva_select = st.selectbox("Choisir la TVA", ["5.5%", "10%", "20%"])

if st.button("Exporter PDF GoodNotes"):
    pdf_bytes = build_pdf_goodnotes(items, totaux_fictifs, tva_select)
    st.download_button("📄 Télécharger le PDF", data=pdf_bytes, file_name="devis_goodnotes.pdf")
