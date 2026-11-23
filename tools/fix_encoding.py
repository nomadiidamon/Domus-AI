from pathlib import Path
import argparse
import sys

try:
    import chardet
except ImportError:
    chardet = None

EXTENSIONS = {
    ".bat",
    ".h",
    ".hh",
    ".hpp",
    ".hxx",
    ".cpp",
    ".cc",
    ".c",
    ".css",
    ".csv",
    ".html",
    ".js",
    ".json",
    ".md",
    ".py",
    ".rst",
    ".sh",
    ".svg",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}

REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT_FOLDERS = ("examples", "docs", "cpp/src", "python/src")

REPLACEMENTS = {
    "\u2018": "'",   # left single quote
    "\u2019": "'",   # right single quote
    "\u201c": '"',   # left double quote
    "\u201d": '"',   # right double quote
    "\u2013": "-",   # en dash
    "\u2014": "-",   # em dash
    "\u00b1": "+/-", # plus/minus
}

def find_files():
    return sorted(
        file
        for folder in ROOT_FOLDERS
        for file in (REPO_ROOT / folder).rglob("*")
        if file.is_file() and file.suffix.lower() in EXTENSIONS
    )


def convert_file(path):
    data = path.read_bytes()

    try:
        data.decode("utf-8")
        return False
    except UnicodeDecodeError:
        pass

    if chardet is None:
        print(f"Cannot detect encoding for {path}; install chardet to fix it.")
        return None

    encoding = chardet.detect(data).get("encoding")
    if not encoding:
        print(f"Unable to determine encoding: {path}")
        return None

    try:
        text = data.decode(encoding)
    except (LookupError, UnicodeDecodeError):
        print(f"Unable to decode {path} as {encoding}")
        return None

    print(f"Converting {path} ({encoding} -> UTF-8)")

    for old, new in REPLACEMENTS.items():
        text = text.replace(old, new)

    path.write_text(text, encoding="utf-8")

    return True


def check_file(path):
    data = path.read_bytes()

    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        print(f"BAD ENCODING: {path}")
        return True

    return False


def main():

    parser = argparse.ArgumentParser(
        description="Check or fix repository text file encodings"
    )

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--fix", action="store_true", help="Convert files to UTF-8")
    mode_group.add_argument("--check", action="store_true", help="Check encodings only")

    args = parser.parse_args()
    files = find_files()
    print(f"Scanning {len(files)} files under: {', '.join(ROOT_FOLDERS)}")
    problems = False
    converted = 0

    for file in files:
        if args.fix:
            result = convert_file(file)
            if result is None:
                problems = True
            elif result:
                converted += 1
        else:
            if check_file(file):
                problems = True

    if problems:
        print("\nEncoding issues found.")
        print("Run: python tools/fix_encoding.py --fix")
        sys.exit(1)

    if args.fix:
        print(f"\nEncoding fix completed; converted {converted} files.")
    else:
        print("\nEncoding check passed.")


if __name__ == "__main__":
    main()