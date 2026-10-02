const assert=require('node:assert/strict'),T=require('../model.js');
const current=T.initial(),first=current.properties[0];
first.notes='Private inspection notes';first.comps=[{price:200000,area:50,url:'https://example.com/comp',date:'2026-10-01'}];
current.watch=[first.id];current.scenarios[first.id]={purchase:first.price,custom:'Keep scenario'};current.landWatch=['land-31415263'];current.landNotes={'land-31415263':'Keep land notes'};
const source=T.seed[0],saved=JSON.parse(JSON.stringify(source));
try{
 source.price=first.price-1000;source.publishedObservedAt='2026-10-03T08:00:00Z';source.history=[{price:source.price,at:source.publishedObservedAt}];
 first.history=[{price:first.price,at:'2026-10-02T08:00:00Z'}];
 const merged=T.mergeSeed(current),p=merged.properties.find(x=>x.id===first.id);
 assert.equal(p.price,source.price);assert.equal(p.notes,first.notes);assert.deepEqual(p.comps,first.comps);
 assert.deepEqual(merged.scenarios,current.scenarios);assert.deepEqual(merged.watch,current.watch);assert.deepEqual(merged.landNotes,current.landNotes);assert.deepEqual(merged.landWatch,current.landWatch);assert.equal(p.history.length,2);
 assert.equal(T.drop(p).amount,1000);assert.equal(T.mergeSeed(merged).properties[0].history.length,2);
 p.price=500000;p.history.push({price:500000,at:'2026-10-04T08:00:00Z'});assert.equal(T.mergeSeed(merged).properties[0].price,500000);
}finally{Object.keys(source).forEach(k=>delete source[k]);Object.assign(source,saved);}
assert.equal(new Set(T.seed.map(x=>x.id)).size,T.seed.length);
console.log('PASS: published price merge, genuine history, newer manual observations and all personal data preserved.');
