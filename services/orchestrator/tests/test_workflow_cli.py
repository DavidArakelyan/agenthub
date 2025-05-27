#!/usr/bin/env python3
"""
Command-line interface to test the AgentHub workflow functionality directly.
This script allows you to interact with the workflow without needing the web frontend.
"""

import asyncio
from pathlib import Path
from fastapi import FastAPI

from app.core.workflow import create_agent_workflow, initialize_state

# from app.core.workflow_simple import create_agent_workflow, initialize_state
from app.core.config import get_settings
from app.core.mcp_client import init_mcp
from app.core.types import SimpleQuery, ComplexQuery
import logging
import sys

# Configure logging to show all logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)  # This ensures logs go to the Debug Console
    ],
)

# Set log level for specific loggers
# logging.getLogger("app.core.workflow").setLevel(logging.DEBUG)
logging.getLogger("app.core.workflow").setLevel(logging.INFO)
logging.getLogger("langchain").setLevel(logging.INFO)
logger = logging.getLogger(__name__)

# Initialize settings
settings = get_settings()

# Initialize FastAPI app for FastMCP
app = FastAPI()
init_mcp(app)


async def main():
    """Main CLI interface for testing the workflow."""
    logger.info("Starting AgentHub Workflow CLI Tester")
    print("Welcome to AgentHub Workflow CLI Tester")
    print("=======================================")

    while True:
        # Get user input
        print("\nEnter your message (or 'exit' to quit):")
        message = input("> ")

        if message.lower() == "exit":
            logger.info("Exiting workflow tester")
            break

        try:
            # Create workflow
            logger.info("Creating workflow instance")
            workflow = create_agent_workflow()

            # Initialize state with the message
            logger.info(f"Initializing state with message: {message}")
            state = initialize_state(message)

            print("\nProcessing message through workflow...")
            print("-------------------------------------")

            # Execute workflow
            logger.info("Executing workflow")
            final_state = await workflow.ainvoke(state)
            logger.info("Workflow execution completed")

            # Display results
            logger.debug(f"Final state: {final_state}")
            print("\nWorkflow Results:")
            print("----------------")
            print(
                f"Query Type: {'simple' if isinstance(final_state['query'], SimpleQuery) else 'complex'}"
            )

            if isinstance(final_state["query"], ComplexQuery):
                print(f"Generation Type: {final_state['query'].generator_type.value}")
                if final_state["query"].code_language:
                    print(f"Target Format: {final_state['query'].code_language.value}")
                elif final_state["query"].document_format:
                    print(
                        f"Target Format: {final_state['query'].document_format.value}"
                    )
            else:
                print("Generation Type: none")
                print("Target Format: none")

            print("\nTask Status:")
            for key, value in final_state.get("task_status", {}).items():
                print(f"- {key}: {value}")

            # Show generated content if any
            if final_state["context"].get("canvas_content"):
                content = final_state["context"]["canvas_content"]
                target_format = final_state["context"].get("target_format", "unknown")

                # Determine content type based on task status
                content_type = "unknown"
                if final_state["task_status"].get("code_generated", False):
                    content_type = "code"
                elif final_state["task_status"].get("document_generated", False):
                    content_type = "document"

                logger.info(
                    f"Generated {content_type} content in {target_format} format"
                )
                print(f"\nGenerated {content_type} content ({target_format}):")
                print("-" * 40)

                # Handle both string and dictionary content for backward compatibility
                if isinstance(content, dict) and "content" in content:
                    print(content["content"])
                else:
                    print(content)

                print("-" * 40)

            # Show final response
            logger.info("Displaying final response")
            print("\nFinal Response:")
            print(final_state["messages"][-1].content)

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            print(f"\nError: {str(e)}")


if __name__ == "__main__":
    # Create uploads directory if it doesn't exist
    Path("uploads").mkdir(exist_ok=True)

    # Run the async main function
    asyncio.run(main())
