# Étape 5 : interface web minimale au-dessus de rag.py
import streamlit as st
from rag import repondre  # le bloc if __name__ == "__main__" de rag.py ne s'exécute pas ici

st.set_page_config(page_title="Assistant location", page_icon="🏠")
st.title("Assistant location")
st.write("Posez votre question sur la location d'un logement **vide ou meublé** (parc privé).")
st.warning("Ceci n'est pas un conseil juridique. Les réponses s'appuient sur service-public.fr "
           "et la loi du 6 juillet 1989, mais peuvent être incomplètes.")

# Formulaire : la question part seulement au clic
with st.form("question"):
    question = st.text_area("Votre question",
                            placeholder="Ex. : Mon propriétaire ne me rend pas ma caution, que faire ?")
    envoyer = st.form_submit_button("Demander")

if envoyer and question.strip():
    with st.spinner("Je cherche dans les fiches officielles…"):
        texte, sources = repondre(question)
    st.markdown(texte)
    if sources:
        st.subheader("Sources")
        for s in sources:
            st.markdown(f"- [{s['titre']}]({s['url']}) — *{s['source']}*")