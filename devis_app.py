"""
devis_app.py - Assistant de devis mousse polyuréthane (multi-lignes, mousse libre par article)

Points clés :
- Plusieurs lignes par zone (Murs, Rampants, Combles, Sol, Plafonds de cave, Vide sanitaires)
- Surface en expression (ex: 20+10+50) + affichage du total calculé (= 80.00 m²)
- Mousse au choix pour CHAQUE ligne
- Épaisseur modifiable par ligne, calcul R obtenu
- Diverses protections & calfeutrage (ligne globale)
- Déplacement masqué si 0
- Totaux HT + sélection TVA (5,5 % ou 10 % ou 20 %) + TTC
"""

from __future__ import annotations
import streamlit as st

# --------------------------- Utilitaires ---------------------------

def calculate_thickness(resistance: float, lambda_value: float) -> float:
    return resistance * lambda_value

def parse_surface_input(value: str) -> float:
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

# --------------------------- Données métier ---------------------------

RESISTANCES = {
    "Murs": 3.7,
    "Rampants": 6.2,
    "Combles": 7.0,
    "Vide sanitaires": 3.0,
    "Plafonds de cave": 3.0,
    "Sol": 3.0,
}

FOAMS = {
    "008E (cellules ouvertes)": {
        "lambda": 0.037,
        "price": 1.50,
        "allowed_zones": {"Murs", "Rampants", "Combles", "Vide sanitaires"},
    },
    "240PX (cellules fermées Isotrie)": {
        "lambda": 0.0225,
        "price": 3.80,
        "allowed_zones": {"Murs", "Sol", "Plafonds de cave"},
    },
    "35Z (cellules fermées Synthésia)": {
        "lambda": 0.027,
        "price": 3.50,
        "allowed_zones": {"Murs", "Sol", "Plafonds de cave"},
    },
}

# --------------------------- Application ---------------------------

def run_app():
    st.set_page_config(page_title="Assistant devis mousse PU", page_icon="🧾", layout="centered")
    st.title("Assistant de devis – Mousse polyuréthane (multi-lignes)")
    st.caption("Choix de mousse par ligne, R calculé, HT → TVA → TTC")

    # ---- Infos générales
    st.header("Informations générales")
    col1, col2 = st.columns(2)
    with col1:
        distance = st.number_input("Distance aller simple (km) – 1 €/km A/R", min_value=0.0, value=0.0, step=1.0)
        travel_cost = distance * 2 * 1.0
        if travel_cost > 0:
            st.caption(f"Coût déplacement estimé (HT) : {travel_cost:.2f} €")
    with col2:
        extra_global = st.number_input("Diverses protections & calfeutrage (HT, €)", min_value=0.0, value=0.0, step=1.0)

    total_material_cost = 0.0
    total_extra_cost = 0.0
    zone_summaries: list[str] = []

    st.header("Postes par zone")
    for zone_name, r_min in RESISTANCES.items():
        with st.expander(zone_name, expanded=False):
            nb = st.number_input(f"Nombre de lignes pour {zone_name.lower()}", min_value=0, value=0, step=1, key=f"nb_{zone_name}")
            for i in range(int(nb)):
                st.markdown(f"**Ligne {i+1}**")

                surface_expr = st.text_input(f"Surface ligne {i+1} (m²)", value="", placeholder="ex : 20+10+50", key=f"surf_{zone_name}_{i}")
                surface = parse_surface_input(surface_expr)
                st.caption(f"= {surface:.2f} m²")

                foam_choice = st.selectbox(f"Mousse ligne {i+1}", list(FOAMS.keys()), key=f"foam_{zone_name}_{i}")
                lambda_val = FOAMS[foam_choice]["lambda"]
                unit_price = FOAMS[foam_choice]["price"]

                if zone_name not in FOAMS[foam_choice]["allowed_zones"]:
                    st.caption("⚠️ Mousse sélectionnée hors usage habituel pour cette zone.")

                default_thick_cm = calculate_thickness(r_min, lambda_val) * 100.0
                thickness_cm = st.number_input(f"Épaisseur ligne {i+1} (cm)", min_value=0.0, value=float(f"{default_thick_cm:.2f}"), step=0.1, key=f"thick_{zone_name}_{i}")

                r_calc = (thickness_cm / 100.0) / lambda_val if lambda_val > 0 else 0.0
                cost_per_m2 = thickness_cm * unit_price
                material_cost = cost_per_m2 * surface

                extras = 0.0
                if zone_name == "Murs":
                    include_cut = st.checkbox("Inclure coupe + évacuation (5 €/m²)", value=True, key=f"cut_{zone_name}_{i}")
                    if include_cut and surface > 0:
                        extras += 5.0 * surface
                elif zone_name == "Sol":
                    cost_sanding_m2 = st.number_input("Ponçage (€/m²)", min_value=0.0, value=0.0, step=1.0, key=f"sand_{zone_name}_{i}")
                    extras += cost_sanding_m2 * surface

                if surface > 0:
                    st.write(f"R obtenu ≃ **{r_calc:.2f} m²·K/W** – Coût mousse (HT) **{material_cost:.2f} €** – Extras (HT) **{extras:.2f} €**")
                    st.write(f"Total ligne (HT) : **{(material_cost + extras):.2f} €**")

                total_material_cost += material_cost
                total_extra_cost += extras
                if surface > 0:
                    zone_summaries.append(f"{zone_name} – L{i+1} : {surface:.1f} m², {thickness_cm:.1f} cm ({foam_choice}), {material_cost:.2f} € HT")

    # ---- Récapitulatif & TVA
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

    tva_choice = st.selectbox("TVA", ["5.5 %", "10 %", "20 %"], index=0)
    if "5.5" in tva_choice:
        tva_rate = 0.055
    elif "10" in tva_choice:
        tva_rate = 0.10
    else:
        tva_rate = 0.20

    tva_amount = total_ht * tva_rate
    total_ttc = total_ht + tva_amount

    st.write(f"TVA ({tva_choice}) : **{tva_amount:.2f} €**")
    st.subheader(f"Montant TTC : **{total_ttc:.2f} €**")

if __name__ == "__main__":
    run_app()
