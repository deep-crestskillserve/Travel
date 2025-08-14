import json

def filter_json(data_json):
    # Initialize filtered_data as a list to store valid hotels
    filtered_data = []

    # Check if 'data' exists in data_json; if not, return empty result
    hotels = data_json.get("data", [])

    for hotel in hotels:
        has_name = "name" in hotel
        has_address = "address" in hotel and "lines" in hotel["address"]
        no_forbidden_name = has_name and not any(
            word in hotel["name"].upper() for word in ["TEST", "PROPERTY", "VALIDATION"]
        )
        no_forbidden_address = has_address and not any(
            word in " ".join(hotel["address"]["lines"]).upper() for word in ["TEST", "ADDRESS"]
        )
        not_house_of_travel = has_name and "HOUSE OF TRAVEL" not in hotel["name"].upper()

        if has_name and has_address and no_forbidden_name and no_forbidden_address and not_house_of_travel:
            filtered_data.append(hotel)

    # Update the original data_json with filtered hotels
    data_json["data"] = filtered_data
    return data_json