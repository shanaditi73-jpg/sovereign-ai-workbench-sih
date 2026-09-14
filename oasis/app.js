const API="http://localhost:8000";
let TOKEN=null, FILE=null, CAN_UPLOAD=false, UPFILE=null, UPLEVEL=null;
const $=id=>document.getElementById(id);

/* ---------- flowing particle wave ---------- */
(function(){
  const c=$("wave"), x=c.getContext("2d");
  let W,H,parts=[],t=0;
  function size(){ W=c.width=innerWidth*devicePixelRatio; H=c.height=innerHeight*devicePixelRatio; }
  size(); addEventListener("resize",size);
  for(let i=0;i<1400;i++) parts.push({p:Math.random(),o:(Math.random()-.5)*150,
    s:.00016+Math.random()*.00042,a:.1+Math.random()*.6,r:Math.random()*1.5+.25});
  function curve(p){
    const px=p*1.35-.18;
    return { x:px*W, y:H*(.52+Math.sin(px*Math.PI*1.65)*.3+Math.sin(px*7.2)*.018) };
  }
  function draw(){
    x.clearRect(0,0,W,H); t+=.0022;
    for(const q of parts){
      q.p+=q.s; if(q.p>1.05) q.p=-.05;
      const pt=curve(q.p);
      const sp=Math.sin(q.p*Math.PI);
      const off=q.o*devicePixelRatio*(.45+sp*.9);
      const yy=pt.y+off+Math.sin(t*2.4+q.p*11)*7*devicePixelRatio;
      const fade=Math.min(1,sp*1.9);
      const glow=Math.max(0,1-Math.abs(q.o)/110);
      x.beginPath();
      x.arc(pt.x,yy,q.r*devicePixelRatio*(1+glow*.8),0,6.283);
      const dk=document.body.dataset.t==="dark";
      const r=dk?40+glow*90:150-glow*30, g=dk?210+glow*40:132-glow*20,
            b=dk?200+glow*45:220+glow*20;
      x.fillStyle="rgba("+(r|0)+","+(g|0)+","+(b|0)+","+
        (q.a*fade*(dk?.16+glow*.5:.20+glow*.55))+")";
      x.fill();
    }
    requestAnimationFrame(draw);
  }
  draw();
})();

/* ---------- theme ---------- */
$("tgl").onclick=()=>{
  const d=document.body.dataset.t==="dark";
  document.body.dataset.t=d?"light":"dark";
  $("tgl-ic").innerHTML=d?"&#9789;":"&#9788;";
  $("tgl-tx").textContent=d?"Dark":"Light";
};

/* ---------- login ---------- */
const BLURB={
  restricted:"Can retrieve every document, including restricted material, and may add new documents to the library.",
  internal:"Can retrieve public and internal documentation. Restricted material is not returned.",
  public:"Site access only. Internal and restricted documents are not retrievable.",
};

async function loadRoles(){
  try{
    const r=await fetch(API+"/roles");
    const d=await r.json();
    $("roles").innerHTML=d.roles.map(x=>
      '<button class="role" data-u="'+esc(x.username)+'">'+
      '<div class="rn">'+esc(x.role)+'</div>'+
      '<div class="rd">'+esc(BLURB[x.clearance]||"")+'</div>'+
      '<span class="rc">'+esc(x.label)+'</span></button>'
    ).join("");
    document.querySelectorAll(".role").forEach(b=>{
      b.onclick=()=>{
        document.querySelectorAll(".role").forEach(x=>x.classList.remove("on"));
        b.classList.add("on"); $("user").value=b.dataset.u;
        $("pass").focus(); chk();
      };
    });
  }catch(e){
    $("roles").innerHTML='<div class="hint">Cannot reach the server on port 8000. '+
      'Start it with: uvicorn server:app --port 8000</div>';
  }
}
loadRoles();
function chk(){ $("go").disabled=!($("user").value&&$("pass").value); }
$("user").oninput=chk; $("pass").oninput=chk;
$("pass").onkeydown=e=>{ if(e.key==="Enter"&&!$("go").disabled) signIn(); };
$("go").onclick=signIn;

