import httpx

BASE_URL = "http://127.0.0.1:8081/residents"

seen_ids = set()
duplicate_ids = []
page = 1
total_records = 0

with httpx.Client() as client:

    while True:
        response = client.get(
            BASE_URL,
            params={"page": page}
        )

        response.raise_for_status()

        data = response.json()

        results = data["results"]

        print(
            f"Page {page}: "
            f"{len(results)} records"
        )

        for resident in results:
            resident_id = resident["id"]

            if resident_id in seen_ids:
                duplicate_ids.append(resident_id)

            seen_ids.add(resident_id)

        total_records += len(results)

        if not data["has_more"]:
            break

        page += 1

print()
print("---- Summary ----")
print(f"Pages fetched: {page}")
print(f"Records received: {total_records}")
print(f"Unique residents: {len(seen_ids)}")
print(f"Duplicates: {len(duplicate_ids)}")

if duplicate_ids:
    print("Duplicate IDs:")
    for resident_id in duplicate_ids:
        print(f"  {resident_id}")