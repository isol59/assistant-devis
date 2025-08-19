"""
devis_app.py - Assistant de devis mousse polyuréthane (multi-lignes par zone)

Fonctions principales :
- Plusieurs lignes par zone (Murs, Rampants, Combles, Sol, Plafonds de cave, Vide sanitaires)
  => chaque ligne a sa surface (acceptant 20+10+5), sa mousse, son épaisseur modifiable et ses extras
- Affiche le total de surface calculé juste sous le champ (ex : '20+10+50' → '= 80.00 m²')
- Ligne globale : Diverses protections & calfeutrage (HT)
- Déplacement caché si = 0
- Totaux en HT + sélection TVA (5,5 % ou 20 %) + TTC

Paramètres mousses (prix en €/cm/m²) :
- 008E (cellules ouvertes)  λ=0.037   prix=1.50
- 240PX (Isotrie, fermées)  λ=0.0225  prix=3.80   (corrigé)
- 35Z  (Synthésia, fermées) λ=0.027   prix=3.50
"""

from __future__ import annotations
import streamlit as st

# --------------------------- Utilitaires ---------------------------

def calculate_thickness(resistance: float, lambda_value: float) -> float:
    """e = R × λ (épaisseur en mètres)"""
    return resistance * lambda_value

def parse_surface_input(value: str) -> float:
    """Somme les termes 'a+b+c' en m² (gère les virgules)."""
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
        "lambda": 0.037,   # W/m·K
        "price": 1.50,     # €/cm/m²
        "allowed_zones": {"Murs", "Rampants", "Combles", "Vide sanitaires"},
    },
    "240PX (cellules fermées Isotrie)": {
        "lambda": 0.0225,  # W/m·K  (corrigé)
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
    st.caption("Ajoutez plusieurs postes par zone (épaisseurs différentes en plafonds, murs, sols, etc.).")

    # ---- Infos générales
    st.header("Informations générales")
    col1, col2 = st.columns(2)
    with col1:
        distance = st.number_input(
            "Distance aller simple (km) – 1 €/km A/R",
            min_value=0.0, value=0.0, step=1.0
        )
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
    zone_summaries: list[str] = []

    st.header("Postes par zone")
    for zone_name, r_min in RESISTANCES.items():
        with st.expander(zone_name, expanded=False):
            # Nombre de lignes pour cette zone
            nb = st.number_input(
                f"Nombre de lignes pour {zone_name.lower()}",
                min_value=0, value=0, step=1, key=f"nb_{zone_name}"
            )
            # Boucle sur chaque ligne
            for i in range(int(nb)):
                st.markdown(f"**Ligne {i+1}**")

                # Surface : saisie expression + résultat affiché
                surface_expr = st.text_input(
                    f"Surface ligne {i+1} (m²) – ex : 20+10+50",
                    value="", placeholder="ex : 20+10+50", key=f"surf_{zone_name}_{i}"
                )
                surface = parse_surface_input(surface_expr)
                st.caption(f"= {surface:.2f} m²")

                # Mousse autorisée pour cette zone
                foam_options = [n for n, d in FOAMS.items() if zone_name in d["allowed_zones"]]
                foam_choice = st.selectbox(
                    f"Mousse ligne {i+1}",
                    foam_options, key=f"foam_{zone_name}_{i}"
                )
                lambda_val = FOAMS[foam_choice]["lambda"]
                unit_price = FOAMS[foam_choice]["price"]

                # Épaisseur par défaut selon R mini (modifiable)
                default_thick_cm = calculate_thickness(r_min, lambda_val) * 100.0
                thickness_cm = st.number_input(
                    f"Épaisseur ligne {i+1} (cm)",
                    min_value=0.0, value=float(f"{default_thick_cm:.2f}"),
                    step=0.1, key=f"thick_{zone_name}_{i}",
                    help="Modifiez pour les épaisseurs imposées (différentes lignes possibles)."
                )

                # R obtenu
                r_calc = (thickness_cm / 100.0) / lambda_val if lambda_val > 0 else 0.0

                # Coût matière
                cost_per_m2 = thickness_cm * unit_price   # €/m²
                material_cost = cost_per_m2 * surface

                # Extras spécifiques par zone (par ligne)
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

                # Affichage ligne
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

    # ---- Récapitulatif & TVA
    total_ht = total_material_cost + total_extra_cost + travel_cost + extra_global
    st.header("Récapitulatif du devis")
    if zone_summaries:
        for s in zone_summaries:
            st.write("• " + s)

    st.write(f"Coût mousses (HT) : **{total_material_cost:.2f} €**")
    st.write(f"Frais supplémentaires (HT, hors déplacement) : **{total_extra_cost:.2f} €**")
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
