import json, os, time
from pathlib import Path
from urllib.request import urlopen
expected=json.loads((Path(__file__).resolve().parents[1]/'refresh-report.json').read_text())
url=os.environ['SITE_URL'].rstrip('/')+'/refresh-report.json'
for attempt in range(6):
    try:
        with urlopen(url+'?checked='+expected['checkedAt'],timeout=15) as response:
            actual=json.load(response)
        if actual['checkedAt']==expected['checkedAt']:
            print('Verified live source report for '+expected['checkedAt']);break
    except Exception as e: print('Waiting for deployed content: '+str(e))
    time.sleep(10)
else: raise SystemExit('Live content does not match this run')
