"""
SETTINGS FILE - teachers can edit the values in the first section.
Teacher username/password are NOT here: they live in .streamlit/secrets.toml
(or Streamlit Cloud Secrets, or environment variables TEACHER_USERNAME / TEACHER_PASSWORD).
"""
import os
import streamlit as st

# ---------------- EDIT THESE ----------------
ASSESSMENT_TITLE = "Grade 7 Science Assessment"
TOPIC = "Separation Techniques"
PASSING_PERCENT = 50                      # passing grade (%)
NUM_QUESTIONS = None                      # None = use all questions, or e.g. 10
CLASS_OPTIONS = ["7A", "7B", "7C", "7D"]  # class names shown to students
ALLOW_RETAKES = False                     # False = same name + class can submit only once
TIMEZONE = "Asia/Beirut"                  # used for the submission date/time
QUESTIONS_FILE = "questions.json"
EXCEL_FILENAME = "Grade7_Science_Assessment_Results.xlsx"
SQLITE_PATH = "grades.db"                 # local database file (not publicly served)
# --------------------------------------------


def _secret(section, key, env_name):
    try:
        return st.secrets[section][key]
    except Exception:
        return os.environ.get(env_name)


def get_teacher_credentials():
    return _secret("teacher", "username", "TEACHER_USERNAME"), _secret("teacher", "password", "TEACHER_PASSWORD")


def get_database_url():
    url = _secret("database", "url", "DATABASE_URL")
    if not url:
        return f"sqlite:///{SQLITE_PATH}"
    # Always use the modern "psycopg" (v3) driver for PostgreSQL
    for prefix in ("postgresql+psycopg2://", "postgresql://", "postgres://"):
        if url.startswith(prefix):
            url = "postgresql+psycopg://" + url[len(prefix):]
            break
    return url
