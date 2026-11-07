/* Offline compute profile. Does not print positions, IDs or private rows. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),z=require('node:zlib'),G=require('../dashboard/geospatial_core.js');
const input=path.resolve(process.argv[2]||'');
for(let p=path.dirname(input);;p=path.dirname(p)){if(fs.existsSync(path.join(p,'.git')))throw Error('Private input must be outside every Git tree');if(path.dirname(p)===p)break;}
const tick=()=>performance.now();let t=tick();const bytes=fs.readFileSync(input),raw=z.gunzipSync(bytes),decompress=tick()-t;t=tick();const d=JSON.parse(raw),parse=tick()-t;t=tick();G.validateLocal(d,d.scopes);const validation=tick()-t;
const selection={scope:1,start:'2026-01-15 00:00:00',end:'2026-01-15 01:00:00',state:'all',episode:null,quality:'stationary'};
t=tick();G.privateFrame(d,selection);const first=tick()-t,times=[];
for(let hour=1;hour<24;hour++){const start='2026-01-15 '+String(hour).padStart(2,'0')+':00:00',s={...selection,start,end:G.stamp(G.minutes(start)+60)};t=tick();G.privateFrame(d,s);G.dayProfile(d,1,'2026-01-15','all');G.evidenceFrame(d,s);G.weatherFrame(d,{...s,zone:'America/Toronto',variable:'temperature_2m_c'});times.push(tick()-t);}
console.log(JSON.stringify({evidence:'ACTUAL_PRIVATE_PAYLOAD_COMPUTE_ONLY_NOT_BROWSER_PAINT',node:process.version,input_bytes:bytes.length,decoded_bytes:raw.length,cells:d.cells.length,segments:d.segments.length,decompress_ms:decompress,parse_ms:parse,validate_ms:validation,first_frame_with_index_ms:first,warm_frames:times.length,warm_frame_min_ms:Math.min(...times),warm_frame_max_ms:Math.max(...times),external_requests:0}));
