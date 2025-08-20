"""
devis_app.py - Assistant de devis mousse polyuréthane
- Multi-lignes par zone (Murs, Rampants, Combles, Sol, Plafonds de cave, Vide sanitaires)
- Surface en expression (ex: 20+10+50) + affichage du total (= … m²)
- Mousse au choix pour CHAQUE ligne (note si hors usage habituel)
- Épaisseur modifiable, R calculé
- Diverses protections & calfeutrage (HT, global)
- Déplacement masqué si 0
- Totaux HT → TVA (5,5% / 10% / 20%) → TTC
- Export PDF SIMPLE, PRO, et GOODNOTES (TVA choisie au moment de l’export)
- Logo intégré en base64 (placeholder, remplaçable)
"""

from __future__ import annotations
import io
import base64
from typing import List, Dict, Tuple

import streamlit as st

# ============== LOGO intégré (base64) ==============
# Remplacez LOGO_BASE64 par le base64 de votre vrai logo si vous me l’envoyez.
# Pour l’instant, petit PNG transparent 1x1 en placeholder (s’affiche sans erreur).
LOGO_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
)

# ================== Utilitaires ====================

def calculate_thickness(resistance: float, lambda_value: float) -> float:
    """e = R × λ (épaisseur en mètres)"""
    return resistance * lambda_value

def parse_surface_input(value: str) -> float:
    """Somme a+b+c en m² (gère virgules)."""
    if not value:
        return 0.0
    total = 0.0
    for part in value.split("+"):
        part = part.strip().replace(",", ".")
        try:
            total += float(part)
        except ValueError:
            continue
    return total

def decode_logo_bio() -> io.BytesIO:
    try:
        data = base64.b64decode(LOGO_BASE64)
        return io.BytesIO(data)
    except Exception:
        return io.BytesIO()

# ================== Données métier =================

RESISTANCES: Dict[str, float] = {
    "Murs": 3.7,
    "Rampants": 6.2,
    "Combles": 7.0,
    "Vide sanitaires": 3.0,
    "Plafonds de cave": 3.0,
    "Sol": 3.0,
}

FOAMS: Dict[str, Dict] = {
    "008E (cellules ouvertes)": {
        "lambda": 0.037,   # W/m·K
        "price": 1.50,     # €/cm/m²
        "allowed_zones": {"Murs", "Rampants", "Combles", "Vide sanitaires"},
    },
    "240PX (cellules fermées Isotrie)": {
        "lambda": 0.0225,  # W/m·K
        "price": 3.80,
        "allowed_zones": {"Murs", "Sol", "Plafonds de cave"},
    },
    "35Z (cellules fermées Synthésia)": {
        "lambda": 0.027,
        "price": 3.50,
        "allowed_zones": {"Murs", "Sol", "Plafonds de cave"},
    },
}

# ============== Application principale =============

