"""ReelForge Studio — web UI.

`reelforge serve` → open http://localhost:8000

Tabs: Studio (prompt → video), Trends (what's hot), Library (preview,
publish, stats). Generation runs in background threads; the UI polls.
"""
from __future__ import annotations

import threading
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from . import pipeline
from . import trends as trends_mod
from .config import PROJECTS_DIR, Config
from .publish import ADAPTERS, publish as publish_adapter

app = FastAPI(title="ReelForge Studio")

_jobs: dict[str, dict] = {}


class GenRequest(BaseModel):
    topic: str
    duration: int = 30


class TrendRequest(BaseModel):
    niche: str = "general"
    limit: int = 10


class PublishRequest(BaseModel):
    slug: str
    platforms: list[str]
    dry_run: bool = True


def _run_generation(job_id: str, topic: str, duration: int):
    _jobs[job_id] = {"status": "running", "topic": topic, "started": time.time()}
    try:
        cfg = Config()
        workdir = pipeline.create_project(topic, duration, cfg)
        _jobs[job_id] = {"status": "done", "slug": workdir.name,
                         "topic": topic,
                         "video_url": f"/api/video/{workdir.name}"}
    except Exception as e:  # noqa: BLE001
        _jobs[job_id] = {"status": "failed", "topic": topic, "error": str(e)}


@app.post("/api/generate")
def generate(req: GenRequest):
    job_id = uuid.uuid4().hex[:8]
    t = threading.Thread(target=_run_generation,
                         args=(job_id, req.topic, req.duration), daemon=True)
    t.start()
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(404, "unknown job")
    return _jobs[job_id]


@app.post("/api/trends")
def trends(req: TrendRequest):
    ts = trends_mod.harvest(req.niche, req.limit)
    return [{"title": t.title, "source": t.source, "score": t.score,
             "url": t.url} for t in ts]


@app.get("/api/projects")
def projects():
    return pipeline.list_projects()


@app.get("/api/video/{slug}")
def video(slug: str):
    f = Path(PROJECTS_DIR) / slug / "final.mp4"
    if not f.exists():
        raise HTTPException(404, "no video yet")
    return FileResponse(f, media_type="video/mp4")


@app.post("/api/publish")
def publish(req: PublishRequest):
    from .pipeline import load_plan
    plan = load_plan(req.slug)
    video_path = Path(PROJECTS_DIR) / req.slug / "final.mp4"
    results = []
    for p in req.platforms:
        if p not in ADAPTERS:
            results.append({"platform": p, "error": "unknown platform"})
            continue
        try:
            r = publish_adapter(p, video_path, plan.title or req.slug,
                                plan.description or "",
                                plan.hashtags or [], dry_run=req.dry_run)
            results.append(r)
        except Exception as e:  # noqa: BLE001
            results.append({"platform": p, "error": str(e)})
    return results


@app.get("/api/stats")
def stats():
    projects = pipeline.list_projects()
    videos = [p for p in projects if p["has_video"]]
    total_bytes = sum(p.get("size", 0) for p in videos)
    return {
        "projects": len(projects),
        "videos": len(videos),
        "total_mb": round(total_bytes / 1e6, 1),
        "platforms": list(ADAPTERS),
    }


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML_PAGE


