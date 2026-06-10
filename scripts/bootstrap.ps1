# Dev bootstrap: create venv, install dependencies, run the test suite.
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --quiet -r requirements.txt
.\.venv\Scripts\python.exe -m pytest
