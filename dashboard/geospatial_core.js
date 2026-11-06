/* Pure playback contracts shared by the public and local-file map. No I/O. */
(function(root){
'use strict';
const states=['neither','plow_only','spreader_only','both'];
function requireValue(ok,code){if(!ok)throw Error(code);}
function minutes(t){
 requireValue(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(t),'Unzoned source-clock timestamp required');
 const p=t.split(/[- :]/).map(Number), d=new Date(Date.UTC(p[0],p[1]-1,p[2],p[3],p[4],p[5]));
 requireValue(d.toISOString().slice(0,19).replace('T',' ')===t,'Invalid source-clock date');
 return d.getTime()/60000; // Clock index only. Never a claimed UTC instant.
}
function stamp(m){return new Date(m*60000).toISOString().slice(0,19).replace('T',' ');}
function validateLocal(d,scopes){
 requireValue(d.schema==='winterops-local-geospatial-v3','Wrong local payload schema');
 requireValue(Array.isArray(d.scopes)&&d.scopes.length===scopes.length,'Wrong source scope');
 d.scopes.forEach((s,i)=>requireValue(s.processing_key===scopes[i].processing_key&&s.source_file_sha256===scopes[i].source_file_sha256,'Source version mismatch'));
 for(const k of ['cells','segments','episodes','reporting','matches'])requireValue(Array.isArray(d[k]),'Missing '+k);
 requireValue(d.grids&&typeof d.grids==='object'&&!Array.isArray(d.grids),'Missing grid catalog');
 const totals=scopes.map(()=>0),seen=new Set();
 for(const c of d.cells){
  requireValue(c.length===7&&Number.isInteger(c[0])&&c[0]>=0&&c[0]<scopes.length,'Cell scope');
  const m=minutes(c[1]);requireValue(c[1].slice(0,10)>=scopes[c[0]].source_week_start&&c[1].slice(0,10)<scopes[c[0]].source_week_end_exclusive,'Cell outside source period');
  requireValue(Number.isInteger(c[2])&&c[2]>=-18000&&c[2]<18000&&Number.isInteger(c[3])&&c[3]>=-36000&&c[3]<36000&&states.includes(c[4]),'Cell coordinates/state');
  requireValue(Number.isInteger(c[5])&&c[5]>0&&Number.isInteger(c[6])&&c[6]>0&&c[6]<=c[5],'Cell counts');
  const key=c.slice(0,5).join('|');requireValue(!seen.has(key),'Duplicate cell key');seen.add(key);totals[c[0]]+=c[5];
 }
 for(const [i,e] of d.episodes.entries()){
  requireValue(e.length===9&&Number.isInteger(e[0])&&e[0]>=0&&e[0]<scopes.length&&minutes(e[2])>=minutes(e[1])&&e[3]>0,'Episode contract');
 }
 for(const s of d.segments){
  requireValue(s.length===13&&Number.isInteger(s[0])&&Number.isInteger(s[1])&&d.episodes[s[1]]?.[0]===s[0],'Movement scope');
  const seconds=(minutes(s[3])-minutes(s[2]))*60;
  requireValue(seconds>0&&seconds<=60&&states.includes(s[8])&&s[9]>=0&&s[9]<=100,'Movement continuity');
  requireValue(s.slice(4,8).every(Number.isFinite)&&Math.abs(s[4])<=180&&Math.abs(s[6])<=180&&Math.abs(s[5])<=90&&Math.abs(s[7])<=90,'Movement coordinates');
 }
 return totals;
}
function indexLocal(d){
 if(!d._index)Object.defineProperty(d,'_index',{value:{cells:d.cells.map(c=>minutes(c[1])),starts:d.segments.map(s=>minutes(s[2])),ends:d.segments.map(s=>minutes(s[3])),episodes:d.episodes.map(e=>minutes(e[1]))}});
 return d._index;
}
function privateFrame(d,selection){
 const {scope,start,end,state}=selection,lo=minutes(start),hi=minutes(end);
 requireValue(hi>lo&&hi-lo<=360,'Playback bound: at most six source-clock hours');
 const ix=indexLocal(d),rows=d.cells.filter((c,i)=>c[0]===scope&&ix.cells[i]>=lo&&ix.cells[i]<hi);
 const visible=rows.filter(c=>state==='all'||c[4]===state),cells=new Map();
 for(const c of visible){const k=c[2]+':'+c[3];const v=cells.get(k)||{south:c[2]/200,west:c[3]/200,count:0};v.count+=c[5];cells.set(k,v);}
 const segments=d.segments.filter((s,i)=>s[0]===scope&&ix.starts[i]>=lo&&ix.ends[i]<hi&&(state==='all'||s[8]===state)&&(selection.episode==null||s[1]===selection.episode));
 const onsets=d.episodes.filter((e,i)=>e[0]===scope&&ix.episodes[i]>=lo&&ix.episodes[i]<hi);
 return {cells:[...cells.values()],segments,onsets,totalObservations:rows.reduce((n,c)=>n+c[5],0),selectedObservations:visible.reduce((n,c)=>n+c[5],0),status:rows.length?'RECORDED':'MISSING_TELEMETRY_ACTIVITY_UNKNOWN'};
}
function publicCells(data,scope){
 // Fixed week + total only: no hour/state filter or export can reveal a finer
 // intersection or subtract overlapping private spatial summaries.
 const key=data.scopes[scope].processing_key;
 return data.cells.filter(c=>c.processing_key===key&&c.observation_count>=20).map(c=>{const [,y,x]=c.spatial_bin.split(':').map(Number);return{south:y/4,west:x/4,count:c.observation_count};});
}
function weatherFrame(d,selection){
 const key=d.scopes[selection.scope].processing_key,lo=minutes(selection.start),hi=minutes(selection.end),facts=new Map();
 for(const m of d.matches){const h=minutes(m.source_local_hour);if(m.processing_key!==key||m.timezone_hypothesis!==selection.zone||h+60<=lo||h>=hi)continue;
  const k=m.grid_id+'|'+m.source_local_hour;const old=facts.get(k);
  if(old)requireValue(old[selection.variable]===m[selection.variable],'Conflicting weather fact');else facts.set(k,m);
 }
 const byGrid=new Map();for(const m of facts.values()){let g=byGrid.get(m.grid_id);if(!g){g={id:m.grid_id,values:[],hours:0};byGrid.set(m.grid_id,g);}const v=m[selection.variable];if(v!==null&&Number.isFinite(v))g.values.push(v);g.hours++;}
 return [...byGrid.values()].map(g=>({...g,value:g.values.length?g.values.reduce((a,b)=>a+b,0)/g.values.length:null}));
}
const api={minutes,stamp,validateLocal,privateFrame,publicCells,weatherFrame};
if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.WinterOpsGeo=api;
})(typeof globalThis!=='undefined'?globalThis:this);
