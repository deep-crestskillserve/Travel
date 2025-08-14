import os
import httpx
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, confloat, conint, field_validator
from dotenv import load_dotenv
import logging
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from typing import List, Optional
from filter_data import filter_json

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
    amenities: Optional[List[str]] = None
    ratings: Optional[List[int]] = None

    @field_validator("radiusUnit")
    def validate_radius_unit(cls, value):
        valid_units = ["KM", "MILE"]
        if value not in valid_units:
            raise ValueError(f"radiusUnit must be one of {valid_units}")
        return value

class HotelRoomDetails(BaseModel):
    hotelIds: List[str]
    adults: conint(ge=1, le=9) = 1
    checkInDate: str
    checkOutDate: Optional[str] = None
    roomQuantity: Optional[conint(ge=1, le=9)] = None
    currency: Optional[str] = "USD"

    @field_validator("checkInDate", "checkOutDate")
    def validate_date_format(cls, value):
        if value:
            try:
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Date must be in YYYY-MM-DD format")
        return value


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

    # async with httpx.AsyncClient() as client:
    async with httpx.AsyncClient(timeout=float(os.getenv("HTTP_TIMEOUT", 30.0))) as client:
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
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, headers=headers)

        if response.status_code == 200:
            data = response.json()
            data = filter_json(data)
            data = {
                "status": response.status_code,
                "response": data
            }
            return data

        if response.status_code in (400, 404):
            return {
                "status": response.status_code,
                "response": {"title": "NO HOTELS FOUND FOR REQUESTED LOCATION"}
            }

        response.raise_for_status()

@router.post("/", response_model_exclude_none=True)
# async def list_hotels(request: HotelList, access_token: str = Depends(get_access_token_dep)):
async def list_hotels(request: HotelList):
    try:
        access_token = await get_access_token()
        url = "https://test.api.amadeus.com/v1/reference-data/locations/hotels/by-geocode"
        params = {
            "latitude": request.latitude,
            "longitude": request.longitude,
            "radius": request.radius,
            "radiusUnit": request.radiusUnit
        }
        if request.amenities:
            params["amenities"] = ",".join(request.amenities).upper()

        if request.ratings:
            params["ratings"] = ",".join(map(str, request.ratings))

        headers = {"Authorization": f"Bearer {access_token}"}

        data = await list_hotels_helper(url, params, headers)

        if data.get("hotels") == []:
            logger.info("No hotels found for given coordinates")
        return data

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

# @retry(
#     stop=stop_after_attempt(3),
#     wait=wait_exponential(multiplier=1, min=2, max=10),
#     retry=retry_if_exception_type(httpx.HTTPStatusError)
# )
# async def get_hotel_offers_helper(url, params, headers):
#     """
#     Fetches hotel room offers from Amadeus Hotel Search API.
    
#     Args:
#         url (str): API endpoint URL.
#         params (dict): Query parameters.
#         headers (dict): Request headers.
        
#     Returns:
#         dict: API response JSON.
        
#     Raises:
#         HTTPException: If the API request fails.
#     """
#     async with httpx.AsyncClient() as client:
#         response = await client.get(url, params=params, headers=headers)

#         if response.status_code == 200:
#             data = response.json()
#             # data = filter_json(data)
#             data = {
#                 "status": response.status_code,
#                 "response": data
#             }
#             return data

#         if response.status_code in (400, 404):
#             return {
#                 "status": response.status_code,
#                 "response": {"title": "NO ROOM OFFERS FOUND FOR REQUESTED HOTELS"}
#             }

#         response.raise_for_status()

# @router.post("/room-offers", response_model_exclude_none=True)
# async def get_hotel_room_offers(request: HotelRoomDetails, access_token: str = Depends(get_access_token_dep)):
#     """
#     Fetches room details for up to 20 hotels using their hotel IDs.
    
#     Args:
#         request (HotelRoomDetails): Request body with hotel IDs, adults, check-in date, etc.
#         access_token (str): OAuth2 access token.
        
