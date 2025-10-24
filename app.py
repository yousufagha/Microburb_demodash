# app.py
# Microburbs interview - API only interface
# Flask + vanilla JS + Chart.js (one file)
# Endpoints used:
#   /suburb/market, /property/market
# Auth styles tried in order: access_token query, x-api-key, Bearer
# No demo data. If the API returns nothing, the cards stay blank and the debug strip explains why.

import os, json
from flask import Flask, request, Response
import requests

app = Flask(__name__)

API_BASES = [
    "https://www.microburbs.com.au/report_generator/api",
    "https://www.microburbs.com.au/report_generator/api/sandbox",
]
API_KEY = os.environ.get("MICROBURBS_API_KEY", "")

# --------------- HTTP helpers ---------------

def _call(path: str, params: dict, base: str, style: str):
    url = f"{base}{path}"
    headers = {"Accept": "application/json"}
    q = dict(params)
    if style == "query":
        if API_KEY:
            q["access_token"] = API_KEY
    elif style == "xapikey":
        if API_KEY:
            headers["x-api-key"] = API_KEY
    elif style == "bearer":
        if API_KEY:
            headers["Authorization"] = f"Bearer {API_KEY}"
    r = requests.get(url, headers=headers, params=q, timeout=15)
    return r, url, q, headers

def _strict_json(text: str):
    # Convert NaN or Infinity to strict JSON
    obj = json.loads(text)
    return json.loads(json.dumps(obj, allow_nan=False))

def _first_json(path: str, variants: list[dict]):
    # Try access_token in query first, then headers, across both bases
    attempts = [(b, s) for b in API_BASES for s in ("query", "xapikey", "bearer")]
    last = None
    for pv in variants:
        for base, style in attempts:
            r, url, q, h = _call(path, pv, base, style)
            last = {"status": r.status_code, "url": url, "style": style,
                    "params": q, "content_type": r.headers.get("Content-Type","")}
            try:
                if r.status_code < 300 and "application/json" in last["content_type"].lower():
                    return {"ok": True, "data": _strict_json(r.text), "trace": last}
            except Exception:
                continue
    return {"ok": False, "data": {}, "trace": last or {}}

# --------------- UI ---------------

