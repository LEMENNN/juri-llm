"""Étape 2 : découpe fiches + articles en morceaux -> data/chunks.jsonl"""
import html, json, re
import xml.etree.ElementTree as ET
from pathlib import Path

DC = "{http://purl.org/dc/elements/1.1/}"          # espace de noms Dublin Core (dc:title)
BLOCS = {"Paragraphe", "Item", "Titre", "Rangée"}  # balises qui finissent une ligne
MAX_MOTS = 350                                      # au-delà, on coupe le morceau en parties
HORS_PERIMETRE = ("social", "coloc")                # situations exclues (cf. étape 0)


def texte_xml(el, ignorer=()):
    """Texte d'un élément XML, avec un retour à la ligne après chaque bloc."""
    morceaux = [el.text or ""]
    for enfant in el:
        if enfant.tag in ignorer:
            continue
        if enfant.tag == "Item":
            morceaux.append("- ")
        morceaux.append(texte_xml(enfant))
        if enfant.tag in BLOCS:
            morceaux.append("\n")
        elif enfant.tag == "Cellule":
            morceaux.append(" | ")
        morceaux.append(enfant.tail or "")
    return "".join(morceaux)


def nettoyer(txt):
    """Espaces multiples -> un espace ; lignes vides supprimées."""
    lignes = (re.sub(r"\s+", " ", l).strip() for l in txt.splitlines())
    return "\n".join(l for l in lignes if l)


def decouper_long(corps):
    """Coupe un texte trop long en parties de ~MAX_MOTS, sans casser les lignes."""
    parties, courante, n = [], [], 0
    for ligne in corps.splitlines():
        if courante and n + len(ligne.split()) > MAX_MOTS:
            parties.append("\n".join(courante))
            courante, n = [], 0
        courante.append(ligne)
        n += len(ligne.split())
    if courante:
        parties.append("\n".join(courante))
    return parties


def morceaux(id_base, titre, url, source, corps):
    """Fabrique 1 ou plusieurs morceaux ; le titre est répété en tête de chaque partie."""
    corps = nettoyer(corps)
    if len(corps.split()) < 15:            # trop court pour être utile
        return []
    parties = decouper_long(corps)
    return [{
        "id": f"{id_base}#{i}" if len(parties) > 1 else id_base,
        "titre": titre,
        "url": url,
        "source": source,
        "texte": f"{titre}\n{p}",          # le titre aide beaucoup la recherche
    } for i, p in enumerate(parties, 1)]


def decouper_fiche(chemin):
    racine = ET.parse(chemin).getroot()
    fid, url = racine.get("ID"), racine.get("spUrl")
    titre_fiche = racine.findtext(f"{DC}title")

    # Le <Texte> principal, puis un <Texte> par situation (« Logement vide », « meublé »…)
    blocs = [("", racine.find("Texte"))]
    for sit in racine.findall("ListeSituations/Situation"):
        nom = " ".join(sit.findtext("Titre", "").split())
        if any(mot in nom.lower() for mot in HORS_PERIMETRE):
            continue
        blocs.append((nom, sit.find("Texte")))

    resultats = []
    for n, (situation, texte) in enumerate(blocs):
        if texte is None:
            continue
        chapitres = texte.findall("Chapitre") or [texte]   # pas de chapitre -> tout le bloc
        for c, chap in enumerate(chapitres):
            titre_chap = texte_xml(chap.find("Titre")) if chap.find("Titre") is not None else ""
            titre = " — ".join(" ".join(t.split()) for t in (titre_fiche, situation, titre_chap) if t.strip())
            corps = texte_xml(chap, ignorer={"Titre"})   # le titre est déjà en tête
            resultats += morceaux(f"{fid}-{n}-{c}", titre, url, "service-public.fr", corps)
    return resultats


def decouper_article(chemin):
    art = json.loads(chemin.read_text(encoding="utf-8"))["article"]
    # texteHtml garde les alinéas (<br/>, <p>) ; on les transforme en retours à la ligne
    brut = re.sub(r"<br\s*/?>|</p>|</div>", "\n", art["texteHtml"])
    corps = html.unescape(re.sub(r"<[^>]+>", "", brut))
    titre = f"Loi n° 89-462 du 6 juillet 1989 — Article {art['num']}"
    url = f"https://www.legifrance.gouv.fr/loda/article_lc/{art['id']}"
    return morceaux(art["id"], titre, url, "Légifrance", corps)


if __name__ == "__main__":
    tous = []
    for f in sorted(Path("data/raw/fiches").glob("*.xml")):
        tous += decouper_fiche(f)
    for f in sorted(Path("data/raw/loi1989").glob("*.json")):
        tous += decouper_article(f)

    with open("data/chunks.jsonl", "w", encoding="utf-8") as sortie:
        for m in tous:
            sortie.write(json.dumps(m, ensure_ascii=False) + "\n")

    tailles = sorted(len(m["texte"].split()) for m in tous)
    print(f"{len(tous)} morceaux | mots : min {tailles[0]}, médiane {tailles[len(tailles)//2]}, max {tailles[-1]}")