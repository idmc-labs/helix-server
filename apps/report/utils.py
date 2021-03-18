def excel_column_key(headers, header) -> str:
    seed = ord('A')
    return chr(list(headers.keys()).index(header) + seed)
