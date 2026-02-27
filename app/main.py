"""EICMA Network Visualization — FastAPI backend."""

from __future__ import annotations

import os
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from graph_builder import build_graph, graph_to_json, graph_stats

app = FastAPI(title="EICMA Network Viz")

# Build graph once at startup
print("Building EICMA exhibitor graph…")
G = build_graph()
print("Graph ready.")


@app.get("/")
def index():
    return FileResponse("static/index.html")


@app.get("/graph")
def get_graph(
    filter_country: Optional[str] = Query(None),
    min_years: Optional[int] = Query(None),
    filter_community: Optional[int] = Query(None),
    min_degree: Optional[int] = Query(None),
):
    filters = {}
    if filter_country:
        filters["filter_country"] = filter_country
    if min_years is not None:
        filters["min_years"] = min_years
    if filter_community is not None:
        filters["filter_community"] = filter_community

    data = graph_to_json(G, filters if filters else None)

    # Post-filter: min_degree (must be done after edge construction)
    if min_degree is not None and min_degree > 0:
        # Count degrees in the filtered subgraph
        deg = {}
        for link in data["links"]:
            deg[link["source"]] = deg.get(link["source"], 0) + 1
            deg[link["target"]] = deg.get(link["target"], 0) + 1
        keep = {nid for nid, d in deg.items() if d >= min_degree}
        data["nodes"] = [n for n in data["nodes"] if n["id"] in keep]
        node_ids = {n["id"] for n in data["nodes"]}
        data["links"] = [
            l for l in data["links"]
            if l["source"] in node_ids and l["target"] in node_ids
        ]

    return data


@app.get("/stats")
def get_stats():
    return graph_stats(G)


app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
