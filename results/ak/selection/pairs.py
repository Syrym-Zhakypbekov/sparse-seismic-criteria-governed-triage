import requests, sys, math, json
net=sys.argv[1]
u=f"https://service.earthscope.org/fdsnws/station/1/query?net={net}&cha=BHZ&starttime=2024-01-01&endtime=2025-07-01&level=channel&format=text"
r=requests.get(u,timeout=120)
st={}
for l in r.text.splitlines()[1:]:
    p=l.split("|")
    if p[4]=="" : continue
    s=p[1]; sr=float(p[14]); start=p[15][:10]; end=p[16][:10]
    if start>"2024-01-01" or (end and end<"2025-07-01"): continue
    st.setdefault(s,(float(p[4]),float(p[5]),sr,p[2],start,end))
def d(a,b):
    la1,lo1,la2,lo2=map(math.radians,(a[0],a[1],b[0],b[1]))
    return 6371*2*math.asin(math.sqrt(math.sin((la2-la1)/2)**2+math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2))
json.dump(st,open(f"{net}_st.json","w"))
print(len(st),"stations full period")
out=[]
for a in st:
    ds=sorted((d(st[a],st[b]),b) for b in st if b!=a)
    near=[x for x in ds if 20<=x[0]<=60]
    if near and ds[0][0]>=15:
        far=[x for x in ds if 200<=x[0]<=600]
        out.append((a,st[a][2],[(round(x[0]),x[1]) for x in ds[:4]],len(far)))
for o in sorted(out): print(o)
