import React, { useState, KeyboardEvent, useRef, useEffect, useCallback } from 'react';
import { apiClient, ChatMessage, ApiClient } from './services/api';
import Prism from 'prismjs';
// Markdown support
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
// FontAwesome imports
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faFileCode, faFileAlt, faFile, faCopy, faExpand, faCompress } from '@fortawesome/free-solid-svg-icons';
// Core prismjs styles
import 'prismjs/themes/prism-tomorrow.css';
// Core prism
import 'prismjs/components/prism-core';
// Basic languages
import 'prismjs/components/prism-clike';
// Individual languages
import 'prismjs/components/prism-python';
import 'prismjs/components/prism-javascript';
import 'prismjs/components/prism-typescript';
import 'prismjs/components/prism-java';
import 'prismjs/components/prism-c';
import 'prismjs/components/prism-cpp';
import 'prismjs/components/prism-markup';
import 'prismjs/components/prism-markdown';
import 'prismjs/components/prism-css';
import 'prismjs/components/prism-json';
import 'prismjs/components/prism-bash';
import 'prismjs/components/prism-sql';
import 'prismjs/components/prism-yaml';
// Additional languages
import 'prismjs/components/prism-csharp';
import 'prismjs/components/prism-ruby';
import 'prismjs/components/prism-go';
import 'prismjs/components/prism-rust';
import 'prismjs/components/prism-swift';
import 'prismjs/components/prism-php';
import 'prismjs/components/prism-kotlin';
import 'prismjs/components/prism-scala';
import 'prismjs/components/prism-ini';
import 'prismjs/components/prism-powershell';
import './App.css';
import './language-styles.css'; // Import additional language styling
import './code-styling.css'; // Import code-specific styling improvements

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

