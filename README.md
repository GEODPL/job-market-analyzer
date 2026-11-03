# Greek AI Job Market Analyzer

Streamlit εφαρμογή που αναλύει πραγματικές αγγελίες του kariera.gr (skills, κλάδοι, μισθοί, remote, τοποθεσίες) και κάνει CV analysis με radar, semantic job matching, feedback και cover letter.

## Δομή

| Αρχείο | Ρόλος |
|---|---|
| `app.py` | Η Streamlit εφαρμογή (entry point στο Cloud) |
| `styles.css`, `.streamlit/config.toml` | Dark θέμα και στυλ (από το αρχικό frontend) |
| `skills_config.py`, `matching.py`, `docx_utils.py` | Λογική skills, embeddings, Word export |
| `scraper.py` | Τρέχει **τοπικά**: Apify -> Supabase. Δεν χρειάζεται το Cloud |

## Τοπική εκτέλεση

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # συμπλήρωσε τα κλειδιά
streamlit run app.py
```

## Ενημέρωση δεδομένων

Το `scraper.py` διαβάζει `SUPABASE_URL`, `SUPABASE_KEY`, `APIFY_API_TOKEN` από `.env`:

```bash
python scraper.py
```

## Deploy στο Streamlit Community Cloud

1. Ανέβασε το repo στο GitHub (το `.env` και το `secrets.toml` δεν ανεβαίνουν, τα αποκλείει το `.gitignore`).
2. share.streamlit.io -> **Create app** -> διάλεξε repo, branch `main`, αρχείο `app.py`.
3. **Advanced settings** -> Python 3.12 -> στα **Secrets** κόλλησε τα περιεχόμενα του `secrets.toml.example` με τα πραγματικά κλειδιά.
4. **Deploy**.
