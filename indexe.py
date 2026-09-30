# Étape 3 : embeddings bge-m3 (Ollama) -> base Chroma sur disque
import json
import chromadb
import ollama

MODELE = "bge-m3"
LOT = 32  # nombre de morceaux envoyés à Ollama d'un coup

# 1. Charger les morceaux
with open("data/chunks.jsonl", encoding="utf-8") as f:
    morceaux = [json.loads(ligne) for ligne in f]
print(f"{len(morceaux)} morceaux chargés")

# 2. Ouvrir (ou créer) la base dans data/chroma
client = chromadb.PersistentClient(path="data/chroma")
collection = client.get_or_create_collection(
    name="logement",
    configuration={"hnsw": {"space": "cosine"}},  # proximité = cosinus
)

# 3. Calculer les embeddings par lots, puis les écrire
for i in range(0, len(morceaux), LOT):
    lot = morceaux[i:i + LOT]
    textes = [m["texte"] for m in lot]
    vecteurs = ollama.embed(model=MODELE, input=textes)["embeddings"]
    collection.upsert(
        ids=[m["id"] for m in lot],
        embeddings=vecteurs,  # nos vecteurs, pas ceux de Chroma
        documents=textes,
        metadatas=[{"titre": m["titre"], "url": m["url"], "source": m["source"]}
                   for m in lot],
    )
    print(f"{min(i + LOT, len(morceaux))}/{len(morceaux)}")

print("Total dans la base :", collection.count())