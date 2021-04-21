import pathlib
from setuptools import setup, find_packages  # type: ignore

HERE = pathlib.Path(__file__).parent
README = (HERE / "README.md").read_text()

setup(
    name="syblmallus",
    version="0.5.1",
    author="SYBL",
    author_email="grahamk206@gmail.com",
    description="Connect to the sybl server",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/G-Kemp101/mallus",
    packages=find_packages(exclude=("tests")),
    install_requires=["pandas", "pyOpenSSL", "python-dotenv", "xdg", "numpy", "zenlog"],
)
