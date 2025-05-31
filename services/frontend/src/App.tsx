import React, { useState, KeyboardEvent, useRef, useEffect, useCallback } from 'react';
import { apiClient, ChatMessage } from './services/api';

// Import Prism core components first as they must be loaded before the main Prism object
import 'prismjs/components/prism-core';
import 'prismjs/components/prism-clike';
// Then import the main Prism object
import Prism from 'prismjs';

// Then import other language components
import 'prismjs/components/prism-javascript'; // JS depends on clike
import 'prismjs/components/prism-c'; // Import C first as C++ depends on it
import 'prismjs/components/prism-cpp'; // C++ depends on C
import 'prismjs/components/prism-python'; // Add Python language support
import 'prismjs/components/prism-java'; // Add Java language support

// Add diagnostic logging
console.log('Prism loaded:', !!Prism);
console.log('Languages available:', Object.keys(Prism.languages));
console.log('C language available:', !!Prism.languages.c);
console.log('C++ language available:', !!Prism.languages.cpp);
console.log('Python language available:', !!Prism.languages.python);
console.log('Java language available:', !!Prism.languages.java);
console.log('JavaScript language available:', !!Prism.languages.javascript);

// Markdown support
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
// FontAwesome imports
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faFileCode, faFileAlt, faFile, faCopy, faExpand } from '@fortawesome/free-solid-svg-icons';
// Prism styling
import 'prismjs/themes/prism-tomorrow.css';
import './language-styles.css'; // Import additional language styling
import './code-styling.css'; // Import code-specific styling improvements
import './App.css';

interface AttachedFile {
    file: File;
    id: string;
}

interface Chat {
    id: string;
    name: string;
    messages: ChatMessage[];
    createdAt: Date;
    updatedAt: Date;
}

interface GeneratedContent {
    type: 'Code' | 'Document' | string;
    format: string;
    content: string;
}

// Helper function to map content format to Prism language class
const getLanguageClass = (format: string | undefined, type: string | undefined): string => {
    if (!format) return 'text';

    // Normalize format to lowercase
    const formatLower = format.toLowerCase();

    // Special case for Python - make sure it's properly recognized
    if (formatLower === 'py' || formatLower === 'python') {
        return 'python';
    }

    // Map based on format
    const formatMap: Record<string, string> = {
        // Programming languages
        'py': 'python',
        'python': 'python',  // Explicitly add both py and python
        'ts': 'typescript',
        'js': 'javascript',
        'java': 'java',
        'cpp': 'cpp',
        'c': 'c',
        'cs': 'csharp',
        'csharp': 'csharp',
        'rb': 'ruby',
        'ruby': 'ruby',
        'go': 'go',
        'rs': 'rust',
        'rust': 'rust',
        'swift': 'swift',
        'php': 'php',
        'kt': 'kotlin',
        'kotlin': 'kotlin',
        'scala': 'scala',
        'dart': 'dart',
        'elm': 'elm',
        'haskell': 'haskell',
        'hs': 'haskell',
        'perl': 'perl',
        'pl': 'perl',
        'r': 'r',
        'vb': 'vbnet',
        'vbnet': 'vbnet',
        'lisp': 'lisp',
        'clj': 'clojure',
        'clojure': 'clojure',
        'groovy': 'groovy',
        'fsharp': 'fsharp',
        'fs': 'fsharp',
        'tsx': 'tsx',
        'jsx': 'jsx',

        // Markup & configuration
        'md': 'markdown',
        'markdown': 'markdown',
        'html': 'markup',
        'xml': 'markup',
        'svg': 'markup',
        'css': 'css',
        'scss': 'scss',
        'sass': 'sass',
        'less': 'less',
        'json': 'json',
        'yaml': 'yaml',
        'yml': 'yaml',
        'toml': 'toml',
        'ini': 'ini',
        'graphql': 'graphql',
        'gql': 'graphql',

        // Shell scripts
        'sh': 'bash',
        'bash': 'bash',
        'zsh': 'bash',
        'ps1': 'powershell',
        'powershell': 'powershell',
        'bat': 'batch',
        'cmd': 'batch',

        // Data formats
        'sql': 'sql',
        'mysql': 'sql',
        'pgsql': 'sql',
        'txt': 'text',
        'csv': 'text',
        'tsv': 'text',
        'regex': 'regex',

        // Document formats 
        'doc': 'text',
        'pdf': 'text',
        'tex': 'latex',
        'latex': 'latex',
        'diff': 'diff',
        'patch': 'diff',
    };

    // If we have a type, use it to refine our language class decision
    if (type && type.toLowerCase() === 'code') {
        // If it's explicitly code but format isn't in our map, default to a generic code highlighting
        if (!formatMap[formatLower]) {
            return 'clike';
        }
    } else if (type && type.toLowerCase() === 'document') {
        // For documents without a specific format or with doc/pdf format, prefer markdown
        if (!format || formatLower === 'doc' || formatLower === 'pdf') {
            return 'markdown';
        }
    }

    // Return the mapped language or the original format as fallback
    return formatMap[formatLower] || formatLower;
};

