import json
import os
import webbrowser
from datetime import datetime, date
from pathlib import Path
from typing import Optional

import anthropic
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
ANALYSES_DIR = DATA_DIR / "analyses"
ANALYSES_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="ANCMA Policy Monitor & Regulatory Intelligence")

CATEGORIE = [
    "Costruttori motocicli e scooter (termici)",
    "Costruttori e-bike e cargo bike",
    "Costruttori veicoli elettrici L-category",
    "Produttori componentistica e accessori",
    "Importatori e distributori",
    "Fornitori tecnologia e software",
]


def load_normative() -> list[dict]:
    with open(DATA_DIR / "normative.json", "r", encoding="utf-8") as f:
        return json.load(f)


def save_normative(data: list[dict]):
    with open(DATA_DIR / "normative.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_analysis(norm_id: str) -> Optional[dict]:
    path = ANALYSES_DIR / f"{norm_id}.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_analysis(norm_id: str, analysis: dict):
    with open(ANALYSES_DIR / f"{norm_id}.json", "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)


# --- API Endpoints ---

@app.get("/api/categorie")
def get_categorie():
    return CATEGORIE


@app.get("/api/normative")
def get_normative(
    stato: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
):
    norme = load_normative()

    if stato:
        norme = [n for n in norme if n["stato"] == stato]
    if categoria:
        norme = [n for n in norme if categoria in n["categorie_impattate"]]
    if tag:
        norme = [n for n in norme if tag in n["tags"]]
    if q:
        q_lower = q.lower()
        norme = [
            n for n in norme
            if q_lower in n["titolo"].lower()
            or q_lower in n["testo_breve"].lower()
            or any(q_lower in t.lower() for t in n["tags"])
        ]

    norme.sort(key=lambda x: x["data_pubblicazione"], reverse=True)

    for n in norme:
        analysis = load_analysis(n["id"])
        n["has_analysis"] = analysis is not None
        if analysis:
            n["sentiment"] = analysis.get("sentiment", "neutro")

    return norme


@app.get("/api/normative/{norm_id}")
def get_normativa(norm_id: str):
    norme = load_normative()
    for n in norme:
        if n["id"] == norm_id:
            analysis = load_analysis(n["id"])
            n["has_analysis"] = analysis is not None
            if analysis:
                n["sentiment"] = analysis.get("sentiment", "neutro")
            return n
    raise HTTPException(status_code=404, detail="Normativa non trovata")


@app.post("/api/analyze/{norm_id}")
def analyze_normativa(norm_id: str):
    norme = load_normative()
    normativa = None
    for n in norme:
        if n["id"] == norm_id:
            normativa = n
            break

    if not normativa:
        raise HTTPException(status_code=404, detail="Normativa non trovata")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY non configurata")

    client = anthropic.Anthropic(api_key=api_key)

    categorie_str = "\n".join(f"- {c}" for c in CATEGORIE)

    prompt = f"""Sei un esperto di normative per il settore motociclistico e della mobilità leggera. Lavori per ANCMA (Associazione Nazionale Ciclo Motociclo Accessori), l'associazione italiana dei costruttori di moto, scooter, e-bike e veicoli leggeri.

Analizza questa normativa: {normativa['titolo']} — {normativa['testo_breve']}

Fonte: {normativa['fonte']}
Stato: {normativa['stato']}
Categorie impattate: {', '.join(normativa['categorie_impattate'])}
Tags: {', '.join(normativa['tags'])}

Le categorie di associati ANCMA sono:
{categorie_str}

Produci un JSON con questi campi:
- sintesi_esecutiva: stringa, max 150 parole, linguaggio da policy brief professionale
- impatti: oggetto con chiave = nome categoria associato (usa TUTTE le 6 categorie elencate sopra), valore = oggetto con:
  - livello: 'alto' | 'medio' | 'basso' | 'nessuno'
  - descrizione: stringa, max 80 parole
  - opportunita: lista di max 3 stringhe (opportunità che la normativa crea)
  - rischi: lista di max 3 stringhe (rischi o oneri che introduce)
- timeline_chiave: lista di oggetti {{"data": "YYYY-MM-DD", "evento": "descrizione"}} con le scadenze importanti (almeno 3-5 eventi)
- azioni_raccomandate: lista di max 4 azioni concrete che ANCMA dovrebbe intraprendere
- sentiment: 'positivo' | 'neutro' | 'negativo' (per il settore due ruote in generale)

Rispondi SOLO con il JSON valido, nessun testo aggiuntivo, nessun markdown code fence."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1])

    analysis = json.loads(response_text)
    analysis["analyzed_at"] = datetime.now().isoformat()
    analysis["norm_id"] = norm_id

    save_analysis(norm_id, analysis)
    return analysis


@app.get("/api/analyze/{norm_id}")
def get_analysis(norm_id: str):
    analysis = load_analysis(norm_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analisi non disponibile")
    return analysis


@app.get("/api/dashboard")
def get_dashboard():
    norme = load_normative()

    stati = {}
    for n in norme:
        stati[n["stato"]] = stati.get(n["stato"], 0) + 1

    cat_count = {}
    for n in norme:
        for c in n["categorie_impattate"]:
            cat_count[c] = cat_count.get(c, 0) + 1

    analyses_count = len(list(ANALYSES_DIR.glob("*.json")))

    tag_count = {}
    for n in norme:
        for t in n["tags"]:
            tag_count[t] = tag_count.get(t, 0) + 1

    scadenze = []
    today = date.today().isoformat()
    for n in norme:
        if n.get("data_scadenza_commenti") and n["data_scadenza_commenti"] >= today:
            scadenze.append({
                "id": n["id"],
                "titolo": n["titolo"],
                "scadenza": n["data_scadenza_commenti"],
            })
    scadenze.sort(key=lambda x: x["scadenza"])

    return {
        "totale_normative": len(norme),
        "per_stato": stati,
        "per_categoria": cat_count,
        "per_tag": tag_count,
        "analisi_completate": analyses_count,
        "scadenze_imminenti": scadenze[:5],
    }


@app.get("/api/feed")
def get_feed():
    norme = load_normative()
    norme.sort(key=lambda x: x["data_pubblicazione"], reverse=True)
    return norme[:5]


@app.post("/api/mock-alert")
def mock_alert():
    norme = load_normative()
    new_id = f"mock-alert-{len(norme)+1}"

    import random
    mock_norms = [
        {
            "titolo": "Proposta Regolamento EU — Standard caricabatterie universale veicoli L-category",
            "fonte": "EU",
            "stato": "proposta",
            "tags": ["elettrico", "infrastrutture", "standardizzazione"],
            "testo_breve": "Proposta di regolamento per standardizzare il connettore di ricarica per tutti i veicoli elettrici L-category venduti in UE. Obbligo di compatibilità CCS Combo dal 2028 per tutti i nuovi modelli.",
        },
        {
            "titolo": "Decreto MASE — Fondo nazionale infrastrutture ricarica veicoli leggeri",
            "fonte": "Italia",
            "stato": "consultazione",
            "tags": ["infrastrutture", "elettrico", "incentivi", "Italia"],
            "testo_breve": "Nuovo fondo da 150 milioni per l'installazione di colonnine di ricarica dedicate a veicoli elettrici leggeri in aree urbane. Incentivi per condomini e parcheggi pubblici.",
        },
        {
            "titolo": "Regolamento EU — Etichettatura energetica per e-bike e speed pedelec",
            "fonte": "EU",
            "stato": "iter",
            "tags": ["elettrico", "sostenibilità", "etichettatura"],
            "testo_breve": "Introduzione di un sistema di etichettatura energetica A-G per e-bike e speed pedelec, basato su efficienza del motore, autonomia reale e impatto ambientale del ciclo di vita della batteria.",
        },
        {
            "titolo": "Direttiva EU — Responsabilità prodotto per veicoli autonomi e ADAS",
            "fonte": "EU",
            "stato": "proposta",
            "tags": ["sicurezza", "ADAS", "responsabilità", "tecnologia"],
            "testo_breve": "Revisione della direttiva sulla responsabilità del prodotto per includere sistemi ADAS e funzioni di guida assistita su motocicli. Inversione dell'onere della prova per malfunzionamenti software.",
        },
    ]

    mock = random.choice(mock_norms)
    new_norm = {
        "id": new_id,
        "titolo": mock["titolo"],
        "fonte": mock["fonte"],
        "stato": mock["stato"],
        "data_pubblicazione": date.today().isoformat(),
        "data_scadenza_commenti": "2026-09-30",
        "url_fonte": f"https://example.eu/regulation/{new_id}",
        "categorie_impattate": random.sample(CATEGORIE, k=random.randint(2, 4)),
        "tags": mock["tags"],
        "testo_breve": mock["testo_breve"],
    }

    norme.insert(0, new_norm)
    save_normative(norme)

    return new_norm


@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    html_path = BASE_DIR / "templates" / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    print("\n🏛️  ANCMA Policy Monitor & Regulatory Intelligence")
    print("=" * 50)
    print("📡 Server avviato su http://localhost:8001")
    print("🔑 ANTHROPIC_API_KEY:", "✅ configurata" if os.getenv("ANTHROPIC_API_KEY") else "❌ mancante")
    print("=" * 50)
    webbrowser.open("http://localhost:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)
