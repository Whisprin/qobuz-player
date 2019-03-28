import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="qobuz-api",
    version="0.0.2",
    author="Robert Sprunk",
    author_email="github@sprunk.me",
    description="An unofficial Qobuz music streaming API client",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Whisprin/qobuz-player",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
        "Operating System :: OS Independent",
    ],
)