def run_app():
    st.set_page_config(page_title="Assistant devis mousse PU", page_icon="🧾", layout="centered")
    st.title("Assistant de devis – Mousse polyuréthane (multi-lignes)")
    st.caption("Choix de la mousse par ligne, R calculé, HT → TVA → TTC. Export PDF simple, pro & GoodNotes.")

    # ---- Infos client (utilisé surtout pour PDF pro)
    with st.expander("Infos client (facultatif, utilisé dans le PDF pro et GoodNotes)"):
        colc1, colc2 = st.columns(2)
        with colc1:
            client_nom = st.text_input("Nom / Entreprise")
            client_email = st.text_input("Email")
            client_tel = st.text_input("Téléphone")
        with colc2:
            chantier_adresse = st.text_area("Adresse du chantier")
            ref_devis = st.text_input("Référence devis")
            date_devis = st.date_input("Date du devis")

    # ---- Infos générales
    st.header("Informations générales")
    col1, col2 = st.columns(2)
    with col1:
        distance = st.number_input("Distance aller simple (km) – 1 €/km A/R", min_value=0.0, value=0.0, step=1.0)
        travel_cost = distance * 2 * 1.0  # A/R
        if travel_cost > 0:
            st.caption(f"Coût déplacement estimé (HT) : {travel_cost:.2f} €")
    with col2:
        extra_global = st.number_input(
            "Diverses protections & calfeutrage (HT, €)",
            min_value=0.0, value=0.0, step=1.0,
            help="Montant global pour ruban, films, joints, calfeutrage…"
        )

    total_material_cost = 0.0
    total_extra_cost = 0.0
    zone_summaries: List[str] = []
    line_items: List[Tuple[str, float, str, float, float, float]] = []
    # (zone, surface, mousse, ep_cm, cout_mousse_ht, extras_ht)

    st.header("Postes par zone")
    for zone_name, r_min in RESISTANCES.items():
        with st.expander(zone_name, expanded=False):
            nb = st.number_input(f"Nombre de lignes pour {zone_name.lower()}",
                                 min_value=0, value=0, step=1, key=f"nb_{zone_name}")
            for i in range(int(nb)):
                st.markdown(f"**Ligne {i+1}**")

                surface_expr = st.text_input(
                    f"Surface ligne {i+1} (m²) – ex : 20+10+50",
                    value="", placeholder="ex : 20+10+50", key=f"surf_{zone_name}_{i}"
                )
                surface = parse_surface_input(surface_expr)
                st.caption(f"= {surface:.2f} m²")

                foam_choice = st.selectbox(f"Mousse ligne {i+1}", list(FOAMS.keys()), key=f"foam_{zone_name}_{i}")
                lambda_val = FOAMS[foam_choice]["lambda"]
                unit_price = FOAMS[foam_choice]["price"]

                if zone_name not in FOAMS[foam_choice]["allowed_zones"]:
                    st.caption("⚠️ Mousse sélectionnée hors usage habituel pour cette zone.")

                default_thick_cm = calculate_thickness(r_min, lambda_val) * 100.0
                thickness_cm = st.number_input(
                    f"Épaisseur ligne {i+1} (cm)",
                    min_value=0.0, value=float(f"{default_thick_cm:.2f}"),
                    step=0.1, key=f"thick_{zone_name}_{i}",
                    help="Modifiez pour les épaisseurs imposées."
                )

                r_calc = (thickness_cm / 100.0) / lambda_val if lambda_val > 0 else 0.0
                cost_per_m2 = thickness_cm * unit_price
                material_cost = cost_per_m2 * surface

                extras = 0.0
                if zone_name == "Murs":
                    include_cut = st.checkbox(
                        "Inclure coupe + évacuation (5 €/m²)",
                        value=True, key=f"cut_{zone_name}_{i}"
                    )
                    if include_cut and surface > 0:
                        extras += 5.0 * surface
                    colm1, colm2 = st.columns(2)
                    with colm1:
                        nb_menuiseries = st.number_input(
                            "Nb menuiseries à protéger",
                            min_value=0, value=0, step=1, key=f"nb_m_{zone_name}_{i}"
                        )
                    with colm2:
                        cost_per_menuiserie = st.number_input(
                            "Coût par menuiserie (€)",
                            min_value=0.0, value=10.0, step=1.0, key=f"cpm_{zone_name}_{i}"
                        )
                    extras += nb_menuiseries * cost_per_menuiserie

                elif zone_name == "Sol":
                    col_s1, col_s2 = st.columns(2)
                    with col_s1:
                        cost_protection = st.number_input(
                            "Protection bas de murs & fenêtres (€)",
                            min_value=0.0, value=0.0, step=1.0, key=f"prot_{zone_name}_{i}"
                        )
                    with col_s2:
                        cost_sanding_m2 = st.number_input(
                            "Ponçage (€/m²)",
                            min_value=0.0, value=0.0, step=1.0, key=f"sand_{zone_name}_{i}"
                        )
                    extras += cost_protection + cost_sanding_m2 * surface

                elif zone_name == "Plafonds de cave":
                    cost_cutting_m2 = st.number_input(
                        "Coupe/évacuation (€/m²)",
                        min_value=0.0, value=0.0, step=1.0, key=f"cut_cave_{zone_name}_{i}"
                    )
                    extras += cost_cutting_m2 * surface

                if surface > 0:
                    st.write(
                        f"R obtenu ≃ **{r_calc:.2f} m²·K/W** – "
                        f"Coût mousse (HT) **{material_cost:.2f} €** – "
                        f"Extras (HT) **{extras:.2f} €**"
                    )
                    st.write(f"Total ligne (HT) : **{(material_cost + extras):.2f} €**")

                total_material_cost += material_cost
                total_extra_cost += extras
                if surface > 0:
                    zone_summaries.append(
                        f"{zone_name} – L{i+1} : {surface:.1f} m², {thickness_cm:.1f} cm ({foam_choice}), "
                        f"mousse {material_cost:.2f} €, extras {extras:.2f} €"
                    )
                    line_items.append(
                        (zone_name, surface, foam_choice, thickness_cm, material_cost, extras)
                    )

    # ---- Récapitulatif & TVA (affichage à l’écran)
    total_ht = total_material_cost + total_extra_cost + travel_cost + extra_global
    st.header("Récapitulatif du devis")
    if zone_summaries:
        for s in zone_summaries:
            st.write("• " + s)

    st.write(f"Coût mousses (HT) : **{total_material_cost:.2f} €**")
    st.write(f"Frais supplémentaires (HT) : **{total_extra_cost:.2f} €**")
    if travel_cost > 0:
        st.write(f"Déplacement (HT) : **{travel_cost:.2f} €**")
    if extra_global > 0:
        st.write(f"Diverses protections & calfeutrage (HT) : **{extra_global:.2f} €**")
    st.subheader(f"Montant HT : **{total_ht:.2f} €**")

    st.divider()

    # ======= EXPORTS PDF (TVA choisie au moment de l’export) =======
    st.subheader("Export PDF")
    exp_col1, exp_col2, exp_col3 = st.columns(3)

    with exp_col1:
        tva_choice_simple = st.selectbox("TVA (PDF simple)", ["5.5 %", "10 %", "20 %"], key="tva_simple")
        if st.button("📄 Export PDF simple"):
            pdf_bytes = build_pdf_simple(
                line_items=line_items,
                totals=(total_material_cost, total_extra_cost, travel_cost, extra_global, total_ht),
                tva_choice=tva_choice_simple
            )
            st.download_button("Télécharger PDF simple", data=pdf_bytes, file_name="devis_simple.pdf", mime="application/pdf")

    with exp_col2:
        tva_choice_pro = st.selectbox("TVA (PDF pro)", ["5.5 %", "10 %", "20 %"], key="tva_pro")
        if st.button("📄 Export PDF pro"):
            pdf_bytes = build_pdf_pro(
                client=(client_nom, client_email, client_tel, chantier_adresse, ref_devis, str(date_devis)),
                line_items=line_items,
                totals=(total_material_cost, total_extra_cost, travel_cost, extra_global, total_ht),
                tva_choice=tva_choice_pro
            )
            st.download_button("Télécharger PDF pro", data=pdf_bytes, file_name="devis_pro.pdf", mime="application/pdf")

    with exp_col3:
        tva_choice_gn = st.selectbox("TVA (PDF GoodNotes)", ["5.5 %", "10 %", "20 %"], key="tva_gn")
        if st.button("✍️ Export PDF GoodNotes (signature)"):
            pdf_bytes = build_pdf_goodnotes(
                client=(client_nom, client_email, client_tel, chantier_adresse, ref_devis, str(date_devis)),
                line_items=line_items,
                totals=(total_material_cost, total_extra_cost, travel_cost, extra_global, total_ht),
                tva_choice=tva_choice_gn
            )
            st.download_button("Télécharger PDF GoodNotes", data=pdf_bytes, file_name="devis_goodnotes.pdf", mime="application/pdf")

