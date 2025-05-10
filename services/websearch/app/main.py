from fastapi import FastAPI
from fastmcp import FastMCP

app = FastAPI(title="Web Search Service")
mcp = FastMCP(app)


@app.get("/")
async def root():
    return {"message": "Web Search Service is running"}


@app.get("/search")
async def search(query: str):
    # Placeholder for web search logic
    return {"query": query, "results": ["result1", "result2"]}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
