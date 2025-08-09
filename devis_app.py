"""
devis_app.py
---------------

This Streamlit application provides a simple tool for generating quotations
(`devis` in French) for spray‑applied polyurethane foam insulation.  It
implements the thermal resistance formula R = e/λ described in
construction guidance sources【576358474353077†L66-L72】 and allows the user to
estimate material thicknesses and costs for several types of building
elements.  The app supports open‑cell and closed‑cell foams with
configurable conductivities and unit prices.  Additional costs such as
cutting/evacuation, protection of openings, sanding and travel are also
incorporated.

To run this app locally, install Streamlit (`pip install streamlit`) and
then execute:

    streamlit run devis_app.py

This will start a local web server where you can interactively enter
surface areas, select foam types and view a detailed cost breakdown.
"""

from __future__ import annotations

import streamlit as st


def calculate_thickness(resistance: float, lambda_value: float) -> float:
    """Return the required thickness in metres for a given thermal resistance.

    The thermal resistance R of an insulation layer is defined as the ratio
    between its thickness (in metres) and its thermal conductivity λ (W/m·K)
    【576358474353077†L66-L72】.  Rearranging gives e = R × λ.  The returned
    thickness is in metres; multiply by 100 for centimetres.

    Args:
        resistance: Desired thermal resistance (m²·K/W).
        lambda_value: Thermal conductivity of the insulation (W/m·K).

    Returns:
        Thickness in metres required to achieve the specified resistance.
    """
    return resistance * lambda_value