async function signIn(){
  $("err").textContent="";
  const fd=new FormData();
  fd.append("username",$("user").value.trim());
  fd.append("password",$("pass").value);
  try{
    const r=await fetch(API+"/login",{method:"POST",body:fd});
    const d=await r.json();
    if(!d.ok){ $("err").textContent=d.error||"Sign-in failed"; return; }
    TOKEN=d.token; CAN_UPLOAD=!!d.can_upload;
    $("uploader").style.display=CAN_UPLOAD?"block":"none";
    $("uplocked").style.display=CAN_UPLOAD?"none":"block";
    $("who").textContent=d.name;
    $("chip").textContent=d.label;
    $("hello").innerHTML="Hello, <em>"+d.name.split(" ").slice(-1)[0]+"</em>";
    $("login").style.display="none";
    $("app").style.display="flex";
    refresh(); loadSuggestions();
  }catch(e){ $("err").textContent="Cannot reach the server. Is it running on port 8000?"; }
}
$("signout").onclick=()=>{
  TOKEN=null; FILE=null;
  $("thread").innerHTML=""; $("att").textContent="";
  $("stage").classList.remove("busy");
  $("plus").classList.remove("has"); $("pass").value=""; chk();
  $("rail").classList.remove("open"); $("rail-btn").classList.remove("on");
  CAN_UPLOAD=false; UPFILE=null; UPLEVEL=null; $("ures").innerHTML="";
  RECENT=[]; $("chips").innerHTML="";
  document.querySelectorAll(".lvlbtn").forEach(x=>x.classList.remove("on"));
  $("app").style.display="none"; $("login").style.display="flex";
};

/* ---------- rail ---------- */
$("rail-btn").onclick=()=>{
  const o=$("rail").classList.toggle("open");
  $("rail-btn").classList.toggle("on",o);
  if(o){ refresh(); loadDocs(); loadFiles(); }
};
document.querySelectorAll(".rtab").forEach(t=>{
  t.onclick=()=>{
    document.querySelectorAll(".rtab").forEach(x=>x.classList.remove("on"));
    document.querySelectorAll(".rsec").forEach(x=>x.classList.remove("on"));
    t.classList.add("on"); $(t.dataset.s).classList.add("on");
    if(t.dataset.s==="docs") loadDocs();
    if(t.dataset.s==="arte") loadFiles();
  };
});

/* ---------- ask ---------- */
$("plus").onclick=()=>$("file").click();
$("file").onchange=e=>{
  FILE=e.target.files[0]||null;
  $("att").textContent=FILE?"Attached: "+FILE.name+" - used for this question only, not added to the library":"";
  $("plus").classList.toggle("has",!!FILE);
};
/* ---------- suggestions ---------- */
let STARTERS=[], RECENT=[], SUG="";

async function loadSuggestions(){
  if(!TOKEN) return;
  try{
    const r=await fetch(API+"/suggestions?token="+encodeURIComponent(TOKEN));
    const d=await r.json();
    STARTERS=d.starters||[]; RECENT=d.recent||[];
  }catch(e){}
  drawChips();
}

function drawChips(){
  if(!$("chips")) return;
  if($("q").value.trim()){ $("chips").innerHTML=""; return; }
  let h="";
  if(RECENT.length){
    h+='<div class="chips-lbl">this session</div>';
    h+=RECENT.slice(0,3).map(q=>
      '<button class="chip-q recent" data-q="'+esc(q)+'">'+esc(q)+'</button>').join("");
  }
  h+='<div class="chips-lbl">try asking</div>';
  h+=STARTERS.map(q=>
    '<button class="chip-q" data-q="'+esc(q)+'">'+esc(q)+'</button>').join("");
  $("chips").innerHTML=h;
  $("chips").querySelectorAll(".chip-q").forEach(b=>{
    b.onclick=()=>{ $("q").value=b.dataset.q; $("q").focus(); drawGhost(); drawChips(); };
  });
}

/* type-ahead: matches what you have typed, Tab accepts */
function pickSuggestion(v){
  if(!v) return "";
  const low=v.toLowerCase();
  const all=RECENT.concat(STARTERS);
  return all.find(s=>s.toLowerCase().startsWith(low)&&s.length>v.length)||"";
}
function drawGhost(){
  const v=$("q").value;
  SUG=pickSuggestion(v);
  if(!SUG){ $("ghost").innerHTML=""; return; }
  $("ghost").innerHTML="<b>"+esc(v)+"</b>"+esc(SUG.slice(v.length))+
    '<span class="tabkey">tab</span>';
}
$("q").oninput=()=>{ drawGhost(); drawChips(); };
$("q").onfocus=drawGhost;

