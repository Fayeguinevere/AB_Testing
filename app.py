import random
import markdown
import csv
import os
from flask import Flask, render_template, request, redirect, url_for
from markupsafe import Markup

app = Flask(__name__)

# global state
vragen_erp= []
vragen_hrm = []

# Intro pagina
@app.route("/")
def home():
    return render_template("AB_Testing.html")

# Bedankpagina
@app.route("/bedankt")
def bedankt():
    return render_template("bedankt.html")# Incident ERP pagina
@app.route("/incident_erp/<int:nummer>")
def incident_erp(nummer):
    global vragen_erp
    if not vragen_erp:
        vragen_erp = lees_vragen_erp()
    geselecteerde = maak_random_vraag(vragen_erp)
    return render_template("incident_erp.html", vragen=[geselecteerde], nummer=nummer)

# Incident HRM pagina
@app.route("/incident_hrm/<int:nummer>")
def incident_hrm(nummer):
    global vragen_hrm
    if not vragen_hrm:
        vragen_hrm = lees_vragen_hrm()
    geselecteerde = maak_random_vraag(vragen_hrm)
    return render_template("incident_hrm.html", vragen=[geselecteerde], nummer=nummer)

# ERP vragen lezen
def lees_vragen_erp():
    alle_rijen = []
    with open("AB_ERP_ready.csv", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for rij in reader:
            alle_rijen.append(rij)
    return alle_rijen

# HRM vragen lezen
def lees_vragen_hrm():
    alle_rijen = []
    with open("AB_HRM_ready.csv", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for rij in reader:
            alle_rijen.append(rij)
    return alle_rijen

# Random positie — FIXED: maakt nu een kopie
def maak_random_vraag(vragen):
    origineel = random.choice(vragen)            # originele rij
    geselecteerde = origineel.copy()             # <<< FIX: kopie zodat CSV-structuur intact blijft

    # Random volgorde
    if random.choice([True, False]):
        geselecteerde["Optie1"] = geselecteerde["GPTo3_antwoorden"]
        geselecteerde["Optie2"] = geselecteerde["GPT-5.1_low_antwoorden"]
        geselecteerde["Optie1_model"] = "GPT-o3"
        geselecteerde["Optie2_model"] = "GPT-5.1"
    else:
        geselecteerde["Optie1"] = geselecteerde["GPT-5.1_low_antwoorden"]
        geselecteerde["Optie2"] = geselecteerde["GPTo3_antwoorden"]
        geselecteerde["Optie1_model"] = "GPT-5.1"
        geselecteerde["Optie2_model"] = "GPT-o3"

    # HTML formatting
    geselecteerde["Optie1_raw"] = geselecteerde["Optie1"]
    o1 = geselecteerde["Optie1"].replace(":", ":\n    ").replace("\n", "  \n")
    geselecteerde["Optie1_html"] = Markup(markdown.markdown(o1))

    geselecteerde["Optie2_raw"] = geselecteerde["Optie2"]
    o2 = geselecteerde["Optie2"].replace(":", ":\n    ").replace("\n", "  \n")
    geselecteerde["Optie2_html"] = Markup(markdown.markdown(o2))

    return geselecteerde

# Resultaat ERP opslaan — FIXED CSV rewrite
@app.route("/opslaan_erp/<int:nummer>", methods=["POST"])
def opslaan_erp(nummer):
    global vragen_erp

    index = (request.form.get("index"))
    onderwerp = request.form.get("onderwerp")
    toelichting = request.form.get("toelichting")
    keuze = request.form.get("keuze")
    optie1_model = request.form.get("optie1_model")
    optie2_model = request.form.get("optie2_model")

    # Resultaten opslaan
    csv_bestand = "resultaten_erp.csv"
    bestand_bestaat = os.path.exists(csv_bestand)

    with open(csv_bestand, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not bestand_bestaat:
            writer.writerow(["Index", "Model A", "Model B", "Gekozen optie", "Incident", "Onderwerp", "Toelichting"])
        writer.writerow([index, optie1_model, optie2_model, keuze, nummer, onderwerp, toelichting])

    # VERWIJDER de beantwoorde vraag
    vragen_erp = [v for v in vragen_erp if (v["Index"]) != index]

    # SCHRIJF CSV OPNIEUW — FIXED: altijd consistente header
    with open("AB_ERP_ready.csv", "w", newline="", encoding="utf-8") as csvfile:
        if vragen_erp:
            fieldnames = list(vragen_erp[0].keys())
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(vragen_erp)

    # Volgende vraag
    volgend_incident = nummer + 1
    return redirect(url_for("incident_erp", nummer=volgend_incident)) if volgend_incident <= 30 else redirect(url_for("bedankt"))

# Resultaat HRM opslaan — FIXED int comparison + CSV rewrite
@app.route("/opslaan_hrm/<int:nummer>", methods=["POST"])
def opslaan_hrm(nummer):
    global vragen_hrm

    index = int(request.form.get("index"))
    onderwerp = request.form.get("onderwerp")
    toelichting = request.form.get("toelichting")
    keuze = request.form.get("keuze")
    optie1_model = request.form.get("optie1_model")
    optie2_model = request.form.get("optie2_model")

    csv_bestand = "resultaten_hrm.csv"
    bestand_bestaat = os.path.exists(csv_bestand)

    with open(csv_bestand, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not bestand_bestaat:
            writer.writerow(["Index", "Model A", "Model B", "Gekozen optie", "Incident", "Onderwerp", "Toelichting"])
        writer.writerow([index, optie1_model, optie2_model, keuze, nummer, onderwerp, toelichting])

    # VERWIJDER de beantwoorde vraag — FIXED type
    vragen_hrm = [v for v in vragen_hrm if int(v["Index"]) != index]

    # CSV opnieuw schrijven — FIXED
    with open("AB_HRM_ready.csv", "w", newline="", encoding="utf-8") as csvfile:
        if vragen_hrm:
            fieldnames = list(vragen_hrm[0].keys())
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(vragen_hrm)

    volgend_incident = nummer + 1
    return redirect(url_for("incident_hrm", nummer=volgend_incident)) if volgend_incident <= 30 else redirect(url_for("bedankt"))


if __name__ == "__main__":
    vragen_erp = lees_vragen_erp()
    vragen_hrm = lees_vragen_hrm()
    app.run(debug=True)
