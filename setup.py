import os.path
from setuptools import find_packages, setup

# the directory containing this file
ROOT = os.path.dirname(__file__)

# the text of the README file
with open(os.path.join(ROOT, "README.md"), "r") as f:
    README = f.read()

setup(
    name="json_strong_typing",
    version="0.1.3",
    description="Type-safe data interchange for Python data classes",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/hunyadi/strong_typing",
    author="Levente Hunyadi",
    author_email="hunyadi@gmail.com",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    packages=find_packages(exclude=("tests",)),
    include_package_data=True,
    install_requires=["jsonschema", 'typing_extensions;python_version<"3.9"'],
)
