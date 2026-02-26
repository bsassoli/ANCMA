"""
EICMA Exhibitor Network Graph Builder.

Constructs a NetworkX graph from multi-year EICMA exhibitor data with three
edge layers: brand-type links, same-pavilion links, and multi-edition
co-presence links. Computes centrality metrics and community detection.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from collections import defaultdict
from typing import Optional

import networkx as nx

try:
    from community import community_louvain
    HAS_LOUVAIN = True
except ImportError:
    HAS_LOUVAIN = False

DATA_DIR = Path(__file__).parent / "data"


def normalize_name(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r'\s+', ' ', s)
    return s


def load_all_data():
    years = {}
    for year in [2022, 2023, 2024, 2025]:
        fp = DATA_DIR / f"espositori_eicma_{year}.json"
        if fp.exists():
            with open(fp, encoding="utf-8") as f:
                years[year] = json.load(f)
    return years


def load_ancma_members() -> set[str]:
    """Return a set of normalized EICMA names that are ANCMA members."""
    fp = DATA_DIR / "ancma_eicma_matched.json"
    if not fp.exists():
        return set()
    with open(fp, encoding="utf-8") as f:
        matched = json.load(f)
    return {normalize_name(m["nome_eicma"]) for m in matched}


def build_graph() -> nx.Graph:
    all_data = load_all_data()
    ancma_members = load_ancma_members()
    G = nx.Graph()

    # --- Phase 1: Build node registry from all editions ---
    node_registry: dict[str, dict] = {}  # norm_name -> attrs
    name_to_norm: dict[str, str] = {}    # original -> norm

    # 2025 is the richest dataset, build from it first
    for rec in all_data.get(2025, []):
        norm = normalize_name(rec["nome"])
        name_to_norm[rec["nome"]] = norm
        if norm not in node_registry:
            node_registry[norm] = {
                "nome": rec["nome"],
                "paese": rec.get("paese", ""),
                "codice_paese": rec.get("codice_paese", ""),
                "padiglione_2025": rec.get("padiglione", ""),
                "stand_2025": rec.get("stand", ""),
                "brand_type": rec.get("brand_type", 0),
                "azienda_id": rec.get("azienda_id"),
                "edizioni": {2025},
                "is_italian": rec.get("codice_paese", "") == "IT"
                              or rec.get("paese", "").upper() == "ITALY",
            }
        else:
            node_registry[norm]["edizioni"].add(2025)

    # 2024
    for rec in all_data.get(2024, []):
        norm = normalize_name(rec["nome"])
        if norm in node_registry:
            node_registry[norm]["edizioni"].add(2024)
        else:
            node_registry[norm] = {
                "nome": rec["nome"],
                "paese": rec.get("paese", ""),
                "codice_paese": rec.get("codice_paese", ""),
                "padiglione_2025": "",
                "stand_2025": "",
                "brand_type": rec.get("brand_type", 0),
                "azienda_id": rec.get("azienda_id"),
                "edizioni": {2024},
                "is_italian": rec.get("codice_paese", "") == "IT"
                              or rec.get("paese", "").upper() == "ITALY",
            }

    # 2023 (only names)
    for rec in all_data.get(2023, []):
        norm = normalize_name(rec["nome"])
        if norm in node_registry:
            node_registry[norm]["edizioni"].add(2023)
        else:
            node_registry[norm] = {
                "nome": rec["nome"],
                "paese": "",
                "codice_paese": "",
                "padiglione_2025": "",
                "stand_2025": "",
                "brand_type": 0,
                "azienda_id": None,
                "edizioni": {2023},
                "is_italian": False,
            }

    # 2022
    for rec in all_data.get(2022, []):
        norm = normalize_name(rec["nome"])
        if norm in node_registry:
            node_registry[norm]["edizioni"].add(2022)
            if not node_registry[norm].get("website"):
                node_registry[norm]["website"] = rec.get("website", "")
        else:
            node_registry[norm] = {
                "nome": rec["nome"],
                "paese": "",
                "codice_paese": "",
                "padiglione_2025": "",
                "stand_2025": "",
                "brand_type": 0,
                "azienda_id": None,
                "edizioni": {2022},
                "is_italian": False,
                "website": rec.get("website", ""),
            }

    # Add nodes to graph
    for norm, attrs in node_registry.items():
        editions = sorted(attrs["edizioni"])
        G.add_node(norm, **{
            "nome": attrs["nome"],
            "paese": attrs["paese"],
            "codice_paese": attrs["codice_paese"],
            "padiglione_2025": attrs["padiglione_2025"],
            "stand_2025": attrs["stand_2025"],
            "brand_type": attrs["brand_type"],
            "edizioni": editions,
            "longevity_score": len(editions),
            "is_italian": attrs["is_italian"],
            "is_ancma_member": norm in ancma_members,
        })

    # --- Phase 2: Build edges ---

    # Layer 1: brand_type links (weight 3)
    # Connect brand_type=1 (direct) to brand_type=2 or 3 sharing same pad+stand in 2025
    pad_stand_groups: dict[str, list[str]] = defaultdict(list)
    for rec in all_data.get(2025, []):
        norm = normalize_name(rec["nome"])
        pad = rec.get("padiglione", "")
        stand = rec.get("stand", "")
        if pad and stand and ',' not in pad:  # skip multi-pad
            key = f"{pad}_{stand}"
            pad_stand_groups[key].append(norm)

    brand_type_edges = 0
    for key, members in pad_stand_groups.items():
        if len(members) < 2:
            continue
        directs = [m for m in members if G.nodes[m].get("brand_type") == 1]
        represented = [m for m in members if G.nodes[m].get("brand_type") in (2, 3)]
        for d in directs:
            for r in represented:
                if d != r:
                    if G.has_edge(d, r):
                        G[d][r]["weight"] = max(G[d][r]["weight"], 3)
                        G[d][r]["layers"].add("brand_type")
                    else:
                        G.add_edge(d, r, weight=3, layers={"brand_type"})
                        brand_type_edges += 1

    # Layer 2: same stand cluster 2025 (weight 1)
    # Connect exhibitors sharing the same stand (co-located but different
    # from brand_type link — e.g. two brand_type=2 at same stand).
    # This avoids the O(n^2) all-pairs pavilion clique problem.
    pavilion_edges = 0
    for key, members in pad_stand_groups.items():
        if len(members) < 2:
            continue
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                a, b = members[i], members[j]
                if not G.has_edge(a, b):
                    G.add_edge(a, b, weight=1, layers={"same_stand"})
                    pavilion_edges += 1
                else:
                    G[a][b]["layers"].add("same_stand")

    # Layer 3: multi-edition co-presence (weight = shared editions count)
    # Connect exhibitors that appear in 3+ editions AND share the same
    # country or the same pavilion in 2025.  This creates semantically
    # meaningful edges without a massive all-pairs clique.
    copresence_edges = 0
    node_editions = {}
    for norm, data in G.nodes(data=True):
        ls = data.get("longevity_score", 1)
        if ls >= 3:
            node_editions[norm] = {
                "eds": set(data.get("edizioni", [])),
                "paese": data.get("codice_paese", "") or data.get("paese", ""),
                "pad": data.get("padiglione_2025", ""),
            }

    multi_ed_nodes = sorted(node_editions.keys())
    for i in range(len(multi_ed_nodes)):
        for j in range(i + 1, len(multi_ed_nodes)):
            a, b = multi_ed_nodes[i], multi_ed_nodes[j]
            ia, ib = node_editions[a], node_editions[b]
            shared = len(ia["eds"] & ib["eds"])
            if shared < 2:
                continue
            # Must share pavilion in 2025, or both be 4-edition veterans
            same_pad = (ia["pad"] and ia["pad"] == ib["pad"]
                        and ',' not in ia["pad"])
            both_veterans = (len(ia["eds"]) == 4 and len(ib["eds"]) == 4)
            if not (same_pad or both_veterans):
                continue
            if G.has_edge(a, b):
                G[a][b]["weight"] = max(G[a][b]["weight"], shared)
                G[a][b]["layers"].add("copresence")
                G[a][b]["shared_editions"] = shared
            else:
                G.add_edge(a, b, weight=shared, layers={"copresence"},
                           shared_editions=shared)
                copresence_edges += 1

    # --- Phase 3: Compute metrics ---
    # Remove isolated nodes for cleaner visualization
    isolates = list(nx.isolates(G))
    G.remove_nodes_from(isolates)

    deg_cent = nx.degree_centrality(G)
    # Betweenness on full graph can be slow; sample if large
    if G.number_of_nodes() > 2000:
        bet_cent = nx.betweenness_centrality(G, k=min(500, G.number_of_nodes()))
    else:
        bet_cent = nx.betweenness_centrality(G)
    clust = nx.clustering(G)

    # Community detection
    if HAS_LOUVAIN:
        partition = community_louvain.best_partition(G, random_state=42)
    else:
        communities = nx.community.greedy_modularity_communities(G)
        partition = {}
        for idx, comm in enumerate(communities):
            for node in comm:
                partition[node] = idx

    for norm in G.nodes():
        G.nodes[norm]["degree_centrality"] = round(deg_cent.get(norm, 0), 6)
        G.nodes[norm]["betweenness_centrality"] = round(bet_cent.get(norm, 0), 6)
        G.nodes[norm]["clustering_coefficient"] = round(clust.get(norm, 0), 6)
        G.nodes[norm]["community"] = partition.get(norm, -1)

    # Convert set layers to list for JSON serialization
    for u, v, data in G.edges(data=True):
        data["layers"] = sorted(data.get("layers", set()))

    print(f"Graph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    print(f"  brand_type edges: {brand_type_edges}")
    print(f"  pavilion edges: {pavilion_edges}")
    print(f"  co-presence edges: {copresence_edges}")
    print(f"  isolated nodes removed: {len(isolates)}")
    print(f"  communities: {max(partition.values()) + 1 if partition else 0}")

    return G


def graph_to_json(G: nx.Graph, filters: Optional[dict] = None) -> dict:
    """Convert graph to D3-compatible JSON with optional filters."""
    nodes_data = []
    node_set = set()

    for norm, data in G.nodes(data=True):
        # Apply filters
        if filters:
            if filters.get("filter_country"):
                cc = data.get("codice_paese", "")
                if cc.upper() != filters["filter_country"].upper():
                    continue
            if filters.get("min_years"):
                if data.get("longevity_score", 1) < int(filters["min_years"]):
                    continue
            if filters.get("filter_community") is not None:
                if data.get("community", -1) != int(filters["filter_community"]):
                    continue

        node_set.add(norm)
        nodes_data.append({
            "id": norm,
            "nome": data.get("nome", norm),
            "paese": data.get("paese", ""),
            "codice_paese": data.get("codice_paese", ""),
            "padiglione_2025": data.get("padiglione_2025", ""),
            "stand_2025": data.get("stand_2025", ""),
            "brand_type": data.get("brand_type", 0),
            "edizioni": data.get("edizioni", []),
            "longevity_score": data.get("longevity_score", 1),
            "is_italian": data.get("is_italian", False),
            "is_ancma_member": data.get("is_ancma_member", False),
            "degree_centrality": data.get("degree_centrality", 0),
            "betweenness_centrality": data.get("betweenness_centrality", 0),
            "clustering_coefficient": data.get("clustering_coefficient", 0),
            "community": data.get("community", -1),
        })

    links_data = []
    for u, v, data in G.edges(data=True):
        if u in node_set and v in node_set:
            links_data.append({
                "source": u,
                "target": v,
                "weight": data.get("weight", 1),
                "layers": data.get("layers", []),
                "shared_editions": data.get("shared_editions", 0),
            })

    return {"nodes": nodes_data, "links": links_data}


def graph_stats(G: nx.Graph) -> dict:
    """Compute summary statistics."""
    nodes = G.nodes(data=True)

    # Top 10 by betweenness
    top_betweenness = sorted(
        [(d.get("nome", n), d.get("betweenness_centrality", 0), d.get("community", -1))
         for n, d in nodes],
        key=lambda x: x[1], reverse=True
    )[:10]

    # Community sizes
    comm_sizes = defaultdict(int)
    for _, d in nodes:
        comm_sizes[d.get("community", -1)] += 1
    top_communities = sorted(comm_sizes.items(), key=lambda x: x[1], reverse=True)[:10]

    # Country distribution
    country_dist = defaultdict(int)
    for _, d in nodes:
        c = d.get("paese", "") or "Unknown"
        country_dist[c] += 1
    top_countries = sorted(country_dist.items(), key=lambda x: x[1], reverse=True)[:15]

    # Longevity distribution
    longevity_dist = defaultdict(int)
    for _, d in nodes:
        longevity_dist[d.get("longevity_score", 1)] += 1

    # Edge layer counts
    layer_counts = defaultdict(int)
    for _, _, d in G.edges(data=True):
        for layer in d.get("layers", []):
            layer_counts[layer] += 1

    return {
        "num_nodes": G.number_of_nodes(),
        "num_edges": G.number_of_edges(),
        "density": round(nx.density(G), 6),
        "num_components": nx.number_connected_components(G),
        "top_betweenness": [
            {"nome": n, "score": round(s, 6), "community": c}
            for n, s, c in top_betweenness
        ],
        "top_communities": [
            {"id": cid, "size": size} for cid, size in top_communities
        ],
        "top_countries": [
            {"country": c, "count": n} for c, n in top_countries
        ],
        "longevity_distribution": dict(sorted(longevity_dist.items())),
        "edge_layers": dict(layer_counts),
    }


if __name__ == "__main__":
    G = build_graph()
    stats = graph_stats(G)
    print(json.dumps(stats, indent=2, ensure_ascii=False))
