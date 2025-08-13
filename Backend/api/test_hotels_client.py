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
    with open(os.path.join(output_dir, filename), "w") as f:
        json.dump(data, f, indent=2)

# coordinates, 48.8584, 2.2945 (Eiffel tower)
coordinates = {"latitude": 48.8584, "longitude": 2.2945}

async def test_hotels_endpoint():
    """
    Test the /api/hotels/ endpoint with various inputs and save responses to JSON files.
    """
    base_url = "http://127.0.0.1:8000/api/hotels/"
    headers = {"Content-Type": "application/json"}
    output_dir = os.getcwd() + "/data"  # Save files in the current directory

    async with httpx.AsyncClient() as client:
        # Test case 1: Valid request no params
        print("Test case 1...")
        payload = {**coordinates, "radius": 5}
        resp = await client.post(base_url, json=payload, headers=headers)
        await save_and_print_response(output_dir, "test-1.json", resp)

        # Test case 2: Valid request: rating
        print("\nTest case 2...")
        payload = {**coordinates, "radius": 5, "ratings": [5, 4]}
        resp = await client.post(base_url, json=payload, headers=headers)
        await save_and_print_response(output_dir, "test-2.json", resp)

        # Test case 3: valid radius unit
        print("\nTest case 3...")
        payload = {**coordinates, "radius": 5, "radiusUnit": "MILE"}
        resp = await client.post(base_url, json=payload, headers=headers)
        await save_and_print_response(output_dir, "test-3.json", resp)

        # Test case 4: valid amenities
        print("\nTest case 4...")
        payload = {
            **coordinates,
            "radius": 5.0,
            "amenities": ["golf", "air_conditioning", "business_center", "airport_shuttle"]
        }
        resp = await client.post(base_url, json=payload, headers=headers)
        await save_and_print_response(output_dir, "test-4.json", resp)

        # Test case 5: Invalid radiusUnit
        print("\nTest case 5...")
        payload = {**coordinates, "radius": 5, "radiusUnit": "INVALID"}
        resp = await client.post(base_url, json=payload, headers=headers)
        await save_and_print_response(output_dir, "test-5.json", resp)

        # Test case 6: Invalid coordinates (keep as-is)
        print("\nTest case 6...")
        payload = {
            "latitude": 100,  # Out of range
            "longitude": -181,
            "radius": 5,
            "radiusUnit": "KM"
        }
        resp = await client.post(base_url, json=payload, headers=headers)
        await save_and_print_response(output_dir, "test-6.json", resp)

        # Test case 7: coordinates where there is no hotels (keep as-is)
        print("\nTest case 7...")
        payload = {
            "latitude": 11.5570,
            "longitude": 92.2410,
            "radius": 5,
            "radiusUnit": "KM"
        }
        resp = await client.post(base_url, json=payload, headers=headers)
        await save_and_print_response(output_dir, "test-7.json", resp)

        # Test case 8: valid ratings + amenities
        print("\nTest case 8...")
        payload = {
            **coordinates,
            "radius": 5,
            "ratings": [5, 4],
            "amenities": ["golf", "air_conditioning", "business_center", "airport_shuttle"]
        }
        resp = await client.post(base_url, json=payload, headers=headers)
        await save_and_print_response(output_dir, "test-8.json", resp)


if __name__ == "__main__":
    asyncio.run(test_hotels_endpoint())
