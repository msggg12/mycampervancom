Campervan Rentals (Static + Flask)

Run locally (Windows PowerShell):

1) Create venv and install deps
```
cd simple-site
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2) Configure vans in `config.json` (replace the Airbnb iCal URL with your feed)
- Multiple vans are supported; copy the object and change `slug`, `name`, etc.

3) Start the server
```
python app.py
```
Then open http://localhost:5000

Endpoints
- GET /api/vans → list of vans
- GET /api/availability?slug=van-1 → busy ranges from Airbnb iCal

Notes
- Images are loaded directly via their URLs.
- The calendar marks days as busy/free based on the iCal feed.

# mycampervans.com
# mycampervancom
# mycampervancom
