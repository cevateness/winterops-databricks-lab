'use strict';
const assert=require('node:assert/strict'),G=require('../dashboard/geospatial_core.js');
const scope={processing_key:'k',source_file_sha256:'h',source_week_start:'2026-01-05',source_week_end_exclusive:'2026-01-12'};
const d={schema:'winterops-local-geospatial-v3',scopes:[scope],cells:[[0,'2026-01-05 23:59:00',8460,-16600,'plow_only',2,1],[0,'2026-01-06 00:00:00',8460,-16600,'both',3,2]],segments:[],episodes:[],reporting:[],matches:[],grids:{}};
assert.deepEqual(G.validateLocal(d,[scope]),[5]);
assert.equal(G.stamp(G.minutes('2026-01-05 23:59:00')+1),'2026-01-06 00:00:00');
assert.throws(()=>G.minutes('2026-02-30 00:00:00'));assert.throws(()=>G.minutes('2026-01-05T00:00:00Z'));
const s={scope:0,start:'2026-01-05 23:59:00',end:'2026-01-06 00:01:00',state:'all',zone:'UTC',variable:'snowfall_activity_hour_cm'};
assert.equal(G.privateFrame(d,s).selectedObservations,5);
assert.equal(G.privateFrame(d,{...s,state:'both'}).selectedObservations,3);
assert.equal(G.privateFrame(d,{...s,start:'2026-01-06 01:00:00',end:'2026-01-06 02:00:00'}).status,'MISSING_TELEMETRY_ACTIVITY_UNKNOWN');
assert.throws(()=>G.privateFrame(d,{...s,end:'2026-01-07 00:00:00'}));
const pub={scopes:[scope],cells:[{processing_key:'k',spatial_bin:'q25:169:-332',observation_count:19},{processing_key:'k',spatial_bin:'q25:169:-333',observation_count:20}]};
assert.equal(G.publicCells(pub,0).length,1);assert.equal(G.publicCells(pub,0)[0].west,-83.25);
d.matches=[0,1].map(()=>({processing_key:'k',timezone_hypothesis:'UTC',grid_id:'grid',source_local_hour:'2026-01-06 00:00:00',snowfall_activity_hour_cm:1}));
assert.equal(G.weatherFrame(d,s)[0].hours,1);assert.equal(G.weatherFrame(d,s)[0].value,1);
assert.equal(G.weatherFrame(d,{...s,zone:'America/Toronto'}).length,0);
d.matches[1].snowfall_activity_hour_cm=2;assert.throws(()=>G.weatherFrame(d,s));
const duplicate=JSON.parse(JSON.stringify(d));duplicate.cells.push(duplicate.cells[0]);assert.throws(()=>G.validateLocal(duplicate,[scope]));
console.log('Playback, clock arithmetic, missingness, displayed-grain privacy and weather deduplication contracts passed');

const x=JSON.parse(JSON.stringify(d));x.matches=[];x.episodes=[[0,'2026-01-05 23:59:00','2026-01-06 00:01:00',5,120,0,'p',null,null]];
x.segments=[[0,0,'2026-01-05 23:59:45','2026-01-06 00:00:00',-83,42.3,-82.9998,42.3,'plow_only',5,'L/R',2,false],
 [0,0,'2026-01-06 00:00:00','2026-01-06 00:00:15',-82.9998,42.3,-82.9996,42.3,'plow_only',5,'L/R',2,false]];
x.evidence31={schema:'winterops-evidence-v31-private',road_names:['Fixture A','Fixture B'],segment_marks:[[4,'supported',0,0,0,2,1],[3,'ambiguous',-1,-1,null,null,2]],
 passages:[[0,0,'2026-01-05 23:59:30','2026-01-06 00:00:00',2,3,'plow_only',0]],quality_cells:[[0,'2026-01-06 00:00:00',8460,-16600,'stationary',3]],rejected_intervals:[],weather_references:[],reference_weather:[{reference_id:'r',timezone_hypothesis:'UTC',source_local_hour:'2026-01-06 00:00:00'}]};
G.validateLocal(x,[scope]);
const before={...s,end:'2026-01-06 00:00:00'};
assert.equal(G.privateFrame(x,before).segments.length,1); // exact right endpoint included, next interval excluded
assert.equal(G.privateFrame(x,{...s,road:0,tier:'sequence'}).segments.length,1);
assert.equal(G.privateFrame(x,{...s,road:1}).segments.length,0);
assert.equal(G.evidenceFrame(x,{...s,start:'2026-01-06 00:00:00',quality:'stationary'}).passages.length,0); // ending at left bound is past
assert.equal(G.evidenceFrame(x,{...s,quality:'stationary'}).quality[0][5],3);
assert.deepEqual(G.dayProfile(x,0,'2026-01-06','all').recorded.slice(0,2),[true,false]);
assert.deepEqual(G.dayProfile(x,0,'2026-01-06','plow_only').counts.slice(0,2),[0,0]); // recorded other state differs from missing
assert.equal(G.referenceWeatherFrame(x,s,'r').length,1);
const f=G.privateFrame(x,s),bounded=G.boundedSegments(f,null,1);
assert.equal(bounded.rows.length,1);assert.equal(bounded.selected,2);assert.equal(bounded.capped,true);
assert.equal(G.boundedSegments(f,{west:0,east:1,south:0,north:1}).visible,0);
const badMarks=JSON.parse(JSON.stringify(x));badMarks.evidence31.segment_marks.pop();assert.throws(()=>G.validateLocal(badMarks,[scope]));
console.log('Indexed midnight windows, sequence/road filters, missingness, weather references and uncapped metrics passed');
