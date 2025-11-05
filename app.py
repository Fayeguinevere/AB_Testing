import random
import markdown
import csv
import os
from flask import Flask, render_template, request, redirect, url_for
from markupsafe import Markup

app = Flask(__name__)

# Intro pagina
@app.route("/")
def home():
    return render_template("AB_Testing.html")


# Incident pagina
@app.route("/incident/<int:nummer>")
def incident(nummer):
    """Toon een willekeurig incident met Markdown-opmaak."""
    vragen = lees_vragen()
    random.seed(nummer)
    geselecteerde = maak_random_vraag(vragen)
    return render_template("incident.html", vragen=[geselecteerde], nummer=nummer)

# Bedankpagina
@app.route("/bedankt")
def bedankt():
    return render_template("bedankt.html")

# CSV lezen
def lees_vragen():
    """Lees alle rijen uit het CSV-bestand."""
    alle_rijen = []
    with open("AB_dataset_nieuw.csv", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for rij in reader:
            alle_rijen.append(rij)
    return alle_rijen


# Random positie
def maak_random_vraag(vragen):
    geselecteerde = random.sample(vragen, 1)[0]

    if random.choice([True, False]):
        geselecteerde["Optie1"] = geselecteerde["GPTo_antwoorden"]
        geselecteerde["Optie2"] = geselecteerde["GPT5_antwoorden"]
        geselecteerde["Optie1_model"] = "GPT-o3"
        geselecteerde["Optie2_model"] = "GPT-5"
    else:
        geselecteerde["Optie1"] = geselecteerde["GPT5_antwoorden"]
        geselecteerde["Optie2"] = geselecteerde["GPTo_antwoorden"]
        geselecteerde["Optie1_model"] = "GPT-5"
        geselecteerde["Optie2_model"] = "GPT-o3"

    geselecteerde["Optie1"] = Markup(markdown.markdown(geselecteerde["Optie1"]))
    geselecteerde["Optie2"] = Markup(markdown.markdown(geselecteerde["Optie2"]))

    return geselecteerde

# Resultaat opslaan
# Resultaat opslaan
@app.route("/opslaan/<int:nummer>", methods=["POST"])
def opslaan_incident(nummer):
    """Sla resultaat op, verwijder de gebruikte vraag, en ga door naar het volgende incident."""
    index = request.form.get("index")
    onderwerp = request.form.get("onderwerp")
    toelichting = request.form.get("toelichting")
    optie1 = request.form.get("optie1")
    optie2 = request.form.get("optie2")
    keuze = request.form.get("keuze")
    optie1_model = request.form.get("optie1_model")
    optie2_model = request.form.get("optie2_model")

    # --- 1️⃣ Resultaat opslaan in resultaten.csv ---
    csv_bestand = "resultaten.csv"
    bestand_bestaat = os.path.exists(csv_bestand)

    with open(csv_bestand, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not bestand_bestaat:
            writer.writerow([
                "Index", "Incident", "Onderwerp", "Toelichting", "Optie 1", "Optie 2",
                "Model 1", "Model 2", "Gekozen optie"
            ])
        writer.writerow([
            index, nummer, onderwerp, toelichting, optie1, optie2,
            optie1_model, optie2_model, keuze
        ])

    # --- 2️⃣ Verwijder de gebruikte vraag uit AB_dataset_nieuw.csv ---
    try:
        alle_vragen = lees_vragen()
        # Filter alle vragen behalve degene met het gekozen indexnummer
        nieuwe_vragen = [v for v in alle_vragen if v["Index"] != index]

        # Alleen herschrijven als er iets is verwijderd
        if len(nieuwe_vragen) < len(alle_vragen):
            with open("AB_dataset_nieuw.csv", "w", newline="", encoding="utf-8") as csvfile:
                fieldnames = alle_vragen[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(nieuwe_vragen)
    except Exception as e:
        print(f"⚠️ Fout bij verwijderen van vraag {index}: {e}")

    # --- 3️⃣ Naar volgende incident of bedankt ---
    volgend_incident = nummer + 1
    if volgend_incident <= 5:
        return redirect(url_for("incident", nummer=volgend_incident))
    else:
        return redirect(url_for("bedankt"))



if __name__ == "__main__":
    app.run(debug=True)
