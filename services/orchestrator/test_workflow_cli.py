#!/usr/bin/env python3
"""
Command-line interface to test the AgentHub workflow functionality directly.
This script allows you to interact with the workflow without needing the web frontend.
"""

import asyncio
from pathlib import Path
from fastapi import FastAPI
from app.core.workflow import create_agent_workflow, initialize_state
from app.core.config import get_settings
from app.core.mcp_client import init_mcp
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize settings
settings = get_settings()

# Initialize FastAPI app for FastMCP
app = FastAPI()
init_mcp(app)


async def main():
    """Main CLI interface for testing the workflow."""
    print("Welcome to AgentHub Workflow CLI Tester")
    print("=======================================")

    while True:
        # Get user input
        print("\nEnter your message (or 'quit' to exit):")
        message = input("> ")

        if message.lower() == "quit":
            break

        try:
            # Create workflow
            workflow = create_agent_workflow()

            # Initialize state with the message
            state = initialize_state(message)

            print("\nProcessing message through workflow...")
            print("-------------------------------------")

            # Execute workflow
            final_state = workflow.invoke(state)

            # Display results
            print("\nWorkflow Results:")
            print("----------------")
            print(f"Query Type: {final_state['query_type']}")
            print(f"Generation Type: {final_state['generation_type']}")
            print(f"Target Format: {final_state['target_format']}")
            print("\nTask Status:")
            for key, value in final_state["task_status"].items():
                print(f"- {key}: {value}")

            # Show generated content if any
            if final_state["context"].get("canvas_content"):
                content = final_state["context"]["canvas_content"]
                print(f"\nGenerated {content['type']} content ({content['format']}):")
                print("-" * 40)
                print(content["content"])
                print("-" * 40)

            # Show final response
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
