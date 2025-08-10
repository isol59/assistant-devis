"""
devis_app.py - Assistant de devis mousse polyuréthane
Version mise à jour :
- Ajout d'une ligne globale "Diverses protections et calfeutrage (HT)"
- Masquer la ligne Déplacement si le montant est 0
- Conserve les améliorations précédentes
"""

import streamlit as st

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

def run_app():
    st.set_page_config(page_title="Assistant devis mousse PU", page_icon="🧾")

    st.title("Assistant de devis - Mousse polyuréthane")
    st.write("Calcule les épaisseurs et coûts pour la projection de mousse polyuréthane.")

    resistances = {
        "Murs": 3.7,
        "Rampants": 6.2,
        "Combles": 7.0,
        "Vide sanitaires": 3.0,
        "Plafonds de cave": 3.0,
        "Sol": 3.0,
    }

    foams = {
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

    st.header("Informations générales")
    col1, col2 = st.columns(2)
    with col1:
        distance = st.number_input("Distance aller simple (km) – 1 €/km A/R", min_value=0.0, value=0.0, step=1.0)
        travel_cost = distance * 2 * 1.0
        if travel_cost > 0:
            st.caption(f"Coût déplacement estimé (HT) : {travel_cost:.2f} €")
    with col2:
        extra_global = st.number_input(
            "Diverses protections et calfeutrage (HT, €)", min_value=0.0, value=0.0, step=1.0
        )

    total_material_cost = 0.0
    total_extra_cost = 0.0
    zone_summaries = []

    st.header("Saisissez les surfaces et paramètres par zone")
    for zone in resistances:
        with st.expander(zone):
            surface_expr = st.text_input(f"Surface pour {zone.lower()} (m²)", value="", placeholder="ex : 20+10+5", key=f"surf_{zone}")
            surface = parse_surface_input(surface_expr)

            foam_options = [n for n, d in foams.items() if zone in d["allowed_zones"]]
            foam_choice = st.selectbox(f"Type de mousse pour {zone.lower()}", foam_options, key=f"foam_{zone}")
            lambda_val = foams[foam_choice]["lambda"]
            unit_price = foams[foam_choice]["price"]

            default_thickness_cm = calculate_thickness(resistances[zone], lambda_val) * 100.0
            thickness_cm = st.number_input("Épaisseur (cm)", min_value=0.0, value=float(f"{default_thickness_cm:.2f}"), step=0.1, key=f"thick_{zone}")
            r_calc = (thickness_cm / 100.0) / lambda_val if lambda_val > 0 else 0.0

            cost_per_m2 = thickness_cm * unit_price
            material_cost = cost_per_m2 * surface
            extra_cost = 0.0

            if zone == "Murs":
                if st.checkbox("Inclure la coupe et l’évacuation (5 €/m²)", value=True, key=f"cut_{zone}"):
                    extra_cost += 5.0 * surface
                nb_menuiseries = st.number_input("Nombre de menuiseries à protéger", min_value=0, value=0, step=1, key=f"nb_menuis_{zone}")
                cost_per_menuiserie = st.number_input("Coût par menuiserie (€)", min_value=0.0, value=10.0, step=1.0, key=f"cost_menuis_{zone}")
                extra_cost += nb_menuiseries * cost_per_menuiserie

            elif zone == "Sol":
                cost_protection = st.number_input("Protection bas de murs et fenêtres (€)", min_value=0.0, value=0.0, step=1.0, key=f"prot_{zone}")
                extra_cost += cost_protection
                cost_sanding = st.number_input("Ponçage par m² (€)", min_value=0.0, value=0.0, step=1.0, key=f"sand_{zone}")
                extra_cost += cost_sanding * surface

            elif zone == "Plafonds de cave":
                cost_cutting = st.number_input("Coupe/évacuation par m² (€)", min_value=0.0, value=0.0, step=1.0, key=f"cut_cave_{zone}")
                extra_cost += cost_cutting * surface

            if surface > 0:
                st.write(f"Épaisseur : **{thickness_cm:.1f} cm** – R ≃ **{r_calc:.2f}**")
                st.write(f"Coût mousse (HT) : **{material_cost:.2f} €**")
                if extra_cost > 0:
                    st.write(f"Frais suppl. (HT) : **{extra_cost:.2f} €**")
                st.write(f"Total zone (HT) : **{(material_cost + extra_cost):.2f} €**")

            total_material_cost += material_cost
            total_extra_cost += extra_cost
            if surface > 0:
                zone_summaries.append(f"{zone} : {surface:.1f} m², {thickness_cm:.1f} cm, mousse {material_cost:.2f} €, extras {extra_cost:.2f} €")

    total_ht = total_material_cost + total_extra_cost + travel_cost + extra_global
    st.header("Récapitulatif du devis")
    for summary in zone_summaries:
        st.write("• " + summary)
    st.write(f"Coût mousses (HT) : **{total_material_cost:.2f} €**")
    st.write(f"Frais suppl. (HT, hors déplacement) : **{total_extra_cost:.2f} €**")
    if travel_cost > 0:
        st.write(f"Déplacement (HT) : **{travel_cost:.2f} €**")
    if extra_global > 0:
        st.write(f"Diverses protections & calfeutrage (HT) : **{extra_global:.2f} €**")
    st.subheader(f"Montant HT : **{total_ht:.2f} €**")

    tva_choice = st.selectbox("TVA", ["5.5 %", "20 %"], index=0)
    tva_rate = 0.055 if "5.5" in tva_choice else 0.20
    tva_amount = total_ht * tva_rate
    total_ttc = total_ht + tva_amount

    st.write(f"TVA ({tva_choice}) : **{tva_amount:.2f} €**")
    st.subheader(f"Montant TTC : **{total_ttc:.2f} €**")

if __name__ == "__main__":
    run_app()
