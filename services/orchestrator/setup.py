from setuptools import setup, find_packages

setup(
    name="orchestrator",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.68.0",
        "uvicorn>=0.15.0",
        "pydantic>=1.8.0",
        "python-dotenv==1.0.0",
        "python-multipart>=0.0.5",
        "langchain>=0.1.0",
        "langchain-core>=0.2.38",
        "langchain-community>=0.0.20",
        "langgraph>=0.0.10",
        "langsmith>=0.0.83",
        "openai>=1.3.0",
        "fastmcp>=0.1.0",
    ],
)