def run_app() -> None:
    """Launch the Streamlit application."""
    st.set_page_config(page_title="Assistant de devis – Mousse polyuréthane", page_icon="🧾", layout="centered")

    st.title("Assistant de devis pour mousse polyuréthane projetée")
    st.markdown(
        """
        Cette application vous aide à générer un devis en calculant automatiquement
        l'épaisseur et le coût des mousses polyuréthane projetées en fonction des
        surfaces et des résistances thermiques requises.  La résistance thermique
        (R) est calculée selon la formule \(R = e / \lambda\) où \(e\) est
        l’épaisseur de l’isolant et \(\lambda\) sa conductivité thermique
        【576358474353077†L66-L72】.  Une fois l'épaisseur déterminée, elle est
        convertie en centimètres pour évaluer la quantité de mousse nécessaire.
        """
    )

    # Définition des résistances thermiques minimales selon la zone
    resistances = {
        "Murs": 3.7,
        "Rampants": 6.2,
        "Combles": 7.0,
        "Vide sanitaires": 3.0,
        "Plafonds de cave": 3.0,
        "Sol": 3.0,
    }

    # Définition des mousses disponibles, leurs lambdas et prix par centimètre par m²
    foams = {
        "008E (cellules ouvertes)": {
            "lambda": 0.037,  # W/m·K, typique des mousses à cellules ouvertes
            "price": 1.50,   # € par cm et par m²
            "allowed_zones": {"Murs", "Rampants", "Combles", "Vide sanitaires"},
        },
        "240PX (cellules fermées Isotrie)": {
            "lambda": 0.225,  # valeur fournie dans l’énoncé utilisateur
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
    distance = st.number_input(
        "Distance aller simple en kilomètres (pour le déplacement)",
        min_value=0.0,
        value=0.0,
        step=1.0,
    )
    # Le coût du déplacement est calculé aller‑retour à 1 €/km
    travel_cost = distance * 2 * 1.0
    st.write(f"Coût de déplacement calculé : **{travel_cost:.2f} €**")

    # Préparer la collecte des coûts et détails par zone
    total_material_cost = 0.0
    total_extra_cost = 0.0
    zone_summaries: list[str] = []

    st.header("Saisissez les surfaces et paramètres par zone")
    for zone in resistances:
        with st.expander(f"{zone}"):
            surface = st.number_input(
                f"Surface pour {zone.lower()} (m²)", min_value=0.0, value=0.0, step=1.0, key=f"surface_{zone}"
            )
            # Sélectionner les mousses disponibles pour cette zone
            foam_options = [name for name, data in foams.items() if zone in data["allowed_zones"]]
            if not foam_options:
                st.warning("Aucune mousse disponible pour cette zone.")
                continue
            foam_choice = st.selectbox(
                f"Type de mousse pour {zone.lower()}", foam_options, key=f"foam_{zone}"
            )
            foam_data = foams[foam_choice]
            lambda_val = foam_data["lambda"]
            unit_price = foam_data["price"]

            # Déterminer l'épaisseur
            if zone == "Sol":
                thickness_cm = st.number_input(
                    "Épaisseur souhaitée (cm) – laissez 0 pour calculer selon R ≃ 3", min_value=0.0, value=0.0, step=0.1, key=f"thickness_{zone}"
                )
                if thickness_cm <= 0.0:
                    # calculer selon la résistance par défaut
                    thickness_m = calculate_thickness(resistances[zone], lambda_val)
                    thickness_cm = thickness_m * 100.0
            else:
                thickness_m = calculate_thickness(resistances[zone], lambda_val)
                thickness_cm = thickness_m * 100.0

            # Calculer le R réel obtenu avec l'épaisseur choisie/calculée
            r_calc = (thickness_cm / 100.0) / lambda_val if lambda_val > 0 else 0.0

            # Coût matériau
            cost_per_m2 = thickness_cm * unit_price
            material_cost = cost_per_m2 * surface

            # Coûts supplémentaires spécifiques
            extra_cost = 0.0
            if zone == "Murs":
                # Coupe et évacuation des déchets
                extra_cost += 5.0 * surface
                st.write(
                    f"Coût coupe/évacuation des déchets (5 €/m²) : {5.0 * surface:.2f} €"
                )
                # Protection des menuiseries
                nb_menuiseries = st.number_input(
                    "Nombre de menuiseries (fenêtres, baies vitrées…) à protéger", min_value=0, value=0, step=1, key=f"nb_menuiseries_{zone}"
                )
                cost_per_menuiserie = st.number_input(
                    "Coût de protection par menuiserie (€)", min_value=0.0, value=10.0, step=1.0, key=f"cost_menuiserie_{zone}"
                )
                extra_cost += nb_menuiseries * cost_per_menuiserie
            elif zone == "Sol":
                # Protection des bas de murs et des fenêtres
                cost_protection = st.number_input(
                    "Coût de protection des bas de murs et des fenêtres (€)", min_value=0.0, value=0.0, step=1.0, key=f"cost_protection_{zone}"
                )
                extra_cost += cost_protection
                # Ponçage
                cost_sanding = st.number_input(
                    "Coût du ponçage par m² (€)", min_value=0.0, value=0.0, step=1.0, key=f"cost_sanding_{zone}"
                )
                extra_cost += cost_sanding * surface
            elif zone == "Plafonds de cave":
                # Optionnel : couper/évacuer pour les plafonds
                cost_cutting = st.number_input(
                    "Coût pour coupe et évacuation des déchets par m² (optionnel)", min_value=0.0, value=0.0, step=1.0, key=f"cost_cutting_{zone}"
                )
                extra_cost += cost_cutting * surface
            # Afficher les résultats pour cette zone
            zone_total = material_cost + extra_cost
            st.write(
                f"Épaisseur calculée : **{thickness_cm:.1f} cm** – Résistance obtenue ≃ **{r_calc:.2f} m²·K/W**"
            )
            st.write(f"Coût de la mousse : **{material_cost:.2f} €**")
            if extra_cost > 0:
                st.write(f"Coûts supplémentaires pour cette zone : **{extra_cost:.2f} €**")
            st.write(f"Total pour {zone.lower()} : **{zone_total:.2f} €**")

            # Conserver les totaux
            total_material_cost += material_cost
            total_extra_cost += extra_cost
            if surface > 0:
                zone_summaries.append(
                    f"{zone} : surface {surface:.1f} m², épaisseur {thickness_cm:.1f} cm, coût mousse {material_cost:.2f} €, extras {extra_cost:.2f} €"
                )

    # Calcul final
    grand_total = total_material_cost + total_extra_cost + travel_cost
    st.header("Récapitulatif du devis")
    if zone_summaries:
        for summary in zone_summaries:
            st.write("• " + summary)
    st.write(f"Coût total des mousses : **{total_material_cost:.2f} €**")
    st.write(f"Coût total des frais supplémentaires (hors déplacement) : **{total_extra_cost:.2f} €**")
    st.write(f"Coût du déplacement : **{travel_cost:.2f} €**")
    st.subheader(f"Devis estimatif TTC : **{grand_total:.2f} €**")


if __name__ == "__main__":
    run_app()
