from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
import os
from dotenv import load_dotenv
import logging

load_dotenv()
router = APIRouter(prefix="/api/hotels")
logger = logging.getLogger(__name__)

BOOKING_API_KEY = os.getenv("BOOKING_API_KEY")  # From rapidapi.com or similar

class HotelRequest(BaseModel):
    location: str
    checkin: str
    checkout: str
    budget: float

@router.post("/")
async def search_hotels(request: HotelRequest):
    try:
        async with httpx.AsyncClient() as client:
            # Mock response (replace with real Booking.com API)
            # Example: response = await client.get(
            #     "https://booking-api.com/v3/hotels/search",
            #     headers={"X-API-Key": BOOKING_API_KEY},
            #     params={
            #         "city": request.location,
            #         "checkin_date": request.checkin,
            #         "checkout_date": request.checkout,
            #         "max_price": request.budget
            #     }
            # )
            mock_response = {
                "hotels": [
                    {
                        "name": "Hotel ABC",
                        "price_per_night": min(150.0, request.budget),  # Ensure within budget
                        "location": request.location,
                        "checkin": request.checkin,
                        "checkout": request.checkout
                    }
                ]
            }
            return mock_response
    except Exception as e:
        logger.error(f"Hotel API error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch hotels")