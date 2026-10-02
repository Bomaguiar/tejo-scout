'use strict';
// Refresh public data only; private state stays in this browser.
let syncBusy=false,lastSyncAttempt=0;
async function syncPublishedData(){
 if(syncBusy||Date.now()-lastSyncAttempt<60000||location.protocol==='file:')return;
 // Defer while a user is editing an assumption, note, filter or comparable.
 if(document.activeElement?.matches('input,textarea,select')||route==='analyzer')return;
 syncBusy=true;lastSyncAttempt=Date.now();
 try{
  const [cr,rr]=await Promise.all([fetch('catalog.json',{cache:'no-store'}),fetch('refresh-report.json',{cache:'no-store'})]);
  if(!cr.ok||!rr.ok)throw Error('Published data unavailable');
  const [catalog,report]=await Promise.all([cr.json(),rr.json()]);
  if(report.checkedAt===RefreshStatus.checkedAt)return;
  if(!report.catalogUpdatedAt||catalog.updatedAt!==report.catalogUpdatedAt)throw Error('Deployment still propagating');
  if(catalog.schemaVersion!==1||!Array.isArray(catalog.houses)||!Array.isArray(catalog.land)||catalog.land.length>5000||!Array.isArray(report.records)||!Number.isFinite(Date.parse(report.checkedAt)))throw Error('Invalid published catalogue');
  validateBackup({...Tejo.initial(),properties:catalog.houses,watch:[],scenarios:{}});
  const ids=new Set();for(const p of catalog.land){if(!p.id.startsWith('land-')||ids.has(p.id)||!Tejo.safeURL(p.sourceURL)||!Number.isFinite(p.price)||p.price<=0||!Number.isFinite(p.area)||p.area<=0||!['Lisbon','Setúbal'].includes(p.district)||![p.title,p.note,p.evidence,p.view,p.planning,p.municipality].every(x=>typeof x==='string'))throw Error('Invalid published land');ids.add(p.id);}
  Tejo.seed.splice(0,Tejo.seed.length,...catalog.houses);
  LandCatalog.splice(0,LandCatalog.length,...catalog.land);
  Object.keys(RefreshStatus).forEach(k=>delete RefreshStatus[k]);Object.assign(RefreshStatus,report);
  state=Tejo.mergeSeed(state);persist();render();toast('Published listings updated. Your saved workspace is preserved.');
 }catch(e){console.info('Public data refresh deferred:',e.message);}
 finally{syncBusy=false;}
}
window.addEventListener('load',()=>{setTimeout(syncPublishedData,1500);setInterval(syncPublishedData,300000);});
window.addEventListener('focus',syncPublishedData);
