# ANCMA — Demo applicazioni IA generativa

---

> **ATTENZIONE — DISCLAIMER**
>
> Le applicazioni descritte in questo documento sono **pure demo realizzate a scopo esclusivamente illustrativo**. I dati contenuti **non sono stati verificati, validati o controllati** e possono contenere errori, imprecisioni o informazioni non aggiornate. Le analisi generate dall'intelligenza artificiale **non costituiscono pareri professionali** e non devono essere utilizzate per decisioni operative, strategiche o legali.
>
> **L'unica finalità di queste demo è dimostrare le potenzialità dell'IA generativa** applicata al settore della mobilità a due ruote e al contesto associativo di ANCMA.

---

## 1. Policy Monitor & Regulatory Intelligence

**URL:** https://ancma-policy-monitor.onrender.com/

### Cosa fa

Monitora le normative europee e italiane rilevanti per il settore due ruote e le analizza automaticamente tramite intelligenza artificiale (Claude, Anthropic).

### Come funziona

- L'app presenta un catalogo di normative (regolamenti EU, decreti italiani, direttive) che riguardano il settore motociclistico, e-bike e veicoli leggeri.
- Ogni normativa è classificata per **stato** (vigente, proposta, in iter legislativo, in consultazione), **categorie di associati ANCMA** coinvolte e **temi** (emissioni, incentivi, sicurezza, omologazione, ecc.).
- L'utente può **filtrare** le normative per stato, categoria o tema e cercare per testo libero.
- Cliccando **"Analizza con AI"**, l'app invia la normativa al modello Claude che produce:
  - Una **sintesi esecutiva** in linguaggio da policy brief
  - Una valutazione di **impatto per ogni categoria di associato** (alto/medio/basso/nessuno), con opportunità e rischi specifici
  - Una **timeline** delle scadenze chiave
  - Una lista di **azioni raccomandate** per ANCMA
  - Un **sentiment** complessivo per il settore (positivo/neutro/negativo)

### Categorie di associati considerate

1. Costruttori motocicli e scooter (termici)
2. Costruttori e-bike e cargo bike
3. Costruttori veicoli elettrici L-category
4. Produttori componentistica e accessori
5. Importatori e distributori
6. Fornitori tecnologia e software

### Cosa dimostra

- La capacità dell'IA di **analizzare testi normativi** e produrre sintesi strutturate
- La possibilità di generare automaticamente **valutazioni di impatto differenziate** per tipologia di associato
- L'utilità di un sistema di **monitoraggio normativo** centralizzato per un'associazione di categoria

---

## 2. EICMA Network Visualizer

**URL:** https://ancma-eicma-network.onrender.com/

### Cosa fa

Visualizza la rete di relazioni tra gli espositori EICMA delle edizioni 2022, 2023, 2024 e 2025 sotto forma di grafo interattivo.

### Come funziona

- L'app elabora i dati degli espositori di quattro edizioni EICMA e costruisce un **grafo di rete** dove:
  - Ogni **nodo** rappresenta un espositore
  - I **collegamenti** tra espositori sono basati su: co-presenza nello stesso padiglione, tipologia di brand simile e partecipazione a più edizioni
- Gli espositori che risultano **associati ANCMA** sono evidenziati con un colore diverso
- Il grafo è navigabile: si può zoomare, trascinare i nodi e cliccare per vedere i dettagli
- Sono disponibili **filtri** per paese, numero minimo di edizioni, community e grado minimo di connessione
- Una sezione **statistiche** mostra metriche aggregate sulla rete (centralità, community, distribuzione)

### Cosa dimostra

- La capacità di **estrarre relazioni implicite** da dati fieristici e renderle visibili
- L'utilità della **network analysis** per comprendere l'ecosistema industriale del settore
- La possibilità di identificare **cluster**, attori chiave e pattern di partecipazione nel tempo

---

## 3. Dashboard Mercato Moto Italia

**URL:** https://ancma-dashboard-mercato.onrender.com/

### Cosa fa

Dashboard interattiva che visualizza i dati di immatricolazione del mercato moto, scooter e cicli in Italia dal 2022 al 2025, con grafici D3.js e un chatbot AI per l'analisi conversazionale dei dati.

### Come funziona

- La **Panoramica** mostra 4 KPI principali (totale immatricolazioni, scooter, moto, elettrici) con variazione percentuale anno su anno e un grafico a barre raggruppate per confronto annuale 2022-2025.
- Il **Trend Mensile** presenta un grafico a linee con l'andamento mese per mese di moto, scooter e ciclomotori. È possibile sovrapporre i dati 2024 e 2025 per un confronto diretto.
- La sezione **Segmenti** include un donut chart con le quote di mercato e una tabella comparativa con variazioni percentuali colorate.
- Il **Focus Elettrico** mostra un area chart del trend mensile dei veicoli elettrici 2024 vs 2025, con mini-card riassuntive e sparkline.
- La **Chat AI** consente di interrogare i dati in linguaggio naturale. Il modello Claude ha accesso all'intero dataset e risponde con analisi concrete, citando numeri specifici.

### Dati inclusi

- Immatricolazioni annuali 2022-2025 per segmento (moto, scooter, ciclomotori, elettrici)
- Dati mensili completi 2024 e 2025
- Contesto narrativo: trend di mercato, effetto Euro 5+, performance per segmento

### Cosa dimostra

- L'efficacia della **visualizzazione dati interattiva** (D3.js) per comunicare trend di mercato complessi
- La potenza di un **chatbot AI contestualizzato** che conosce i dati specifici dell'associazione
- La possibilità di creare **strumenti di business intelligence** accessibili senza competenze tecniche

---

## Note tecniche

| | Policy Monitor | EICMA Network | Dashboard Mercato |
|---|---|---|---|
| **Backend** | Python, FastAPI | Python, FastAPI | Python, FastAPI |
| **Frontend** | HTML/JS (single page) | HTML/JS (single page) | HTML/JS + D3.js v7 |
| **IA** | Claude API (Anthropic) | — | Claude API (Anthropic) |
| **Dati** | 15 normative mock precaricate | Espositori EICMA 2022-2025 | Immatricolazioni 2022-2025 |
| **Hosting** | Render (free tier) | Render (free tier) | Render (free tier) |

Essendo ospitate su Render free tier, le app possono richiedere **30-60 secondi** per il primo caricamento se il server è in stato di inattività.

---

*Documento preparato a supporto della presentazione delle demo IA per ANCMA.*
