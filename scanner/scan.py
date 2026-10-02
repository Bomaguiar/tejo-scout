"""Bounded public-page scanner. No AI, API keys, browser login or proxy required."""
from __future__ import annotations
import argparse, concurrent.futures, hashlib, json, math, os, re, socket, time, unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib import request, error, parse, robotparser
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = 'TejoScout/1.0 (+https://bomaguiar.github.io/tejo-scout/; public listing monitor)'
HOUSE_CITIES = ['Lisbon', 'Setúbal', 'Mafra', 'Torres Vedras', 'Lourinhã']
DISTRICTS = {
    'Lisbon': ['Lisbon','Amadora','Odivelas','Loures','Oeiras','Cascais','Sintra','Mafra','Torres Vedras','Lourinhã','Alenquer','Arruda dos Vinhos','Azambuja','Cadaval','Sobral de Monte Agraço','Vila Franca de Xira'],
    'Setúbal': ['Setúbal','Almada','Seixal','Barreiro','Moita','Montijo','Alcochete','Palmela','Sesimbra','Grândola','Santiago do Cacém','Sines','Alcácer do Sal']}
ALIASES = {'lisboa':'Lisbon','ericeira':'Mafra','milharado':'Mafra','carvoeira':'Mafra','santo isidoro':'Mafra','santa cruz':'Torres Vedras','a dos cunhados':'Torres Vedras','sao pedro da cadeira':'Torres Vedras','ribamar':'Lourinhã','atalaia':'Lourinhã','melides':'Grândola','carvalhal':'Grândola','troia':'Grândola','porto covo':'Sines','meco':'Sesimbra','caparica':'Almada'}

def fold(s):
    return ''.join(c for c in unicodedata.normalize('NFD', str(s)) if not unicodedata.combining(c)).lower()

def canonical(url):
    p = parse.urlsplit(url)
    if p.scheme != 'https' or not p.hostname or p.username or p.password:
        raise ValueError('Only public HTTPS listing URLs are supported')
    if p.hostname == 'localhost' or re.match(r'^(127\.|10\.|192\.168\.|169\.254\.|172\.(1[6-9]|2\d|3[01])\.)', p.hostname):
        raise ValueError('Private host rejected')
    return parse.urlunsplit((p.scheme, p.netloc.lower(), p.path.rstrip('/'), '', ''))

def number(s):
    if isinstance(s, (float, int)):
        return float(s) if math.isfinite(s) else None
    s = re.sub(r'[^\d.,]', '', str(s or ''))
    if not s: return None
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    elif re.fullmatch(r'\d{1,3}(?:\.\d{3})+', s):
        s = s.replace('.', '')
    try: return float(s)
    except ValueError: return None

def js(name, value):
    data = json.dumps(value, ensure_ascii=False, indent=2).replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    return "'use strict';\nconst " + name + ' = ' + data + ";\nif(typeof module!=='undefined')module.exports=" + name + ';\n'