$("send").onclick=ask;
$("q").onkeydown=e=>{
  if(e.key==="Tab"&&SUG){ e.preventDefault(); $("q").value=SUG; drawGhost(); return; }
  if(e.key==="ArrowRight"&&SUG&&$("q").selectionStart===$("q").value.length){
    e.preventDefault(); $("q").value=SUG; drawGhost(); return; }
  if(e.key==="Enter") ask();
};

async function ask(){
  const q=$("q").value.trim(); if(!q) return;
  $("send").disabled=true; $("stage").classList.add("busy");
  const box=document.createElement("div"); box.className="turn";
  box.innerHTML='<div class="qline">'+esc(q)+'</div><div class="meta">'+
    '<span class="tag"><span class="spin"></span>retrieving</span></div>';
  $("thread").appendChild(box); $("q").value=""; drawGhost();
  const fd=new FormData();
  fd.append("token",TOKEN); fd.append("question",q);
  if(FILE) fd.append("file",FILE);
  try{
    const r=await fetch(API+"/ask",{method:"POST",body:fd});
    const d=await r.json(); render(box,q,d);
    if(d.ledger) rows(d.ledger);
    if(d.recent){ RECENT=d.recent; }
  }catch(e){
    box.querySelector(".meta").innerHTML='<span class="tag warn">server unreachable</span>';
  }
  FILE=null; $("file").value=""; $("att").textContent="";
  $("plus").classList.remove("has"); $("send").disabled=false;
  drawChips();
}

function render(box,q,d){
  let t='<span class="tag">'+d.sources.length+' passages</span>';
  if(d.excluded) t+='<span class="tag warn">'+d.excluded+' excluded by clearance</span>';
  if(!d.refused) t+='<span class="tag acc">'+esc(d.model_used)+' &middot; '+esc(d.model_reason)+'</span>';
  let h='<div class="qline">'+esc(q)+'</div><div class="meta">'+t+'</div>';
  if(d.steps&&d.steps.length){
    h+='<div class="steps">'+d.steps.map(s=>
      '<div class="step"><b>'+esc(s.tool)+'</b> '+esc(String(s.result||''))+'</div>'
    ).join("")+'</div>';
  }
  h+='<div class="ans'+(d.refused?' ref':'')+'">'+esc(d.answer)+'</div>';
  if(d.sources.length){
    h+='<div class="srcs"><h4>Sources</h4>';
    d.sources.forEach((s,i)=>{
      const pg=s.page===null?"queried":"page "+s.page;
      h+='<div class="src mono">['+(i+1)+'] <b>'+esc(s.document)+'</b> &middot; '+pg+'</div>';
    });
    h+='</div>';
  }
  if(d.pending_action){
    h+='<div class="appr"><div class="t">Agent wants to <b>'+esc(d.pending_action.description)+
       '</b></div><div><button class="bt p" data-ok="true">Approve</button>'+
       '<button class="bt" data-ok="false">Reject</button></div></div>';
  }
  box.innerHTML=h;
  box.querySelectorAll(".bt").forEach(b=>{
    b.onclick=async()=>{
      const fd=new FormData();
      fd.append("token",TOKEN); fd.append("action_id",d.pending_action.id);
      fd.append("approved",b.dataset.ok);
      const r=await fetch(API+"/approve",{method:"POST",body:fd});
      const res=await r.json();
      let inner='<div class="t">'+esc(res.message)+'</div>';
      if(res.file){
        inner+='<a class="dl" href="'+API+'/download/'+encodeURIComponent(res.file)+
               '" download>Download '+esc(res.file)+'</a>';
      }
      b.closest(".appr").outerHTML='<div class="appr" style="display:block">'+inner+'</div>';
      if(res.ledger) rows(res.ledger);
      if(res.file) loadFiles();
    };
  });
}
function rows(L){
  $("ledrows").innerHTML=L.slice().reverse().map(e=>
    '<div class="lg"><i class="mono">'+String(e.seq).padStart(3,"0")+'</i>'+esc(e.event)+'</div>'
  ).join("")||'<div class="lg"><i>-</i>no entries yet</div>';
}
/* ---------- generated files tab ---------- */
async function loadFiles(){
  if(!TOKEN) return;
  try{
    const r=await fetch(API+"/outputs?token="+encodeURIComponent(TOKEN));
    const d=await r.json();
    $("artelist").innerHTML=(d.files||[]).map(f=>
      '<div class="arow"><span class="aname">'+esc(f.file)+'</span>'+
      '<span class="awhen">'+esc(f.when)+'</span>'+
      '<span class="akind">'+esc(f.kind)+'</span>'+
      '<a class="adl" href="'+API+'/download/'+encodeURIComponent(f.file)+
      '" download>get</a></div>'
    ).join("")||'<div class="lg"><i>-</i>nothing generated yet</div>';
  }catch(e){}
}

