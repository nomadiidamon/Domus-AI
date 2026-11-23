"""Read shared package metadata from the repository-level project.ini."""

from configparser import ConfigParser
from email.parser import Parser
from pathlib import Path

from setuptools import setup


PROJECT_ROOT = Path(__file__).resolve().parent.parent
METADATA_FILE = PROJECT_ROOT / "project.ini"
if not METADATA_FILE.is_file():
    METADATA_FILE = Path(__file__).resolve().parent / "project.ini"
README_FILE = Path(__file__).resolve().parent / "README.md"
PACKAGE_INFO = Path(__file__).resolve().parent / "PKG-INFO"

metadata = ConfigParser(interpolation=None)
if PACKAGE_INFO.is_file():
    generated = Parser().parsestr(PACKAGE_INFO.read_text(encoding="utf-8"))
    version = generated["Version"]
    description = generated["Summary"]
    author_names = generated.get("Author", "")
    license_name = generated.get("License", "Not specified")
    python_requires = generated.get("Requires-Python", ">=3.10")
    homepage = generated.get("Home-page", "")
elif metadata.read(METADATA_FILE):
    project = metadata["project"]
    author_names = metadata.get("people", "authors", fallback="")
    version = project["version"]
    description = project["description"]
    license_name = project["license"]
    python_requires = project["python_requires"]
    homepage = project["homepage"]
else:
    raise RuntimeError(f"Shared project metadata not found: {METADATA_FILE}")

authors = [
    {"name": name.strip()}
    for name in author_names.split(",")
    if name.strip()
]

setup(
    version=version,
    description=description,
    long_description=README_FILE.read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    author=", ".join(author["name"] for author in authors),
    license=license_name,
    python_requires=python_requires,
    url=homepage,
    project_urls={"Homepage": homepage} if homepage else {},
)