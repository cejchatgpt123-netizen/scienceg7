"""Grade 7 Science Assessment - run with:  streamlit run app.py"""
import copy
import hmac
import json
import random
import re
import uuid
from io import BytesIO

import pandas as pd
import streamlit as st
from openpyxl.styles import Alignment, Font, PatternFill

import config
import database

st.set_page_config(page_title=config.ASSESSMENT_TITLE, page_icon="🔬", layout="centered")
st.markdown("""
<style>
.block-container {max-width: 760px; padding-top: 2rem;}
h1, h2, h3 {color: #1b5e8c;}
div.stButton > button, div.stFormSubmitButton > button, div.stDownloadButton > button
  {border-radius: 10px; font-weight: 600; width: 100%;}
</style>""", unsafe_allow_html=True)

ss = st.session_state
ss.setdefault("page", "welcome")


# ---------------------------------------------------------------- helpers
@st.cache_data
def load_questions():
    with open(config.QUESTIONS_FILE, encoding="utf-8") as f:
        return json.load(f)


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def valid_name(name):
    return 2 <= len(name) <= 60 and re.fullmatch(r"[\w .'\-]+", name) is not None


def prepare_attempt():
    """Random question order + random answer order. Correct answers are kept by value."""
    qs = copy.deepcopy(load_questions())
    random.shuffle(qs)
    if config.NUM_QUESTIONS:
        qs = qs[:config.NUM_QUESTIONS]
    for q in qs:
        if q["type"] == "mcq":
            random.shuffle(q["options"])
        elif q["type"] == "tf":
            q["options"] = ["True", "False"]
            q["answer"] = str(q["answer"]).capitalize()
        elif q["type"] == "matching":
            random.shuffle(q["pairs"])
            q["choices"] = [p["right"] for p in q["pairs"]]
            random.shuffle(q["choices"])
    return qs


def go(page):
    ss.page = page
    st.rerun()


def reset_student():
    for k in [k for k in ss if k.startswith("q_")] + ["attempt", "result", "student", "submission_id"]:
        ss.pop(k, None)


def grade(questions):
    """Returns (correct_count, feedback list, number_unanswered)."""
    correct, feedback, unanswered = 0, [], 0
    for q in questions:
        if q["type"] == "matching":
            given = [ss.get(f"q_{q['id']}_{i}") for i in range(len(q["pairs"]))]
            if None in given:
                unanswered += 1
            ok = given == [p["right"] for p in q["pairs"]]
            right = "; ".join(f"{p['left']} → {p['right']}" for p in q["pairs"])
            yours = "; ".join(f"{p['left']} → {g}" for p, g in zip(q["pairs"], given))
        else:
            given = ss.get(f"q_{q['id']}")
            if given is None:
                unanswered += 1
            ok, right, yours = given == q["answer"], q["answer"], given
        correct += ok
        feedback.append({"q": q["question"], "ok": ok, "yours": yours, "right": right,
                         "why": q.get("explanation", "")})
    return correct, feedback, unanswered


def build_excel(df):
    out = pd.DataFrame({
        "Student Name": df["student_name"],
        "Class": df["class_name"],
        "Score (%)": df["score_percent"].round().astype(int) / 100,
    })
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        out.to_excel(writer, sheet_name="Student Grades", index=False)
        ws = writer.sheets["Student Grades"]
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="1B5E8C")
            cell.alignment = Alignment(horizontal="center")
        for row in ws.iter_rows(min_row=2, min_col=3, max_col=3):
            row[0].number_format = "0%"
            row[0].alignment = Alignment(horizontal="center")
        for col, width in zip("ABC", (32, 12, 12)):
            ws.column_dimensions[col].width = width
        ws.freeze_panes = "A2"
    return buf.getvalue()


# ---------------------------------------------------------------- screen 1
def welcome_page():
    st.title(f"🔬 {config.ASSESSMENT_TITLE}")
    st.subheader(f"Topic: {config.TOPIC}")
    st.write("Enter your details, then press **Start Assessment**.")
    with st.form("start_form"):
        name = st.text_input("Full Name *", max_chars=60)
        cls = st.selectbox("Class / Section *", config.CLASS_OPTIONS, index=None,
                           placeholder="Choose your class")
        start = st.form_submit_button("Start Assessment", type="primary")
    if start:
        name = clean(name)
        if not valid_name(name):
            st.error("Please enter your full name (letters only, 2–60 characters).")
        elif not cls:
            st.error("Please choose your class / section.")
        elif not config.ALLOW_RETAKES and database.already_submitted(name, cls):
            st.warning("An assessment has already been submitted for this name and class. "
                       "Please ask your teacher if you need help.")
        else:
            reset_student()
            ss.student = {"name": name, "class": cls}
            ss.submission_id = uuid.uuid4().hex
            ss.attempt = prepare_attempt()
            go("assessment")
    st.divider()
    if st.button("👩‍🏫 Teacher Login"):
        go("teacher")


