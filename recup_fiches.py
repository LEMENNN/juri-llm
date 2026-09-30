"""Télécharge les fiches service-public.fr sur la location (vide et meublée)."""
import json, re, time
from pathlib import Path
import xml.etree.ElementTree as ET
import requests

URL = "https://lecomarquage.service-public.gouv.fr/vdd/3.5/part/xml/{}.xml"
# Dossiers du sous-thème « Bail d'habitation » (thème Logement N19808).
# N31802 (logement social) volontairement exclu.
DOSSIERS = ["N292", "N349", "N337", "N31059", "N19424", "N339"]
# Fiches hors périmètre (location vide/meublée du parc privé uniquement)
HORS_PERIMETRE = {
    "F31290", "F31601", "F1170", "F2559", "F1239", "F282",   # logement social
    "F1219", "F17709", "F10039",                             # loi de 1948
    "F1626", "F1351", "F34825", "F2541", "F31044",           # Anah / conventionné
    "F34759",                                                # bail mobilité
    "F34661", "F2044",                                       # colocation
    "F14747", "F35254", "F14748",                            # parking, squat, micro-logement
}

OUT = Path("data/raw/fiches")
OUT.mkdir(parents=True, exist_ok=True)
session = requests.Session()
session.headers["User-Agent"] = "juri-llm (projet etudiant)"

def telecharger(pub_id):
    r = session.get(URL.format(pub_id), timeout=30)
    r.raise_for_status()
    time.sleep(0.5)  # on reste poli avec le serveur
    return r.content

# 1) Lister les fiches de chaque dossier
fiche_ids = []
for dossier in DOSSIERS:
    root = ET.fromstring(telecharger(dossier))
    exclus = set()
    for bloc in root.iter("VoirAussi"):  # liens « voir aussi » = autres sujets
        exclus |= {e.get("ID") for e in bloc.iter() if e.get("ID")}
    for sd in root.iter("SousDossier"):  # sous-dossiers « logement social »
        if "social" in (sd.findtext("Titre") or "").lower():
            exclus |= {e.get("ID") for e in sd.iter() if e.get("ID")}
    for el in list(root.iter("Fiche")) + list(root.iter("QuestionReponse")):
        fid = el.get("ID")
        if fid and fid.startswith("F") and fid not in exclus and fid not in fiche_ids  and fid not in HORS_PERIMETRE:
            fiche_ids.append(fid)
print(len(fiche_ids), "fiches à télécharger")

# 2) Télécharger chaque fiche + noter les articles de la loi de 1989 qu'elle cite
refs = {}
for fid in fiche_ids:
    try:
        contenu = telecharger(fid)
    except requests.HTTPError as e:
        print("ignorée", fid, e)
        continue
    (OUT / f"{fid}.xml").write_bytes(contenu)
    root = ET.fromstring(contenu)
    for ref in root.iter("Reference"):
        titre = ref.findtext("Titre") or ""   # ex. "Loi n°89-462 ... : article 17-1"
        m = re.search(r"LEGIARTI\d+", ref.get("URL") or "")
        if "89-462" in titre and m:
            refs[m.group()] = {"titre": titre, "url": ref.get("URL")}
    print("ok", fid, root.findtext("{http://purl.org/dc/elements/1.1/}title"))

Path("data/refs_loi1989.json").write_text(
    json.dumps(refs, ensure_ascii=False, indent=2), encoding="utf-8")
print(len(refs), "articles de la loi de 1989 cités")