#     Returns:
#         dict: Room offers for the specified hotels.
        
#     Raises:
#         HTTPException: If the API request fails.
#     """
#     try:
#         # Limit to first 20 hotel IDs to respect API constraints
#         hotel_ids = request.hotelIds[:20]
#         if not hotel_ids:
#             raise HTTPException(status_code=400, detail="No hotel IDs provided")

#         url = "https://test.api.amadeus.com/v3/shopping/hotel-offers"
#         params = {
#             "hotelIds": ",".join(hotel_ids),
#             "adults": request.adults,
#             "checkInDate": request.checkInDate
#         }
#         if request.checkOutDate:
#             params["checkOutDate"] = request.checkOutDate
#         if request.roomQuantity:
#             params["roomQuantity"] = request.roomQuantity
#         if request.currency:
#             params["currency"] = request.currency

#         headers = {"Authorization": f"Bearer {access_token}"}

#         data = await get_hotel_offers_helper(url, params, headers)
#         return data

#     except httpx.HTTPStatusError as e:
#         logger.error(f"Hotel Offers API HTTP error: {e.response.text if e.response else str(e)}, params: {params}")
#         raise HTTPException(
#             status_code=e.response.status_code if e.response else 500, 
#             detail=e.response.text if e.response else "Unknown API error"
#         )
#     except Exception as e:
#         logger.error(f"Hotel Offers API unexpected error: {str(e)}, params: {params}")
#         raise HTTPException(
#             status_code=500, 
#             detail="Failed to fetch hotel room offers"
#         )

# @router.post("/hotels-and-rooms", response_model_exclude_none=True)
# async def list_hotels_and_get_rooms(
#     request: HotelList,
#     adults: conint(ge=1, le=9) = 1,
#     checkInDate: str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
#     checkOutDate: Optional[str] = None,
#     roomQuantity: Optional[conint(ge=1, le=9)] = None,
#     currency: Optional[str] = "USD",
#     access_token: str = Depends(get_access_token_dep)
# ):
#     """
#     Fetches hotels by geolocation and their room offers for up to 20 hotels.
    
#     Args:
#         request (HotelList): Geolocation-based hotel search parameters.
#         adults (int): Number of adults.
#         checkInDate (str): Check-in date in YYYY-MM-DD format.
#         checkOutDate (Optional[str]): Check-out date in YYYY-MM-DD format.
#         roomQuantity (Optional[int]): Number of rooms.
#         currency (Optional[str]): Currency code.
#         access_token (str): OAuth2 access token.
        
#     Returns:
#         dict: Combined hotel list and room offers.
#     """
#     try:
#         # Step 1: Fetch hotel list
#         hotel_list_response = await list_hotels(request)
#         hotel_data = hotel_list_response.get("response", {}).get("data", [])
        
#         if not hotel_data:
#             return {
#                 "status": 200,
#                 "response": {"title": "NO HOTELS FOUND, NO ROOM OFFERS FETCHED"}
#             }

#         # Extract up to 20 hotel IDs
#         hotel_ids = [hotel["hotelId"] for hotel in hotel_data[:20]]
#         if not hotel_ids:
#             return {
#                 "status": 200,
#                 "response": {"title": "NO VALID HOTEL IDS FOUND"}
#             }

#         # Step 2: Fetch room offers for the hotel IDs
#         room_request = HotelRoomDetails(
#             hotelIds=hotel_ids,
#             adults=adults,
#             checkInDate=checkInDate,
#             checkOutDate=checkOutDate,
#             roomQuantity=roomQuantity,
#             currency=currency
#         )
#         room_offers_response = await get_hotel_room_offers(room_request, access_token)

#         # Combine responses
#         combined_response = {
#             "status": 200,
#             "response": {
#                 "hotels": hotel_data,
#                 "room_offers": room_offers_response.get("response", {})
#             }
#         }
#         return combined_response

#     except Exception as e:
#         logger.error(f"Combined hotels and rooms error: {str(e)}")
#         raise HTTPException(status_code=500, detail="Failed to fetch hotels and room offers")