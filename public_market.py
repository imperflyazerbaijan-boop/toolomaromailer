"""Keyless World Bank market indicators. No contact data or email discovery."""
import argparse
import json
import math
import os
import time
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

MARKETS = dict(zip(
    ("United States","Australia","Switzerland","Canada","United Kingdom","Germany","Norway","Denmark","Netherlands","Sweden","New Zealand","Finland","Ireland","Austria","Belgium","Luxembourg","France","Singapore","United Arab Emirates","Iceland","Japan","South Korea","Qatar","Kuwait","Saudi Arabia","Israel","Italy","Spain","Taiwan","Bahrain","Portugal","Czechia","Poland","Estonia","Slovenia","Malta","Cyprus","Lithuania","Hong Kong","Greece"),
    ("USA","AUS","CHE","CAN","GBR","DEU","NOR","DNK","NLD","SWE","NZL","FIN","IRL","AUT","BEL","LUX","FRA","SGP","ARE","ISL","JPN","KOR","QAT","KWT","SAU","ISR","ITA","ESP",None,"BHR","PRT","CZE","POL","EST","SVN","MLT","CYP","LTU","HKG","GRC")
))
INDICATORS = {"population":"SP.POP.TOTL","internet_pct":"IT.NET.USER.ZS","gdp_per_capita_usd":"NY.GDP.PCAP.CD"}
ROOT = Path(__file__).resolve().parent

def endpoint(indicator, page=1):
    codes = ";".join(c for c in MARKETS.values() if c)
    year = date.today().year
    query = urlencode({"format":"json","date":f"{year-5}:{year}","per_page":500,"page":page})
    return f"https://api.worldbank.org/v2/country/{codes}/indicator/{indicator}?{query}"

def request(url):
    for attempt in range(3):
        try:
            with urlopen(Request(url,headers={"Accept":"application/json","User-Agent":"ToolomaroMarketResearch/1.0"}),timeout=20) as response:
                body = response.read(4_000_001)
                if len(body)>4_000_000:
                    raise ValueError("Response too large")
            return json.loads(body)
        except HTTPError as exc:
            if exc.code not in (429,500,502,503,504) or attempt==2:
                raise
            if exc.code==429:
                # Defer to the next manual run rather than retry inside rate limit.
                raise
            time.sleep(2**attempt)
        except (URLError,TimeoutError):
            if attempt==2:
                raise
            time.sleep(2**attempt)

def collect(indicator, fetch=request):
    result={}
    page=1
    codes=set(MARKETS.values())-{None}
    while True:
        payload=fetch(endpoint(indicator,page))
        if not isinstance(payload,list) or len(payload)!=2 or not isinstance(payload[0],dict) or not isinstance(payload[1],list):
            raise ValueError("Invalid World Bank response")
        meta,rows=payload
        pages=int(meta.get("pages",0))
        if not 1<=pages<=20 or int(meta.get("page",0))!=page:
            raise ValueError("Invalid pagination metadata")
        for row in rows:
            if not isinstance(row,dict):
                continue
            code=row.get("countryiso3code")
            value=row.get("value")
            year=row.get("date")
            if (code not in codes or type(value) not in (int,float) or not math.isfinite(value) or value<0
                or not isinstance(year,str) or not year.isdigit()):
                continue
            if indicator==INDICATORS["internet_pct"] and value>100:
                continue
            if code not in result or int(year)>result[code]["year"]:
                result[code]={"year":int(year),"value":value}
        if page>=pages:
            return result
        page+=1

def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
        os.replace(tmp,path)
    finally:
        tmp.unlink(missing_ok=True)

def run(cache, fetch=request):
    try:
        data=json.loads(cache.read_text(encoding="utf-8"))
        if not isinstance(data,dict):
            data={}
    except (OSError,ValueError):
        data={}
    failures=[]
    for name,indicator in INDICATORS.items():
        try:
            values=collect(indicator,fetch)
            data[name]={"updated":date.today().isoformat(),"observations":values}
            save(cache,data)
        except (OSError,ValueError,TypeError,OverflowError) as exc:
            failures.append(name)
            print(f"{name}: unavailable ({type(exc).__name__}); retained existing cache")
            if isinstance(exc,HTTPError) and exc.code in (403,429):
                break
    print("Country | Population | Internet users % | GDP/person USD")
    for market,code in MARKETS.items():
        cells=[]
        for metric in INDICATORS:
            item=data.get(metric,{}).get("observations",{}).get(code)
            cells.append(f'{item["value"]:,.1f} ({item["year"]})' if item else "N/A")
        print(f"{market} | "+" | ".join(cells))
    print("World Bank WDI; market context only, not advertising RPM. Cached values may be older.")
    return 1 if failures else 0

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache",type=Path,default=ROOT/"data"/"public_market.json")
    raise SystemExit(run(parser.parse_args().cache))
