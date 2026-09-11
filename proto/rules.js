/* The board rules, shared by both prototypes.

   Lifted from src/engine.js so a prototype answers to the same laws the real
   boards were designed against: what a piece covers, which side you may enter
   from, what counts as reachable floor.

   ⚠ ONE copy, inlined into both templates by build_proto.py. It started as a
   block inside the honey template and was pulled out the moment a second
   prototype needed it: two copies of a rule set means every fix has to be made
   twice, and the second one is the one that gets forgotten.

   RULE_FREEZE and RULE_FULL are the honey prototype's experiments. The 3D
   remake leaves them at false / "leave", which is the original game. */

/* ---------------------------------------------------------------- rules
   Lifted from src/engine.js so the prototype answers to the same laws the real
   boards were designed against: what a comb covers, which side you may enter
   from, what counts as reachable floor. The one new law is SETTING, below. */
const DIRS = [[0,-1],[1,0],[0,1],[-1,0]];
const FACING = DIRS;                 // 0 up, 1 right, 2 down, 3 left
const GREY_TAKES = 2;                // a plain wax comb only ever takes the common pollen

let S = null, RULE_FREEZE = true, CUR = 0;
/* What happens to a piece the moment it fills.

   ⚠ "leave" IS NOT THE ORIGINAL GAME, whatever an earlier version of this
   comment said. Nothing in src/engine.js or src/game_shell.js ever removes a
   seat - grep them for it. The `gone` flag I took it from lives only in
   src/bench_rush.html, an abandoned August prototype that src/solvecheck.py
   still points at; reading that file and assuming it was the engine put a rule
   into two prototypes that the shipped game has never had.

     "stay"   it stays and can still be dragged   <- THE SHIPPED GAME
     "leave"  it lifts off the floor              (bench_rush only; an experiment here)
     "capped" it stays, sealed, and never moves again (an experiment; kills every board tried)

   A full piece is already refused by accepts(), which tests freeSlots. Staying
   put is not a special case - it is what happens when nothing removes it. */
let RULE_FULL = "stay";

const idx = (g,c,r) => r*g.W + c;
const inBoard = (g,c,r) => c>=0 && c<g.W && r>=0 && r<g.H && !g.hole[idx(g,c,r)];
const isFree  = (g,c,r) => inBoard(g,c,r) && g.occ[idx(g,c,r)] < 0;

function cellsOf(b){
  const a=[];
  for(let k=0;k<b.len;k++) a.push(b.dir&1 ? [b.c,b.r+k] : [b.c+k,b.r]);
  return a;
}
const placeCell = (b,k) => cellsOf(b)[k];            // len === cap in this data

/** Never in over the back wall of the comb. */
function entryDirs(b){
  const f=FACING[b.dir];
  return DIRS.filter(d => !(d[0]===-f[0] && d[1]===-f[1]));
}
function cellEntries(g,b,k){
  const own=new Set(cellsOf(b).map(p=>p[0]+","+p[1]));
  const pc=placeCell(b,k), out=[];
  for(const d of entryDirs(b)){
    const nc=pc[0]+d[0], nr=pc[1]+d[1];
    if(!inBoard(g,nc,nr) || own.has(nc+","+nr)) continue;
    out.push([nc,nr]);
  }
  return out;
}
function place(g,b,c,r){
  for(const p of cellsOf(b)) g.occ[idx(g,p[0],p[1])]=-1;
  b.c=c; b.r=r;
  for(const p of cellsOf(b)) g.occ[idx(g,p[0],p[1])]=b.id;
  b.smoked=false;                 // one puff buys one drag, then the honey sets again
}
function lift(g,b){                                  // a full comb leaves the board
  for(const p of cellsOf(b)) g.occ[idx(g,p[0],p[1])]=-1;
  b.gone=true;
}
const walkerAt = (g,c,r) => g.walkers.some(a=>a.cell && a.cell[0]===c && a.cell[1]===r);

