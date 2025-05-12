from setuptools import setup, find_packages

setup(
    name="document-service",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "fastmcp",
        "chromadb",
        "langchain",
        "sentence-transformers",
        "python-multipart",
    ],
    python_requires=">=3.8",
)
