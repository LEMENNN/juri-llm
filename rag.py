# Étape 4 : question -> recherche dans Chroma -> réponse simple qui cite ses sources
import re
import chromadb
import ollama

EMBED = "bge-m3"
LLM = "qwen3:8b" # usually this : qwen3:4b-instruct-2507-q4_K_M
N_CANDIDATS = 10  # morceaux demandés à Chroma
N_EXTRAITS = 5    # morceaux envoyés au LLM
MAX_PAR_PAGE = 2  # une même fiche ne prend pas plus de 2 places

collection = chromadb.PersistentClient(path="data/chroma").get_collection("logement")

CONSIGNE = """Tu aides des particuliers sur la location d'un logement vide ou meublé du parc privé, en France.
Règles :
- Utilise UNIQUEMENT les extraits fournis, jamais tes propres connaissances.
- Si les extraits ne répondent pas à la question, écris seulement :
  "Je ne sais pas répondre à cette question avec mes sources."
  Si tu peux répondre, n'écris jamais cette phrase.
- Vouvoie la personne. Français simple, phrases courtes, 3 à 6 phrases maximum.
- Termine chaque phrase par le numéro de l'extrait utilisé, ex. [2]. Jamais de numéro seul sur une ligne.
- Si la réponse dépend d'une information que la personne n'a pas donnée (vide ou meublé, zone tendue, surface…),
  donne la règle pour chaque cas au lieu de trancher.
- Les exemples chiffrés des extraits sont des exemples : ne les présente pas comme des règles générales.
- Dans le langage courant, « caution » veut souvent dire « dépôt de garantie ».
- Ignore ce qui concerne le bail mobilité, la colocation et le logement social."""


def rechercher(question):
    """Les extraits les plus proches de la question, 2 max par page source."""
    vecteur = ollama.embed(model=EMBED, input=question)["embeddings"]
    res = collection.query(query_embeddings=vecteur, n_results=N_CANDIDATS)
    extraits, compte = [], {}
    for texte, meta in zip(res["documents"][0], res["metadatas"][0]):
        url = meta["url"]
        if compte.get(url, 0) < MAX_PAR_PAGE:
            compte[url] = compte.get(url, 0) + 1
            extraits.append({"texte": texte, **meta})  # texte + titre/url/source
    return extraits[:N_EXTRAITS]


def repondre(question):
    """Renvoie (réponse, liste des sources citées)."""
    extraits = rechercher(question)
    # Extraits numérotés [1], [2]…
    contexte = "\n\n".join(f"[{i}] {e['texte']}" for i, e in enumerate(extraits, 1))
    rep = ollama.chat(
        model=LLM,
        messages=[
            {"role": "system", "content": CONSIGNE},
            {"role": "user", "content": f"Extraits :\n\n{contexte}\n\nQuestion : {question}"},
        ],
        options={"temperature": 0.2, "num_ctx": 6144},
    )
    texte = rep["message"]["content"].strip()

    if "je ne sais pas" in texte.lower():
        return texte, []  # pas de réponse -> pas de sources
    # On garde seulement les extraits cités, une fois par page
    cites = {int(n) for n in re.findall(r"\[(\d+)\]", texte)}
    sources = []
    for i, e in enumerate(extraits, 1):
        if i in cites and e["url"] not in [s["url"] for s in sources]:
            sources.append(e)
    texte = re.sub(r"\s*\[\d+\]", "", texte)  # enlève les [1], [3]… du texte affiché
    return texte, sources


if __name__ == "__main__":
    QUESTIONS = [
        "Ça fait 2 mois que j'ai rendu les clés et mon proprio ne m'a pas rendu ma caution, c'est normal ?",
        "Je loue un meublé, combien de temps de préavis je dois donner pour partir ?",
        "J'habite un appart vide à Paris, je peux partir avec 1 mois de préavis ?",
        "Mon propriétaire peut augmenter le loyer quand il veut ?",
        "Le proprio me demande 2 mois de caution pour un appart vide, il a le droit ?",
        "L'agence me demande 300 € de frais de dossier, c'est légal ?",
        "Ma chaudière est en panne, c'est à moi ou au propriétaire de payer ?",
        "Mon propriétaire veut vendre, il peut me mettre dehors ?",
        "Il y a des moisissures chez moi, je peux arrêter de payer le loyer ?",
        "Comment contester une amende de stationnement ?",
    ]
    for q in QUESTIONS:
        texte, sources = repondre(q)
        print("=" * 70, f"\nQ : {q}\n\n{texte}")
        for s in sources:
            print(f"  -> [{s['source']}] {s['titre']}\n     {s['url']}")