import re


def is_dialogue(text: str) -> bool:
    return bool(re.search(r"(M|W)[:：]", text))


def split_dialogue_paragraph_to_lines(text: str):
    return text.strip().splitlines()


def parse_dialogue_lines(lines):
    parsed = []
    for line in lines:
        match = re.match(r"(M|W)[:：]\s*(.*)", line)
        if match:
            parsed.append((match.group(1), match.group(2).strip()))
    return parsed
