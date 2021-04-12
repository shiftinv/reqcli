import os


def create_dirs_for_file(file_path: str) -> None:
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