# ---------------------------------------------------------------- screen 2
def show_question(n, q):
    st.markdown(f"**Question {n}.** {q['question']}")
    if q.get("image"):
        st.image(q["image"])
    key = f"q_{q['id']}"
    if q["type"] == "mcq":
        st.radio("answer", q["options"], index=None, key=key, label_visibility="collapsed")
    elif q["type"] == "tf":
        st.radio("answer", q["options"], index=None, key=key, horizontal=True,
                 label_visibility="collapsed")
    else:
        for i, p in enumerate(q["pairs"]):
            st.selectbox(p["left"], q["choices"], index=None, key=f"{key}_{i}",
                         placeholder="Choose...")
    st.write("")


def assessment_page():
    if "attempt" not in ss:
        go("welcome")
    student, questions = ss.student, ss.attempt
    st.title(f"🔬 {config.ASSESSMENT_TITLE}")
    st.caption(f"{student['name']} • Class {student['class']} • {len(questions)} questions")

    if "result" in ss:
        show_result(ss.result)
        return

    with st.form("assessment_form"):
        for n, q in enumerate(questions, 1):
            show_question(n, q)
        submit = st.form_submit_button("Submit Assessment", type="primary")

    if submit:
        correct, feedback, unanswered = grade(questions)
        if unanswered:
            st.warning(f"Please answer every question. Unanswered: {unanswered}.")
            return
        status = database.save_result(ss.submission_id, student["name"], student["class"],
                                      correct, len(questions))
        ss.result = {"correct": correct, "total": len(questions), "feedback": feedback,
                     "status": status}
        st.rerun()


def show_result(r):
    pct = round(100 * r["correct"] / r["total"], 1)
    passed = pct >= config.PASSING_PERCENT
    st.success("✅ Your assessment has been submitted and your grade was saved.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Score", f"{r['correct']} / {r['total']}")
    c2.metric("Percentage", f"{pct:g}%")
    c3.metric("Result", "Passed 🎉" if passed else "Keep practising 💪")
    wrong = [f for f in r["feedback"] if not f["ok"]]
    if not wrong:
        st.balloons()
        st.info("Perfect! You answered every question correctly.")
    else:
        st.subheader("Let's review your mistakes")
        for f in wrong:
            with st.container(border=True):
                st.markdown(f"**{f['q']}**")
                st.markdown(f"❌ Your answer: {f['yours']}")
                st.markdown(f"✅ Correct answer: {f['right']}")
                if f["why"]:
                    st.caption(f"💡 {f['why']}")
    if st.button("Finish"):
        reset_student()
        go("welcome")


# ---------------------------------------------------------------- screen 3
def teacher_page():
    st.title("👩‍🏫 Teacher Dashboard")
    if not ss.get("teacher_ok"):
        login_form()
        return

    df = database.get_all_results()
    top1, top2 = st.columns(2)
    top1.metric("Completed assessments", len(df))
    top2.metric("Class average", f"{df['score_percent'].mean():.1f}%" if len(df) else "–")

    classes = ["All classes"] + sorted(df["class_name"].unique().tolist())
    choice = st.selectbox("Filter by class", classes)
    view = df if choice == "All classes" else df[df["class_name"] == choice]

    table = pd.DataFrame({
        "Student Name": view["student_name"], "Class": view["class_name"],
        "Correct": view["correct"], "Total": view["total"],
        "Score (%)": view["score_percent"], "Submitted": view["submitted_at"],
    })
    st.dataframe(table, hide_index=True, use_container_width=True)

    if len(df):
        st.download_button("⬇️ Download ALL grades (Excel)", build_excel(df),
                           file_name=config.EXCEL_FILENAME,
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        if choice != "All classes":
            safe = re.sub(r"[^\w\-]", "_", choice)
            st.download_button(f"⬇️ Download class {choice} only (Excel)", build_excel(view),
                               file_name=config.EXCEL_FILENAME.replace(".xlsx", f"_{safe}.xlsx"),
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.info("No students have completed the assessment yet.")

    if st.button("Logout"):
        ss.teacher_ok = False
        go("welcome")


def login_form():
    user, pwd = config.get_teacher_credentials()
    if not user or not pwd:
        st.error("Teacher credentials are not configured. See README (Secrets).")
    ss.setdefault("failed_logins", 0)
    if ss.failed_logins >= 5:
        st.error("Too many failed attempts. Close this tab and try again later.")
    elif user and pwd:
        with st.form("login_form"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            ok = st.form_submit_button("Login", type="primary")
        if ok:
            if hmac.compare_digest(u.encode(), user.encode()) and \
               hmac.compare_digest(p.encode(), pwd.encode()):
                ss.teacher_ok, ss.failed_logins = True, 0
                st.rerun()
            else:
                ss.failed_logins += 1
                st.error("Incorrect username or password.")
    if st.button("← Back to student page"):
        go("welcome")


# ---------------------------------------------------------------- router
_db_error = database.check_connection()
if _db_error:
    st.error("The grade database could not be reached. Please tell your teacher.")
    st.code(_db_error)
    st.stop()
{"welcome": welcome_page, "assessment": assessment_page, "teacher": teacher_page}[ss.page]()
