import re

## function to clean the release notes/change logs text
## text: str - release notes/change logs text
## returns: str - cleaned release notes/change logs text
def clean_text(text: str) -> str:
    # Remove trailing whitespace from each line
    text = "\n".join(line.rstrip() for line in text.splitlines())

    # Collapse multiple blank lines into one
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove leading/trailing whitespace from the whole document
    return text.strip()