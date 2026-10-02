'use strict';
const Availability=(()=>{
 const maximumAge=48*60*60*1000;
 function status(p,now=Date.now()){
  const a=p.availability;
  if(a&&['removed','sold','reserved'].includes(a.status))return a.status;
  const at=a?.checkedAt||p.sourceCheck?.checkedAt;
  const observed=a?.status==='advert-live'||(!a&&p.sourceCheck?.status==='observed');
  const age=now-Date.parse(at);
  return observed&&Number.isFinite(age)&&age>=-300000&&age<=maximumAge?'advert-live':'unverified';
 }
 function show(p,mode='current') {const s=status(p);return mode==='all'||s==='advert-live'||(mode==='unverified'&&s==='unverified');}
 const label=p=>({'advert-live':'Advert live · recently checked',unverified:'Availability unverified',removed:'Advert removed / not found',sold:'Advertiser marks sold',reserved:'Advertiser marks reserved'})[status(p)];
 return {status,show,label,maximumAge};
})();
if(typeof module!=='undefined')module.exports=Availability;
