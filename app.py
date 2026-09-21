from datetime import datetime, timezone
from secrets import randbelow

from flask import Flask, render_template, request

app = Flask(__name__)

PRIORITIES = {
    "baja": ("Baja", "priority-low"),
    "media": ("Media", "priority-medium"),
    "alta": ("Alta", "priority-high"),
    "critica": ("Crítica", "priority-critical"),
}


def create_ticket(form):
    priority_key = form.get("priority", "media")
    priority = PRIORITIES.get(priority_key, PRIORITIES["media"])
    ticket_number = f"TCK-{datetime.now(timezone.utc):%Y%m%d}-{randbelow(9000) + 1000}"
    return {
        "number": ticket_number,
        "created_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "requester": form.get("requester", "").strip(),
        "email": form.get("email", "").strip(),
        "category": form.get("category", "Soporte"),
        "priority": priority[0],
        "priority_class": priority[1],
        "subject": form.get("subject", "").strip(),
        "description": form.get("description", "").strip(),
    }


@app.route("/", methods=["GET", "POST"])
def index():
    ticket = None
    if request.method == "POST":
        ticket = create_ticket(request.form)
    return render_template("index.html", ticket=ticket)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
