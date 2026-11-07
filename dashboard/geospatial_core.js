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
 const totals=scopes.map(()=>0),seen=new Set(),clockCache=new Map();
 function clock(t){if(!clockCache.has(t))clockCache.set(t,minutes(t));return clockCache.get(t);}
 const seeds={cells:[],starts:[],ends:[],episodes:[]};
 for(const c of d.cells){
  requireValue(c.length===7&&Number.isInteger(c[0])&&c[0]>=0&&c[0]<scopes.length,'Cell scope');
  const m=clock(c[1]);seeds.cells.push(m);requireValue(c[1].slice(0,10)>=scopes[c[0]].source_week_start&&c[1].slice(0,10)<scopes[c[0]].source_week_end_exclusive,'Cell outside source period');
  requireValue(Number.isInteger(c[2])&&c[2]>=-18000&&c[2]<18000&&Number.isInteger(c[3])&&c[3]>=-36000&&c[3]<36000&&states.includes(c[4]),'Cell coordinates/state');
  requireValue(Number.isInteger(c[5])&&c[5]>0&&Number.isInteger(c[6])&&c[6]>0&&c[6]<=c[5],'Cell counts');
  const key=c.slice(0,5).join('|');requireValue(!seen.has(key),'Duplicate cell key');seen.add(key);totals[c[0]]+=c[5];
 }
 for(const [i,e] of d.episodes.entries()){
  requireValue(e.length===9&&Number.isInteger(e[0])&&e[0]>=0&&e[0]<scopes.length&&clock(e[2])>=clock(e[1])&&e[3]>0,'Episode contract');seeds.episodes.push(clock(e[1]));
 }
 for(const s of d.segments){
  requireValue(s.length===13&&Number.isInteger(s[0])&&Number.isInteger(s[1])&&d.episodes[s[1]]?.[0]===s[0],'Movement scope');
  const start=clock(s[2]),end=clock(s[3]),seconds=(end-start)*60;seeds.starts.push(start);seeds.ends.push(end);
  requireValue(seconds>0&&seconds<=60&&states.includes(s[8])&&s[9]>=0&&s[9]<=100,'Movement continuity');
  requireValue(s.slice(4,8).every(Number.isFinite)&&Math.abs(s[4])<=180&&Math.abs(s[6])<=180&&Math.abs(s[5])<=90&&Math.abs(s[7])<=90,'Movement coordinates');
 }
 if(d.evidence31){
  const e=d.evidence31;requireValue(e.schema==='winterops-evidence-v31-private'&&Array.isArray(e.segment_marks)&&e.segment_marks.length===d.segments.length,'Road evidence alignment');
  for(const k of ['road_names','passages','quality_cells','rejected_intervals','reference_weather','weather_references'])requireValue(Array.isArray(e[k]),'Missing road evidence '+k);
  for(const m of e.segment_marks)requireValue(m.length===7&&[3,4].includes(m[0])&&Number.isInteger(m[2])&&m[2]>=-1&&m[2]<e.road_names.length,'Road evidence mark');
  for(const p of e.passages)requireValue(p.length===8&&Number.isInteger(p[0])&&p[0]>=0&&p[0]<scopes.length&&p[1]>=0&&p[1]<e.road_names.length&&clock(p[3])>clock(p[2])&&p[4]>=2,'Passage candidate contract');
 }
 Object.defineProperty(d,'_timeSeeds',{value:seeds,configurable:true});
 if(d._index)delete d._index;
 return totals;
}
function indexLocal(d){
 if(d._index&&d._index.matchReference===d.matches&&d._index.matchLength===d.matches.length)return d._index;
 const ix=d._timeSeeds||{cells:d.cells.map(c=>minutes(c[1])),starts:d.segments.map(s=>minutes(s[2])),ends:d.segments.map(s=>minutes(s[3])),episodes:d.episodes.map(e=>minutes(e[1]))};
 ix.cellHours=new Map();ix.segmentHours=new Map();ix.onsetHours=new Map();ix.reportingHours=new Map();ix.weatherHours=new Map();ix.qualityHours=new Map();ix.rejectedHours=new Map();ix.passageHours=new Map();ix.referenceHours=new Map();ix.dayCache=new Map();
 const scopeIndex=new Map(d.scopes.map((s,i)=>[s.processing_key,i]));
 function add(map,key,value){if(!map.has(key))map.set(key,[]);map.get(key).push(value);}
 d.cells.forEach((r,i)=>add(ix.cellHours,r[0]+'|'+Math.floor(ix.cells[i]/60),i));
 d.segments.forEach((r,i)=>add(ix.segmentHours,r[0]+'|'+Math.floor(ix.starts[i]/60),i));
 d.episodes.forEach((r,i)=>add(ix.onsetHours,r[0]+'|'+Math.floor(ix.episodes[i]/60),i));
 d.reporting.forEach((r,i)=>add(ix.reportingHours,scopeIndex.get(r.processing_key)+'|'+r.bucket_minutes+'|'+Math.floor(minutes(r.source_local_bucket)/60),i));
 d.matches.forEach((r,i)=>add(ix.weatherHours,scopeIndex.get(r.processing_key)+'|'+r.timezone_hypothesis+'|'+Math.floor(minutes(r.source_local_hour)/60),i));
 if(d.evidence31){const e=d.evidence31;
  e.quality_cells.forEach((r,i)=>add(ix.qualityHours,r[0]+'|'+Math.floor(minutes(r[1])/60),i));
  e.rejected_intervals.forEach((r,i)=>add(ix.rejectedHours,r[0]+'|'+Math.floor(minutes(r[1])/60),i));
  e.passages.forEach((r,i)=>{for(let h=Math.floor(minutes(r[2])/60);h<=Math.floor(minutes(r[3])/60);h++)add(ix.passageHours,r[0]+'|'+h,i);});
  e.reference_weather.forEach((r,i)=>add(ix.referenceHours,r.reference_id+'|'+r.timezone_hypothesis+'|'+Math.floor(minutes(r.source_local_hour)/60),i));
 }
 ix.matchReference=d.matches;ix.matchLength=d.matches.length;Object.defineProperty(d,'_index',{value:ix,configurable:true});
 return d._index;
}
function hourRows(map,prefix,lo,hi){const result=[];for(let h=Math.floor(lo/60);h<Math.ceil(hi/60);h++)result.push(...(map.get(prefix+'|'+h)||[]));return result;}
function privateFrame(d,selection){
 const {scope,start,end,state}=selection,lo=minutes(start),hi=minutes(end);
 requireValue(hi>lo&&hi-lo<=360,'Playback bound: at most six source-clock hours');
 const ix=indexLocal(d),rows=hourRows(ix.cellHours,scope,lo,hi).filter(i=>ix.cells[i]>=lo&&ix.cells[i]<hi).map(i=>d.cells[i]);
 const visible=rows.filter(c=>state==='all'||c[4]===state),cells=new Map();
 for(const c of visible){const k=c[2]+':'+c[3];const v=cells.get(k)||{south:c[2]/200,west:c[3]/200,count:0};v.count+=c[5];cells.set(k,v);}
 const segmentIndices=hourRows(ix.segmentHours,scope,lo,hi).filter(i=>{const s=d.segments[i],m=d.evidence31?.segment_marks[i];return ix.starts[i]>=lo&&ix.ends[i]<=hi&&(state==='all'||s[8]===state)&&(selection.episode==null||s[1]===selection.episode)&&(selection.road==null||m?.[2]===selection.road)&&(selection.tier!=='sequence'||m?.[0]===4);});
 const segments=segmentIndices.map(i=>d.segments[i]),onsets=hourRows(ix.onsetHours,scope,lo,hi).filter(i=>ix.episodes[i]>=lo&&ix.episodes[i]<hi).map(i=>d.episodes[i]);
 return {cells:[...cells.values()],segments,segmentIndices,onsets,totalObservations:rows.reduce((n,c)=>n+c[5],0),selectedObservations:visible.reduce((n,c)=>n+c[5],0),status:rows.length?'RECORDED':'MISSING_TELEMETRY_ACTIVITY_UNKNOWN'};
}
function reportingFrame(d,selection,width){const lo=minutes(selection.start),hi=minutes(selection.end),ix=indexLocal(d);return hourRows(ix.reportingHours,selection.scope+'|'+width,lo,hi).map(i=>d.reporting[i]).filter(r=>minutes(r.source_local_bucket)>=lo&&minutes(r.source_local_bucket)<hi);}
function dayProfile(d,scope,day,state){const ix=indexLocal(d),key=[scope,day,state].join('|');if(ix.dayCache.has(key))return ix.dayCache.get(key);const lo=minutes(day+' 00:00:00'),counts=Array(24).fill(0),recorded=Array(24).fill(false);for(const i of hourRows(ix.cellHours,scope,lo,lo+1440)){const r=d.cells[i],h=Math.floor((ix.cells[i]-lo)/60);recorded[h]=true;if(state==='all'||r[4]===state)counts[h]+=r[5];}const value={counts,recorded};ix.dayCache.set(key,value);return value;}
function evidenceFrame(d,selection){
 const e=d.evidence31;if(!e)return {quality:[],rejected:[],passages:[]};const ix=indexLocal(d),lo=minutes(selection.start),hi=minutes(selection.end);
 const quality=hourRows(ix.qualityHours,selection.scope,lo,hi).map(i=>e.quality_cells[i]).filter(r=>minutes(r[1])>=lo&&minutes(r[1])<hi&&r[4]===selection.quality);
 const rejected=hourRows(ix.rejectedHours,selection.scope,lo,hi).map(i=>e.rejected_intervals[i]).filter(r=>minutes(r[1])>=lo&&minutes(r[1])<hi);
 const passages=[...new Set(hourRows(ix.passageHours,selection.scope,lo,hi))].map(i=>e.passages[i]).filter(p=>minutes(p[2])<hi&&minutes(p[3])>lo&&(selection.road==null||p[1]===selection.road)&&(selection.state==='all'||p[6]===selection.state));
 return{quality,rejected,passages};
}
function boundedSegments(frame,bounds,limit=4000){const visible=frame.segments.map((s,i)=>({s,index:frame.segmentIndices[i]})).filter(({s})=>!bounds||(Math.max(s[4],s[6])>=bounds.west&&Math.min(s[4],s[6])<=bounds.east&&Math.max(s[5],s[7])>=bounds.south&&Math.min(s[5],s[7])<=bounds.north));return{rows:visible.slice(0,limit),visible:visible.length,selected:frame.segments.length,capped:visible.length>limit};}
function publicCells(data,scope){
 // Fixed week + total only: no hour/state filter or export can reveal a finer
 // intersection or subtract overlapping private spatial summaries.
 const key=data.scopes[scope].processing_key;
 return data.cells.filter(c=>c.processing_key===key&&c.observation_count>=20).map(c=>{const [,y,x]=c.spatial_bin.split(':').map(Number);return{south:y/4,west:x/4,count:c.observation_count};});
}
function weatherFrame(d,selection){
 const key=d.scopes[selection.scope].processing_key,lo=minutes(selection.start),hi=minutes(selection.end),facts=new Map();
 for(const i of hourRows(indexLocal(d).weatherHours,selection.scope+'|'+selection.zone,lo,hi)){const m=d.matches[i],h=minutes(m.source_local_hour);if(m.processing_key!==key||m.timezone_hypothesis!==selection.zone||h+60<=lo||h>=hi)continue;
  const k=m.grid_id+'|'+m.source_local_hour;const old=facts.get(k);
  if(old)requireValue(old[selection.variable]===m[selection.variable],'Conflicting weather fact');else facts.set(k,m);
 }
 const byGrid=new Map();for(const m of facts.values()){let g=byGrid.get(m.grid_id);if(!g){g={id:m.grid_id,values:[],hours:0};byGrid.set(m.grid_id,g);}const v=m[selection.variable];if(v!==null&&Number.isFinite(v))g.values.push(v);g.hours++;}
 return [...byGrid.values()].map(g=>({...g,value:g.values.length?g.values.reduce((a,b)=>a+b,0)/g.values.length:null}));
}
function referenceWeatherFrame(d,selection,reference){if(!d.evidence31)return[];const lo=minutes(selection.start),hi=minutes(selection.end);return hourRows(indexLocal(d).referenceHours,reference+'|'+selection.zone,lo,hi).map(i=>d.evidence31.reference_weather[i]);}
const api={minutes,stamp,validateLocal,indexLocal,privateFrame,publicCells,weatherFrame,reportingFrame,dayProfile,evidenceFrame,boundedSegments,referenceWeatherFrame};
if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.WinterOpsGeo=api;
})(typeof globalThis!=='undefined'?globalThis:this);