const apiClientInstance = new ApiClient();

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
        'rb': 'ruby',
        'go': 'go',
        'rs': 'rust',
        'swift': 'swift',
        'php': 'php',
        'kt': 'kotlin',
        'scala': 'scala',

        // Markup & configuration
        'md': 'markdown',
        'html': 'markup',
        'xml': 'markup',
        'css': 'css',
        'json': 'json',
        'yaml': 'yaml',
        'yml': 'yaml',
        'toml': 'toml',
        'ini': 'ini',

        // Shell scripts
        'sh': 'bash',
        'bash': 'bash',
        'zsh': 'bash',
        'ps1': 'powershell',

        // Data formats
        'sql': 'sql',
        'txt': 'text',
        'csv': 'text',
        'tsv': 'text',

        // Document formats 
        'doc': 'text',
        'pdf': 'text',
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
    const [canvasWidth, setCanvasWidth] = useState<number>(400); // Default width
    const [isResizing, setIsResizing] = useState<boolean>(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

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
            triggerSyntaxHighlighting();
        }
    }, [messages]);

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

            // Update messages state
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

                setCanvas([...canvas, normalizedContent]);

                // Ensure syntax highlighting is applied
                setTimeout(() => triggerSyntaxHighlighting(), 100);
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

    useEffect(() => {
        const newServerSaveState = { ...serverSaveEnabled };
        canvas.forEach((_, index) => {
            if (!(index in newServerSaveState)) {
                newServerSaveState[index] = true; // Default to checked
            }
        });
        setServerSaveEnabled(newServerSaveState);
    }, [canvas, serverSaveEnabled]);

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

    // Initialize Prism highlighting after content updates
    useEffect(() => {
        // Force Prism to re-highlight everything when canvas changes
        if (canvas.length > 0) {
            // Give the DOM a chance to update before highlighting
            setTimeout(() => {
                try {
                    console.log('Highlighting code with Prism.js');
                    Prism.highlightAll();
                    // Apply manual Python highlighting after Prism
                    setTimeout(() => manuallyHighlightPython(), 200);
                } catch (error) {
                    console.error('Error while highlighting code:', error);
                    // Fallback to manual highlighting
                    manuallyHighlightPython();
                }
            }, 100); // Slightly longer timeout to ensure DOM is updated
        }
    }, [canvas]);

    // Special handling for Python syntax highlighting
    useEffect(() => {
        if (canvas.length > 0) {
            // Check if we have any Python content
            const hasPythonContent = canvas.some(content =>
                content.format?.toLowerCase() === 'py' ||
                content.format?.toLowerCase() === 'python'
            );

            if (hasPythonContent) {
                console.log('Python content detected, ensuring proper highlighting');
                // Multiple triggers with increasing delays to ensure highlighting works
                // even if DOM updates are slow
                setTimeout(() => Prism.highlightAll(), 100);
                setTimeout(() => Prism.highlightAll(), 500);
                setTimeout(() => Prism.highlightAll(), 1000);
            }
        }
    }, [canvas]);

    // Function to manually trigger Prism highlighting
    const triggerSyntaxHighlighting = () => {
        console.log('Manually triggering syntax highlighting');
        // Wait a bit for the DOM to update
        setTimeout(() => {
            try {
                Prism.highlightAll();
                // After Prism has done its work, apply our manual Python highlighting
                setTimeout(() => manuallyHighlightPython(), 50);

                // Also highlight any code blocks in Markdown messages
                document.querySelectorAll('.message-text pre code').forEach((block) => {
                    if (block.className.includes('language-')) {
                        Prism.highlightElement(block);
                    }
                });
            } catch (error) {
                console.error('Error during syntax highlighting:', error);
                // Fallback to manual Python highlighting if Prism fails
                manuallyHighlightPython();
            }
        }, 100);
    };

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

    // Canvas resizing handlers
    const handleResizeMove = useCallback((e: MouseEvent) => {
        if (!isResizing) return;

        // Calculate new width based on window width and mouse position
        const containerWidth = window.innerWidth;
        // Calculate mouse position from right edge of screen
        const distanceFromRight = containerWidth - e.clientX;

        // Min: 300px, Max: 50% of window width or 800px (whichever is smaller)
        const maxWidth = Math.min(containerWidth * 0.5, 800);
        const newWidth = Math.max(300, Math.min(maxWidth, distanceFromRight));

        setCanvasWidth(newWidth);
    }, [isResizing]);

    const handleResizeEnd = useCallback(() => {
        setIsResizing(false);

        // Remove event listeners
        document.removeEventListener('mousemove', handleResizeMove);
        document.removeEventListener('mouseup', handleResizeEnd);

        // Remove the resize class from body
        document.body.classList.remove('resizing');

        // Save width preference to localStorage
        localStorage.setItem('canvasWidth', canvasWidth.toString());
    }, [canvasWidth]);

    // Fix circular dependency between handleResizeMove and handleResizeEnd
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
        // The actual event listeners are set in the useEffect above

        // Add a resize class to the body to disable text selection during resize
        document.body.classList.add('resizing');
    };

    // Clean up any remaining event listeners on component unmount
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
                            triggerSyntaxHighlighting();
                            // If it's Python content, ensure it gets special treatment
                            if (content.format === 'py' || content.format === 'python') {
                                setTimeout(() => manuallyHighlightPython(), 50);
                            }
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
                                            checked={serverSaveEnabled[index]}
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

