import os
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

APP_KEY=os.getenv("APP_ACCESS_KEY","")
CONSUMER_KEY=os.getenv("KOTAK_CONSUMER_KEY","")

app=FastAPI(title="Neo Options Assistant Backend",version="1.0.0")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["GET"],allow_headers=["*"])

@app.get("/")
def health():
    return {"ok":True,"service":"neo-options-backend","mode":"MARKET_DATA_ONLY"}

@app.get("/health")
def health_check():
    return {"ok":True}

def auth(x_app_key: str | None):
    if not APP_KEY or not x_app_key or x_app_key != APP_KEY:
        raise HTTPException(status_code=401,detail="Invalid app access key")

@app.get("/api/market")
def market(underlying: str="NIFTY", x_app_key: str | None=Header(default=None)):
    auth(x_app_key)
    if not CONSUMER_KEY:
        raise HTTPException(status_code=503,detail="Backend Kotak consumer key is not configured")
    symbol=underlying.upper()
    mapping={"NIFTY":("nse_fo","NIFTY"),"BANKNIFTY":("nse_fo","BANKNIFTY"),"SENSEX":("bse_fo","SENSEX")}
    if symbol not in mapping:
        raise HTTPException(status_code=400,detail="Unsupported underlying")
    exchange,neo_symbol=mapping[symbol]
    try:
        from neo_api_client import NeoAPI
        client=NeoAPI(consumer_key=CONSUMER_KEY,environment="prod")
        response=client.option_chain(exchange=exchange,underlying=neo_symbol,instrument_type="option",count=40)
    except Exception as e:
        raise HTTPException(status_code=502,detail=f"Kotak API error: {type(e).__name__}: {str(e)[:180]}")
    data=response.get("data",response) if isinstance(response,dict) else {}
    calls=data.get("call",[]) or []
    puts=data.get("put",[]) or []
    by_strike={}
    for item in calls:
        inst=item.get("instrument",{}); q=item.get("quote",{}); oi=item.get("openInterest",{})
        strike=float(inst.get("strikePrice",0) or 0)
        row=by_strike.setdefault(strike,{"strike":strike,"ce":{},"pe":{}})
        row["ce"]={"oi":oi.get("current"),"oi_change":oi.get("change"),"ltp":q.get("ltp"),"symbol":inst.get("symbol")}
    for item in puts:
        inst=item.get("instrument",{}); q=item.get("quote",{}); oi=item.get("openInterest",{})
        strike=float(inst.get("strikePrice",0) or 0)
        row=by_strike.setdefault(strike,{"strike":strike,"ce":{},"pe":{}})
        row["pe"]={"oi":oi.get("current"),"oi_change":oi.get("change"),"ltp":q.get("ltp"),"symbol":inst.get("symbol")}
    rows=sorted(by_strike.values(),key=lambda r:r["strike"])
    total_ce=sum(float(r.get("ce",{}).get("oi") or 0) for r in rows)
    total_pe=sum(float(r.get("pe",{}).get("oi") or 0) for r in rows)
    pcr=round(total_pe/total_ce,2) if total_ce else None
    support=max(rows,key=lambda r:float(r.get("pe",{}).get("oi") or 0))["strike"] if rows else None
    resistance=max(rows,key=lambda r:float(r.get("ce",{}).get("oi") or 0))["strike"] if rows else None
    atm=rows[len(rows)//2]["strike"] if rows else None
    atm_row=min(rows,key=lambda r:abs(r["strike"]-(atm or 0))) if rows else {}
    premium=float(atm_row.get("ce",{}).get("ltp") or 0)
    analysis={"pcr":pcr,"support":support,"resistance":resistance,"signal":"WAIT","score":5,
      "reason":"Market-data snapshot only; signal rules are not validated.","atm_strike":atm,
      "selected_premium":premium or None,"stop_loss":round(premium*.8,2) if premium else None,
      "target":round(premium*1.3,2) if premium else None}
    return {"mode":"LIVE_API","underlying":symbol,"spot":atm,"change":0,"change_pct":0,
      "spot_is_atm_proxy":True,"expiry":data.get("common_data",{}).get("expiryDt"),
      "lot_size":data.get("common_data",{}).get("mktLot"),"option_chain":rows,
      "analysis":analysis,"as_of":None}
