"""Télécharge le texte des articles de la loi de 1989 cités par les fiches."""
import json, os, time
from pathlib import Path
import requests
from dotenv import load_dotenv
load_dotenv()  

# Secrets lus depuis l'environnement : jamais écrits dans le code ni commités.
TOKEN_URL = "https://oauth.piste.gouv.fr/api/oauth/token"
API = "https://api.piste.gouv.fr/dila/legifrance/lf-engine-app"

r = requests.post(TOKEN_URL, data={
    "grant_type": "client_credentials",
    "client_id": os.environ["PISTE_CLIENT_ID"],
    "client_secret": os.environ["PISTE_CLIENT_SECRET"],
    "scope": "openid"}, timeout=30)
r.raise_for_status()
headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

OUT = Path("data/raw/loi1989")
OUT.mkdir(parents=True, exist_ok=True)
refs = json.loads(Path("data/refs_loi1989.json").read_text(encoding="utf-8"))

def get_article(legiarti):
    r = requests.post(f"{API}/consult/getArticle", json={"id": legiarti},
                      headers=headers, timeout=30)
    r.raise_for_status()
    time.sleep(0.5)
    return r.json()

for legiarti, info in refs.items():
    data = get_article(legiarti)
    art = data["article"]
    if art["etat"] != "VIGUEUR":
        # La fiche cite une ancienne version : on va chercher celle en vigueur
        en_vigueur = [v["id"] for v in art.get("articleVersions") or []
                      if v.get("etat") == "VIGUEUR"]
        if not en_vigueur:
            print("pas de version en vigueur :", info["titre"])
            continue
        data = get_article(en_vigueur[0])
        art = data["article"]
    (OUT / f"{art['id']}.json").write_text(
        json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print(f"article {art['num']} | {legiarti} -> {art['id']} | état : {art['etat']}")