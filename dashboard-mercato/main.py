"""ANCMA Dashboard Mercato Moto Italia — FastAPI backend."""

import json
import os
from pathlib import Path

import anthropic
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

load_dotenv()

BASE_DIR = Path(__file__).parent
app = FastAPI(title="ANCMA Dashboard Mercato Moto Italia")

# ---------------------------------------------------------------------------
# DATA
# ---------------------------------------------------------------------------

ANNUALI = {
    "2022": {"moto": 145300, "scooter": 173600, "ciclomotori": 21800, "elettrici_totali": 9200, "totale": 340700},
    "2023": {"moto": 145400, "scooter": 173500, "ciclomotori": 18800, "elettrici_totali": 10180, "totale": 337700},
    "2024": {"moto": 166454, "scooter": 186639, "ciclomotori": 20220, "elettrici_totali": 10166, "totale": 373313},
    "2025": {"moto": 134480, "scooter": 197043, "ciclomotori": 13764, "elettrici_totali": 8561, "totale": 345287},
}

MENSILI_2024 = [
    {"mese": "Gen", "moto": 8200, "scooter": 9100, "ciclomotori": 1100, "elettrici": 580},
    {"mese": "Feb", "moto": 9800, "scooter": 11200, "ciclomotori": 1250, "elettrici": 650},
    {"mese": "Mar", "moto": 17431, "scooter": 16704, "ciclomotori": 1470, "elettrici": 1065},
    {"mese": "Apr", "moto": 19200, "scooter": 20100, "ciclomotori": 1580, "elettrici": 1120},
    {"mese": "Mag", "moto": 20667, "scooter": 23143, "ciclomotori": 1814, "elettrici": 1200},
    {"mese": "Giu", "moto": 16800, "scooter": 19200, "ciclomotori": 1600, "elettrici": 980},
    {"mese": "Lug", "moto": 14200, "scooter": 16800, "ciclomotori": 1420, "elettrici": 870},
    {"mese": "Ago", "moto": 7491, "scooter": 9362, "ciclomotori": 1000, "elettrici": 520},
    {"mese": "Set", "moto": 11127, "scooter": 14772, "ciclomotori": 1677, "elettrici": 780},
    {"mese": "Ott", "moto": 13800, "scooter": 15900, "ciclomotori": 1600, "elettrici": 720},
    {"mese": "Nov", "moto": 11479, "scooter": 14000, "ciclomotori": 1172, "elettrici": 693},
    {"mese": "Dic", "moto": 16762, "scooter": 9823, "ciclomotori": 3002, "elettrici": 520},
]

MENSILI_2025 = [
    {"mese": "Gen", "moto": 5200, "scooter": 10800, "ciclomotori": 680, "elettrici": 420},
    {"mese": "Feb", "moto": 6800, "scooter": 12400, "ciclomotori": 780, "elettrici": 510},
    {"mese": "Mar", "moto": 10200, "scooter": 16800, "ciclomotori": 950, "elettrici": 680},
    {"mese": "Apr", "moto": 12100, "scooter": 18200, "ciclomotori": 1050, "elettrici": 750},
    {"mese": "Mag", "moto": 14800, "scooter": 21000, "ciclomotori": 1200, "elettrici": 820},
    {"mese": "Giu", "moto": 12400, "scooter": 17800, "ciclomotori": 1100, "elettrici": 710},
    {"mese": "Lug", "moto": 10800, "scooter": 15600, "ciclomotori": 980, "elettrici": 620},
    {"mese": "Ago", "moto": 5900, "scooter": 8200, "ciclomotori": 580, "elettrici": 380},
    {"mese": "Set", "moto": 9200, "scooter": 13400, "ciclomotori": 820, "elettrici": 540},
    {"mese": "Ott", "moto": 10800, "scooter": 15200, "ciclomotori": 920, "elettrici": 610},
    {"mese": "Nov", "moto": 9400, "scooter": 14600, "ciclomotori": 840, "elettrici": 580},
    {"mese": "Dic", "moto": 7880, "scooter": 13043, "ciclomotori": 856, "elettrici": 441},
]

MENSILI = {"2024": MENSILI_2024, "2025": MENSILI_2025}

