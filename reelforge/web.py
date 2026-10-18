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
from .publish import ADAPTERS, platform_status, publish as publish_adapter

app = FastAPI(title="ReelForge Studio")

_jobs: dict[str, dict] = {}


class GenRequest(BaseModel):
    topic: str
    duration: int = 30
    language: str = "en"


class TrendRequest(BaseModel):
    niche: str = "general"
    limit: int = 10


class PublishRequest(BaseModel):
    slug: str
    platforms: list[str]
    dry_run: bool = True


def _run_generation(job_id: str, topic: str, duration: int, language: str = "en"):
    _jobs[job_id] = {"status": "running", "topic": topic, "started": time.time()}
    try:
        cfg = Config()
        workdir = pipeline.create_project(topic, duration, cfg)
        slug = workdir.name
        if language and language != "en":
            _jobs[job_id]["status"] = "dubbing"
            from reelforge import dub as dub_mod
            dub_mod.dub_project(slug, language, cfg)
            slug = f"{slug}-dub-{language}"
        _jobs[job_id] = {"status": "done", "slug": slug,
                         "topic": topic,
                         "video_url": f"/api/video/{slug}"}
    except Exception as e:  # noqa: BLE001
        _jobs[job_id] = {"status": "failed", "topic": topic, "error": str(e)}


@app.post("/api/generate")
def generate(req: GenRequest):
    job_id = uuid.uuid4().hex[:8]
    t = threading.Thread(target=_run_generation,
                         args=(job_id, req.topic, req.duration, req.language),
                         daemon=True)
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


