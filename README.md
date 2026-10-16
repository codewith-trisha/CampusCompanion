# CampusCompanion — Django + RAG Chatbot

A working college website with a chatbot that can answer two kinds of questions:

1. **Personal questions** ("How many credits do I have left?") — answered by querying
   the student's own database records directly. No AI guessing involved.
2. **General campus questions** ("What's the sports club fee?") — answered using
   **RAG (Retrieval-Augmented Generation)**: your question is matched against a set of
   campus documents, and the closest matches are handed to an AI model to summarize.

This README takes you from an empty folder to a live app running on AWS EC2.

---

## 1. Why this architecture (read this before you build)

A single AI model answering everything sounds simpler, but it creates two real problems
for a college chatbot:

- **Security**: if you let the AI freely query the database, a cleverly-worded question
  could leak another student's marks. So personal data is fetched by plain Django code
  that always filters by `request.user` — the AI never touches the database directly.
- **Accuracy**: AI models can "hallucinate" numbers. Credits and grades must come from
  the database, not from the model's guess. The AI's only job is to phrase the answer —
  never to invent the numbers in it.

So the system is split into two engines that both feed into one final answer:

```
Student question
      │
      ├── looks personal? ──► Django ORM query (request.user only) ──┐
      │                                                              │
      └── always ──► Vector search over campus documents (RAG) ──────┼──► Gemini writes
                                                                      │    the final answer
                                                                      ▼
                                                              Combined context
```

---

## 2. Tech stack and where each piece comes from

| Layer | Tool | Where to get it |
|---|---|---|
| Web framework | Django | `pip install django` |
| Database | SQLite | Built into Python, nothing to install |
| Embeddings (turns text into vectors) | `sentence-transformers` | `pip install sentence-transformers` (model downloads free from Hugging Face on first run) |
| Vector store (semantic search) | ChromaDB | `pip install chromadb` |
| LLM (writes the final answer) | Google Gemini API | Free key at **https://aistudio.google.com** → "Get API key"  |
| Static files in production | WhiteNoise | `pip install whitenoise` |
| Production server | Gunicorn | `pip install gunicorn` |

All of this is already listed in `requirements.txt`.

---

## 3. Project structure

```
class_companion/
├── manage.py
├── requirements.txt
├── .env             
├── class_companion/         # project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── core/                      # the app
│   ├── models.py              # StudentProfile, Course, Enrollment, CollegeInformation, ChatLog
│   ├── views.py                # dashboard + the dual-engine chat API
│   ├── rag_engine.py           # embeddings + vector search + Gemini call
│   ├── admin.py
│   ├── urls.py
│   └── management/commands/
│       ├── seed_data.py            # realistic demo data (see section 6)
│       └── build_vector_index.py   # embeds CollegeInformation into ChromaDB
└── templates/
    ├── base.html
    └── core/
        ├── login.html
        └── dashboard.html          # student dashboard + chat widget
```

---

## 4. Run it locally (start to finish)

```bash
# 1. Get the project folder and enter it
cd class_companion

# 2. Create an isolated Python environment (keeps this project's packages separate)
python3 -m venv venv
source venv/bin/activate            # on Windows: venv\Scripts\activate

# 3. Install everything
pip install -r requirements.txt

# 4. Configure secrets
cp .env.example .env
# open .env and paste your free Gemini API key from https://aistudio.google.com

# 5. Create the database tables
python manage.py migrate

# 6. Load realistic demo data (students, courses, campus info — see section 6)
python manage.py seed_data

# 7. Embed the campus documents into the vector store (only needed once,
#    or whenever you add/change CollegeInformation entries)
python manage.py build_vector_index

# 8. Create an admin account for yourself (optional, for /admin/)
python manage.py createsuperuser

# 9. Run it
python manage.py runserver
```

Open **http://127.0.0.1:8000/login/** and sign in with one of the seeded demo accounts
(printed at the end of step 6 — e.g. `rahul` / `campus1234`).

---

## 5. What the chatbot can actually answer (every use case covered)

**Personal (from the database, always accurate):**
- "How many credits have I earned / have left?"
- "What courses have I completed?" (with grades)
- "What courses am I currently taking?"
- "Do I have any backlogs?"
- "What electives should I take to finish my remaining credits?" (suggestion engine)

**General campus info (from RAG documents, seeded across every category you mentioned):**
- Sports club fee, cultural club fee, hostel fee, exam re-evaluation fee, bus fee
- Library timings, canteen timings, admin office timings, bus pickup/drop timings
- Credits for joining NCC, NSS, sports teams; coding club benefits
- Hall ticket download process, exam timetable release, backlog/reappear rules,
  minimum attendance for exam eligibility
- Semester break schedule, festival/national holidays
- Hostel curfew rules
- How the credit system works, minimum CGPA requirement
- Grievance cell contact, counseling services
- Placement eligibility criteria

