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


def add_prefix(sentence):
    """
    Add prefix in cloned objects
    """
    def get_new_prefix(word):
        digit = int(re.findall(r'\d+', word)[0]) + 1
        return f"Clone {digit}:"

    matched_pattern_1 = re.search(r'Clone \d+:', sentence)
    matched_pattern_2 = re.search(r'Clone :', sentence)

    if matched_pattern_1:
        rx = r'(?<!\d){}(?!\d)'.format(matched_pattern_1.group())
        return re.sub(rx, lambda x: get_new_prefix(x.group()), sentence)
    if matched_pattern_2:
        return re.sub("Clone :", "Clone 1:", sentence)

    return f"Clone : {sentence}"
