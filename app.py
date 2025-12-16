import random
import markdown
import csv
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
from markupsafe import Markup
from functools import wraps
from io import StringIO
from database import DatabaseManager

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

# Configuration
CONFIG = {
    "database": "ab_testing.db",
    "admin_key": os.environ.get("ADMIN_KEY", "djh2udc3hug_JND-vxv"),  # Change this!
    "max_incidents": 30,
    "models": {
        "model_a": "GPT-o3",
        "model_b": "GPT-5.1",
        "column_a": "GPTo3_antwoorden",
        "column_b": "GPT-5.1_low_antwoorden"
    },
    "erp": {
        "csv_ready": "AB_ERP_ready.csv",
        "table_questions": "questions_erp",
        "table_results": "results_erp",
        "template": "incident_erp.html",
        "route": "incident_erp"
    },
    "hrm": {
        "csv_ready": "AB_HRM_ready.csv",
        "table_questions": "questions_hrm",
        "table_results": "results_hrm",
        "template": "incident_hrm.html",
        "route": "incident_hrm"
    }
}

# Initialize database manager
db = DatabaseManager(CONFIG)

# Admin authentication decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Intro pagina
@app.route("/")
def home():
    return render_template("AB_Testing.html")

# Bedankpagina
@app.route("/bedankt")
def bedankt():
    return render_template("bedankt.html")

# Admin login
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        key = request.form.get("key")
        if key == CONFIG["admin_key"]:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Ongeldige toegangscode", "error")
    return render_template("admin_login.html")

# Admin logout
@app.route("/admin/logout")
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('home'))

# Admin dashboard
@app.route("/admin")
@admin_required
def admin_dashboard():
    # Get results
    erp_results = db.get_all_results("erp")
    hrm_results = db.get_all_results("hrm")
    
    # Get statistics
    stats = db.get_statistics()
    
    return render_template("admin_dashboard.html", 
                         erp_results=erp_results,
                         hrm_results=hrm_results,
                         erp_count=stats["erp_count"],
                         hrm_count=stats["hrm_count"],
                         erp_remaining=stats["erp_remaining"],
                         hrm_remaining=stats["hrm_remaining"])

# Export results as CSV
@app.route("/admin/export/<incident_type>")
@admin_required
def export_results(incident_type):
    if incident_type not in ["erp", "hrm"]:
        return "Invalid type", 400
    
    results = db.get_all_results(incident_type)
    
    if not results:
        return "No results to export", 404
    
    # Create CSV with old format to match original
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header (matching old format exactly)
    writer.writerow(["Index", "Model A", "Model B", "Gekozen optie", "Incident", "Onderwerp", "Toelichting"])
    
    # Write data (mapping new column names to old format)
    for row in results:
        writer.writerow([
            row["question_index"],  # Index
            row["model_a"],          # Model A
            row["model_b"],          # Model B
            row["gekozen_optie"],    # Gekozen optie
            row["incident_nummer"],  # Incident
            row["onderwerp"],        # Onderwerp
            row["toelichting"]       # Toelichting
        ])
    
    # Prepare response
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=results_{incident_type}.csv"}
    )

# Reset database
@app.route("/admin/reset/<incident_type>", methods=["POST"])
@admin_required
def reset_database(incident_type):
    if incident_type not in ["erp", "hrm", "all"]:
        return "Invalid type", 400
    
    db.reset_database(incident_type)
    flash(f"Database gereset voor {incident_type.upper()}", "success")
    return redirect(url_for('admin_dashboard'))

# Generic incident pagina
def toon_incident(incident_type, nummer):
    vraag = db.get_random_question(incident_type)
    
    if not vraag:
        # No more questions available
        return redirect(url_for("bedankt"))
    
    geselecteerde = maak_random_vraag(vraag)
    return render_template(CONFIG[incident_type]["template"], vragen=[geselecteerde], nummer=nummer)

# Incident ERP pagina
@app.route("/incident_erp/<int:nummer>")
def incident_erp(nummer):
    return toon_incident("erp", nummer)

# Incident HRM pagina
@app.route("/incident_hrm/<int:nummer>")
def incident_hrm(nummer):
    return toon_incident("hrm", nummer)


# Random positie
def maak_random_vraag(vraag):
    geselecteerde = vraag.copy()

    # Random volgorde
    if random.choice([True, False]):
        geselecteerde["Optie1"] = geselecteerde[CONFIG["models"]["column_a"]]
        geselecteerde["Optie2"] = geselecteerde[CONFIG["models"]["column_b"]]
        geselecteerde["Optie1_model"] = CONFIG["models"]["model_a"]
        geselecteerde["Optie2_model"] = CONFIG["models"]["model_b"]
    else:
        geselecteerde["Optie1"] = geselecteerde[CONFIG["models"]["column_b"]]
        geselecteerde["Optie2"] = geselecteerde[CONFIG["models"]["column_a"]]
        geselecteerde["Optie1_model"] = CONFIG["models"]["model_b"]
        geselecteerde["Optie2_model"] = CONFIG["models"]["model_a"]

    # HTML formatting
    geselecteerde["Optie1_raw"] = geselecteerde["Optie1"]
    o1 = geselecteerde["Optie1"].replace(":", ":\n    ").replace("\n", "  \n")
    geselecteerde["Optie1_html"] = Markup(markdown.markdown(o1))

    geselecteerde["Optie2_raw"] = geselecteerde["Optie2"]
    o2 = geselecteerde["Optie2"].replace(":", ":\n    ").replace("\n", "  \n")
    geselecteerde["Optie2_html"] = Markup(markdown.markdown(o2))

    return geselecteerde

# Generic save function (thread-safe with SQLite)
def opslaan_resultaat(incident_type, nummer):
    index = request.form.get("index")
    onderwerp = request.form.get("onderwerp")
    toelichting = request.form.get("toelichting")
    keuze = request.form.get("keuze")
    optie1_model = request.form.get("optie1_model")
    optie2_model = request.form.get("optie2_model")

    # Save to database
    db.save_result(incident_type, index, optie1_model, optie2_model, 
                   keuze, nummer, onderwerp, toelichting)
    
    # Redirect to next question
    volgend_incident = nummer + 1
    if volgend_incident <= CONFIG["max_incidents"]:
        return redirect(url_for(CONFIG[incident_type]["route"], nummer=volgend_incident))
    else:
        return redirect(url_for("bedankt"))

# Resultaat ERP opslaan
@app.route("/opslaan_erp/<int:nummer>", methods=["POST"])
def opslaan_erp(nummer):
    return opslaan_resultaat("erp", nummer)

# Resultaat HRM opslaan
@app.route("/opslaan_hrm/<int:nummer>", methods=["POST"])
def opslaan_hrm(nummer):
    return opslaan_resultaat("hrm", nummer)


if __name__ == "__main__":
    db.init_database()
    app.run(debug=True)
