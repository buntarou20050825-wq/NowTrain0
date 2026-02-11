import json
import urllib.request

lines = [
    "yamanote",
    "chuo_rapid",
    "keihin_tohoku",
    "sobu_local",
    "yokohama",
    "saikyo",
    "nambu",
    "joban",
    "joban_rapid",
    "joban_local",
    "keiyo",
    "musashino",
    "sobu_rapid",
    "tokaido",
    "yokosuka",
    "takasaki",
    "utsunomiya",
    "shonan_shinjuku",
]

names = {
    "yamanote": "山手線",
    "chuo_rapid": "中央線快速",
    "keihin_tohoku": "京浜東北線",
    "sobu_local": "総武線各駅",
    "yokohama": "横浜線",
    "saikyo": "埼京線",
    "nambu": "南武線",
    "joban": "常磐線",
    "joban_rapid": "常磐線快速",
    "joban_local": "常磐線各駅",
    "keiyo": "京葉線",
    "musashino": "武蔵野線",
    "sobu_rapid": "総武快速線",
    "tokaido": "東海道線",
    "yokosuka": "横須賀線",
    "takasaki": "高崎線",
    "utsunomiya": "宇都宮線",
    "shonan_shinjuku": "湘南新宿",
}

print(f"{'Line ID':>20s}  {'Name':>10s}  {'Trains':>6s}  {'Source':>10s}")
print("-" * 55)

total = 0
for lid in lines:
    try:
        url = f"http://localhost:8000/api/trains/{lid}/positions/v4"
        r = urllib.request.urlopen(url, timeout=10)
        d = json.loads(r.read())
        n = d.get("total_trains", 0)
        src = d.get("source", "?")
        total += n
        print(f"{lid:>20s}  {names[lid]:>10s}  {n:>6d}  {src:>10s}")
    except Exception as e:
        print(f"{lid:>20s}  {names[lid]:>10s}  ERROR: {e}")

print("-" * 55)
print(f"{'TOTAL':>20s}  {'':>10s}  {total:>6d}")