@app.get("/api/platforms")
def platforms():
    return platform_status()


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
.platgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px}
.pcard{background:#0b0e14;border:1px solid var(--line);border-radius:10px;
padding:14px;cursor:pointer;transition:border-color .15s}
.pcard.sel{border-color:var(--acc);box-shadow:0 0 0 1px var(--acc)}
.pcard.off{opacity:.55;cursor:not-allowed}
.pcard h4{margin:0 0 6px;font-size:15px;display:flex;align-items:center;gap:8px}
.pcard .st{font-size:12px;padding:2px 9px;border-radius:12px}
.st.ready{background:#052e16;color:var(--grn)}
.st.needs_auth{background:#451a03;color:#fdba74}
.st.needs_setup{background:#1a2130;color:var(--dim)}
.pcard small{color:var(--dim);font-size:12px}
.pcard input{width:auto;margin-right:8px}
.res{padding:10px 12px;border-radius:8px;margin-bottom:8px;font-size:14px}
.res.ok{background:#052e16;border:1px solid #14532d}
.res.err{background:#2a0a0a;border:1px solid #7f1d1d}
.res a{color:#7dd3fc}
</style></head><body>
<header><h1>⚒️ Reel<span>Forge</span> Studio</h1></header>
<nav>
<button class="on" onclick="tab('studio')">🎬 Studio</button>
<button onclick="tab('trends')">📈 Trends</button>
<button onclick="tab('library')">📚 Library</button>
<button onclick="tab('publish')">🚀 Publish</button>
<button onclick="tab('stats')">📊 Stats</button>
</nav><main>
<div id="t-studio" class="tab on">
 <div class="panel"><h3>New video</h3>
  <div class="row">
   <div><label>Topic</label><input id="topic" placeholder="hyderabadi biryani"></div>
   <div style="max-width:120px"><label>Seconds</label>
    <input id="dur" type="number" value="30" min="5" max="180"></div>
   <div style="max-width:150px"><label>Language</label>
    <select id="lang">
     <option value="en">English</option>
     <option value="ur">Urdu</option>
     <option value="ur-roman">Urdu (Roman)</option>
     <option value="hi">Hindi</option>
     <option value="hi-roman">Hindi (Roman)</option>
     <option value="ar">Arabic</option>
     <option value="es">Spanish</option>
     <option value="fr">French</option>
     <option value="de">German</option>
     <option value="pt">Portuguese</option>
    </select></div>
   <div style="max-width:150px"><label>&nbsp;</label><br>
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
<div id="t-publish" class="tab">
 <div class="panel"><h3>🚀 Publish to platforms</h3>
  <div class="row" style="margin-bottom:14px"><div><label>Video</label>
   <select id="pubslug" onchange="updateCount()"></select></div>
   <div style="max-width:220px"><label>Mode</label><select id="pubmode">
    <option value="dry">🧪 Dry run (safe test)</option>
    <option value="live">🚨 Go live (posts for real)</option>
   </select></div></div>
  <div id="platgrid" class="platgrid"></div>
  <div style="margin-top:16px;display:flex;gap:10px;align-items:center">
   <button class="go" id="pubbtn" onclick="doPublish()">Publish to selected</button>
   <span class="log" id="pubcount"></span></div>
  <div id="pubresults" style="margin-top:14px"></div>
 </div>
 <div class="panel"><h3>🔑 Platform setup</h3>
  <p class="log">One-time setup per platform. Keys go in your environment or
  <b>.env</b> — never in the repo. See <b>docs/setup-&lt;platform&gt;.md</b> for the
  2-minute walkthrough each.</p>
  <div id="setuphelp"></div></div>
</div>
<div id="t-stats" class="tab"><div class="panel"><h3>Studio stats</h3>
 <div id="statlist"></div></div></div>
</main>
<script>
function tab(n){document.querySelectorAll('.tab').forEach(e=>e.classList.remove('on'));
document.getElementById('t-'+n).classList.add('on');
document.querySelectorAll('nav button').forEach(e=>e.classList.remove('on'));
event.target.classList.add('on');
if(n==='library')loadProjects();if(n==='stats')loadStats();
if(n==='trends')loadTrends();if(n==='publish')loadPublish();}
function friendlyError(e){
 if(!e) return 'Something went wrong.';
 if(/non-zero exit status|ffmpeg/i.test(e)){
  if(/fontfile|drawtext|vignette|gradients/i.test(e))
   return 'Video renderer crashed (usually a font or filter issue on Windows). Try again — if it repeats, run `reelforge doctor`.';
  return 'Video rendering failed. Run `reelforge doctor` to check ffmpeg.';
 }
 if(/pixabay|pexels|api key|401|403/i.test(e))
  return 'Stock footage API issue — check your API key, or the video will use placeholder visuals.';
 if(/edge-tts|piper|tts|voice/i.test(e))
  return 'Voice generation failed — check your internet or voice setup.';
 if(/gemini|llm|nvidia|429|quota/i.test(e))
  return 'AI script service is busy or out of quota — try again in a few minutes.';
 return e.length>200 ? e.slice(0,200)+'…' : e;
}
async function generate(){
 const topic=document.getElementById('topic').value.trim();
 if(!topic){alert('Enter a topic');return;}
 const btn=document.getElementById('genbtn');btn.disabled=true;
 const log=document.getElementById('genlog');log.textContent='Forging… (script → voice → verified footage → captions → render)';
 const lang=document.getElementById('lang').value;
 const r=await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({topic,duration:+document.getElementById('dur').value,language:lang})});
 const {job_id}=await r.json();
 const iv=setInterval(async()=>{
  const s=await (await fetch('/api/jobs/'+job_id)).json();
  if(s.status==='done'){clearInterval(iv);btn.disabled=false;
   log.innerHTML='✅ Done: <b>'+s.slug+'</b> — see Library to preview & publish.';
   loadProjects();}
  else if(s.status==='failed'){clearInterval(iv);btn.disabled=false;
   log.innerHTML='❌ '+friendlyError(s.error);}
  else if(s.status==='dubbing'){log.textContent='Dubbing into '+document.getElementById('lang').selectedOptions[0].text+'…';}
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
 document.querySelectorAll('nav button')[3].click();tab('publish');
 document.getElementById('pubslug').value=slug;}
let _plats=[];
async function loadPublish(){
 const ps=await (await fetch('/api/projects')).json();
 const vids=ps.filter(p=>p.has_video);
 document.getElementById('pubslug').innerHTML=vids.map(p=>
  `<option value="${p.slug}">${p.slug}</option>`).join('')
  ||'<option value="">— no videos yet —</option>';
 _plats=await (await fetch('/api/platforms')).json();
 const grid=document.getElementById('platgrid');
 grid.innerHTML=_plats.map(p=>{
  const dis=p.state==='needs_setup';
  const badge=p.state==='ready'?'✅ Ready':p.state==='needs_auth'?'🔑 Needs one-time auth':'⚠️ Needs setup';
  return `<div class="pcard ${dis?'off':'sel'}" id="pc-${p.platform}"
   ${dis?'':`onclick="togglePlat('${p.platform}')"`}>
   <h4>${dis?'':`<input type="checkbox" checked onclick="event.stopPropagation();togglePlat('${p.platform}')">`}${p.label}</h4>
   <span class="st ${p.state}">${badge}</span><br>
   <small>${p.state==='ready'?'Good to go.'
    :p.state==='needs_auth'?p.hint
    :'Missing: '+p.missing.join(', ')+'. See docs/setup-'+p.platform+'.md'}</small></div>`;}).join('');
 document.getElementById('setuphelp').innerHTML=_plats.filter(p=>p.state==='needs_setup').map(p=>
  `<p class="log"><b>${p.label}</b> — set ${p.missing.join(', ')} in your environment or .env, then refresh. <b>docs/setup-${p.platform}.md</b> has the 2-minute guide.</p>`).join('')
  ||'<p class="log">✅ Every platform is configured. Pick a video and hit Publish.</p>';
 updateCount();}
function togglePlat(p){
 const card=document.getElementById('pc-'+p);
 card.classList.toggle('sel');
 const cb=card.querySelector('input');if(cb)cb.checked=card.classList.contains('sel');
 updateCount();}
function selPlats(){return _plats.filter(p=>{const c=document.getElementById('pc-'+p.platform);
 return c&&c.classList.contains('sel')&&!c.classList.contains('off');}).map(p=>p.platform);}
function updateCount(){const n=selPlats().length;
 document.getElementById('pubcount').textContent=n?`${n} platform${n>1?'s':''} selected`:'Select at least one platform';
 document.getElementById('pubbtn').disabled=!n||!document.getElementById('pubslug').value;}
async function doPublish(){
 const slug=document.getElementById('pubslug').value;
 const platforms=selPlats();if(!slug||!platforms.length)return;
 const live=document.getElementById('pubmode').value==='live';
 if(live&&!confirm(`Post "${slug}" to ${platforms.join(', ')} FOR REAL?`))return;
 const btn=document.getElementById('pubbtn');btn.disabled=true;
 const box=document.getElementById('pubresults');
 box.innerHTML='<p class="log">Publishing…</p>';
 const r=await fetch('/api/publish',{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({slug,platforms,dry_run:!live})});
 const res=await r.json();
 box.innerHTML=res.map(x=>{
  if(x.error)return `<div class="res err">❌ <b>${x.platform}</b> — ${x.error}</div>`;
  const url=x.url?` — <a href="${x.url}" target="_blank">view post ↗</a>`:'';
  const tag=x.dry_run?'🧪 dry run':'✅ posted';
  return `<div class="res ok">${tag} <b>${x.platform}</b>${url}</div>`;}).join('');
 btn.disabled=false;}
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