// Helper function to get an appropriate icon for a content type
const getContentTypeIcon = (type: string | undefined) => {
    if (!type) return faFileCode;

    const typeLower = type.toLowerCase();
    switch (typeLower) {
        case 'code':
            return faFileCode;
        case 'document':
            return faFileAlt;
        default:
            return faFile;
    }
};

// Simple function to detect Python code based on patterns
const detectPythonCode = (content: string): boolean => {
    if (!content) return false;

    // Simple detection for Python code (minimal patterns for basic detection)
    const pythonPatterns = [
        /\bdef\s+\w+\s*\(/,        // Function definitions
        /\bimport\s+\w+/,          // Import statements
        /^\s*if\s+.*:\s*$/m,       // If statements with colon
    ];

    // At least one pattern must match
    return pythonPatterns.some(pattern => pattern.test(content));
};

// Simple function to detect language from code content
const detectLanguage = (content: string): string | null => {
    if (!content || content.trim().length < 20) return null;

    // Simplified minimal language detection for basic code classification
    // This is a fallback for when backend doesn't specify target_format
    const patterns: { [key: string]: RegExp[] } = {
        'js': [/\bfunction\s+\w+\s*\(/, /\bconst\s+\w+\s*=/],
        'ts': [/:\s*\w+/, /interface\s+\w+/],
        'py': [/\bdef\s+\w+\s*\(/, /\bimport\s+/],
        'html': [/<\w+[^>]*>/, /<\/\w+>/] // Removed unnecessary escapes for < and >
    };

    // Simple pattern matching to find the most likely language
    for (const [lang, langPatterns] of Object.entries(patterns)) {
        if (langPatterns.some(pattern => pattern.test(content))) {
            return lang;
        }
    }

    return null;
};

function App() {
    const [chats, setChats] = useState<Chat[]>([]);
    const [currentChatId, setCurrentChatId] = useState<string | null>(null);
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState('');
    const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([]);
    const [canvas, setCanvas] = useState<GeneratedContent[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [isDragging, setIsDragging] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [serverSaveEnabled, setServerSaveEnabled] = useState<{ [key: number]: boolean }>({});
    const [canvasWidth, setCanvasWidth] = useState<number>(400);
    const [isResizing, setIsResizing] = useState<boolean>(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const triggerSyntaxHighlighting = useCallback(() => {
        console.log('Global triggerSyntaxHighlighting: Attempting Prism.highlightAll()');
        setTimeout(() => {
            try {
                Prism.highlightAll();
                console.log('Global triggerSyntaxHighlighting: Prism.highlightAll() executed.');
            } catch (error) {
                console.error('Error during global syntax highlighting:', error);
            }
        }, 100);
    }, []);

    // Load chats from localStorage on initial render
    useEffect(() => {
        // Load canvas width from localStorage
        const savedWidth = localStorage.getItem('canvasWidth');
        if (savedWidth) {
            setCanvasWidth(parseInt(savedWidth));
        }

        // Load saved chats
        const savedChats = localStorage.getItem('chats');
        if (savedChats) {
            const parsedChats = JSON.parse(savedChats).map((chat: any) => ({
                ...chat,
                createdAt: new Date(chat.createdAt),
                updatedAt: new Date(chat.updatedAt)
            }));
            setChats(parsedChats);
            if (parsedChats.length > 0) {
                setCurrentChatId(parsedChats[0].id);
                loadChatHistory(parsedChats[0].id);
            }
        }
    }, []);

    // Save chats to localStorage whenever they change
    useEffect(() => {
        localStorage.setItem('chats', JSON.stringify(chats));
    }, [chats]);

    // useEffect for serverSaveEnabled state, depends only on canvas
    useEffect(() => {
        setServerSaveEnabled(prevServerSaveEnabled => {
            const newServerSaveState = { ...prevServerSaveEnabled };
            let changed = false;
            canvas.forEach((_, index) => {
                if (!(index in newServerSaveState)) {
                    newServerSaveState[index] = true; // Default to checked (true)
                    changed = true;
                }
            });
            // Only update state if something actually changed to prevent unnecessary re-renders
            return changed ? newServerSaveState : prevServerSaveEnabled;
        });
    }, [canvas]); // Only depends on canvas

    const loadChatHistory = async (chatId: string) => {
        try {
            const history = await apiClient.getChatHistory(chatId);
            setMessages(history);
        } catch (error) {
            console.error('Error loading chat history:', error);
            setError('Failed to load chat history');
        }
    };

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
        // Trigger syntax highlighting for code blocks in messages
        if (messages.length > 0) {
            triggerSyntaxHighlighting(); // Call the useCallback version
        }
    }, [messages, triggerSyntaxHighlighting]);

    const generateChatName = (firstMessage: string) => {
        const maxLength = 30;
        const truncatedMessage = firstMessage.length > maxLength
            ? firstMessage.substring(0, maxLength) + '...'
            : firstMessage;
        return truncatedMessage;
    };

    const createNewChat = async () => {
        try {
            setIsLoading(true);
            setError(null);

            // Check connection first
            const isConnected = await apiClient.checkConnection();
            if (!isConnected) {
                throw new Error('Cannot connect to the server. Please check if the orchestrator service is running.');
            }

            const chatId = await apiClient.createNewChat();
            const newChat: Chat = {
                id: chatId,
                name: 'New Chat',
                messages: [],
                createdAt: new Date(),
                updatedAt: new Date()
            };
            setChats(prev => [newChat, ...prev]);
            setCurrentChatId(chatId);
            setMessages([]);
            setCanvas([]);
            setAttachedFiles([]);
        } catch (error) {
            console.error('Error creating new chat:', error);
            setError(error instanceof Error ? error.message : 'Failed to create new chat');

            // If we have existing chats, don't show the error banner
            // as the user can still use existing chats
            if (chats.length === 0) {
                // If no chats exist, show a retry button
                setError(prev => prev + ' Click here to retry.');
            }
        } finally {
            setIsLoading(false);
        }
    };

    const switchChat = async (chatId: string) => {
        try {
            const chat = chats.find(c => c.id === chatId);
            if (chat) {
                setCurrentChatId(chatId);
                await loadChatHistory(chatId);
                setCanvas([]); // Reset canvas when switching chats
                setAttachedFiles([]);
            }
        } catch (error) {
            console.error('Error switching chat:', error);
            setError('Failed to switch chat');
        }
    };

    const handleSend = async () => {
        if ((!input.trim() && attachedFiles.length === 0) || !currentChatId) return;

        try {
            setIsLoading(true);
            setError(null);

            const newMessage: ChatMessage = {
                id: Math.random().toString(36).substr(2, 9),
                text: input,
                type: 'user',
                files: attachedFiles.map(f => f.file),
                timestamp: new Date().toISOString()
            };

            const updatedMessages = [...messages, newMessage];
            setMessages(updatedMessages);

            // Update chat name if this is the first message
            if (updatedMessages.length === 1) {
                const chatName = generateChatName(input);
                setChats(prev => prev.map(chat =>
                    chat.id === currentChatId
                        ? { ...chat, name: chatName, messages: updatedMessages, updatedAt: new Date() }
                        : chat
                ));
            }

            // Send to backend
            const response = await apiClient.sendMessage(
                currentChatId,
                input,
                attachedFiles.map(f => f.file)
            );

            // Response is now normalized in the API client to the ChatResponse type

            // Add response to messages
            const responseMessage: ChatMessage = {
                id: Math.random().toString(36).substr(2, 9),
                text: response.message,
                type: 'reply',
                timestamp: new Date().toISOString()
            };

            const finalMessages = [...updatedMessages, responseMessage];
            setMessages(finalMessages);

            // Update canvas if there's generated content
            if (response.canvas_content) {
                // Determine content type based on available information
                let contentType = 'Code'; // Default type
                let format = response.target_format || 'text';

                // Check if we can infer type from format
                if (response.target_format) {
                    const documentFormats = ['md', 'txt', 'doc', 'pdf'];
                    const codeFormats = ['py', 'js', 'ts', 'java', 'cpp', 'c', 'cs', 'rb', 'go', 'rs', 'swift', 'php'];

                    const formatLower = response.target_format.toLowerCase();
                    if (documentFormats.includes(formatLower)) {
                        contentType = 'Document';
                    } else if (codeFormats.includes(formatLower)) {
                        contentType = 'Code';
                    }
                } else {
                    // Try to detect Python code if no format is specified
                    if (detectPythonCode(response.canvas_content)) {
                        format = 'py';
                        contentType = 'Code';
                        console.log('Auto-detected Python code');
                    }
                }

                // Create a GeneratedContent object from the raw content
                const normalizedContent: GeneratedContent = {
                    // Set the content type (Code or Document)
                    type: contentType,
                    // Use target_format if available, otherwise default to 'text' or detected format
                    format: format,
                    // The canvas_content is the actual raw content string
                    content: response.canvas_content
                };

                // Further processing on the content to try to detect language type if not specified
                if (normalizedContent.format === 'text' && normalizedContent.type === 'Code') {
                    // Try to auto-detect common programming languages
                    const detectedLanguage = detectLanguage(normalizedContent.content);
                    if (detectedLanguage) {
                        normalizedContent.format = detectedLanguage;
                        console.log(`Setting format to ${detectedLanguage} based on content analysis`);
                    }
                }
                // The useEffect hook observing 'canvas' will handle the highlighting.
                // No direct call to triggerSyntaxHighlighting() here anymore.
                setCanvas(prevCanvas => [...prevCanvas, normalizedContent]);
            }

            // Update chat in state
            setChats(prev => prev.map(chat =>
                chat.id === currentChatId
                    ? { ...chat, messages: finalMessages, updatedAt: new Date() }
                    : chat
            ));

            setInput('');
            setAttachedFiles([]);
        } catch (error) {
            console.error('Error sending message:', error);
            setError('Failed to send message');
            // Add error message to chat
            const errorMessage: ChatMessage = {
                id: Math.random().toString(36).substr(2, 9),
                text: 'Sorry, there was an error processing your message. Please try again.',
                type: 'reply',
                timestamp: new Date().toISOString()
            };
            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyPress = (event: KeyboardEvent<HTMLTextAreaElement>) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            handleSend();
        }
    };

    const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
        if (event.target.files) {
            const newFiles = Array.from(event.target.files).map(file => ({
                file,
                id: Math.random().toString(36).substr(2, 9)
            }));
            setAttachedFiles(prev => [...prev, ...newFiles]);
        }
    };

    const removeFile = (id: string) => {
        setAttachedFiles(prev => prev.filter(f => f.id !== id));
    };

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);

        if (e.dataTransfer.files) {
            const newFiles = Array.from(e.dataTransfer.files).map(file => ({
                file,
                id: Math.random().toString(36).substr(2, 9)
            }));
            setAttachedFiles(prev => [...prev, ...newFiles]);
        }
    };

    const formatFileSize = (bytes: number) => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    const deleteChat = async (chatId: string, event: React.MouseEvent) => {
        event.stopPropagation();
        try {
            await apiClient.deleteChat(chatId);
            setChats(prev => prev.filter(chat => chat.id !== chatId));
            if (currentChatId === chatId) {
                if (chats.length > 1) {
                    const remainingChats = chats.filter(chat => chat.id !== chatId);
                    switchChat(remainingChats[0].id);
                } else {
                    createNewChat();
                }
            }
        } catch (error) {
            console.error('Error deleting chat:', error);
            setError('Failed to delete chat');
        }
    };

    const handleSaveCanvas = async (content: GeneratedContent, index: number) => {
        try {
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            // Ensure we have a valid format, defaulting to 'txt' if missing or if toLowerCase() would fail
            const extension = content.format ? content.format.toLowerCase() : 'txt';
            const filename = `generated_${content.type || 'content'}_${timestamp}.${extension}`;

            // Create a blob and trigger browser download
            const blob = new Blob([content.content], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);

            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            document.body.appendChild(link);
            link.click();

            // Clean up download elements
            document.body.removeChild(link);
            URL.revokeObjectURL(url);

            // Save to server if enabled and use the response
            if (serverSaveEnabled[index]) {
                const { message } = await apiClient.saveContentToServer(
                    content.content,
                    content.format || 'text',
                    filename
                );
                setError(message);
            } else {
                setError(`Successfully downloaded ${filename}`);
            }

            setTimeout(() => setError(null), 3000);
        } catch (error) {
            console.error('Error saving content:', error);
            setError('Failed to save content');
        }
    };

    // useEffect for canvas changes (syntax highlighting)
    useEffect(() => {
        if (canvas.length > 0) {
            const timerId = setTimeout(() => {
                console.log('[Canvas Effect] Attempting Prism.highlightAll(). Current canvas length:', canvas.length);

                // More detailed diagnostics for C/C++ languages
                if (Prism && Prism.languages) {
                    console.log('Available Prism languages:', Object.keys(Prism.languages).join(', '));
                    console.log('C language grammar:', Prism.languages.c ? 'Loaded' : 'Not loaded');
                    console.log('C++ language grammar:', Prism.languages.cpp ? 'Loaded' : 'Not loaded');
                    console.log('Python language grammar:', Prism.languages.python ? 'Loaded' : 'Not loaded');
                    console.log('Java language grammar:', Prism.languages.java ? 'Loaded' : 'Not loaded');

                    // Check for specific tokens in the C++ grammar to verify it's properly loaded
                    if (Prism.languages.cpp) {
                        console.log('C++ grammar keys:', Object.keys(Prism.languages.cpp).slice(0, 10).join(', ') + '...');
                    }

                    // Check for specific tokens in the Python grammar to verify it's properly loaded
                    if (Prism.languages.python) {
                        console.log('Python grammar keys:', Object.keys(Prism.languages.python).slice(0, 10).join(', ') + '...');
                    }

                    // Check for specific tokens in the Java grammar to verify it's properly loaded
                    if (Prism.languages.java) {
                        console.log('Java grammar keys:', Object.keys(Prism.languages.java).slice(0, 10).join(', ') + '...');
                    }

                    // Log specific canvas content language classes
                    canvas.forEach((content, idx) => {
                        const langClass = getLanguageClass(content.format, content.type);
                        console.log(`Canvas item ${idx} language class: ${langClass}, Prism has grammar: ${!!Prism.languages[langClass]}`);
                    });
                } else {
                    console.log('[Canvas Effect] Prism or Prism.languages not available.');
                }

                try {
                    Prism.highlightAll();
                    console.log('[Canvas Effect] Prism.highlightAll() executed.');
                } catch (e) {
                    console.error('[Canvas Effect] Error during Prism.highlightAll():', e);
                }
            }, 200); // Increased delay slightly

            return () => clearTimeout(timerId);
        }
    }, [canvas]); // Only depends on canvas

    // Function to toggle code block expansion
    const toggleCodeExpansion = (index: number) => {
        const codeBlock = document.querySelector(`.canvas-content:nth-child(${index + 1}) pre`);
        if (codeBlock) {
            codeBlock.classList.toggle('expanded');
        }
    };

    // Function to copy code to clipboard
    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text).then(
            () => {
                // Show feedback to the user
                setError("Code copied to clipboard!");
                setTimeout(() => setError(null), 1500);

                // Create visual feedback element
                const feedbackEl = document.createElement('div');
                feedbackEl.className = 'copy-success';
                feedbackEl.textContent = 'Copied to clipboard!';
                document.body.appendChild(feedbackEl);

                // Remove feedback element after animation
                setTimeout(() => {
                    if (document.body.contains(feedbackEl)) {
                        document.body.removeChild(feedbackEl);
                    }
                }, 1500);
            },
            err => {
                console.error('Error copying to clipboard:', err);
                setError('Failed to copy to clipboard');
            }
        );
    };

    // Canvas resizing handlers - RESTORED
    const handleResizeMove = useCallback((e: MouseEvent) => {
        if (!isResizing) return;
        const containerWidth = window.innerWidth;
        const distanceFromRight = containerWidth - e.clientX;
        const maxWidth = Math.min(containerWidth * 0.5, 800);
        const newWidth = Math.max(300, Math.min(maxWidth, distanceFromRight));
        setCanvasWidth(newWidth);
    }, [isResizing]);

    const handleResizeEnd = useCallback(() => {
        setIsResizing(false);
        document.removeEventListener('mousemove', handleResizeMove);
        document.removeEventListener('mouseup', handleResizeEnd);
        document.body.classList.remove('resizing');
        localStorage.setItem('canvasWidth', canvasWidth.toString());
    }, [canvasWidth, handleResizeMove]); // Added handleResizeMove to deps

    useEffect(() => {
        if (isResizing) {
            document.addEventListener('mousemove', handleResizeMove);
            document.addEventListener('mouseup', handleResizeEnd);
        }
        return () => {
            document.removeEventListener('mousemove', handleResizeMove);
            document.removeEventListener('mouseup', handleResizeEnd);
        };
    }, [isResizing, handleResizeMove, handleResizeEnd]);

    const handleResizeStart = (e: React.MouseEvent) => {
        e.preventDefault();
        setIsResizing(true);
        document.body.classList.add('resizing');
    };

    useEffect(() => {
        return () => {
            document.body.classList.remove('resizing');
        };
    }, []);

    return (
        <div className="App">
            {error && (
                <div className="error-banner" onClick={() => {
                    if (chats.length === 0) {
                        createNewChat();
                    } else {
                        setError(null);
                    }
                }}>
                    {error}
                    <button onClick={(e) => {
                        e.stopPropagation();
                        setError(null);
                    }}>×</button>
                </div>
            )}
            <div className="chat-layout">
                <div className="sidebar">
                    <button className="new-chat-button" onClick={createNewChat}>
                        + New Chat
                    </button>
                    <div className="chat-history">
                        {chats.map(chat => (
                            <div
                                key={chat.id}
                                className={`chat-item ${currentChatId === chat.id ? 'active' : ''}`}
                                onClick={() => switchChat(chat.id)}
                            >
                                <div className="chat-item-content">
                                    <span className="chat-name">{chat.name}</span>
                                    <span className="chat-date">
                                        {new Date(chat.updatedAt).toLocaleDateString()}
                                    </span>
                                </div>
                                <button
                                    className="delete-chat"
                                    onClick={(e) => deleteChat(chat.id, e)}
                                    title="Delete chat"
                                >
                                    ×
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
                <div className="main-content">
                    {!currentChatId ? (
                        <div className="welcome-screen">
                            <h1>Welcome to AgentHub</h1>
                            <p>Click "New Chat" to start a conversation</p>
                        </div>
                    ) : (
                        <>
                            <div className="messages-container">
                                {messages.length === 0 ? (
                                    <div className="welcome-message">
                                        <h1>AgentHub Chat</h1>
                                        <p>Start a conversation with the AI assistant</p>
                                    </div>
                                ) : (
                                    messages.map((msg, index) => (
                                        <div key={index} className={`message-wrapper ${msg.type}`}>
                                            <div className="message-content">
                                                <div className="message-header">
                                                    <span className="message-label">
                                                        {msg.type === 'user' ? 'You' : 'Assistant'}
                                                    </span>
                                                </div>
                                                <div className="message-text">
                                                    <ReactMarkdown
                                                        remarkPlugins={[remarkGfm]}
                                                        components={{
                                                            code({ node, inline, className, children, ...props }: any) {
                                                                const match = /language-(\w+)/.exec(className || '');
                                                                const language = match ? match[1] : '';

                                                                return !inline && language ? (
                                                                    <pre className={`language-${language}`}>
                                                                        <code className={`language-${language}`} {...props}>
                                                                            {String(children).replace(/\n$/, '')}
                                                                        </code>
                                                                    </pre>
                                                                ) : (
                                                                    <code className={className} {...props}>
                                                                        {children}
                                                                    </code>
                                                                );
                                                            }
                                                        }}
                                                    >
                                                        {msg.text}
                                                    </ReactMarkdown>
                                                </div>
                                                {msg.files && msg.files.length > 0 && (
                                                    <div className="message-files">
                                                        {msg.files.map((file, fileIndex) => (
                                                            <div key={fileIndex} className="file-preview">
                                                                <span className="file-name">{file.name}</span>
                                                                <span className="file-size">{formatFileSize(file.size)}</span>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    ))
                                )}
                                {isLoading && (
                                    <div className="message-wrapper reply">
                                        <div className="message-content">
                                            <div className="message-header">
                                                <span className="message-label">Assistant</span>
                                            </div>
                                            <div className="message-text">
                                                <div className="typing-indicator">
                                                    <span></span>
                                                    <span></span>
                                                    <span></span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                )}
                                <div ref={messagesEndRef} />
                            </div>
                            <div className="input-area">
                                {attachedFiles.length > 0 && (
                                    <div className="attached-files">
                                        {attachedFiles.map(({ file, id }) => (
                                            <div key={id} className="file-tag">
                                                <span className="file-name">{file.name}</span>
                                                <span className="file-size">{formatFileSize(file.size)}</span>
                                                <button
                                                    className="remove-file"
                                                    onClick={() => removeFile(id)}
                                                    title="Remove file"
                                                >
                                                    ×
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                )}
                                <div
                                    className={`input-container ${isDragging ? 'dragging' : ''}`}
                                    onDragOver={handleDragOver}
                                    onDragLeave={handleDragLeave}
                                    onDrop={handleDrop}
                                >
                                    <textarea
                                        value={input}
                                        onChange={(e) => setInput(e.target.value)}
                                        onKeyPress={handleKeyPress}
                                        placeholder="Message AgentHub..."
                                        rows={1}
                                    />
                                    <div className="input-actions">
                                        <button
                                            className="attach-button"
                                            onClick={() => fileInputRef.current?.click()}
                                            title="Attach files"
                                        >
                                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                                                <polyline points="17 8 12 3 7 8" />
                                                <line x1="12" y1="3" x2="12" y2="15" />
                                            </svg>
                                        </button>
                                        <button
                                            className="send-button"
                                            onClick={handleSend}
                                            disabled={(!input.trim() && attachedFiles.length === 0) || isLoading}
                                        >
                                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                <path d="M22 2L11 13M22 2L15 22L11 13L2 9L22 2Z" />
                                            </svg>
                                        </button>
                                    </div>
                                    <input
                                        type="file"
                                        ref={fileInputRef}
                                        onChange={handleFileSelect}
                                        multiple
                                        style={{ display: 'none' }}
                                    />
                                </div>
                                <div className="input-footer">
                                    <span>AgentHub can make mistakes. Consider checking important information.</span>
                                </div>
                            </div>
                        </>
                    )}
                </div>
                <div className="canvas-panel" style={{ width: `${canvasWidth}px` }}>
                    <div className={`canvas-resizer ${isResizing ? 'active' : ''}`} onMouseDown={handleResizeStart}></div>
                    <h2>Generated Content</h2>
                    {canvas.map((content, index) => (
                        <div key={index} className="canvas-content" onClick={() => {
                            // It's generally better to trigger highlighting based on data changes (useEffect)
                            // rather than click events on the whole canvas item,
                            // but leaving as is for now if it serves a specific purpose.
                            // Consider if this specific call is still needed given the useEffect [canvas]
                            triggerSyntaxHighlighting();
                        }}>
                            <div className="canvas-header">
                                <span className={`content-type content-type-${content.type?.toLowerCase() || 'code'}`}>
                                    <FontAwesomeIcon icon={getContentTypeIcon(content.type)} className="content-icon" />
                                    {content.type || 'Content'} - {content.format || 'text'}
                                </span>
                                <div className="save-options">
                                    <div className="save-checkbox">
                                        <input
                                            type="checkbox"
                                            id={`server-save-${index}`}
                                            checked={serverSaveEnabled[index] || false} // Ensure controlled component with boolean
                                            onChange={(e) => setServerSaveEnabled(prev => ({
                                                ...prev,
                                                [index]: e.target.checked
                                            }))}
                                        />
                                        <label htmlFor={`server-save-${index}`}>Keep on server</label>
                                    </div>
                                    <button
                                        className="save-button"
                                        onClick={() => handleSaveCanvas(content, index)}
                                        title="Save to file"
                                    >
                                        Save
                                    </button>
                                </div>
                            </div>
                            {/* Use Prism for syntax highlighting */}
                            <pre className={`language-${getLanguageClass(content.format, content.type)}`}>
                                <code className={`language-${getLanguageClass(content.format, content.type)}`}>
                                    {content.content}
                                </code>
                                {content.format && content.format !== 'text' && (
                                    <div className="language-badge">
                                        {content.format}
                                    </div>
                                )}
                                <div className="code-actions">
                                    <button
                                        className="code-action-btn copy-btn"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            copyToClipboard(content.content);
                                        }}
                                        title="Copy to clipboard"
                                    >
                                        <FontAwesomeIcon icon={faCopy} /> Copy
                                    </button>
                                    <button
                                        className="code-action-btn expand-btn"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            toggleCodeExpansion(index);
                                        }}
                                        title="Expand/collapse code"
                                    >
                                        <FontAwesomeIcon icon={faExpand} /> Expand
                                    </button>
                                </div>
                            </pre>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

export default App;