function fits(g,b,c,r){
  const hc=b.c, hr=b.r;
  b.c=c; b.r=r; const cs=cellsOf(b); b.c=hc; b.r=hr;
  for(const p of cs){
    if(!inBoard(g,p[0],p[1])) return false;
    const id=g.occ[idx(g,p[0],p[1])];
    if(id>=0 && id!==b.id) return false;
    if(walkerAt(g,p[0],p[1])) return false;
  }
  return true;
}
function reachRegion(g){
  const seen=new Uint8Array(g.W*g.H), DC=g.door[0], DR=g.door[1];
  if(!isFree(g,DC,DR)) return seen;
  seen[idx(g,DC,DR)]=1;
  const st=[[DC,DR]];
  while(st.length){
    const p=st.pop();
    for(const d of DIRS){
      const nc=p[0]+d[0], nr=p[1]+d[1];
      if(isFree(g,nc,nr) && !seen[idx(g,nc,nr)]){ seen[idx(g,nc,nr)]=1; st.push([nc,nr]); }
    }
  }
  return seen;
}
function floorDist(g){
  const dist=new Int32Array(g.W*g.H).fill(-1), DC=g.door[0], DR=g.door[1];
  if(!isFree(g,DC,DR)) return dist;
  dist[idx(g,DC,DR)]=0;
  const q=[[DC,DR]];
  while(q.length){
    const p=q.shift();
    for(const d of DIRS){
      const nc=p[0]+d[0], nr=p[1]+d[1];
      if(!isFree(g,nc,nr) || dist[idx(g,nc,nr)]>=0) continue;
      dist[idx(g,nc,nr)]=dist[idx(g,p[0],p[1])]+1;
      q.push([nc,nr]);
    }
  }
  return dist;
}
const freeSlots = b => b.occ.reduce((n,v)=>n+(v==null?1:0),0);
const accepts = (b,ci) => !b.gone && freeSlots(b) > (b.pending||0)
                       && (b.colour===0 ? ci===GREY_TAKES : b.colour===ci);
const FIXED = b => b.colour===0;

/* ---- THE NEW LAW ------------------------------------------------------
   A comb holding honey but not yet full is SETTING: stuck where it stands.

   ⚠ Full combs still lift away, and that is not a detail - it is what keeps the
   board from clogging. Measured over all 2085 boards: capacity equals queue
   length on every single one, zero spare slots anywhere. Freeze a comb for good
   once it fills and the floor runs out on EVERY level. The commitment has to
   land on the half-filled comb, not the finished one. */
const isSetting = b => RULE_FREEZE && !b.gone && !b.smoked && b.cap>1
                    && b.occ.some(v=>v!=null) && freeSlots(b)>0;

/* ---- CAPPED ------------------------------------------------------------
   With RULE_LIFT off nothing ever leaves the floor: a comb that fills is capped
   with wax and becomes part of the hive. ⚠ This is the opposite of what I first
   argued. "A full comb has to lift away or the floor runs out" was reasoning,
   not measurement, and it was wrong: a comb that stays occupies exactly the
   cells it already occupied, so the free floor is unchanged. What shrinks is the
   number of pieces you can still move - which is a difficulty curve that rises
   instead of falling away, and is the whole point of the change. */
const canDrag = b => !b.gone && !b.capped && !FIXED(b) && !isSetting(b);

function placements(g,b){
  if(!canDrag(b)) return [];
  const seen=new Set([b.c+","+b.r]), out=[], q=[[b.c,b.r]];
  while(q.length){
    const p=q.shift();
    for(const d of DIRS){
      const nc=p[0]+d[0], nr=p[1]+d[1], key=nc+","+nr;
      if(seen.has(key)) continue;
      const hc=b.c, hr=b.r;
      b.c=p[0]; b.r=p[1];
      const ok=fits(g,b,nc,nr);
      b.c=hc; b.r=hr;
      if(!ok) continue;
      seen.add(key); out.push([nc,nr]); q.push([nc,nr]);
    }
  }
  return out;
}
/** The nearest cell this pollen colour can actually reach. */
function pickCell(g,ci){
  const DC=g.door[0], DR=g.door[1];
  const plug=g.occ[idx(g,DC,DR)];
  if(plug>=0){                                   // a comb standing in the hatch
    const b=g.combs[plug];
    if(b && accepts(b,ci)) for(let k=0;k<b.cap;k++){
      if(b.occ[k]!=null || b.claim.has(k)) continue;
      const pc=placeCell(b,k);
      if(pc[0]===DC && pc[1]===DR) return {b:b,k:k,entry:null};
    }
    return null;                                 // hatch blocked: nothing behind it is reachable
  }
  const dist=floorDist(g);
  let best=null, bd=Infinity;
  for(const b of g.combs){
    if(!accepts(b,ci)) continue;
    for(let k=0;k<b.cap;k++){
      if(b.occ[k]!=null || b.claim.has(k)) continue;
      for(const e of cellEntries(g,b,k)){
        const dd=dist[idx(g,e[0],e[1])];
        if(dd>=0 && dd<bd){ bd=dd; best={b:b,k:k,entry:e}; }
      }
    }
  }
  return best;
}
function walkPath(g,b,k,entry){
  if(!entry) return [];
  const dist=floorDist(g);
  let c=entry[0], r=entry[1];
  const path=[[c,r]];
  let guard=0;
  while(dist[idx(g,c,r)]>0 && guard++<400){
    for(const d of DIRS){
      const nc=c+d[0], nr=r+d[1];
      if(inBoard(g,nc,nr) && dist[idx(g,nc,nr)]===dist[idx(g,c,r)]-1){ c=nc; r=nr; break; }
    }
    path.push([c,r]);
  }
  path.reverse();
  path.push(placeCell(b,k));
  return path;
}
