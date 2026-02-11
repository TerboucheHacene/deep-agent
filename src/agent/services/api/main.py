import dotenv

dotenv.load_dotenv()

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from agent.services.api.routes import chat_router  # noqa: E402

app = FastAPI(
    title="Deep Agent API",
    description="API for interacting with the Deep Agent",
    version="0.1.0",
)

# CORS middleware for Open WebUI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
