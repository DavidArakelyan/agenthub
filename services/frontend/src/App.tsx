import React, { useState, KeyboardEvent, useRef, useEffect } from 'react';
import { apiClient, ChatMessage, ApiClient } from './services/api';
import Prism from 'prismjs';
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
    type: string;
    format: string;
    content: string;
}

const apiClientInstance = new ApiClient();

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
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Load chats from localStorage on initial render
    useEffect(() => {
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
                setCanvas([...canvas, response.canvas_content]);
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
            const extension = content.format.toLowerCase();
            const filename = `generated_${content.type}_${timestamp}.${extension}`;

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
                    content.format,
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
        Prism.highlightAll();
    }, [canvas]);

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
                                                <div className="message-text">{msg.text}</div>
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
                                            <div className="typing-indicator">
                                                <span></span>
                                                <span></span>
                                                <span></span>
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
                <div className="canvas-panel">
                    <h2>Generated Content</h2>
                    {canvas.map((content, index) => (
                        <div key={index} className="canvas-content">
                            <div className="canvas-header">
                                <span className="content-type">{content.type} - {content.format}</span>
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
                            <pre className={`language-${content.format.toLowerCase()}`}>
                                <code>{content.content}</code>
                            </pre>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

export default App;