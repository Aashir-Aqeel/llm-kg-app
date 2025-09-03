from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.routers import chat, graph, kg
from app.routers.graph_view import router as graph_view_router  # <-- explicit import

app = FastAPI(title="LLM builds a Personal Knowledge Graph")

app.include_router(graph.router)
app.include_router(chat.router)
app.include_router(kg.router)
app.include_router(graph_view_router)  # <-- include the router object

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")

@app.get("/health")
def health():
    return {"ok": True}
