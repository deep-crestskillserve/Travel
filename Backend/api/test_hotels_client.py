import httpx
import asyncio
import json
import os

async def save_and_print_response(output_dir, filename, response):
    try:
        data = {
            "status": response.status_code,
            "response": response.json()
        }
    except Exception:
        data = {
            "status": response.status_code,
            "response": response.text  # fallback if JSON decoding fails
        }

    print(f"Status: {data['status']}")
    # print(f"Response: {json.dumps(data['response'], indent=2) if isinstance(data['response'], dict) else data['response']}")
    with open(os.path.join(output_dir, filename), "w") as f:
        json.dump(data, f, indent=2)

async def test_hotels_endpoint():
    """
    Test the /api/hotels/ endpoint with various inputs and save responses to JSON files.
    """
    base_url = "http://127.0.0.1:8000/api/hotels/"
    headers = {"Content-Type": "application/json"}
    output_dir = os.getcwd()  # Save files in the current directory

    async with httpx.AsyncClient() as client:
        # Test case 1: Valid request (New York City coordinates)
        print("Testing valid request...")
        valid_payload = {
            "latitude": 48.8584,
            "longitude": 2.2945,
            "radius": 5
        }
        resp = await client.post(base_url, json=valid_payload, headers=headers)
        await save_and_print_response(output_dir, "pariis.json", resp)

        # Test case 2: Invalid radiusUnit
        print("\nTesting invalid radiusUnit...")
        invalid_payload = {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "radius": 5,
            "radiusUnit": "INVALID"
        }
        resp = await client.post(base_url, json=invalid_payload, headers=headers)
        await save_and_print_response(output_dir, "invalid_radiusunit_response.json", resp)

        # Test case 3: Invalid latitude
        print("\nTesting invalid latitude...")
        invalid_lat_payload = {
            "latitude": 100,  # Out of range
            "longitude": -74.0060,
            "radius": 5,
            "radiusUnit": "KM"
        }
        resp = await client.post(base_url, json=invalid_lat_payload, headers=headers)
        await save_and_print_response(output_dir, "invalid_latitude_response.json", resp)

if __name__ == "__main__":
    asyncio.run(test_hotels_endpoint())
