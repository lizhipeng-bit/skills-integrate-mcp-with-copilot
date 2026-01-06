"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from email.message import EmailMessage
import smtplib
from typing import Dict

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


def _get_int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


class EmailSettings:
    def __init__(self) -> None:
        self.host = os.getenv("SMTP_HOST")
        self.port = _get_int_env("SMTP_PORT", 587)
        self.username = os.getenv("SMTP_USERNAME")
        self.password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("FROM_EMAIL")
        self.from_name = os.getenv("FROM_NAME", "Mergington High School Activities")
        # Default to TLS for common SMTP setups
        self.use_tls = os.getenv("SMTP_USE_TLS", "true").lower() != "false"

    @property
    def sender(self) -> str:
        if self.from_name and self.from_email:
            return f"{self.from_name} <{self.from_email}>"
        return self.from_email or ""

    @property
    def is_configured(self) -> bool:
        return bool(self.host and self.port and self.from_email)


email_settings = EmailSettings()


def send_email(subject: str, body: str, to_email: str) -> None:
    """Send an email using configured SMTP settings."""
    if not email_settings.is_configured:
        print("Email settings not configured; skipping email send.")
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = email_settings.sender
    message["To"] = to_email
    message.set_content(body)

    try:
        with smtplib.SMTP(email_settings.host, email_settings.port) as server:
            if email_settings.use_tls:
                server.starttls()
            if email_settings.username and email_settings.password:
                server.login(email_settings.username, email_settings.password)
            server.send_message(message)
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to send email to {to_email}: {exc}")


def _registration_email_body(activity_name: str, activity: Dict, student_email: str) -> str:
    return (
        "Registration Confirmation\n"
        "---------------------------\n"
        f"Student: {student_email}\n"
        f"Activity: {activity_name}\n"
        f"Schedule: {activity.get('schedule', 'TBD')}\n"
        f"Location: {activity.get('location', 'On campus')}\n\n"
        "You are successfully registered. If you need to cancel, use the unregister option on the site."
    )


def _cancellation_email_body(activity_name: str, activity: Dict, student_email: str) -> str:
    return (
        "Cancellation Confirmation\n"
        "---------------------------\n"
        f"Student: {student_email}\n"
        f"Activity: {activity_name}\n"
        f"Schedule: {activity.get('schedule', 'TBD')}\n\n"
        "Your registration has been cancelled. You can re-register anytime if spots are available."
    )


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str, background_tasks: BackgroundTasks):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)

    background_tasks.add_task(
        send_email,
        subject=f"Successfully Registered for {activity_name}",
        body=_registration_email_body(activity_name, activity, email),
        to_email=email,
    )

    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str, background_tasks: BackgroundTasks):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)

    background_tasks.add_task(
        send_email,
        subject=f"Activity Registration Cancelled - {activity_name}",
        body=_cancellation_email_body(activity_name, activity, email),
        to_email=email,
    )

    return {"message": f"Unregistered {email} from {activity_name}"}
