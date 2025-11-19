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
    return render_template("bedankt.html")

# Incident ERP pagina
@app.route("/incident_erp/<int:nummer>")
def incident_erp(nummer):
    global vragen_erp
    if not vragen_erp:           # Probleem zit hier
        vragen_erp = lees_vragen_erp()
    geselecteerde = maak_random_vraag(vragen_erp)
    return render_template("incident_erp.html", vragen=[geselecteerde], nummer=nummer)

# Incident HRM pagina
@app.route("/incident_hrm/<int:nummer>")
def incident_hrm(nummer):
    global vragen_hrm
    if not vragen_hrm:           # Probleem zit hier
        vragen_hrm = lees_vragen_hrm()
    geselecteerde = maak_random_vraag(vragen_hrm)
    return render_template("incident_hrm.html", vragen=[geselecteerde], nummer=nummer)

# ERP Vragen lezen
def lees_vragen_erp():
    alle_rijen = []
    with open("AB_ERP_app.csv", newline="", encoding="utf-8") as csvfile: # deze veranderen wanneer echt live
        reader = csv.DictReader(csvfile)
        for rij in reader:
            alle_rijen.append(rij)
    return alle_rijen

# Hrm Vragen lezen
def lees_vragen_hrm():
    alle_rijen = []
    with open("AB_HRM_app.csv", newline="", encoding="utf-8") as csvfile: # deze veranderen wanneer echt live
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
    
    geselecteerde["Optie1_raw"] = geselecteerde["Optie1"]
    optie1_clean = geselecteerde["Optie1"].replace(":", ":\n    ")
    optie1_clean = optie1_clean.replace("\n", "  \n")
    geselecteerde["Optie1_html"] = Markup(markdown.markdown(optie1_clean))

    geselecteerde["Optie2_raw"] = geselecteerde["Optie2"]
    optie2_clean = geselecteerde["Optie2"].replace(":", ":\n    ")
    optie2_clean = optie2_clean.replace("\n", "  \n")
    geselecteerde["Optie2_html"] = Markup(markdown.markdown(optie2_clean))

    #geselecteerde["Optie1"] = Markup(markdown.markdown(geselecteerde["Optie1"]))
    #geselecteerde["Optie2"] = Markup(markdown.markdown(geselecteerde["Optie2"]))

    return geselecteerde

# Resultaat ERP opslaan
@app.route("/opslaan_erp/<int:nummer>", methods=["POST"])
def opslaan_erp(nummer):
    global vragen_erp
    index = request.form.get("index")
    onderwerp = request.form.get("onderwerp")
    toelichting = request.form.get("toelichting")
    optie1 = request.form.get("optie1")
    optie2 = request.form.get("optie2")
    keuze = request.form.get("keuze")
    optie1_model = request.form.get("optie1_model")
    optie2_model = request.form.get("optie2_model")

    csv_bestand = "resultaten_erp.csv"
    bestand_bestaat = os.path.exists(csv_bestand)

    with open(csv_bestand, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not bestand_bestaat:
            writer.writerow(["Index", "Incident", "Onderwerp", "Toelichting", "Optie 1", "Optie 2","Model 1", "Model 2", "Gekozen optie"])
        writer.writerow([index, nummer, onderwerp, toelichting, optie1, optie2, optie1_model, optie2_model, keuze])

    try:
        nieuwe_vragen = [v for v in vragen_erp if v["Index"] != index]
        vragen_erp = nieuwe_vragen
        with open("AB_ERP_app.csv", "w", newline="", encoding="utf-8") as csvfile: # ook wijzigen
                fieldnames = vragen_erp[0].keys() if vragen_erp else []
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                if fieldnames:
                    writer.writeheader()
                    writer.writerows(vragen_erp)
    except Exception as e:
        print(f"Fout bij verwijderen van vraag {index}: {e}")

    volgend_incident = nummer + 1
    if volgend_incident <= 20:
        return redirect(url_for("incident_erp", nummer=volgend_incident))
    else:
        return redirect(url_for("bedankt"))

# Resultaat opslaan HRM
@app.route("/opslaan_hrm/<int:nummer>", methods=["POST"])
def opslaan_hrm(nummer):
    global vragen_hrm
    index = request.form.get("index")
    onderwerp = request.form.get("onderwerp")
    toelichting = request.form.get("toelichting")
    optie1 = request.form.get("optie1")
    optie2 = request.form.get("optie2")
    keuze = request.form.get("keuze")
    optie1_model = request.form.get("optie1_model")
    optie2_model = request.form.get("optie2_model")

    csv_bestand = "resultaten_hrm.csv"
    bestand_bestaat = os.path.exists(csv_bestand)

    with open(csv_bestand, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not bestand_bestaat:
            writer.writerow(["Index", "Incident", "Onderwerp", "Toelichting", "Optie 1", "Optie 2","Model 1", "Model 2", "Gekozen optie"])
        writer.writerow([index, nummer, onderwerp, toelichting, optie1, optie2, optie1_model, optie2_model, keuze])

    try:
        nieuwe_vragen = [v for v in vragen_hrm if v["Index"] != index]
        vragen_hrm = nieuwe_vragen
        with open("AB_HRM_app.csv", "w", newline="", encoding="utf-8") as csvfile: # ook wijzigen
                fieldnames = vragen_hrm[0].keys() if vragen_hrm else []
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                if fieldnames:
                    writer.writeheader()
                    writer.writerows(vragen_hrm)
    except Exception as e:
        print(f"Fout bij verwijderen van vraag {index}: {e}")

    volgend_incident = nummer + 1
    if volgend_incident <= 20:
        return redirect(url_for("incident_hrm", nummer=volgend_incident))
    else:
        return redirect(url_for("bedankt"))


if __name__ == "__main__":
    vragen_erp = lees_vragen_erp()
    vragen_hrm = lees_vragen_hrm()
    app.run(debug=True)
