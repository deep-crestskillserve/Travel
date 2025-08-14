from fastapi import FastAPI
from hotels import router

app = FastAPI()

# Include the hotels router
app.include_router(router)