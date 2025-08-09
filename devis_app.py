"""
devis_app.py
---------------

Application Streamlit pour générer des devis de projection de mousse polyuréthane.
- Saisie de surfaces sous forme d'expression (ex : 20+10+5)
- Épaisseur modifiable pour chaque zone (valeur par défaut calculée via R = e/λ)
- Option d'inclure/exclure la coupe+évacuation des déchets (Murs)
- Total en HT, puis sélection de TVA (5,5 % ou 20 %) et calcul TTC
"""

from __future__ import annotations

import streamlit as st


def calculate_thickness(resistance: float, lambda_value: float) -> float:
    """Retourne l'épaisseur nécessaire (m) pour une résistance thermique donnée.
    R = e / λ  =>  e = R × λ
    """
    return resistance * lambda_value


def parse_surface_input(value: str) -> float:
    """Convertit une expression utilisateur (ex: '20+10+5') en surface totale (m²)."""
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


def run_app() -> None:
    st.set_page_config(page_title="Assistant de devis – Mousse polyuréthane", page_icon="🧾", layout="centered")

    st.title("Assistant de devis pour mousse polyuréthane projetée")
    st.markdown(
        """
        Calcule automatiquement **l'épaisseur** et le **coût** des mousses polyuréthane projetées
        à partir des surfaces et des résistances thermiques requises.
        La résistance thermique (R) suit la formule **R = e / λ** (avec **e** en mètres et **λ** en W/m·K).
        """
    )

    # Résistances thermiques minimales (m²·K/W)
    resistances = {
        "Murs": 3.7,
        "Rampants": 6.2,
        "Combles": 7.0,
        "Vide sanitaires": 3.0,
        "Plafonds de cave": 3.0,
        "Sol": 3.0,
    }

    # Mousses disponibles
    foams = {
        "008E (cellules ouvertes)": {
            "lambda": 0.037,   # W/m·K
            "price": 1.50,     # €/cm/m²
            "allowed_zones": {"Murs", "Rampants", "Combles", "Vide sanitaires"},
        },
        "240PX (cellules fermées Isotrie)": {
            "lambda": 0.0225,  # corrigé : 0.0225 W/m·K
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
        "Distance aller simple en kilomètres (pour le déplacement, 1 € / km A/R)",
        min_value=0.0,
        value=0.0,
        step=1.0,
    )
    travel_cost = distance * 2 * 1.0  # A/R

    total_material_cost = 0.0
    total_extra_cost = 0.0
    zone_summaries: list[str] = []

    st.header("Saisissez les surfaces et paramètres par zone")
    for zone in resistances:
        with st.expander(f"{zone}"):
            # Surface en expression libre (ex : 20+10+5)
            surface_expr = st.text_input(
                f"Surface pour {zone.lower()} (m²)",
                value="",
                placeholder="ex : 20+10+5",
                key=f"surface_{zone}",
            )
            surface = parse_surface_input(surface_expr)

            # Type de mousse autorisé dans cette zone
            foam_options = [name for name, data in foams.items() if zone in data["allowed_zones"]]
            if not foam_options:
                st.warning("Aucune mousse disponible pour cette zone.")
                continue
            foam_choice = st.selectbox(
                f"Type de mousse pour {zone.lower()}",
                foam_options,
                key=f"foam_{zone}",
            )
            foam_data = foams[foam_choice]
            lambda_val = foam_data["lambda"]
            unit_price = foam_data["price"]

            # Épaisseur par défaut (cm) selon R mini
            default_thickness_cm = calculate_thickness(resistances[zone], lambda_val) * 100.0

            # Épaisseur modifiable pour TOUTES les zones (y compris Sol)
            thickness_cm = st.number_input(
                "Épaisseur (cm)",
                min_value=0.0,
                value=float(f"{default_thickness_cm:.2f}"),
                step=0.1,
                key=f"thickness_{zone}",
                help="Modifiez si le client impose une épaisseur précise.",
            )

            # R obtenu avec l'épaisseur choisie
            r_calc = (thickness_cm / 100.0) / lambda_val if lambda_val > 0 else 0.0

            # Coût matière
            cost_per_m2 = thickness_cm * unit_price
            material_cost = cost_per_m2 * surface

            # Coûts supplémentaires spécifiques
            extra_cost = 0.0
            if zone == "Murs":
                include_cutting = st.checkbox(
                    "Inclure la coupe et l’évacuation des déchets (5 €/m²)",
                    value=True,
                    key=f"include_cutting_{zone}",
                )
                if include_cutting and surface > 0:
                    extra_cost += 5.0 * surface
                    st.caption(f"Coupe/évacuation : {5.0 * surface:.2f} €")

                nb_menuiseries = st.number_input(
                    "Nombre de menuiseries à protéger (fenêtres, baies, etc.)",
                    min_value=0,
                    value=0,
                    step=1,
                    key=f"nb_menuiseries_{zone}",
                )
                cost_per_menuiserie = st.number_input(
                    "Coût de protection par menuiserie (€)",
                    min_value=0.0,
                    value=10.0,
                    step=1.0,
                    key=f"cost_menuiserie_{zone}",
                )
                extra_cost += nb_menuiseries * cost_per_menuiserie

            elif zone == "Sol":
                cost_protection = st.number_input(
                    "Coût de protection des bas de murs et des fenêtres (€)",
                    min_value=0.0,
                    value=0.0,
                    step=1.0,
                    key=f"cost_protection_{zone}",
                )
                extra_cost += cost_protection

                cost_sanding = st.number_input(
                    "Coût du ponçage par m² (€)",
                    min_value=0.0,
                    value=0.0,
                    step=1.0,
                    key=f"cost_sanding_{zone}",
                )
                extra_cost += cost_sanding * surface

            elif zone == "Plafonds de cave":
                cost_cutting = st.number_input(
                    "Coût coupe/évacuation par m² (optionnel)",
                    min_value=0.0,
                    value=0.0,
                    step=1.0,
                    key=f"cost_cutting_{zone}",
                )
                extra_cost += cost_cutting * surface

            # Affichage zone (uniquement si surface > 0)
            if surface > 0:
                st.write(
                    f"Épaisseur : **{thickness_cm:.1f} cm** – R obtenu ≃ **{r_calc:.2f} m²·K/W**"
                )
                st.write(f"Coût mousse (HT) : **{material_cost:.2f} €**")
                if extra_cost > 0:
                    st.write(f"Frais supplémentaires (HT) : **{extra_cost:.2f} €**")
                st.write(f"Total zone (HT) : **{(material_cost + extra_cost):.2f} €**")

            total_material_cost += material_cost
            total_extra_cost += extra_cost
            if surface > 0:
                zone_summaries.append(
                    f"{zone} : {surface:.1f} m², {thickness_cm:.1f} cm, mousse {material_cost:.2f} €, extras {extra_cost:.2f} €"
                )

    # Récapitulatif & TVA
    total_ht = total_material_cost + total_extra_cost + travel_cost
    st.header("Récapitulatif du devis")
    if zone_summaries:
        for summary in zone_summaries:
            st.write("• " + summary)

    st.write(f"Coût total des mousses (HT) : **{total_material_cost:.2f} €**")
    st.write(f"Frais supplémentaires (HT, hors déplacement) : **{total_extra_cost:.2f} €**")
    st.write(f"Déplacement (HT) : **{travel_cost:.2f} €**")
    st.subheader(f"Montant HT : **{total_ht:.2f} €**")

    tva_choix = st.selectbox("TVA", ["5.5 %", "20 %"], index=0)
    tva_taux = 0.055 if "5.5" in tva_choix else 0.20
    tva_montant = total_ht * tva_taux
    total_ttc = total_ht + tva_montant

    st.write(f"TVA ({tva_choix}) : **{tva_montant:.2f} €**")
    st.subheader(f"Montant TTC : **{total_ttc:.2f} €**")


if __name__ == "__main__":
    run_app()
