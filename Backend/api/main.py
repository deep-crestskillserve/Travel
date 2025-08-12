from fastapi import FastAPI
from hotels import router 
app = FastAPI()

# Include your hotels router
app.include_router(router)