HTML_PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ReelForge Studio ⚒️</title>
<style>
:root{--bg:#0b0e14;--panel:#131722;--line:#232a3a;--txt:#e8ecf4;--dim:#8b94a7;
--acc:#f97316;--grn:#22c55e;--red:#ef4444}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);
font-family:system-ui,-apple-system,sans-serif}
header{padding:18px 28px;border-bottom:1px solid var(--line);display:flex;
align-items:center;gap:12px}
header h1{margin:0;font-size:20px}header h1 span{color:var(--acc)}
nav{display:flex;gap:6px;padding:14px 28px 0}
nav button{background:none;border:none;color:var(--dim);font-size:15px;
padding:10px 16px;cursor:pointer;border-bottom:2px solid transparent}
nav button.on{color:var(--txt);border-bottom-color:var(--acc)}
main{padding:24px 28px;max-width:1100px}
.tab{display:none}.tab.on{display:block}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:12px;
padding:20px;margin-bottom:18px}
input,select,textarea{background:#0b0e14;border:1px solid var(--line);
color:var(--txt);border-radius:8px;padding:10px 12px;font-size:14px;width:100%}
button.go{background:var(--acc);border:none;color:#000;font-weight:700;
border-radius:8px;padding:11px 22px;font-size:15px;cursor:pointer}
button.go:disabled{opacity:.5}
.row{display:flex;gap:12px;align-items:end}.row>*{flex:1}
.trend{padding:12px;border-bottom:1px solid var(--line);cursor:pointer}
.trend:hover{background:#1a2130}.trend small{color:var(--dim)}
video{width:270px;border-radius:12px;border:1px solid var(--line)}
.proj{display:flex;gap:16px;align-items:center;padding:14px;
border-bottom:1px solid var(--line)}
.badge{font-size:12px;padding:3px 10px;border-radius:20px;background:#1a2130;
color:var(--dim)}.badge.ok{background:#052e16;color:var(--grn)}
.log{font-family:monospace;font-size:13px;color:var(--dim);white-space:pre-wrap}
.stat{display:inline-block;margin-right:28px}.stat b{font-size:26px;
display:block}.stat span{color:var(--dim);font-size:13px}
</style></head><body>
<header><h1>⚒️ Reel<span>Forge</span> Studio</h1></header>
<nav>
<button class="on" onclick="tab('studio')">🎬 Studio</button>
<button onclick="tab('trends')">📈 Trends</button>
<button onclick="tab('library')">📚 Library</button>
<button onclick="tab('stats')">📊 Stats</button>
</nav><main>
<div id="t-studio" class="tab on">
 <div class="panel"><h3>New video</h3>
  <div class="row">
   <div><label>Topic</label><input id="topic" placeholder="hyderabadi biryani"></div>
   <div style="max-width:140px"><label>Seconds</label>
    <input id="dur" type="number" value="30" min="5" max="180"></div>
   <div style="max-width:170px"><label>&nbsp;</label><br>
    <button class="go" id="genbtn" onclick="generate()">Forge ⚒️</button></div>
  </div>
  <p class="log" id="genlog"></p>
 </div>
</div>
<div id="t-trends" class="tab">
 <div class="panel"><h3>What's hot</h3>
  <div class="row"><div><select id="niche">
   <option>food</option><option>ai</option><option>tech</option>
   <option>fitness</option><option>finance</option><option>travel</option>
   <option>motivation</option><option>health</option><option>general</option>
  </select></div>
  <div style="max-width:170px"><button class="go" onclick="loadTrends()">Refresh</button></div></div>
  <div id="trendlist" style="margin-top:12px"></div>
 </div>
</div>
<div id="t-library" class="tab"><div class="panel"><h3>Projects</h3>
 <div id="projlist"></div></div></div>
<div id="t-stats" class="tab"><div class="panel"><h3>Studio stats</h3>
 <div id="statlist"></div></div></div>
</main>
<script>
function tab(n){document.querySelectorAll('.tab').forEach(e=>e.classList.remove('on'));
document.getElementById('t-'+n).classList.add('on');
document.querySelectorAll('nav button').forEach(e=>e.classList.remove('on'));
event.target.classList.add('on');
if(n==='library')loadProjects();if(n==='stats')loadStats();if(n==='trends')loadTrends();}
async function generate(){
 const topic=document.getElementById('topic').value.trim();
 if(!topic){alert('Enter a topic');return;}
 const btn=document.getElementById('genbtn');btn.disabled=true;
 const log=document.getElementById('genlog');log.textContent='Forging… (script → voice → verified footage → captions → render)';
 const r=await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({topic,duration:+document.getElementById('dur').value})});
 const {job_id}=await r.json();
 const iv=setInterval(async()=>{
  const s=await (await fetch('/api/jobs/'+job_id)).json();
  if(s.status==='done'){clearInterval(iv);btn.disabled=false;
   log.innerHTML='✅ Done: <b>'+s.slug+'</b> — see Library to preview & publish.';
   loadProjects();}
  else if(s.status==='failed'){clearInterval(iv);btn.disabled=false;
   log.textContent='❌ '+s.error;}
 },3000);}
async function loadTrends(){
 const niche=document.getElementById('niche').value;
 const r=await fetch('/api/trends',{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({niche,limit:12})});
 const ts=await r.json();
 document.getElementById('trendlist').innerHTML=ts.map((t,i)=>
  `<div class="trend" onclick="useTrend(${JSON.stringify(t.title).replace(/"/g,'&quot;')})">
   <b>${i+1}. ${t.title}</b><br><small>${t.source} · score ${t.score}</small></div>`).join('')
  ||'<p class="log">No trends — check connection.</p>';}
function useTrend(t){document.getElementById('topic').value=t;
 document.querySelector('nav button').click();tab('studio');}
async function loadProjects(){
 const ps=await (await fetch('/api/projects')).json();
 document.getElementById('projlist').innerHTML=ps.map(p=>
  `<div class="proj"><div style="flex:1"><b>${p.slug}</b><br>
   <span class="badge ${p.has_video?'ok':''}">${p.has_video?'🎬 video ready':'📝 in progress'}</span>
   ${p.has_video?` <span class="badge">${Math.round(p.size/1024)}KB</span>`:''}</div>
  ${p.has_video?`<video src="/api/video/${p.slug}" controls preload="none"></video>
   <button class="go" onclick="publish('${p.slug}')">Publish</button>`:''}</div>`).join('')
  ||'<p class="log">No projects yet.</p>';}
async function publish(slug){
 const plats=prompt('Platforms (comma-separated):','youtube,tiktok');
 if(!plats)return;
 const r=await fetch('/api/publish',{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({slug,platforms:plats.split(',').map(s=>s.trim()),dry_run:true})});
 alert(JSON.stringify(await r.json(),null,2));}
async function loadStats(){
 const s=await (await fetch('/api/stats')).json();
 document.getElementById('statlist').innerHTML=
  `<div class="stat"><b>${s.projects}</b><span>projects</span></div>
   <div class="stat"><b>${s.videos}</b><span>videos rendered</span></div>
   <div class="stat"><b>${s.total_mb}</b><span>MB of video</span></div>
   <div class="stat"><b>${s.platforms.length}</b><span>platforms</span></div>
   <p class="log" style="margin-top:14px">Platforms: ${s.platforms.join(', ')}</p>`;}
</script></body></html>
"""


def main(host: str = "127.0.0.1", port: int = 8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
