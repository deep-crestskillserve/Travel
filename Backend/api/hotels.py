import os
import httpx
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, confloat, conint, field_validator
from dotenv import load_dotenv
import logging
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()
router = APIRouter(prefix="/api/hotels", tags=["Hotels"])

AMADEUS_CLIENT_ID = os.getenv("AMADEUS_CLIENT_ID")
AMADEUS_CLIENT_SECRET = os.getenv("AMADEUS_CLIENT_SECRET")

if not AMADEUS_CLIENT_ID or not AMADEUS_CLIENT_SECRET:
    raise RuntimeError("Amadeus API credentials are missing in .env file")

class HotelList(BaseModel):
    latitude: confloat(ge=-90, le=90)
    longitude: confloat(ge=-180, le=180)
    radius: conint(ge=0)
    radiusUnit: str = "KM"

    @field_validator("radiusUnit")
    def validate_radius_unit(cls, value):
        valid_units = ["KM", "MILE"]
        if value not in valid_units:
            raise ValueError(f"radiusUnit must be one of {valid_units}")
        return value

class HotelRequest(BaseModel):
    location: str
    checkin: str
    checkout: str
    budget: float


_token_cache = {"token": None, "expires_at": None}
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(httpx.HTTPStatusError)
)

async def get_access_token():
    """
    Fetches OAuth2 access token from Amadeus API
    
    Returns:
        str: Access token.
    
    Raises:
        HTTPException: If token retrieval fails.
    """

    global _token_cache
    now = datetime.now()

    if _token_cache["token"] and _token_cache["expires_at"] > now:
        return _token_cache["token"]

    async with httpx.AsyncClient(timeout = 10.0) as client:
        token_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": AMADEUS_CLIENT_ID,
            "client_secret": AMADEUS_CLIENT_SECRET,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response  = await client.post(
            token_url, 
            data = payload,
            headers = headers
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to get access token")
        
        token_data = response.json()
        _token_cache["token"] = token_data["access_token"]
        _token_cache["expires_at"] = now + timedelta(seconds=token_data.get("expires_in", 1800) - 60)  # Buffer of 60s
        return _token_cache["token"]

async def get_access_token_dep():
    return await get_access_token()

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(httpx.HTTPStatusError)
)

async def list_hotels_helper(url, params, headers):
    """
    Fetches hotel data from Amadeus API.
    
    Args:
        url (str): API endpoint URL.
        params (dict): Query parameters.
        headers (dict): Request headers.
        
    Returns:
        dict: API response JSON.
        
    Raises:
        HTTPException: If the API request fails.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()

@router.post("/")
async def list_hotels(request: HotelList, access_token: str = Depends(get_access_token_dep)):
    try:
        # access_token = await get_access_token()
        url = "https://test.api.amadeus.com/v1/reference-data/locations/hotels/by-geocode"
        params = {
            "latitude": request.latitude,
            "longitude": request.longitude,
            "radius": request.radius,
            "radiusUnit": request.radiusUnit
        }
        headers = {"Authorization": f"Bearer {access_token}"}
        return await list_hotels_helper(url, params, headers)
        # async with httpx.AsyncClient() as client:
        #     response = await client.get(
        #         url,
        #         params = params,
        #         headers = headers
        #     )
        #     response.raise_for_status()
        #     return response.json()

    except httpx.HTTPStatusError as e:
        logger.error(f"Hotel API HTTP error: {e.response.text if e.response else str(e)}, params: {params}")
        
        raise HTTPException(
            status_code=e.response.status_code if e.response else 500, 
            detail=e.response.text if e.response else "Unknown API error"
        )

    except Exception as e:
        logger.error(f"Hotel API unexpected error: {str(e)}, params: {params}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to fetch hotels"
        )