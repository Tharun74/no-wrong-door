

def _normalize_xml_name(name: str) -> tuple[str, str]:
    """'QUILL, Paul' -> ('paul', 'quill')"""
    last, first = name.split(",", 1)
    return first.strip().lower(), last.strip().lower()


def build_match_index(benefits_records: list) -> dict:
    index: dict = {}
    for record in benefits_records:
        if not record.get("born"):
            continue 
        first, last = _normalize_xml_name(record["name"])
        key = (first, last, record["born"])
        index.setdefault(key, []).append(record)
    return index


def match_resident(resident: dict, match_index: dict):
    key = (
        resident["first_name"].strip().lower(),
        resident["last_name"].strip().lower(),
        resident["date_of_birth"],
    )
    candidates = match_index.get(key, [])

    if len(candidates) == 1:
        return (
            candidates[0],
            "matched",
            "first name, last name, and date of birth matched exactly one benefits record",
        )
    if len(candidates) == 0:
        return (
            None,
            "no_match",
            "no benefits record shares this resident's first name, last name, and date of birth",
        )
    return (
        None,
        "ambiguous",
        f"{len(candidates)} benefits records share this name and date of birth; declined to merge",
    )