# Grade 7 Science Assessment – Separation Techniques

## Files
| File | Purpose |
|---|---|
| `app.py` | The website (3 screens) |
| `config.py` | **Settings**: title, topic, passing grade, classes, number of questions |
| `questions.json` | **Questions & answers** (15 samples) |
| `database.py` | Saves grades (SQLite locally, PostgreSQL online) |
| `.streamlit/secrets.toml` | Teacher username/password (+ optional database URL). **Never upload to GitHub** |

## Run locally
1. Install Python 3.10+ from python.org.
2. Open a terminal in this folder and run:
   ```
   pip install -r requirements.txt
   streamlit run app.py
   ```
3. Open http://localhost:8501. Grades are saved in `grades.db`.
4. Teacher: click **Teacher Login** and use the credentials in `.streamlit/secrets.toml`.

## Editing questions (`questions.json`)
Copy an existing block and change it. Types:
- `"mcq"`: `question`, `options` (list), `answer` (must match one option exactly), `explanation`
- `"tf"`: `question`, `answer` (`"True"` or `"False"`), `explanation`
- `"matching"`: `question`, `pairs` (list of `{"left": ..., "right": ...}`), `explanation`
- Optional image on any question: `"image": "https://.../picture.png"`
Every question needs a unique `"id"`. Keep commas between blocks. Set `NUM_QUESTIONS` in `config.py` to use fewer questions per student.

## Deploy on Streamlit Community Cloud (with permanent grades)
Streamlit Cloud's disk is erased on restart, so use a free hosted PostgreSQL database.

1. **Create the database** (free): sign up at https://neon.tech (or https://supabase.com), create a project, and copy the connection string, e.g. `postgresql://user:pass@host/dbname?sslmode=require`.
2. **Upload to GitHub**: create a *private* repository with all files **except** `.streamlit/secrets.toml` and `grades.db` (the `.gitignore` already excludes them).
3. Go to https://share.streamlit.io → **New app** → choose the repo, branch, and `app.py`.
4. **Advanced settings → Secrets**: paste
   ```toml
   [teacher]
   username = "cyoussef"
   password = "kouki20"

   [database]
   url = "postgresql://user:pass@host/dbname?sslmode=require"
   ```
5. Deploy. The grade table is created automatically on first run. Share the app link with students.

## Security notes
- Students only ever see their own result. The dashboard and Excel export render only after teacher login (5 failed attempts lock the session); the Excel file is generated in memory, never stored at a public URL.
- Change the teacher password in Secrets whenever you like. Since it was shared in a chat, a stronger password is recommended.
- A downloaded Excel file is not password-protected by this app.
- Duplicate protection: each attempt has a unique ID (a refresh cannot save it twice), and with `ALLOW_RETAKES = False` the same name + class cannot submit again.