/* ---------- documents tab ---------- */
async function loadDocs(){
  if(!TOKEN) return;
  try{
    const r=await fetch(API+"/documents?token="+encodeURIComponent(TOKEN));
    const d=await r.json();
    if(d.error) return;
    CAN_UPLOAD=!!d.can_upload;
    $("uploader").style.display=CAN_UPLOAD?"block":"none";
    $("uplocked").style.display=CAN_UPLOAD?"none":"block";
    drawDocs(d.documents);
  }catch(e){}
}
function drawDocs(list){
  $("doclist").innerHTML=(list||[]).map(x=>
    '<div class="drow"><span class="dname">'+esc(x.document)+'</span>'+
    '<span class="dmeta">'+x.chunks+'</span>'+
    '<span class="lvl '+esc(x.sensitivity)+'">'+esc(x.sensitivity)+'</span></div>'
  ).join("")||'<div class="lg"><i>-</i>nothing indexed yet</div>';
}

$("drop").onclick=()=>$("upfile").click();
$("drop").ondragover=e=>{ e.preventDefault(); $("drop").classList.add("over"); };
$("drop").ondragleave=()=>$("drop").classList.remove("over");
$("drop").ondrop=e=>{
  e.preventDefault(); $("drop").classList.remove("over");
  if(e.dataTransfer.files[0]) setUpFile(e.dataTransfer.files[0]);
};
$("upfile").onchange=e=>{ if(e.target.files[0]) setUpFile(e.target.files[0]); };

function setUpFile(f){
  UPFILE=f;
  $("dropname").textContent=f.name;
  $("drophint").textContent="ready to add";
  $("ures").innerHTML="";
  upState();
}
document.querySelectorAll(".lvlbtn").forEach(b=>{
  b.onclick=()=>{
    document.querySelectorAll(".lvlbtn").forEach(x=>x.classList.remove("on"));
    b.classList.add("on"); UPLEVEL=b.dataset.l; upState();
  };
});
function upState(){ $("ubtn").disabled=!(UPFILE&&UPLEVEL); }

$("ubtn").onclick=async()=>{
  if(!UPFILE||!UPLEVEL) return;
  $("ubtn").disabled=true;
  $("ures").innerHTML='<span class="spin"></span>indexing';
  const fd=new FormData();
  fd.append("token",TOKEN); fd.append("level",UPLEVEL); fd.append("file",UPFILE);
  try{
    const r=await fetch(API+"/upload",{method:"POST",body:fd});
    const d=await r.json();
    if(d.error){
      $("ures").innerHTML='<span style="color:var(--bad)">'+esc(d.error)+'</span>';
    }else{
      $("ures").innerHTML='<span style="color:var(--acc-ink)">'+esc(d.document)+
        ' indexed as '+esc(d.level)+' &middot; '+d.chunks+' chunks</span>';
      drawDocs(d.documents);
      if(d.ledger) rows(d.ledger);
      UPFILE=null; UPLEVEL=null;
      $("upfile").value="";
      $("dropname").textContent="Choose a PDF";
      $("drophint").textContent="or drag one here";
      document.querySelectorAll(".lvlbtn").forEach(x=>x.classList.remove("on"));
    }
  }catch(e){
    $("ures").innerHTML='<span style="color:var(--bad)">Upload failed. '+
      'Is the server running?</span>';
  }
  upState();
};

$("verify").onclick=async()=>{
  const r=await fetch(API+"/verify",{method:"POST"}); const d=await r.json();
  $("vres").innerHTML=d.intact
    ?'<span style="color:var(--acc-ink)">chain intact &middot; '+d.entries+' entries</span>'
    :'<span style="color:var(--bad)">broken at entry '+d.broken_at+'</span>';
};
async function refresh(){
  try{ const r=await fetch(API+"/status"); const d=await r.json();
    $("blk").textContent=d.blocked; if(d.ledger) rows(d.ledger);
  }catch(e){}
}
function esc(s){return String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));}