// Function to manually highlight Python code in case Prism doesn't do it properly
const manuallyHighlightPython = () => {
    // Find all Python code blocks that haven't been highlighted yet
    const pythonBlocks = document.querySelectorAll('code.language-python:not(.python-highlighted)');

    if (pythonBlocks.length === 0) {
        return; // No Python blocks found that need highlighting
    }

    console.log(`Found ${pythonBlocks.length} Python blocks to highlight manually`);

    // Process each block
    pythonBlocks.forEach((block, index) => {
        try {
            // Get the raw content
            const content = block.textContent || '';

            if (content.trim() === '') {
                console.log(`Python block ${index} is empty, skipping`);
                return;
            }

            console.log(`Manually highlighting Python block ${index}`);

            // Use Prism's Python language definition if available
            if (Prism.languages.python) {
                // Highlight the code using Prism's Python grammar
                const highlightedCode = Prism.highlight(
                    content,
                    Prism.languages.python,
                    'python'
                );

                // Set the highlighted HTML
                block.innerHTML = highlightedCode;

                // Add custom CSS class to parent pre element for better styling
                const preElement = block.closest('pre');
                if (preElement) {
                    preElement.classList.add('python-enhanced');
                }

                // Mark as processed
                block.classList.add('python-highlighted');
                console.log(`Successfully highlighted Python block ${index}`);
            } else {
                console.error('Python language definition not found in Prism');
            }
        } catch (err) {
            console.error('Error during manual Python highlighting:', err);

            // Fallback: Apply basic syntax highlighting for common Python elements
            try {
                // Get the raw content again for the fallback
                const content = block.textContent || '';

                // Simple regex-based highlighting for basic Python elements
                let html = content
                    .replace(/\b(def|class|import|from|as|if|else|elif|for|while|return|yield|try|except|finally|with|in|is|not|and|or|True|False|None)\b/g, '<span class="token keyword">$1</span>')
                    .replace(/(?<!\w)(["'])(?:(?=(\\?))\2.)*?\1/g, '<span class="token string">$&</span>')
                    .replace(/(#.*)$/gm, '<span class="token comment">$1</span>')
                    .replace(/\b([0-9]+(?:\.[0-9]+)?)\b/g, '<span class="token number">$1</span>');

                block.innerHTML = html;
                block.classList.add('python-highlighted');
                console.log(`Applied fallback highlighting for Python block ${index}`);
            } catch (fallbackError) {
                console.error('Fallback highlighting also failed:', fallbackError);
            }
        }
    });

    // Apply additional DOM-based styles for Python elements
    document.querySelectorAll('.python-highlighted .token.keyword').forEach(keyword => {
        keyword.classList.add('python-keyword');
    });
};

// Function to detect Python code based on patterns
const detectPythonCode = (content: string): boolean => {
    if (!content) return false;

    // Look for Python-specific patterns
    const pythonPatterns = [
        /\bdef\s+\w+\s*\(/,                    // Function definitions
        /\bclass\s+\w+\s*[:\(]/,               // Class definitions
        /\bimport\s+\w+/,                      // Import statements
        /\bfrom\s+\w+\s+import/,               // From import statements
        /^\s*if\s+.*:\s*$/m,                   // If statements with colon
        /^\s*for\s+.*\s+in\s+.*:\s*$/m,        // For loops
        /^\s*while\s+.*:\s*$/m,                // While loops
        /\bprint\s*\(/,                        // Print function
        /^\s*@\w+/m                            // Decorators
    ];

    // Check if at least 2 patterns match to reduce false positives
    const matchCount = pythonPatterns.filter(pattern => pattern.test(content)).length;
    return matchCount >= 2;
};

// Function to detect language from code content
const detectLanguage = (content: string): string | null => {
    if (!content || content.trim().length < 20) return null;

    // Look for common language patterns
    const patterns: { [key: string]: RegExp[] } = {
        // JavaScript patterns
        'js': [
            /\bconst\s+\w+\s*=/,               // const declarations
            /\blet\s+\w+\s*=/,                 // let declarations
            /\bfunction\s+\w+\s*\(/,           // function declarations
            /=>\s*{/,                          // Arrow functions
            /\bdocument\.\w+/,                 // DOM manipulation
            /\bconsole\.log\(/                 // console.log
        ],

        // TypeScript patterns
        'ts': [
            /:\s*\w+Type\b/,                  // Type annotations
            /interface\s+\w+\s*{/,            // Interface declarations
            /\w+<\w+>/,                       // Generics
            /:\s*string\b/,                   // string type
            /:\s*number\b/,                   // number type
            /:\s*boolean\b/                   // boolean type
        ],

        // Python patterns
        'py': [
            /\bdef\s+\w+\s*\(/,               // Function definitions
            /\bclass\s+\w+\s*[:\(]/,          // Class definitions
            /\bimport\s+\w+/,                 // Import statements
            /\bfrom\s+\w+\s+import/,          // From import statements
            /^\s*if\s+.*:\s*$/m,              // If statements with colon
            /^\s*for\s+.*\s+in\s+.*:\s*$/m    // For loops
        ],

        // Java patterns
        'java': [
            /\bpublic\s+class\s+\w+/,         // Class declarations
            /\bpublic\s+(static\s+)?\w+\s+\w+\s*\(/,  // Method declarations
            /\bSystem\.out\.println\(/,       // Print statements
            /\bnew\s+\w+\s*\(/,               // Object instantiation
            /\bprivate\s+\w+\s+\w+/           // Private fields
        ]
    };

    // Check patterns for each language
    const results: { [key: string]: number } = {};

    for (const [lang, langPatterns] of Object.entries(patterns)) {
        const matchCount = langPatterns.filter(pattern => pattern.test(content)).length;
        results[lang] = matchCount;
    }

    // Find the language with the most matches
    let bestMatch = null;
    let maxMatches = 1; // Require at least 2 matches

    for (const [lang, count] of Object.entries(results)) {
        if (count > maxMatches) {
            maxMatches = count;
            bestMatch = lang;
        }
    }

    return bestMatch;
};

export default App;