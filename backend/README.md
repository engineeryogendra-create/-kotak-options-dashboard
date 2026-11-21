# Neo Options Assistant Backend

Market-data-only backend. It does not place, modify, or cancel orders.

## Deploy on Render
Create a Web Service from this repository. Set Root Directory to `backend`, Build Command `pip install -r requirements.txt`, Start Command `uvicorn main:app --host 0.0.0.0 --port $PORT`.

Environment variables (Render only):
- `APP_ACCESS_KEY`: a long random secret used by the dashboard.
- `KOTAK_CONSUMER_KEY`: your Kotak Neo Trade API consumer key. Never commit this value or enter it in the dashboard.

The `/api/market` endpoint requires `X-App-Key`. It supports NIFTY, BANKNIFTY, and SENSEX.

Important: The current scaffold uses the ATM strike as a spot proxy and flags `spot_is_atm_proxy=true`; it is not yet a true index spot quote. Signals are intentionally WAIT-only until we validate the data and analysis rules.