def atomic(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(text, encoding='utf-8'); tmp.replace(path)

class Fetcher:
    """One instance per host; sequential, cached requests respect robots and delays."""
    def __init__(self, base, delay=1.2):
        self.base = base; self.host = parse.urlsplit(base).hostname
        self.delay = delay; self.last = 0; self.cache = {}; self.robot = None; self.robot_error = None
        try:
            body = self.raw(base.rstrip('/') + '/robots.txt')
            self.robot = robotparser.RobotFileParser(); self.robot.parse(body.splitlines())
            self.delay = max(delay, self.robot.crawl_delay('TejoScout') or self.robot.crawl_delay('*') or 0)
        except error.HTTPError as e:
            if e.code == 404: self.robot = robotparser.RobotFileParser(); self.robot.parse([])
            else: self.robot_error = 'robots HTTP ' + str(e.code)
        except Exception as e: self.robot_error = 'robots unavailable: ' + str(e)[:150]

    def raw(self, url):
        if parse.urlsplit(url).hostname != self.host: raise ValueError('Cross-host fetch refused')
        time.sleep(max(0, self.delay - (time.monotonic() - self.last))); self.last = time.monotonic()
        req = request.Request(url, headers={'User-Agent':USER_AGENT,'Accept':'text/html,application/xml;q=0.9'})
        with request.urlopen(req, timeout=18) as r:
            if parse.urlsplit(r.url).hostname != self.host: raise ValueError('Cross-host redirect refused')
            body = r.read(3_000_001)
            if len(body)>3_000_000: raise ValueError('Page exceeds 3 MB limit')
            # Honor HTTP/meta encoding: several Portuguese agency sites use ISO-8859-1.
            charset = r.headers.get_content_charset()
            if not charset:
                m = re.search(br'charset\s*=\s*["\']?([a-zA-Z0-9_-]+)', body[:10000])
                charset = m[1].decode('ascii') if m else 'utf-8'
            return body.decode(charset, errors='replace')

    def get(self, url):
        if url in self.cache: return self.cache[url]
        try:
            canonical(url)
            if self.robot_error: raise ValueError(self.robot_error)
            if not self.robot.can_fetch('TejoScout', url): raise ValueError('Disallowed by robots.txt')
            body = self.raw(url)
            title = BeautifulSoup(body[:40000], 'html.parser').title if '<html' in body[:10000].lower() else None
            title = fold(title.get_text() if title else '')
            if any(x in title for x in ['just a moment','access denied','captcha','attention required']):
                raise ValueError('Access challenge; no bypass attempted')
            result = {'ok':True,'body':body}
        except Exception as e: result = {'ok':False,'error':str(e)[:200]}
        self.cache[url] = result; return result

def nodes(soup):
    result = []
    def walk(v):
        if isinstance(v, dict):
            result.append(v)
            for c in v.values(): walk(c)
        elif isinstance(v, list):
            for c in v: walk(c)
    for tag in soup.find_all('script', type='application/ld+json'):
        raw = tag.string or tag.get_text()
        try: data = json.loads(raw)
        except json.JSONDecodeError:
            # Nestenn publishes two comma-separated JSON objects without an array.
            try: data = json.loads('[' + raw.strip().strip(',') + ']')
            except json.JSONDecodeError: continue
        walk(data)
    return result

def location(text):
    text = fold(text)
    # Municipality evidence only; description distances must never become location.
    for district, cities in DISTRICTS.items():
        for city in sorted(cities, key=len, reverse=True):
            if re.search(r'(?<!\w)' + re.escape(fold(city)) + r'(?!\w)', text): return city, district
    for alias, city in ALIASES.items():
        if re.search(r'(?<!\w)' + alias + r'(?!\w)', text):
            return city, next(d for d,c in DISTRICTS.items() if city in c)
    return None, None

def extract(body, url, adapter='schema', known=None):
    soup = BeautifulSoup(body, 'html.parser'); graph = nodes(soup)
    primary = next((n for n in graph if n.get('@type') in ['RealEstateListing','House','Apartment','Product','Residence'] and (n.get('name') or n.get('description'))), {})
    entity_url = primary.get('url')
    if entity_url and isinstance(entity_url,str) and entity_url.startswith('https://') and canonical(entity_url)!=canonical(url):
        raise ValueError('Structured listing URL does not match requested advert')
    h1 = soup.find('h1'); title = (h1.get_text(' ',strip=True) if h1 else primary.get('name')) or (soup.title.get_text(' ',strip=True) if soup.title else '')
    desc = primary.get('description') or ''
    if not desc:
        meta = soup.find('meta',attrs={'property':'og:description'}) or soup.find('meta',attrs={'name':'description'})
        desc = meta.get('content','') if meta else ''
    if adapter=='imomelides':
        heading=soup.select_one('h2.text-primary')
        if heading:
            title=heading.get_text(' ',strip=True)
            desc=heading.parent.get_text(' ',strip=True)
    desc = BeautifulSoup(str(desc).replace('\\r\\n',' '), 'html.parser').get_text(' ',strip=True)
    offer = primary.get('offers') or next((n for n in graph if n.get('@type')=='Offer'), {})
    if isinstance(offer,list): offer = offer[0] if len(offer)==1 else {}
    if not isinstance(offer,dict): offer={}
    if offer.get('priceCurrency','EUR')!='EUR': raise ValueError('Non-EUR price')
    price = number(offer.get('price'))
    if price is None:
        tag = soup.find(attrs={'itemprop':'price'})
        if tag: price=number(tag.get('content') or tag.get_text(' ',strip=True))
    if price is None and adapter=='nestenn':
        # Main property price, excluding similar-listing .price cards.
        tag=soup.select_one('.widthFC.no_mb'); price=number(tag.get_text(' ',strip=True)) if tag else None
    if price is None and adapter=='imomelides':
        tag=soup.select_one('.col-auto.price');price=number(tag.get_text(' ',strip=True)) if tag else None
    if price is None and 'idealista.pt' in url:
        text=soup.get_text(' ',strip=True); m=re.search(r'Preço do imóvel:\s*([\d.,\s]+)\s*€',text)
        price=number(m[1]) if m else None
    if price is None or not 1000<=price<=100_000_000: raise ValueError('Unambiguous asking price missing')
    action = fold(str(offer.get('businessFunction',''))+' '+title+' '+url)
    if any(x in action for x in ['/rent','arrend','alquilar','/lease']): raise ValueError('Rental excluded')
    kind = 'land' if re.search(r'\b(terreno|lote|land|plot)\b',fold(title)) else 'house'
    loc = json.dumps(primary.get('address',{}),ensure_ascii=False)+' '+title+' '+parse.unquote(parse.urlsplit(url).path)
    breadcrumbs=[n.get('name','') for n in graph if n.get('@type')=='ListItem']; loc+=' '+' '.join(breadcrumbs)
    city,district = location(loc)
    if known: city=known.get('city') or known.get('municipality'); district=known.get('district') or next((d for d,c in DISTRICTS.items() if city in c),None);kind='land' if 'municipality' in known else 'house'
    if not city: raise ValueError('Municipality not established from title/address/URL')
    if kind=='house' and city not in HOUSE_CITIES: raise ValueError('Outside house-search municipalities')
    # Use explicit floorSize for homes, never landSize or the first m² in page navigation.
    size=primary.get('floorSize',{}) if kind=='house' else primary.get('landSize',{})
    area=number(size.get('value')) if isinstance(size,dict) else number(size)
    if adapter=='imomelides':
        tag=soup.find(attrs={'title':'surface land' if kind=='land' else 'surface house'})
        if tag:area=number(tag.get_text(' ',strip=True).replace('m2',''))
    text=fold(title+' '+desc)
    if area is None:
        patterns=[r'(?:area (?:bruta|de construcao)|floor area)\s*(?:de|:)?\s*([\d.,\s]+)\s*m[²2]'] if kind=='house' else [r'(?:terreno(?: urbano| rustico)? (?:com|de)|lote (?:com|de)|area (?:do terreno|total))\s*(?:de|:)?\s*([\d.,\s]+)\s*m[²2]',r'\bterreno(?: urbano| rustico)?\s+([\d.,\s]+)\s*m[²2]']
        for pattern in patterns:
            m=re.search(pattern,text)
            if m: area=number(m[1]);break
    if known and area is None: area=known['area']
    if area is None or not 1<=area<=20_000_000: raise ValueError('Explicit floor/plot area missing')
    view=None
    if kind=='land':
        if re.search(r'(sem|nao tem|nao possui)\s+vista\s+(?:de |para o )?mar',text): raise ValueError('Sea view explicitly denied')
        m=re.search(r'(?:vista[s]?\s+(?:(?:parcial|panoramica|distante)\s+)?(?:para\s+o\s+|sobre\s+o\s+|ao\s+|de\s+)?(?:mar|oceano)|(?:partial\s+)?sea\s+view|ocean\s+view)',text)
        if not m and not known: raise ValueError('No explicit sea-view evidence (beach proximity is insufficient)')
        if m and re.search(r'(futur|apos construir|potencial vista|podera.*vista)',text): raise ValueError('Projected-only view requires review')
        view=known.get('view') if known and not m else 'Ocean view'
        if m:
            nearby=text[max(0,m.start()-50):m.end()+50]
            if 'parcial' in nearby or 'partial' in nearby:view='Partial'
            elif 'horizonte' in nearby or 'distant' in nearby:view='Distant / horizon'
            elif 'panoram' in nearby:view='Panoramic'
    elif not known and not re.search(r'recuper|reabilit|remodela|ruina|restaur|renovat',text):
        raise ValueError('No renovation evidence in the listing description')
    planning='Potential advertised'
    if re.search(r'nao urbanizavel|nao construt|rustico|agricol',text): planning='Rural / non-buildable'
    if re.search(r'(projeto|projecto|pip|licenca).{0,30}aprova',text): planning='Approval advertised'
    ref=re.search(r'(?:#ref:|ref(?:erencia)?[.ªº\s:]*)\s*([a-z0-9]+[-/][a-z0-9-]+|[a-z]+\d+[a-z0-9]*|\d{3,}[a-z]+|\d{3,})',text)
    return {'title':title[:200],'price':price,'area':area,'kind':kind,'municipality':city,'district':district,'view':view,'planning':planning,'description':desc[:3000],'reference':ref[1].upper() if ref else None,'sourceURL':canonical(url),'method':'public-page / '+adapter,'contentHash':hashlib.sha256(body.encode()).hexdigest()}

def discover(fetch, config, cursor, limit):
    urls=set(); errors=[]; pattern=re.compile(config['detailPattern'])
    def include(url):
        if parse.urlsplit(url).hostname==fetch.host and pattern.fullmatch(parse.urlsplit(url).path.rstrip('/')):urls.add(canonical(url))
    maps=[parse.urljoin(config['base'],p) for p in config.get('sitemaps',[])]
    for url in maps[:2]:
        r=fetch.get(url)
        if not r['ok']:errors.append({'url':url,'error':r['error']});continue
        try:
            root=ET.fromstring(r['body'])
            for node in root.findall('.//{*}loc'):
                if node.text:include(node.text.strip())
        except ET.ParseError:errors.append({'url':url,'error':'Invalid sitemap'})
    for p in config.get('entrypoints',[])[:5]:
        url=parse.urljoin(config['base'],p);r=fetch.get(url)
        if not r['ok']:errors.append({'url':url,'error':r['error']});continue
        soup=BeautifulSoup(r['body'],'html.parser')
        for a in soup.find_all('a',href=True):include(parse.urljoin(url,a['href']))
    # Prioritize explicit renovation/sea-view slugs, rotate the rest to avoid starvation.
    # Sea-view land and renovation slugs first; ordinary new homes don't consume the budget.
    def priority(u):
        slug=fold(parse.unquote(u))
        if any(x in slug for x in ['recuper','ruina','reabilit']):return 0
        if ('terreno' in slug or 'lote' in slug) and 'vista' in slug:return 1
        if 'terreno' in slug or 'lote' in slug:return 2
        return 3
    ordered=sorted((u for u in urls if priority(u)<3),key=lambda u:(priority(u),u))
    count=len(ordered)
    selected=[ordered[(cursor+i)%count] for i in range(min(limit,count))] if count else []
    return selected,(cursor+len(selected))%count if count else 0,count,errors

def new_record(obs, at):
    prefix='land-' if obs['kind']=='land' else 'agency-'
    id=prefix+hashlib.sha256(obs['sourceURL'].encode()).hexdigest()[:14]
    common={'id':id,'title':obs['title'],'price':obs['price'],'area':obs['area'],'sourceURL':obs['sourceURL'],'firstSeen':at,'lastObserved':at,'researchedAt':at[:10],'reference':obs['reference'],'history':[{'price':obs['price'],'at':at,'method':obs['method']}],'notes':'','imageURL':'','imageLabel':''}
    if obs['kind']=='land':return {**common,'municipality':obs['municipality'],'district':obs['district'],'view':obs['view'],'planning':obs['planning'],'evidence':'Advertiser explicitly describes a sea view; actual view not independently verified.','note':'Planning and permitted uses are advertiser claims. Obtain municipal documentation. '+('Agency reference: '+obs['reference']+'. ' if obs['reference'] else '')+'Source description: '+obs['description'][:650]}
    return {**common,'city':obs['municipality'],'areaName':obs['municipality'],'type':'Unknown','floor':'Not confirmed','condition':'Renovation advertised','occupancy':'Not confirmed','risk':'review','risks':['Renovation claim from agency description: confirm scope, gross floor area, title and occupancy.','Agency floorSize is unverified and can include multiple buildings; obtain a measured allocation.','No ROI or resale estimate is assumed.'],'comps':[],'lat':None,'lon':None}

def match_duplicate(obs, rows):
    for p in rows:
        if canonical(p['sourceURL'])==obs['sourceURL']:return p,'same source URL'
        text=fold(str(p.get('reference',''))+' '+p.get('note','')+' '+p.get('evidence',''))
        if obs['reference'] and re.search(r'(?<!\w)'+re.escape(fold(obs['reference']))+r'(?!\w)',text):
            city=p.get('city') or p.get('municipality')
            if city==obs['municipality'] and abs(p['area']-obs['area'])<1:return p,'matching agency reference and area'
    return None,None

def validate_catalog(catalog):
    ids=set();urls=set()
    for group in ['houses','land']:
        for p in catalog[group]:
            url=canonical(p['sourceURL'])
            if p['id'] in ids or url in urls:raise ValueError('Duplicate listing ID/URL')
            ids.add(p['id']);urls.add(url)
            if not isinstance(p['price'],(int,float)) or not math.isfinite(p['price']) or p['price']<=0:raise ValueError('Invalid price')
            if not isinstance(p['area'],(int,float)) or not math.isfinite(p['area']) or p['area']<=0:raise ValueError('Invalid area')
            if group=='houses' and p['city'] not in HOUSE_CITIES:raise ValueError('Invalid house location')
            if group=='land' and p['municipality'] not in DISTRICTS[p['district']]:raise ValueError('Invalid land location')
            for h in p.get('history',[]):
                if h['price']<=0:raise ValueError('Invalid history')
                datetime.fromisoformat(h['at'].replace('Z','+00:00'))

def publish(catalog, report, state):
    validate_catalog(catalog)
    catalog['updatedAt']=report['checkedAt'];report['catalogUpdatedAt']=report['checkedAt']
    atomic(ROOT/'catalog.json',json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    atomic(ROOT/'house-data.js',js('HouseCatalog',catalog['houses']))
    atomic(ROOT/'land-data.js',js('LandCatalog',catalog['land']))
    atomic(ROOT/'refresh-report.json',json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    atomic(ROOT/'refresh-status.js',js('RefreshStatus',report))
    atomic(ROOT/'scanner/state.json',json.dumps(state,indent=2)+'\n')
    atomic(ROOT/'research'/('scan-'+report['checkedAt'][:10]+'.json'),json.dumps(report,ensure_ascii=False,indent=2)+'\n')

def scan(limit_override=None):
    at=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
    catalog=json.loads((ROOT/'catalog.json').read_text(encoding='utf-8'))
    config=json.loads((ROOT/'scanner/sources.json').read_text(encoding='utf-8'))
    previous=json.loads((ROOT/'refresh-report.json').read_text(encoding='utf-8'))
    state=json.loads((ROOT/'scanner/state.json').read_text()) if (ROOT/'scanner/state.json').exists() else {'cursors':{}}
    rows=catalog['houses']+catalog['land'];hosts={parse.urlsplit(p['sourceURL']).hostname for p in rows}
    settings={parse.urlsplit(s['base']).hostname:s for s in config['sources']};hosts.update(settings)
    def work(host):
        cfg=settings.get(host);fetch=Fetcher(cfg['base'] if cfg else 'https://'+host)
        results=[];discoveries=[];stats={'name':cfg['name'] if cfg else host,'host':host,'existing':0,'fetched':0,'errors':0,'discoveredURLs':0,'detailCandidates':0,'discoveryErrors':[]}
        for p in [p for p in rows if parse.urlsplit(p['sourceURL']).hostname==host]:
            stats['existing']+=1;r=fetch.get(p['sourceURL']);entry={'id':p['id'],'sourceURL':p['sourceURL'],'checkedAt':at}
            if not r['ok']:entry.update(status='unavailable',error=r['error']);stats['errors']+=1
            else:
                try:obs=extract(r['body'],p['sourceURL'],cfg['adapter'] if cfg else 'schema',p);entry.update(status='observed',observation=obs);stats['fetched']+=1
                except ValueError as e:entry.update(status='needs-review',error=str(e));stats['errors']+=1
            results.append(entry)
        cursor=state['cursors'].get(host,0)
        if cfg:
            candidates,cursor,count,errors=discover(fetch,cfg,cursor,limit_override or config['dailyDetailLimitPerAgency']);stats.update(discoveredURLs=count,detailCandidates=len(candidates),discoveryErrors=errors)
            for url in candidates:
                if any(canonical(p['sourceURL'])==url for p in rows):continue
                r=fetch.get(url);entry={'sourceURL':url,'checkedAt':at,'agency':cfg['name']}
                if not r['ok']:entry.update(status='unavailable',error=r['error'])
                else:
                    try:entry.update(status='candidate',observation=extract(r['body'],url,cfg['adapter']))
                    except ValueError as e:entry.update(status='rejected',reason=str(e))
                discoveries.append(entry)
        return results,discoveries,stats,cursor
    results=[];discovery=[];agencies=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures={pool.submit(work,host):host for host in sorted(hosts)}
        for future in concurrent.futures.as_completed(futures):
            host=futures[future]
            try:
                r,d,s,c=future.result();results+=r;discovery+=d;agencies.append(s);state['cursors'][host]=c
                print(json.dumps({'host':host,'observed':s['fetched'],'errors':s['errors'],'discovered':s['discoveredURLs']},ensure_ascii=True),flush=True)
            except Exception as e:raise RuntimeError('Source worker failed for '+host) from e
    updated=0;changes=[];added=0
    for entry in results:
        p=next(p for p in rows if p['id']==entry['id']);p['sourceCheck']={k:v for k,v in entry.items() if k!='observation'}
        if entry['status']!='observed':continue
        obs=entry['observation'];old=p['price']
        p.setdefault('history',[]).append({'price':obs['price'],'at':at,'method':obs['method'],'contentHash':obs['contentHash']})
        p['lastObserved']=at;p['price']=obs['price'];p['publishedObservedAt']=at;updated+=1
        if old!=p['price']:changes.append({'id':p['id'],'from':old,'to':p['price'],'sourceURL':p['sourceURL'],'observedAt':at})
    for entry in discovery:
        if entry['status']!='candidate':continue
        obs=entry['observation'];existing,reason=match_duplicate(obs,rows)
        if existing:
            entry.update(status='duplicate',matches=existing['id'],reason=reason)
            existing.setdefault('alternateSources',[])
            if obs['sourceURL']!=canonical(existing['sourceURL']) and obs['sourceURL'] not in existing['alternateSources']:existing['alternateSources'].append(obs['sourceURL'])
            continue
        # Flag weak cross-site duplicates for review instead of counting them twice.
        possible=next((p for p in rows if (p.get('city') or p.get('municipality'))==obs['municipality'] and p['price']==obs['price'] and abs(p['area']-obs['area'])<1),None)
        if possible:entry.update(status='needs-review',reason='Possible cross-site duplicate',matches=possible['id']);continue
        p=new_record(obs,at);p['sourceCheck']={'checkedAt':at,'status':'observed','sourceURL':obs['sourceURL']};p['publishedObservedAt']=at
        catalog['land' if obs['kind']=='land' else 'houses'].append(p);rows.append(p);entry.update(status='added',id=p['id']);added+=1
    observed=sum(x['status']=='observed' for x in results)
    report={'schemaVersion':2,'checkedAt':at,'mode':'github-actions' if os.getenv('GITHUB_ACTIONS') else 'local-scanner','schedule':'Daily at 08:17 Europe/Lisbon','existingAttempted':len(results),'directlyObserved':observed,'unavailable':sum(x['status']=='unavailable' for x in results),'needsReview':sum(x['status']=='needs-review' for x in results),'newListings':added,'priceChanges':changes,'lastSuccessfulScan':at if observed or added else previous.get('lastSuccessfulScan'),'lastSuccessfulContentUpdate':at if added or changes else previous.get('lastSuccessfulContentUpdate',previous['checkedAt']),'coverage':'Bounded public agency pages and sitemaps; incomplete coverage. Failed/blocked pages retain last good data. Advertised availability, sea views and permissions are not independently verified.','records':sorted(results,key=lambda x:x['id']),'discovery':sorted(discovery,key=lambda x:x['sourceURL']),'sources':sorted(agencies,key=lambda x:x['host']),'runURL':'https://github.com/'+os.getenv('GITHUB_REPOSITORY','Bomaguiar/tejo-scout')+'/actions/runs/'+os.getenv('GITHUB_RUN_ID','')}
    publish(catalog,report,state)
    summary=f'Scan complete: {observed}/{len(results)} existing ads directly observed; {added} added; {len(changes)} price changes; {report["unavailable"]} unavailable; {report["needsReview"]} need review.'
    print(summary)
    if os.getenv('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:f.write(summary+'\n\n'+report['coverage']+'\n')
    if not observed and not added:raise SystemExit('No usable observations; status published but scan marked failed.')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--render-only',action='store_true');parser.add_argument('--limit',type=int);args=parser.parse_args()
    if args.render_only:
        c=json.loads((ROOT/'catalog.json').read_text(encoding='utf-8'));validate_catalog(c)
        atomic(ROOT/'house-data.js',js('HouseCatalog',c['houses']));atomic(ROOT/'land-data.js',js('LandCatalog',c['land']))
    else:scan(args.limit)
