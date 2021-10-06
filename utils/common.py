import datetime
import re


def convert_date_object_to_string_in_dict(dictionary):
    """
    Change date objects to string
    """
    for key, value in dictionary.items():
        if isinstance(value, (datetime.date, datetime.datetime)):
            dictionary[key] = str(value)
    return dictionary


def add_clone_prefix(sentence):
    """
    Add prefix in cloned objects
    """
    match = re.match(r"Clone\s*(\d+):\s+(.*)", sentence)
    if match:
        return f"Clone {int(match.group(1)) + 1}: {match.group(2)}"

    match = re.match(r"Clone\s*:\s+(.*)", sentence)
    if match:
        return f"Clone 2: {match.group(1)}"

    return f"Clone: {sentence}"