You can add more anytime through `/admin/` → **Core → College informations** — just
remember to re-run `python manage.py build_vector_index` afterward so new entries
become searchable.

---

## 6. Demo data included (`seed_data` command)

Three students representing different real situations, so your client demo shows
the system handling variety, not just one happy path:

| Username | Password | Situation |
|---|---|---|
| `rahul` | `campus1234` | Final semester (46 credits earned so far), zero backlogs, close to graduation |
| `priya` | `campus1234` | Mid-course, one active backlog |
| `arjun` | `campus1234` | First semester, just started |

20 courses across 6 semesters (core + electives), and 25 `CollegeInformation` entries
spanning fees, timings, clubs, exams, holidays, hostel rules, academic policy,
grievances, and placements.

---

## 7. Deploying to AWS EC2 (from zero to live URL)

### Step 1 — Launch the EC2 instance
1. AWS Console → **EC2** → **Launch instance**.
2. Name it (e.g. `campus-assistant`).
3. AMI: **Ubuntu Server 24.04 LTS**.
4. Instance type: **t2.micro** (free-tier eligible) is enough for a demo.
5. Key pair: create a new one, download the `.pem` file — you need it to SSH in.
6. Network settings → Edit → add these inbound rules:
   - SSH (22) — Source: My IP
   - HTTP (80) — Source: Anywhere
   - HTTPS (443) — Source: Anywhere (only if you'll add a domain + SSL later)
7. Launch.

### Step 2 — Connect to the instance
```bash
chmod 400 your-key.pem
ssh -i your-key.pem ubuntu@<your-ec2-public-ip>
```

### Step 3 — Install system dependencies
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv nginx git
```

### Step 4 — Get your project onto the server
```bash
git clone <your-repo-url> class_companion
cd class_companion
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
(No GitHub repo yet? Just `scp -i your-key.pem -r class_companion ubuntu@<ip>:~/` from
your own machine instead of `git clone`.)

### Step 5 — Configure production settings
```bash
cp .env.example .env
nano .env
```
Set:
```
DJANGO_SECRET_KEY=<generate a long random string>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=<your-ec2-public-ip>,yourdomain.com
GEMINI_API_KEY=<your real key>
```

### Step 6 — Set up the database and vector index on the server
```bash
python manage.py migrate
python manage.py seed_data
python manage.py build_vector_index
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

### Step 7 — Run Gunicorn as a permanent background service
Create `/etc/systemd/system/class_companion.service`:
```ini
[Unit]
Description=Gunicorn server for CampusCompanion
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/class_companion
ExecStart=/home/ubuntu/class_companion/venv/bin/gunicorn \
    --workers 3 \
    --bind unix:/home/ubuntu/class_companion/class_companion.sock \
    class_companion.wsgi:application

[Install]
WantedBy=multi-user.target
```
Start it:
```bash
sudo systemctl start class_companion
sudo systemctl enable class_companion
sudo systemctl status class_companion   # should say "active (running)"
```

### Step 8 — Point Nginx at Gunicorn
Create `/etc/nginx/sites-available/class_companion`:
```nginx
server {
    listen 80;
    server_name <your-ec2-public-ip> yourdomain.com;

    location /static/ {
        alias /home/ubuntu/class_companion/staticfiles/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/ubuntu/class_companion/class_companion.sock;
    }
}
```
Enable it:
```bash
sudo ln -s /etc/nginx/sites-available/class_companion /etc/nginx/sites-enabled
sudo nginx -t          # tests the config for errors
sudo systemctl restart nginx
```

### Step 9 — Visit your live site
Open `http://<your-ec2-public-ip>/login/` in a browser.

### After any future code change
```bash
git pull                                  # or re-upload changed files
source venv/bin/activate
pip install -r requirements.txt           # only if requirements changed
python manage.py migrate                  # only if models changed
python manage.py collectstatic --noinput
sudo systemctl restart class_companion
```

---

## 8. Costs to be aware of

- **AWS t2.micro**: free for 12 months under the AWS Free Tier, then a few dollars/month.
- **Gemini API**: free tier is generous for a demo (no card needed), but double-check
  current limits at `ai.google.dev` before a live client demo — free-tier quotas change
  over time.
- **Domain name**: optional, ~$10-15/year if you want one instead of using the raw IP.

---

## 9. Common issues

| Problem | Fix |
|---|---|
| `GEMINI_API_KEY is not set` error in chat | Check `.env` has the real key and you restarted the server/service after editing it |
| Chat says it can't find campus info | Run `python manage.py build_vector_index` — it only indexes on demand, not automatically |
| 502 Bad Gateway on EC2 | Gunicorn isn't running — check `sudo systemctl status class_companion` and `journalctl -u class_companion` |
| CSS/Tailwind not loading | Confirm you have internet access on the server (it loads from a CDN) or switch to a locally-built Tailwind file for offline use |
