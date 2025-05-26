#!/usr/bin/env python
"""
CLI tool for testing the orchestrator service endpoints.
This tool allows you to interact with the orchestrator service from the command line.
"""

import argparse
import json
import requests
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from tabulate import tabulate
import os
import time

# Default server URL
DEFAULT_SERVER_URL = "http://localhost:8000"


# Terminal colors for output
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def print_success(message: str):
    print(f"{Colors.GREEN}✓ {message}{Colors.ENDC}")


def print_error(message: str):
    print(f"{Colors.RED}✗ {message}{Colors.ENDC}")


def print_info(message: str):
    print(f"{Colors.BLUE}ℹ {message}{Colors.ENDC}")


def print_header(message: str):
    print(f"\n{Colors.HEADER}{Colors.BOLD}=== {message} ==={Colors.ENDC}\n")


def print_json(data: Dict[str, Any]):
    """Pretty print JSON data"""
    print(json.dumps(data, indent=2))


class OrchestratorClient:
    """Client for interacting with the orchestrator service"""

    def __init__(self, base_url: str = DEFAULT_SERVER_URL):
        self.base_url = base_url
        self.current_chat_id = None
        self.chat_ids = []  # Keep track of all created chat IDs

    def create_chat(self) -> str:
        """Create a new chat session"""
        print_info("Creating new chat session...")
        response = requests.post(f"{self.base_url}/chat/new")
        if response.status_code == 200:
            data = response.json()
            if data.get("success", False):
                chat_id = data["data"]["chatId"]
                self.current_chat_id = chat_id
                self.chat_ids.append(chat_id)  # Add to list of chat IDs
                print_success(f"Chat session created with ID: {chat_id}")
                return chat_id
            else:
                print_error(
                    f"Failed to create chat: {data.get('error', {}).get('message', 'Unknown error')}"
                )
                return None
        else:
            print_error(f"HTTP Error: {response.status_code} - {response.text}")
            return None

    def send_message(
        self, chat_id: str, message: str, file_paths: List[str] = None
    ) -> Dict[str, Any]:
        """Send a message to the chat"""
        print_info(f"Sending message: '{message}'")

        # Prepare form data
        data = {"chat_id": chat_id, "message": message}

        files = []
        if file_paths:
            for i, file_path in enumerate(file_paths):
                path = Path(file_path)
                if path.exists():
                    files.append(("files", (path.name, open(path, "rb"))))
                else:
                    print_error(f"File not found: {file_path}")

        # Send request
        start_time = time.time()
        response = requests.post(
            f"{self.base_url}/chat/message", data=data, files=files
        )
        elapsed = time.time() - start_time

        if response.status_code == 200:
            data = response.json()
            if data.get("success", False):
                print_success(f"Message sent successfully (took {elapsed:.2f}s)")
                return data["data"]
            else:
                print_error(
                    f"Failed to send message: {data.get('error', {}).get('message', 'Unknown error')}"
                )
                return None
        else:
            print_error(f"HTTP Error: {response.status_code} - {response.text}")
            return None

    def get_chat_history(self, chat_id: str) -> List[Dict[str, Any]]:
        """Get the chat history"""
        print_info(f"Getting chat history for chat ID: {chat_id}")
        response = requests.get(f"{self.base_url}/chat/{chat_id}/history")
        if response.status_code == 200:
            data = response.json()
            if data.get("success", False):
                print_success(
                    f"Retrieved chat history with {len(data['data'])} messages"
                )
                return data["data"]
            else:
                print_error(
                    f"Failed to get chat history: {data.get('error', {}).get('message', 'Unknown error')}"
                )
                return None
        else:
            print_error(f"HTTP Error: {response.status_code} - {response.text}")
            return None

    def delete_chat(self, chat_id: str) -> bool:
        """Delete a chat session"""
        print_info(f"Deleting chat session with ID: {chat_id}")
        response = requests.delete(f"{self.base_url}/chat/{chat_id}")
        if response.status_code == 200:
            data = response.json()
            if data.get("success", False):
                print_success("Chat deleted successfully")
                if self.current_chat_id == chat_id:
                    self.current_chat_id = None
                if chat_id in self.chat_ids:
                    self.chat_ids.remove(chat_id)
                return True
            else:
                print_error(
                    f"Failed to delete chat: {data.get('error', {}).get('message', 'Unknown error')}"
                )
                return False
        else:
            print_error(f"HTTP Error: {response.status_code} - {response.text}")
            return False

    def upload_document(
        self, file_path: str, metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Upload a document to the orchestrator service"""
        path = Path(file_path)
        if not path.exists():
            print_error(f"File not found: {file_path}")
            return None

        print_info(f"Uploading document: {path.name}")

        files = {"file": (path.name, open(path, "rb"))}

        data = {}
        if metadata:
            data["metadata"] = json.dumps(metadata)

        response = requests.post(
            f"{self.base_url}/documents/upload", files=files, data=data
        )

        if response.status_code == 200:
            data = response.json()
            print_success(f"Document uploaded successfully with ID: {data.id}")
            return data
        else:
            print_error(f"HTTP Error: {response.status_code} - {response.text}")
            return None

    def search_documents(self, query: str, k: int = 4) -> List[Dict[str, Any]]:
        """Search for documents using semantic search"""
        print_info(f"Searching for documents with query: '{query}'")
        response = requests.get(
            f"{self.base_url}/documents/search", params={"query": query, "k": k}
        )

        if response.status_code == 200:
            results = response.json()
            print_success(f"Found {len(results)} document(s)")
            return results
        else:
            print_error(f"HTTP Error: {response.status_code} - {response.text}")
            return None

    def web_search(self, query: str) -> Dict[str, Any]:
        """Perform a web search"""
        print_info(f"Performing web search with query: '{query}'")
        response = requests.get(
            f"{self.base_url}/websearch/search", params={"query": query}
        )

        if response.status_code == 200:
            result = response.json()
            print_success(f"Web search completed with {len(result.results)} results")
            return result
        else:
            print_error(f"HTTP Error: {response.status_code} - {response.text}")
            return None

    def health_check(self) -> bool:
        """Check if the orchestrator service is healthy"""
        try:
            print_info("Checking orchestrator service health...")
            response = requests.get(f"{self.base_url}/health")
            if response.status_code == 200:
                print_success("Orchestrator service is healthy")
                return True
            else:
                print_error(f"Service returned status code: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print_error(f"Could not connect to {self.base_url}")
            return False

    def save_content(
        self, content: str, format_type: str, filename: str
    ) -> Dict[str, Any]:
        """Save content to a file on the server"""
        print_info(f"Saving content to file: {filename}")
        data = {"content": content, "format": format_type, "filename": filename}

        response = requests.post(f"{self.base_url}/save", json=data)

        if response.status_code == 200:
            result = response.json()
            print_success(f"Content saved successfully to: {result.get('path')}")
            return result
        else:
            print_error(f"HTTP Error: {response.status_code} - {response.text}")
            return None

    def list_chats(self) -> List[Dict[str, Any]]:
        """Get a list of all chat sessions"""
        print_info("Getting list of all chat sessions...")
        response = requests.get(f"{self.base_url}/chat/list")
        if response.status_code == 200:
            data = response.json()
            if data.get("success", False):
                chat_list = data.get("data", [])
                print_success(f"Retrieved {len(chat_list)} chat sessions")
                return chat_list
            else:
                print_error(
                    f"Failed to list chats: {data.get('error', {}).get('message', 'Unknown error')}"
                )
                return []
        else:
            print_error(f"HTTP Error: {response.status_code} - {response.text}")
            return []


def interactive_mode(client: OrchestratorClient):
    """Start an interactive session with the orchestrator service"""
    print_header("Interactive Mode")
    print_info("Type 'help' for available commands, 'exit' to quit")

    # Check if service is healthy before starting
    if not client.health_check():
        print_error(
            "Could not connect to orchestrator service. Make sure it's running."
        )
        return

    # Create initial chat session
    if not client.create_chat():
        print_error("Failed to create initial chat session. Exiting.")
        return

    while True:
        command = input(f"\n{Colors.BOLD}orchestrator> {Colors.ENDC}").strip()

        if command == "exit":
            print_info("Exiting interactive mode")
            break

        elif command == "help":
            print_info("Available commands:")
            print("  chat new              - Create a new chat session")
            print("  chat list             - Show current chat ID")
            print("  chat history          - Show message history for current chat")
            print("  chat delete           - Delete current chat session")
            print("  chat all              - List all available chat sessions")
            print("  chat switch <id>      - Switch to a specific chat session")
            print("  send <message>        - Send a message to current chat")
            print(
                "  send-file <file> <message> - Send a message with a file attachment"
            )
            print("  upload <file>         - Upload a document")
            print("  search <query>        - Search documents")
            print("  websearch <query>     - Perform a web search")
            print("  health                - Check service health")
            print("  exit                  - Exit interactive mode")

        elif command == "chat new":
            client.create_chat()

        elif command == "chat list":
            if client.current_chat_id:
                print_info(f"Current chat ID: {client.current_chat_id}")
            else:
                print_error("No active chat session")

        elif command == "chat all":
            chats = client.list_chats()
            if chats:
                # Format chat list as table
                table_data = []
                for chat in chats:
                    is_current = "✓" if chat["id"] == client.current_chat_id else ""
                    table_data.append(
                        [
                            is_current,
                            chat["id"],
                            chat["name"],
                            chat["message_count"],
                            chat["updated_at"],
                        ]
                    )

                print(
                    tabulate(
                        table_data,
                        headers=["Current", "ID", "Name", "Messages", "Last Updated"],
                        tablefmt="grid",
                    )
                )

        elif command.startswith("chat switch "):
            chat_id = command[12:].strip()
            # Check if the chat exists
            chats = client.list_chats()
            chat_ids = [chat["id"] for chat in chats]

            if chat_id in chat_ids:
                client.current_chat_id = chat_id
                print_success(f"Switched to chat: {chat_id}")
                # Also add to our list if it's not there already
                if chat_id not in client.chat_ids:
                    client.chat_ids.append(chat_id)
            else:
                print_error(f"Chat ID not found: {chat_id}")

        elif command == "chat history":
            if not client.current_chat_id:
                print_error("No active chat session")
                continue

            history = client.get_chat_history(client.current_chat_id)
            if history:
                # Format chat history as table
                table_data = []
                for msg in history:
                    table_data.append(
                        [
                            msg["type"],
                            msg["text"][:100]
                            + ("..." if len(msg["text"]) > 100 else ""),
                            msg["timestamp"],
                        ]
                    )

                print(
                    tabulate(
                        table_data,
                        headers=["Type", "Message", "Timestamp"],
                        tablefmt="grid",
                    )
                )

        elif command == "chat delete":
            if not client.current_chat_id:
                print_error("No active chat session")
                continue

            client.delete_chat(client.current_chat_id)

        elif command.startswith("send "):
            if not client.current_chat_id:
                print_error("No active chat session")
                continue

            message = command[5:]
            client.send_message(client.current_chat_id, message)

        elif command.startswith("send-file "):
            if not client.current_chat_id:
                print_error("No active chat session")
                continue

            parts = command[10:].split(" ", 1)
            if len(parts) != 2:
                print_error("Usage: send-file <file> <message>")
                continue

            file_path, message = parts
            client.send_message(client.current_chat_id, message, [file_path])

        elif command.startswith("upload "):
            file_path = command[7:]
            client.upload_document(file_path)

        elif command.startswith("search "):
            query = command[7:]
            results = client.search_documents(query)
            if results:
                for i, doc in enumerate(results):
                    print(f"\n{Colors.BOLD}Document {i + 1}:{Colors.ENDC}")
                    print(f"Content: {doc['content'][:200]}...")
                    print(f"Metadata: {doc['metadata']}")

        elif command.startswith("websearch "):
            query = command[10:]
            results = client.web_search(query)
            if results:
                print(f"\n{Colors.BOLD}Web Search Results:{Colors.ENDC}")
                for result in results.get("results", []):
                    print(f"Title: {result.get('title')}")
                    print(f"URL: {result.get('url')}")
                    print(f"Snippet: {result.get('snippet')}\n")

        elif command == "health":
            client.health_check()

        else:
            print_error(f"Unknown command: {command}")
            print_info("Type 'help' for available commands")


def run_automated_tests(client: OrchestratorClient):
    """Run automated tests against the orchestrator service"""
    print_header("Running Automated Tests")

    # Keep track of pass/fail count
    passed = 0
    failed = 0

    def test_case(name, test_func):
        nonlocal passed, failed
        print_info(f"Test: {name}")
        try:
            result = test_func()
            if result:
                passed += 1
                print_success("PASSED")
            else:
                failed += 1
                print_error("FAILED")
        except Exception as e:
            failed += 1
            print_error(f"EXCEPTION: {str(e)}")
        print("")

    # Test 1: Health check
    test_case("Health Check", lambda: client.health_check())

    # Test 2: Create new chat
    chat_id = None

    def test_create_chat():
        nonlocal chat_id
        chat_id = client.create_chat()
        return chat_id is not None

    test_case("Create Chat", test_create_chat)

    # Test 3: Send message
    message_response = None

    def test_send_message():
        nonlocal message_response
        message_response = client.send_message(
            chat_id, "This is a test message from automated tests"
        )
        return message_response is not None

    if chat_id:
        test_case("Send Message", test_send_message)

        # Test 4: Get chat history
        def test_get_history():
            history = client.get_chat_history(chat_id)
            return (
                history is not None and len(history) >= 2
            )  # At least user message + response

        test_case("Get Chat History", test_get_history)

        # Test 5: Delete chat
        test_case("Delete Chat", lambda: client.delete_chat(chat_id))

    # Test 6: Web search
    def test_web_search():
        results = client.web_search("What is LangGraph?")
        return results is not None

    test_case("Web Search", test_web_search)

    # Print summary
    print_header("Test Summary")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total: {passed + failed}")

    return failed == 0


def main():
    """Main entry point for the CLI tool"""
    parser = argparse.ArgumentParser(
        description="CLI tool for testing the orchestrator service"
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_SERVER_URL,
        help=f"Base URL of the orchestrator service (default: {DEFAULT_SERVER_URL})",
    )
    parser.add_argument("--test", action="store_true", help="Run automated tests")

    args = parser.parse_args()

    client = OrchestratorClient(base_url=args.url)

    if args.test:
        success = run_automated_tests(client)
        sys.exit(0 if success else 1)
    else:
        interactive_mode(client)


if __name__ == "__main__":
    main()
