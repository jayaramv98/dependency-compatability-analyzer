from pathlib import Path

### Fetching files from external source (e.g. GitHub) will be implemented in the future

## function to load the release notes/change logs from the file system
## path: str - path to the release notes/change logs file
## returns: str - release notes/change logs text
def load_release_note(path: str) -> str:
    file_path = Path(path)

    return file_path.read_text(encoding="utf-8")