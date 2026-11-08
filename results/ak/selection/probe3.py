import requests, sys, datetime as dt, time, json, concurrent.futures as cf
net=sys.argv[1]; T0=dt.date.fromisoformat(sys.argv[2]); T1=dt.date.fromisoformat(sys.argv[3]); stas=sys.argv[4:]
HOUR=int(__import__("os").environ.get("PH","12"))
def one(sta,d):
    s=dt.datetime.combine(d,dt.time(HOUR)); e=s+dt.timedelta(minutes=1)
    u=f"https://service.earthscope.org/fdsnws/dataselect/1/query?net={net}&sta={sta}&cha=BHZ&start={s:%Y-%m-%dT%H:%M:%S}&end={e:%Y-%m-%dT%H:%M:%S}&nodata=404"
    for a in range(6):
        try:
            r=requests.get(u,timeout=60)
            if r.status_code==200: return len(r.content)
            if r.status_code in (204,404): return 0
            if r.status_code==429: time.sleep(30*(a+1)); continue
        except Exception: time.sleep(5)
    return -1
res={}
jobs=[(s,T0+dt.timedelta(i)) for s in stas for i in range(0,(T1-T0).days,3)]
with cf.ThreadPoolExecutor(4) as ex:
    for (s,d),v in zip(jobs, ex.map(lambda j: one(*j), jobs)):
        res.setdefault(s,{})[str(d)]=v
json.dump(res,open(f"probe_{net}_{HOUR}.json","w"))
for s in stas:
    v=res[s]; miss=[d for d,x in v.items() if x==0]; err=[d for d,x in v.items() if x<0]
    runs=[]
    for d in miss:
        dd=dt.date.fromisoformat(d)
        if runs and (dd-runs[-1][1]).days==1: runs[-1][1]=dd
        else: runs.append([dd,dd])
    print(s,"probed",len(v),"empty",len(miss),"err",len(err),"runs",[(str(a),(b-a).days+1) for a,b in runs][:15])
