from setuptools import setup, find_packages

setup(
    name="cs_ticket_system",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "sqlalchemy",
        "pytest",
        "pytest-asyncio",
        "httpx",
        "aiosqlite",
        "python-multipart",  # for file uploads
        "aiofiles",
    ],
)