CONTESTO = """Contesto narrativo del mercato:
- 2024 miglior anno dal 2010: +10,5%, totale 373.313 unita
- 2025 chiude a -7,5% (345.287 unita) — effetto Euro 5+ che ha gonfiato dicembre 2024
- Scooter motore del 2025: +5,5% su 2024, unico segmento in crescita
- Moto in forte calo nel 2025: -19,2%, effetto fine-serie Euro 5
- Ciclomotori in crollo nel 2025: -31,9%
- Elettrici 2025: -15,8%, ciclomotori elettrici -27,2%, scooter elettrici -13,9%
- Quadricicli 2024: +28,1%, di cui 65% elettrici
- Il settore vale 14,8 miliardi di euro, leadership europea per produzione e mercato
- Modelli top 2024: Benelli TRK 502X (moto piu venduta), Honda SH 125 (scooter piu venduto)
- Presidente ANCMA: Mariano Roman"""

FULL_DATASET = {
    "annuali": ANNUALI,
    "mensili_2024": MENSILI_2024,
    "mensili_2025": MENSILI_2025,
    "contesto": CONTESTO,
}


def calc_delta(curr, prev):
    if prev == 0:
        return 0
    return round((curr - prev) / prev * 100, 1)


# ---------------------------------------------------------------------------
# ENDPOINTS
# ---------------------------------------------------------------------------

@app.get("/api/dati")
def get_dati():
    return FULL_DATASET


@app.get("/api/dati/mensili")
def get_mensili(anno: str = Query("2024")):
    if anno not in MENSILI:
        raise HTTPException(404, f"Dati mensili non disponibili per {anno}")
    return MENSILI[anno]


@app.get("/api/dati/annuali")
def get_annuali():
    return ANNUALI


@app.get("/api/kpi")
def get_kpi():
    c = ANNUALI["2025"]
    p = ANNUALI["2024"]
    quota_el = round(c["elettrici_totali"] / c["totale"] * 100, 1)
    return {
        "totale_2025": c["totale"],
        "delta_totale": calc_delta(c["totale"], p["totale"]),
        "moto_2025": c["moto"],
        "delta_moto": calc_delta(c["moto"], p["moto"]),
        "scooter_2025": c["scooter"],
        "delta_scooter": calc_delta(c["scooter"], p["scooter"]),
        "ciclomotori_2025": c["ciclomotori"],
        "delta_ciclomotori": calc_delta(c["ciclomotori"], p["ciclomotori"]),
        "elettrici_2025": c["elettrici_totali"],
        "delta_elettrici": calc_delta(c["elettrici_totali"], p["elettrici_totali"]),
        "quota_elettrico": quota_el,
        "per_segmento": {
            seg: {
                "2024": p[seg],
                "2025": c[seg],
                "delta": calc_delta(c[seg], p[seg]),
            }
            for seg in ["moto", "scooter", "ciclomotori", "elettrici_totali"]
        },
    }


@app.post("/api/chat")
def chat(body: dict):
    message = body.get("message", "").strip()
    if not message:
        raise HTTPException(400, "Messaggio vuoto")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(500, "ANTHROPIC_API_KEY non configurata")

    client = anthropic.Anthropic(api_key=api_key)

    system_prompt = f"""Sei l'assistente AI di ANCMA — Confindustria ANCMA, l'associazione italiana dei costruttori di moto, scooter e cicli.
Rispondi in italiano, tono professionale ma accessibile.
Hai accesso ai seguenti dati di mercato aggiornati:

{json.dumps(FULL_DATASET, ensure_ascii=False, indent=2)}

{CONTESTO}

Rispondi con analisi concrete, cita sempre i numeri specifici.
Struttura la risposta con: risposta diretta (1-2 frasi), poi analisi con dati, poi un insight finale.
Tieni le risposte sotto le 200 parole. Non inventare dati non presenti nel dataset.
Se ti chiedono cose non legate al mercato moto/cicli, rispondi cortesemente che puoi aiutare solo con dati di mercato ANCMA."""

    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": message}],
    )

    return {"reply": resp.content[0].text}


@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    html_path = BASE_DIR / "templates" / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8002))
    print("\n🏍️  ANCMA Dashboard Mercato Moto Italia")
    print("=" * 50)
    print(f"📡 Server: http://localhost:{port}")
    print("🔑 ANTHROPIC_API_KEY:", "configurata" if os.getenv("ANTHROPIC_API_KEY") else "mancante")
    print("=" * 50)
    if not os.getenv("RENDER"):
        import webbrowser
        webbrowser.open(f"http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
