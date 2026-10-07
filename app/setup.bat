@echo off
REM setup.bat : Windows version of setup.sh (UNTESTED - see README). Run from the app folder.
py -m venv .venv
call .venv\Scripts\activate
pip install -r requirements.txt
if not exist .env copy .env.example .env
python seed_db.py
echo Setup done. Next: pytest -q  and  python run_queue.py
