# app/main.py
from fastapi import FastAPI
from .routers import chat, graph, kg
from app.services.neo4j_client import init_driver, close_driver
from starlette.responses import RedirectResponse

app = FastAPI(title="LLM-KG API")

# ensure Neo4j is ready
@app.on_event("startup")
def _on_startup():
    init_driver()

@app.on_event("shutdown")
def _on_shutdown():
    close_driver()

# include routers
app.include_router(graph.router)
app.include_router(kg.router)
app.include_router(chat.router)

# handy root redirect
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/docs")
