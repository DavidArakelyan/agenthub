# AgentHub Technical Documentation

## System Architecture

AgentHub is built as a microservices architecture consisting of the following components:

1. **Frontend Service**: React-based web application
2. **Orchestrator Service**: Central coordination service
3. **Document Service**: Handles document processing
4. **Web Search Service**: Provides web search functionality

## Frontend Service

The frontend is a React application with TypeScript that provides the user interface for AgentHub.

### Key Components

#### App Component
The main App component manages:
- Chat state management
- Message display and interaction
- Canvas for generated content
- File attachment handling

#### Chat Management
- Maintains multiple chat sessions
- Stores chat history in localStorage
- Provides chat switching and deletion functionality

#### Canvas Implementation
- Renders generated content with syntax highlighting
- Supports multiple programming languages and document formats
- Provides copy/save functionality
- Maintains proper association between chats and canvas content

#### API Integration
- Communicates with backend services
- Handles file uploads and downloads
- Manages error states and loading indicators

### State Management

The application uses React's useState and useEffect hooks to manage:

```typescript
// Main state objects
const [chats, setChats] = useState<Chat[]>([]);
const [currentChatId, setCurrentChatId] = useState<string | null>(null);
const [messages, setMessages] = useState<ChatMessage[]>([]);
const [canvas, setCanvas] = useState<GeneratedContent[]>([]);
```

### Data Structures

```typescript
interface Chat {
    id: string;
    name: string;
    messages: ChatMessage[];
    createdAt: Date;
    updatedAt: Date;
    canvas?: GeneratedContent[]; // Canvas content associated with each chat
}

interface GeneratedContent {
    type: 'Code' | 'Document' | string;
    format: string;
    content: string;
}

interface ChatMessage {
    id: string;
    text: string;
    type: 'user' | 'reply';
    files?: File[];
    timestamp: string;
}
```

### Syntax Highlighting

The frontend uses Prism.js for syntax highlighting with:
- Custom language components for specific languages
- Dark theme styling
- Dynamic language detection

## Orchestrator Service

The orchestrator service is the core backend component that:

1. Processes user queries
2. Classifies query types
3. Coordinates with language models
4. Manages content generation

### Query Classification

The system classifies queries into:
- Simple queries (direct questions)
- Complex queries (requiring code/document generation)
- Update queries (modifying previously generated content)

```python
def query_type_classifier(state: Dict[str, Any]) -> Dict[str, Any]:
    """First level classification: Simple vs Complex and New vs Update"""
    # Implementation determines if query is:
    # 1. Simple or complex
    # 2. New or update
    # 3. Requires web search
    # 4. Requires document processing
```

### Content Generation

Generated content is:
- Tagged with metadata (type, format)
- Stored with unique identifiers
- Linked to originating queries

### Update Detection

The orchestrator implements sophisticated update detection:
- Pattern matching for explicit update requests
- LLM-based classification for implicit updates
- Reference resolution to identify which content to update

## Document Service

Handles document processing tasks:
- File parsing and content extraction
- Document embedding and retrieval
- Contextual analysis of document content

## Web Search Service

Provides web search capabilities:
- Real-time information retrieval
- Search result filtering and processing
- Integration with response generation

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat/new` | POST | Create a new chat session |
| `/chat/{chat_id}/message` | POST | Send a message in a chat |
| `/chat/{chat_id}/history` | GET | Get chat history |
| `/chat/{chat_id}` | DELETE | Delete a chat |
| `/content/save` | POST | Save generated content to server |
| `/status` | GET | Check system status |

## Security Considerations

- All API endpoints validate input data
- User data is stored locally where possible
- Server-side content storage is optional

## Performance Optimizations

- Lazy loading of chat history
- Efficient syntax highlighting with debouncing
- Connection resilience with automatic retries

## Browser Compatibility

Tested and compatible with:
- Chrome (latest 2 versions)
- Firefox (latest 2 versions)
- Safari (latest 2 versions)
- Edge (latest 2 versions)

---

*This technical documentation is intended for developers and system administrators.*
