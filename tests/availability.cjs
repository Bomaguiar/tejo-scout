const assert=require('node:assert/strict'),A=require('../availability.js'),T=require('../model.js');
const now=Date.now(),p={sourceCheck:{status:'observed',checkedAt:new Date(now).toISOString()}};
assert.equal(A.status(p,now),'advert-live');assert.equal(A.status(p,now+49*3600000),'unverified');
assert.equal(A.show({sourceCheck:{status:'unavailable'}}),false);
assert.equal(A.show({availability:{status:'removed',checkedAt:new Date(now).toISOString()}}),false);
assert.equal(A.show({availability:{status:'sold'}},'unverified'),false);
assert.equal(A.show({availability:{status:'reserved'}},'all'),true);
assert.equal(A.show({sourceCheck:{status:'source-snapshot'}},'current'),false);
const s=T.initial(),source=T.seed[0],saved=JSON.parse(JSON.stringify(source));s.properties[0].notes='My note';s.watch=[source.id];
try{source.availability={status:'removed',checkedAt:new Date(now).toISOString()};source.availabilityCheckedAt=source.availability.checkedAt;source.sourceCheck={status:'removed'};const m=T.mergeSeed(s);assert.equal(m.properties[0].availability.status,'removed');assert.equal(m.properties[0].notes,'My note');assert.deepEqual(m.watch,s.watch);}finally{Object.keys(source).forEach(k=>delete source[k]);Object.assign(source,saved);}
console.log('PASS: blocked/cached/stale/inactive adverts excluded by default; availability-only updates preserve saved records.');