@app.get("/")
def index():
    html = r"""
<!doctype html><html><head><meta charset="utf-8"/>
<title>Microburbs Mini Dashboard - API only</title>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<style>
:root{--ink:#0f172a;--muted:#334155;--border:#e2e8f0;--panel:#f6f8fb;--brand:#0a2540}
*{box-sizing:border-box} body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial;margin:0;color:var(--ink)}
header{padding:14px 18px;background:var(--brand);color:#fff}
.controls{display:flex;gap:8px;padding:12px 18px;background:var(--panel);align-items:center;flex-wrap:wrap}
.controls input,.controls select{padding:8px;border:1px solid var(--border);border-radius:6px}
.controls button{padding:8px 12px;border:1px solid var(--brand);border-radius:6px;background:var(--brand);color:#fff;cursor:pointer}
.container{padding:16px 18px}
.grid{display:grid;grid-template-columns:1fr;gap:16px}
@media(min-width:1000px){.grid{grid-template-columns:1fr 1fr}}
.card{background:#fff;border:1px solid var(--border);border-radius:10px;padding:12px}
.kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.kpi{background:#f8fafc;border:1px solid var(--border);border-radius:8px;padding:12px}
.kpi .t{font-size:12px;color:var(--muted)} .kpi .v{font-size:22px;font-weight:700;margin-top:2px}
.chartbox{height:260px}
footer{padding:12px 18px;border-top:1px solid var(--border);color:#475569}
small.m{color:#64748b}
.debug{font:12px/1.3 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;white-space:nowrap;overflow-x:auto}
</style></head><body>
<header>
  <h2 style="margin:0;">Microburbs Mini Dashboard</h2>
  <div>Find your suburb. Find your property.</div>
</header>

<section class="controls">
  <input id="suburb" placeholder="Belmont North" />
  <select id="state">
    <option>NSW</option><option>VIC</option><option>QLD</option><option>SA</option>
    <option>WA</option><option>TAS</option><option>ACT</option><option>NT</option>
  </select>
  <button id="go">Fetch suburb</button>
  <input id="prop" placeholder="Property id (GNAF) e.g. GANSW704074813" style="margin-left:16px;width:300px"/>
  <button id="goProp">Fetch property</button>
  <div id="msg" style="margin-left:auto;color:#334155;"></div>
</section>

<section class="container">
  <div class="card">
    <h3 style="margin:6px 0 10px 0;">Suburb KPIs</h3>
    <div class="kpis">
      <div class="kpi"><div class="t">Median Price</div><div class="v" id="s-price">–</div></div>
      <div class="kpi"><div class="t">Rent Yield</div><div class="v" id="s-yield">–</div></div>
      <div class="kpi"><div class="t">5-year Growth</div><div class="v" id="s-growth">–</div></div>
    </div>
    <div class="grid" style="margin-top:12px">
      <div class="card chartbox"><canvas id="s-chart-price"></canvas></div>
      <div class="card chartbox"><canvas id="s-chart-yield"></canvas></div>
    </div>
    <div class="debug" id="s-trace"></div>
  </div>

  <div class="card" style="margin-top:16px">
    <h3 style="margin:6px 0 10px 0;">Property KPIs</h3>
    <div class="kpis">
      <div class="kpi"><div class="t">Median Price</div><div class="v" id="p-price">–</div></div>
      <div class="kpi"><div class="t">Rent Yield</div><div class="v" id="p-yield">–</div></div>
      <div class="kpi"><div class="t">5-year Growth</div><div class="v" id="p-growth">–</div></div>
    </div>
    <div class="grid" style="margin-top:12px">
      <div class="card chartbox"><canvas id="p-chart-price"></canvas></div>
      <div class="card chartbox"><canvas id="p-chart-yield"></canvas></div>
    </div>
    <div class="debug" id="p-trace"></div>
  </div>
</section>

<footer><small>Endpoints are from Microburbs’ API and sandbox. Token can be passed as access_token. </small></footer>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
const $=s=>document.querySelector(s);let sP,sY,pP,pY;
const aud=x=>x==null?"–":x.toLocaleString("en-AU",{style:"currency",currency:"AUD",maximumFractionDigits:0});
const pct=x=>x==null?"–":(Number(x).toFixed(1)+"%");
function draw(sel, labels, values, ref){
  const ctx=$(sel).getContext("2d"); if(window[ref]) window[ref].destroy();
  window[ref]=new Chart(ctx,{type:"line",data:{labels,datasets:[{label:"",data:values,tension:0.2}]},
    options:{responsive:true,maintainAspectRatio:false,scales:{x:{ticks:{maxTicksLimit:8}},y:{beginAtZero:false}}}});
}
async function j(url){
  const r=await fetch(url); const ct=(r.headers.get("content-type")||"").toLowerCase();
  const t=await r.text(); if(!r.ok) throw new Error(r.status+" "+t.slice(0,200));
  if(ct.includes("application/json")) return JSON.parse(t);
  throw new Error("Expected JSON, got "+(ct||"unknown")+": "+t.slice(0,160));
}
const note=m=>{ $("#msg").textContent=m; setTimeout(()=>$("#msg").textContent="",4000); };

function pick(obj, paths){ for(const p of paths){ try{ let v=p.split(".").reduce((o,k)=>o?.[k],obj); if(v!=null) return v; }catch{} } return null; }
function toS(arr){ return (arr||[]).map(d=>({t:(d.date||d.period||d.t||d.Time), v:(d.value ?? d.price ?? d.yield ?? d.v ?? null)})).filter(d=>d.t && d.v!=null); }
function series(obj){ const price=pick(obj,["timeseries.price","price_timeseries","series.price","prices"])||[]; const yld=pick(obj,["timeseries.yield","yield_timeseries","series.yield","yields"])||[]; return {price:toS(price), yld:toS(yld)}; }
function last(a){ return a.length?a[a.length-1]:null; } function back5y(a){ return a.length? a[Math.max(0,a.length-61)] : null; }
function derive(data){
  const s = series(data); const sm = pick(data,["summary","current","kpis","metrics"])||{};
  const median = pick(sm,["median_price","medianPrice","price_median"]) ?? last(s.price)?.v ?? null;
  const ry     = pick(sm,["rental_yield","rentalYield","yield"]) ?? last(s.yld)?.v ?? null;
  let g5       = pick(sm,["growth_5y","growth5Y","five_year_growth"]);
  if(g5==null && s.price.length){ const e=last(s.price), b=back5y(s.price); if(b && b.v>0 && e.v>0) g5=(Math.pow(e.v/b.v,1/5)-1)*100; }
  return {median, ry, g5, s};
}
function showSuburb(payload){
  const data = payload.__data, trace = payload.__trace;
  const k=derive(data||{});
  $("#s-price").textContent= k.median!=null?aud(k.median):"–";
  $("#s-yield").textContent= k.ry!=null?pct(k.ry):"–";
  $("#s-growth").textContent= k.g5!=null?pct(k.g5):"–";
  draw("#s-chart-price", k.s.price.map(d=>d.t), k.s.price.map(d=>d.v), "sP");
  draw("#s-chart-yield", k.s.yld.map(d=>d.t),   k.s.yld.map(d=>d.v), "sY");
  $("#s-trace").textContent = trace ? `suburb: ${trace.status} ${trace.content_type}  ->  ${trace.url}  params=${JSON.stringify(trace.params)}` : "";
}
function showProperty(payload){
  const data = payload.__data, trace = payload.__trace;
  const k=derive(data||{});
  $("#p-price").textContent= k.median!=null?aud(k.median):"–";
  $("#p-yield").textContent= k.ry!=null?pct(k.ry):"–";
  $("#p-growth").textContent= k.g5!=null?pct(k.g5):"–";
  draw("#p-chart-price", k.s.price.map(d=>d.t), k.s.price.map(d=>d.v), "pP");
  draw("#p-chart-yield", k.s.yld.map(d=>d.t),   k.s.yld.map(d=>d.v), "pY");
  $("#p-trace").textContent = trace ? `property: ${trace.status} ${trace.content_type}  ->  ${trace.url}  params=${JSON.stringify(trace.params)}` : "";
}

$("#go").onclick=async()=>{
  const suburb=($("#suburb").value||"Belmont North").trim(), state=$("#state").value;
  note("Loading suburb…");
  try{
    const payload=await j(`/api/suburb/market?suburb=${encodeURIComponent(suburb)}&state=${encodeURIComponent(state)}`);
    showSuburb(payload); note("Suburb loaded");
  }catch(e){ note(e.message); }
};
$("#goProp").onclick=async()=>{
  const pid=($("#prop").value||"").trim();
  if(!pid){ note("Enter a property id"); return; }
  note("Loading property…");
  try{
    const payload=await j(`/api/property/market?id=${encodeURIComponent(pid)}`);
    showProperty(payload); note("Property loaded");
  }catch(e){ note(e.message); }
};
</script></body></html>
"""
    return Response(html, content_type="text/html")

# --------------- API routes ---------------

@app.get("/api/suburb/market")
def suburb_market():
    suburb = request.args.get("suburb","").strip()
    state  = request.args.get("state","").strip()
    if not suburb:
        return Response(json.dumps({"error": "suburb is required"}), status=400, content_type="application/json")
    variants = [{"suburb": suburb}]
    if state:
        variants += [{"suburb": suburb, "state": state},
                     {"suburb": suburb, "state_code": state}]
    result = _first_json("/suburb/market", variants)
    out = result["data"] if result["ok"] else {}
    return Response(json.dumps({"__data": out, "__trace": result.get("trace")}), content_type="application/json")

@app.get("/api/property/market")
def property_market():
    pid = (request.args.get("id") or "").strip()
    if not pid:
        return Response(json.dumps({"error": "id is required"}), status=400, content_type="application/json")
    result = _first_json("/property/market", [{"id": pid}])
    out = result["data"] if result["ok"] else {}
    return Response(json.dumps({"__data": out, "__trace": result.get("trace")}), content_type="application/json")

if __name__ == "__main__":
    port = int(os.environ.get("PORT","5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
