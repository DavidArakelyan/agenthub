# Orchestrator Service CLI Testing Tool

This CLI tool provides a convenient way to test the orchestrator service's backend endpoints directly from the command line. It offers both interactive and automated testing modes.

## Features

- Interactive shell for testing the orchestrator service
- Automated test suite for CI/CD pipelines
- Support for all major endpoints:
  - Chat creation and management
  - Message sending and retrieval
  - Document upload and search
  - Web search functionality
- Colorful terminal output for better readability
- File upload support

## Requirements

- Python 3.7+
- The `tabulate` package (automatically installed by the run script)
- Running orchestrator service instance

## Usage

### Interactive Mode

The interactive mode provides a shell-like interface to test the orchestrator service:

```bash
./run_test_cli.sh
```

Once in the interactive shell, you can use the following commands:

- `chat new` - Create a new chat session
- `chat list` - Show current chat ID
- `chat all` - List all available chat sessions
- `chat switch <id>` - Switch to a specific chat session
- `chat history` - Show message history for current chat
- `chat delete` - Delete current chat session
- `send <message>` - Send a message to current chat
- `send-file <file> <message>` - Send a message with a file attachment
- `upload <file>` - Upload a document
- `search <query>` - Search documents
- `websearch <query>` - Perform a web search
- `health` - Check service health
- `help` - Show available commands
- `exit` - Exit interactive mode

### Automated Testing

To run automated tests against the orchestrator service:

```bash
./run_automated_tests.sh
```

This will:
1. Check if the orchestrator service is running
2. Start it if necessary
3. Run the automated test suite, which tests various features including:
   - Service health checks
   - Chat creation and deletion
   - Message sending and retrieval
   - Chat history management
   - Web search functionality
4. Report the results

For CI/CD pipelines, you can use:

```bash
./run_test_cli.sh --test
```

This will exit with a non-zero status code if any tests fail.

### Custom Server URL

By default, the CLI tool connects to `http://localhost:8000`. You can specify a different URL:

```bash
./run_test_cli.sh --url http://example.com:8000
```

## Example Workflow

Here's a typical workflow for manual testing:

1. Start the orchestrator service:
   ```bash
   ./run_orchestrator_no_reload.sh
   ```

2. In another terminal, run the CLI tool:
   ```bash
   ./run_test_cli.sh
   ```

3. Create a new chat session:
   ```
   orchestrator> chat new
   ```

4. Send a message:
   ```
   orchestrator> send What is LangGraph?
   ```

5. View the chat history:
   ```
   orchestrator> chat history
   ```

6. Create another chat session:
   ```
   orchestrator> chat new
   ```

7. List all available chat sessions:
   ```
   orchestrator> chat all
   ```

8. Switch back to the first chat:
   ```
   orchestrator> chat switch <id>
   ```

## Troubleshooting

If you encounter issues:

1. Make sure the orchestrator service is running
2. Check the service health: `health`
3. Verify your terminal supports ANSI color codes
4. If using automated tests, ensure the service URL is correct

## Chat Management Features

The CLI tool supports managing multiple chat sessions:

- **Creating Chats**: Use `chat new` to create a new chat session. The tool will automatically switch to the newly created chat.
- **Listing Chats**: Use `chat all` to see all available chat sessions in a table format, showing their IDs, names, message counts, and last update times.
- **Switching Between Chats**: Use `chat switch <id>` to change the active chat session to one with the specified ID.
- **Current Chat**: The currently active chat is marked with a checkmark (✓) in the chat list.
- **Chat History**: View messages in the current chat with `chat history`.
- **Deleting Chats**: Remove the current chat with `chat delete`.

This allows for testing multiple conversations and switching between them, similar to how a user would interact with the web interface.

## Future Improvements

Planned enhancements:
- Support for batch testing
- Performance benchmarking
- Error analysis and reporting
