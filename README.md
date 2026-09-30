# Assistant location — RAG juridique grand public

Un assistant qui répond aux questions de locataires (logement vide ou meublé, parc privé)
**uniquement à partir des fiches service-public.fr et de la loi du 6 juillet 1989**,
en langage simple, avec ses sources. 100 % local : aucune question ne quitte la machine.

> Projet de portfolio. Ceci n'est pas un conseil juridique.

## Demo



https://github.com/user-attachments/assets/50c05987-7173-4ad1-9d12-c8965c4ba8a2



## Comment ça marche
```
question ─► bge-m3 (vecteur) ─► Chroma : 5 extraits les plus proches (2 max par fiche)
                                     │
                                     ▼
          qwen3:8b + consigne « uniquement ces extraits, sinon je ne sais pas »
                                     │
                                     ▼
                 réponse simple + sources réellement citées
```

## Données
- 67 fiches service-public.fr (XML DILA) + 51 articles de la loi n° 89-462 (API Légifrance)
- 1 079 morceaux : une section de fiche ou un article par morceau, avec titre et URL

## Choix techniques
| Choix | Pourquoi |
|---|---|
| Ollama + qwen3:8b | Local et gratuit. Le 4B testé ignorait une partie des consignes. |
| bge-m3 | Embeddings multilingues, bons en français |
| Chroma | Base vectorielle locale, sans serveur |
| Découpage maison (bibliothèque standard) | Le vrai travail est de lire la structure XML des fiches, pas besoin de LangChain |
| 2 extraits max par fiche | Une fiche de 134 morceaux (encadrement des loyers) monopolisait les résultats |
| Hors-sujet décidé par le LLM | Une question hors sujet est aussi « proche » qu'une bonne question (distance 0,39 contre 0,38) : un seuil ne marche pas |

## Limites connues
- **Vocabulaire** : les gens écrivent « caution » ou « moisissures », les fiches disent
  « dépôt de garantie » ou « infiltrations d'eau », et la recherche rate alors la bonne fiche.
  Piste : reformuler la question avant la recherche.
- **Exemples chiffrés** : le modèle reprend parfois les montants d'un exemple
  (« logement de 25 m² ») comme si c'était une règle.
- **Lenteur** : environ 1 min par réponse sur une RTX 3050 4 Go (le 8B déborde sur le processeur).
- Pas d'évaluation chiffrée : 10 questions de test vérifiées à la main.

## Lancer le projet
Prérequis : Python [VERSION], [Ollama](https://ollama.com).
```powershell
ollama pull bge-m3
ollama pull qwen3:8b
python -m venv .venv ; .venv\Scripts\activate
pip install -r requirements.txt
python indexe.py      # construit la base Chroma depuis data/chunks.jsonl
streamlit run app.py
```
Les données sont incluses. Pour les retélécharger : `recup_fiches.py`, puis `recup_loi.py`
(identifiants PISTE dans `.env`), puis `decoupe.py`.

## Sources des données
- Fiches : Service-Public.gouv.fr / DILA, Licence Ouverte 2.0, récupérées le [DATE]
- Loi n° 89-462 du 6 juillet 1989 : Légifrance / DILA, récupérée le [DATE]