# ================== Génération des PDFs ==================

def _tva_rate_from_choice(choice: str) -> float:
    if "5.5" in choice:
        return 0.055
    if "10" in choice:
        return 0.10
    return 0.20

def build_pdf_simple(
    line_items: List[Tuple[str, float, str, float, float, float]],
    totals: Tuple[float, float, float, float, float],
    tva_choice: str
) -> bytes:
    """PDF simple : logo, lignes, totaux HT, TVA, TTC."""
    # Import local pour éviter erreur si reportlab manque
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm

    logo_io = decode_logo_bio()
    total_material_cost, total_extra_cost, travel_cost, extra_global, total_ht = totals
    tva_rate = _tva_rate_from_choice(tva_choice)
    tva_amount = total_ht * tva_rate
    total_ttc = total_ht + tva_amount

    buff = io.BytesIO()
    c = canvas.Canvas(buff, pagesize=A4)
    width, height = A4

    # Logo
    try:
        c.drawImage(logo_io, width - 40*mm, height - 25*mm, width=30*mm, height=20*mm, preserveAspectRatio=True, mask='auto')
    except Exception:
        pass

    # Titre
    c.setFont("Helvetica-Bold", 16)
    c.drawString(20*mm, height - 20*mm, "Devis – Isolation mousse polyuréthane")

    y = height - 30*mm
    c.setFont("Helvetica", 10)
    for (zone, surface, foam, ep_cm, mat_ht, extras_ht) in line_items:
        line = f"{zone} | {surface:.1f} m² | {foam} | {ep_cm:.1f} cm | mousse {mat_ht:.2f} € HT | extras {extras_ht:.2f} € HT"
        c.drawString(15*mm, y, line)
        y -= 6*mm
        if y < 20*mm:
            c.showPage()
            y = height - 20*mm

    # Totaux
    y -= 4*mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(15*mm, y, f"Montant HT : {total_ht:.2f} €")
    y -= 6*mm
    c.setFont("Helvetica", 10)
    c.drawString(15*mm, y, f"TVA ({tva_choice}) : {tva_amount:.2f} €")
    y -= 6*mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(15*mm, y, f"Montant TTC : {total_ttc:.2f} €")

    c.showPage()
    c.save()
    return buff.getvalue()

