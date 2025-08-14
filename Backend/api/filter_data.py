import json
import os
# from .data import test-1.json
# def filter_json(file):
#     with open(file, "r") as f:
#         data_json = json.load(f)
#         if(data_json["status"] == 200):
#             data = data_json["response"]["data"]
#             for i in range(len(data)):
#                 address_lines = data[i]["address"]["lines"]
#                 hotel_name = data[i]["name"]
#                 print(address_lines)
#                 print(hotel_name, '\n')

def filter_json(file):
    with open(file, "r") as f:
        data_json = json.load(f)

        neglected_data = []  # store skipped entries
        filtered_data = []
        output_dir = os.path.join(os.getcwd(), "data")

        if(data_json.get("status") == 200):
            hotels = data_json.get("response", {}).get("data", [])

            for hotel in hotels:
                has_name = "name" in hotel
                has_address = "address" in hotel and "lines" in hotel["address"]
                no_forbidden_name = has_name and not any(
                    word in hotel["name"] for word in ["TEST", "PROPERTY", "VALIDATION"]
                )
                no_forbidden_address = has_address and not any(
                    word in " ".join(hotel["address"]["lines"]) for word in ["TEST", "ADDRESS"]
                )

                not_house_of_travel = has_name and "house of travel" not in hotel["name"].lower()

                if has_name and has_address and no_forbidden_name and no_forbidden_address and not_house_of_travel:
                    filtered_data.append(hotel)
                else:
                    neglected_data.append(hotel)
                    
        
        if neglected_data:
            with open(os.path.join(output_dir, "neglected.json"), "w") as f:
                        json.dump(neglected_data, f, indent=2)

        if filtered_data:
            with open(os.path.join(output_dir, "filtered.json"), "w") as f:
                        json.dump(filtered_data, f, indent=2)


filter_json("data/test-1.json")