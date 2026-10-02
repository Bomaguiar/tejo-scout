'use strict';
const Tejo = (() => {
const regions = ["Lisbon", "Setúbal", "Mafra", "Torres Vedras", "Lourinhã"];
const regionColors = {"Lisbon": "#2d634d", "Setúbal": "#a9c76d", "Mafra": "#bc743d", "Torres Vedras": "#537aa5", "Lourinhã": "#9872a5"};
const seed = (typeof HouseCatalog!=='undefined'?HouseCatalog:require('./house-data.js')).map(p=>({...p,firstSeen:p.firstSeen||null,history:p.history||[],notes:p.notes||'',comps:p.comps||[]}));
const clone = x => JSON.parse(JSON.stringify(x));
function initial(){return {version:1,properties:clone(seed),watch:[],scenarios:{},imports:[],landWatch:[],landNotes:{}};}
function mergeSeed(s){
 const next=clone(s);next.landWatch=next.landWatch||[];next.landNotes=next.landNotes||{};
 for(const p of seed){
  const existing=next.properties.find(x=>x.id===p.id||canonical(x.sourceURL)===canonical(p.sourceURL));
  if(!existing){next.properties.push(clone(p));continue;}
  const latest=existing.history.at(-1)?.at||existing.lastObserved;
  // Availability can change without a price observation, including blocked or removed ads.
  if(p.availabilityCheckedAt&&(!existing.availabilityCheckedAt||Date.parse(p.availabilityCheckedAt)>=Date.parse(existing.availabilityCheckedAt))){
   existing.availability=clone(p.availability);existing.availabilityCheckedAt=p.availabilityCheckedAt;existing.sourceCheck=clone(p.sourceCheck);
  }
  const observed=p.publishedObservedAt;
  if(observed&&(!latest||Date.parse(observed)>Date.parse(latest))){
   const personal={id:existing.id,notes:existing.notes,comps:existing.comps,firstSeen:existing.firstSeen||p.firstSeen};
   const history=[...existing.history,...(p.history||[])].filter((h,i,a)=>a.findIndex(x=>x.at===h.at&&x.price===h.price)===i).sort((a,b)=>Date.parse(a.at)-Date.parse(b.at));
   Object.assign(existing,clone(p),personal,{history});
  }
 }
 return next;
}
function number(v){return v!==''&&v!==null&&v!==undefined&&Number.isFinite(Number(v))?Number(v):null;}
function calculate(s){
 const fields=['purchase','area','renovationRate','contingencyPct','taxes','fees','holding','resaleRate','sellingPct'];
 const missing=fields.filter(k=>number(s[k])===null);
 if(missing.length)return {valid:false,missing,error:'Complete all assumptions to calculate a return.'};
 const n=Object.fromEntries(fields.map(k=>[k,number(s[k])]));
 if(Object.values(n).some(v=>v<0)||n.area<=0||n.sellingPct>=100||n.contingencyPct>100)return {valid:false,missing:[],error:'Use non-negative amounts, area above zero and selling costs below 100%.'};
 const renovation=n.area*n.renovationRate,contingency=renovation*n.contingencyPct/100;
 const invested=n.purchase+renovation+contingency+n.taxes+n.fees+n.holding,arv=n.area*n.resaleRate;
 if(invested<=0)return {valid:false,missing:[],error:'Total investment must be above zero.'};
 const selling=arv*n.sellingPct/100,profit=arv-selling-invested;
 if(![renovation,contingency,invested,arv,selling,profit,profit/invested*100,invested/(1-n.sellingPct/100)].every(Number.isFinite))return {valid:false,missing:[],error:'Amounts are too large to calculate safely.'};
 return {valid:true,renovation,contingency,invested,arv,selling,profit,roi:profit/invested*100,breakEven:invested/(1-n.sellingPct/100)};
}
function defaults(p){return {purchase:p.price,area:p.area,renovationRate:'',contingencyPct:10,taxes:'',fees:'',holding:'',resaleRate:'',sellingPct:5,confirmed:false};}
function safeURL(v){try{const u=new URL(v);return ['https:','http:'].includes(u.protocol)&&!u.username&&!u.password?u.href:null;}catch{return null;}}
function canonical(v){const u=new URL(v);u.hash='';u.search='';return u.href.replace(/\/$/,'');}
function parseCSV(text){
 const rows=[];let row=[],cell='',quoted=false;
 text=text.replace(/^\uFEFF/,'');
 for(let i=0;i<text.length;i++){const c=text[i];if(c==='"'){if(quoted&&text[i+1]==='"'){cell+='"';i++;}else quoted=!quoted;}else if(c===','&&!quoted){row.push(cell);cell='';}else if((c==='\n'||c==='\r')&&!quoted){if(c==='\r'&&text[i+1]==='\n')i++;row.push(cell);if(row.some(x=>x.trim()))rows.push(row);row=[];cell='';}else cell+=c;}
 if(quoted)throw Error('Unclosed quoted CSV field.');row.push(cell);if(row.some(x=>x.trim()))rows.push(row);
 if(rows.length<2)throw Error('CSV needs headers and at least one listing row.');
 const headers=rows.shift().map(x=>x.trim());if(new Set(headers).size!==headers.length)throw Error('Duplicate CSV headers.');
 return rows.map((r,i)=>{if(r.length!==headers.length)throw Error('CSV row '+(i+2)+' has the wrong number of columns.');return Object.fromEntries(headers.map((h,j)=>[h,r[j].trim()]));});
}
function validateRows(rows){
 if(!Array.isArray(rows)||!rows.length||rows.length>5000)throw Error('Import between 1 and 5,000 listings.');
 const ids=new Set();
 return rows.map((r,i)=>{
 const url=safeURL(r.sourceURL),price=number(r.price),area=number(r.area);
 if(!url||!r.title||!regions.includes(r.city)||price===null||price<=0||area===null||area<=0)throw Error('Row '+(i+1)+': title, city (Lisbon, Setúbal, Mafra, Torres Vedras or Lourinhã), positive price/area and valid sourceURL are required.');
 const key=canonical(url);if(ids.has(key))throw Error('Duplicate source URL at row '+(i+1)+'.');ids.add(key);
 let observedAt=r.observedAt;
 if(!observedAt||!Number.isFinite(Date.parse(observedAt))||Date.parse(observedAt)>Date.now()+300000)throw Error('Row '+(i+1)+': a valid, non-future observedAt timestamp is required.');
 observedAt=new Date(observedAt).toISOString();
 const lat=number(r.lat),lon=number(r.lon);
 if((lat!==null||lon!==null)&&(lat===null||lon===null||lat<38||lat>40||lon< -10||lon> -7))throw Error('Row '+(i+1)+': coordinates must both locate the supported Portuguese regions.');
 return {title:String(r.title).slice(0,200),city:r.city,areaName:String(r.areaName||r.city).slice(0,200),sourceURL:url,price,area,type:String(r.type||'Unknown').slice(0,12),observedAt,lat,lon};
 });
}
function importRows(state,input){
 const rows=validateRows(input),next=clone(state),now=new Date().toISOString();let added=0,updated=0,ignored=0;
 for(const r of rows){
 let p=next.properties.find(x=>canonical(x.sourceURL)===canonical(r.sourceURL));
 if(!p){p={id:'import-'+Math.random().toString(36).slice(2,12),...r,firstSeen:now,researchedAt:null,history:[],imageURL:'',imageLabel:'',condition:'Not confirmed',occupancy:'Not confirmed',floor:'Not confirmed',risk:'review',risks:['Imported listing: verify condition, tenure and occupancy with the source.'],notes:'',comps:[]};next.properties.push(p);added++;}
 const last=p.history.at(-1);
 if(last&&Date.parse(r.observedAt)<=Date.parse(last.at)){ignored++;continue;}
 p.history.push({price:r.price,at:r.observedAt,importedAt:now});p.price=r.price;p.area=r.area;p.lastObserved=r.observedAt;updated++;
 }
 next.imports.push({at:now,added,updated,ignored});return {state:next,added,updated,ignored};
}
function drop(p){if(p.history.length<2)return null;const b=p.history.at(-1);let i=p.history.length-2;while(i>=0&&p.history[i].price===b.price)i--;if(i<0)return null;const a=p.history[i],changedAt=p.history[i+1].at;return b.price<a.price?{amount:a.price-b.price,pct:(a.price-b.price)/a.price*100,at:changedAt}:null;}
function benchmark(p){const comps=p.comps||[];if(!comps.length)return null;const values=comps.map(c=>c.price/c.area).sort((a,b)=>a-b);const mid=Math.floor(values.length/2);const rate=values.length%2?values[mid]:(values[mid-1]+values[mid])/2;return {rate,value:rate*p.area,discount:(1-p.price/(rate*p.area))*100,count:values.length};}
function localDay(v){return new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Lisbon',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(v));}
return {seed,regions,regionColors,mergeSeed,clone,initial,calculate,defaults,safeURL,canonical,parseCSV,validateRows,importRows,drop,benchmark,localDay};
})();
if(typeof module!=='undefined')module.exports=Tejo;

