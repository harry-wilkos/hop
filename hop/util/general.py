def pop_dict(data: dict, key_to_split: str) -> tuple:
    dict_1 = {key_to_split: data[key_to_split]} if key_to_split in data else {}
    dict_2 = {k: v for k, v in data.items() if k != key_to_split}
    return dict_1, dict_2