def build_pdf_pro(
    client: Tuple[str, str, str, str, str, str],
    line_items: List[Tuple[str, float, str, float, float, float]],
    totals: Tuple[float, float, float, float, float],
    tva_choice: str
) -> bytes:
    """PDF pro : en-tête Isol’59 + coordonnées client, tableau lignes, totaux, pied de page."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib import colors

    client_nom, client_email, client_tel, chantier_adresse, ref_devis, date_devis = client
    logo_io = decode_logo_bio()
    total_material_cost, total_extra_cost, travel_cost, extra_global, total_ht = totals
    tva_rate = _tva_rate_from_choice(tva_choice)
    tva_amount = total_ht * tva_rate
    total_ttc = total_ht + tva_amount

    buff = io.BytesIO()
    c = canvas.Canvas(buff, pagesize=A4)
    width, height = A4

    # En-tête
    try:
        c.drawImage(logo_io, width - 45*mm, height - 25*mm, width=35*mm, height=20*mm, preserveAspectRatio=True, mask='auto')
    except Exception:
        pass

    c.setFont("Helvetica-Bold", 18)
    c.drawString(20*mm, height - 18*mm, "Devis – Isolation mousse polyuréthane")

    c.setFont("Helvetica", 9)
    c.drawString(20*mm, height - 25*mm, "Isol’59 • Spécialiste isolation mousse polyuréthane")
    c.drawString(20*mm, height - 30*mm, "contact@isol59.fr • 06 00 00 00 00")

    # Coordonnées client
    y = height - 45*mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(20*mm, y, "Client")
    c.setFont("Helvetica", 10)
    y -= 6*mm
    c.drawString(20*mm, y, f"Nom/Entreprise : {client_nom or '-'}")
    y -= 5*mm
    c.drawString(20*mm, y, f"Email : {client_email or '-'}   |   Tél : {client_tel or '-'}")
    y -= 5*mm
    c.drawString(20*mm, y, f"Chantier : {chantier_adresse or '-'}")
    y -= 5*mm
    c.drawString(20*mm, y, f"Réf devis : {ref_devis or '-'}   |   Date : {date_devis or '-'}")

    # Tableau
    y -= 10*mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(15*mm, y, "Zone")
    c.drawString(45*mm, y, "Surface (m²)")
    c.drawString(80*mm, y, "Mousse")
    c.drawString(120*mm, y, "Ép. (cm)")
    c.drawString(145*mm, y, "Mousse HT")
    c.drawString(175*mm, y, "Extras HT")
    y -= 4*mm
    c.line(15*mm, y, 195*mm, y)
    y -= 5*mm
    c.setFont("Helvetica", 9)

    for (zone, surface, foam, ep_cm, mat_ht, extras_ht) in line_items:
        c.drawString(15*mm, y, zone)
        c.drawRightString(75*mm, y, f"{surface:.1f}")
        c.drawString(80*mm, y, foam[:36])
        c.drawRightString(140*mm, y, f"{ep_cm:.1f}")
        c.drawRightString(170*mm, y, f"{mat_ht:.2f} €")
        c.drawRightString(195*mm, y, f"{extras_ht:.2f} €")
        y -= 6*mm
        if y < 25*mm:
            c.showPage()
            y = height - 20*mm
            c.setFont("Helvetica", 9)

    # Totaux
    if y < 55*mm:
        c.showPage()
        y = height - 20*mm

    c.setFont("Helvetica-Bold", 11)
    c.drawString(15*mm, y, f"Montant HT : {total_ht:.2f} €")
    y -= 6*mm
    c.setFont("Helvetica", 10)
    c.drawString(15*mm, y, f"TVA ({tva_choice}) : {tva_amount:.2f} €")
    y -= 6*mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(15*mm, y, f"Montant TTC : {total_ttc:.2f} €")
    y -= 12*mm

    # Pied de page
    c.setFont("Helvetica", 8)
    from reportlab.lib import colors
    c.setFillColor(colors.grey)
    c.drawString(15*mm, 15*mm, "Isol’59 – Votre spécialiste isolation depuis 2017 • devis sans engagement • validité 30 jours")

    c.showPage()
    c.save()
    return buff.getvalue()

def build_pdf_goodnotes(
    client: Tuple[str, str, str, str, str, str],
    line_items: List[Tuple[str, float, str, float, float, float]],
    totals: Tuple[float, float, float, float, float],
    tva_choice: str
) -> bytes:
    """PDF GoodNotes : identique au pro, avec large zone de signature/date en bas de page."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib import colors

    client_nom, client_email, client_tel, chantier_adresse, ref_devis, date_devis = client
    logo_io = decode_logo_bio()
    total_material_cost, total_extra_cost, travel_cost, extra_global, total_ht = totals
    tva_rate = _tva_rate_from_choice(tva_choice)
    tva_amount = total_ht * tva_rate
    total_ttc = total_ht + tva_amount

    buff = io.BytesIO()
    c = canvas.Canvas(buff, pagesize=A4)
    width, height = A4

    # En-tête (logo + titre + infos fixes)
    try:
        c.drawImage(logo_io, width - 45*mm, height - 25*mm, width=35*mm, height=20*mm, preserveAspectRatio=True, mask='auto')
    except Exception:
        pass

    c.setFont("Helvetica-Bold", 18)
    c.drawString(20*mm, height - 18*mm, "Devis – Isolation mousse polyuréthane")

    c.setFont("Helvetica", 9)
    c.drawString(20*mm, height - 25*mm, "Isol’59 • Spécialiste isolation mousse polyuréthane")
    c.drawString(20*mm, height - 30*mm, "contact@isol59.fr • 06 00 00 00 00")

    # Coordonnées client
    y = height - 45*mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(20*mm, y, "Client")
    c.setFont("Helvetica", 10)
    y -= 6*mm
    c.drawString(20*mm, y, f"Nom/Entreprise : {client_nom or '-'}")
    y -= 5*mm
    c.drawString(20*mm, y, f"Email : {client_email or '-'}   |   Tél : {client_tel or '-'}")
    y -= 5*mm
    c.drawString(20*mm, y, f"Chantier : {chantier_adresse or '-'}")
    y -= 5*mm
    c.drawString(20*mm, y, f"Réf devis : {ref_devis or '-'}   |   Date : {date_devis or '-'}")

    # Tableau simple
    y -= 10*mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(15*mm, y, "Zone")
    c.drawString(45*mm, y, "Surface (m²)")
    c.drawString(80*mm, y, "Mousse")
    c.drawString(120*mm, y, "Ép. (cm)")
    c.drawString(145*mm, y, "Mousse HT")
    c.drawString(175*mm, y, "Extras HT")
    y -= 4*mm
    c.line(15*mm, y, 195*mm, y)
    y -= 5*mm
    c.setFont("Helvetica", 9)

    for (zone, surface, foam, ep_cm, mat_ht, extras_ht) in line_items:
        c.drawString(15*mm, y, zone)
        c.drawRightString(75*mm, y, f"{surface:.1f}")
        c.drawString(80*mm, y, foam[:36])
        c.drawRightString(140*mm, y, f"{ep_cm:.1f}")
        c.drawRightString(170*mm, y, f"{mat_ht:.2f} €")
        c.drawRightString(195*mm, y, f"{extras_ht:.2f} €")
        y -= 6*mm
        if y < 55*mm:  # on garde de la place pour la signature
            c.showPage()
            y = height - 20*mm
            c.setFont("Helvetica", 9)

    # Totaux
    if y < 65*mm:
        c.showPage()
        y = height - 20*mm

    c.setFont("Helvetica-Bold", 11)
    c.drawString(15*mm, y, f"Montant HT : {total_ht:.2f} €")
    y -= 6*mm
    c.setFont("Helvetica", 10)
    c.drawString(15*mm, y, f"TVA ({tva_choice}) : {tva_amount:.2f} €")
    y -= 6*mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(15*mm, y, f"Montant TTC : {total_ttc:.2f} €")
    y -= 12*mm

    # Encadré signature/date (grand espace pour stylet)
    from reportlab.lib import colors
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    box_x1, box_y1 = 15*mm, 20*mm
    box_x2, box_y2 = 195*mm, 55*mm
    c.rect(box_x1, box_y1, box_x2 - box_x1, box_y2 - box_y1, stroke=1, fill=0)

    c.setFont("Helvetica", 10)
    c.drawString(box_x1 + 5*mm, box_y2 - 8*mm, "Signature du client :")
    c.line(box_x1 + 50*mm, box_y2 - 10*mm, box_x2 - 10*mm, box_y2 - 10*mm)

    c.drawString(box_x1 + 5*mm, box_y2 - 18*mm, "Date :")
    c.line(box_x1 + 20*mm, box_y2 - 20*mm, box_x1 + 60*mm, box_y2 - 20*mm)

    c.showPage()
    c.save()
    return buff.getvalue()

# ================== Lancement ==================

if __name__ == "__main__":
    run_app()
