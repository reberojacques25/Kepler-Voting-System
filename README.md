<<<<<<< HEAD
# Kepler Student Guild Voting System (Django)

A role-based online voting platform for Kepler College Kigali (Rwanda) with:
- Student sign-up using **Email + Student ID** (both unique)
- **Email verification** before access
- Admin can **block/unblock** students from voting
- Elections, positions, candidates, campaigns
- Voting (one vote per student per position per election)
- Results + live score (optional) + admin reports
- Clean Bootstrap 5 UI

## 1) Setup (Ubuntu/Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open: http://127.0.0.1:8000

## 2) Email verification (development)

By default, the app uses Django's console email backend, which prints emails in the terminal.

To send real emails, update `kepler_voting/settings.py` (EMAIL_* settings).

## 3) Create an election (Admin)

Go to `/admin/` and create:
1. Election
2. Positions (linked to election)
3. Candidates (linked to position + election) and set status to **Approved**

Then login as a student and vote.

## 4) Notes
- Students can view **aggregated results only**.
- Raw vote records are admin-only.
- Admin can enable/disable live results per election.


## Troubleshooting

### "no such table: accounts_user"
If you ran `migrate` before configuring the custom user model, delete the old database and migrate again:

```bash
rm -f db.sqlite3
python manage.py migrate
```
=======
# Kepler-Voting-System
>>>>>>> e0c7ff561b2318d306ebecee72eea627c0b61c38
