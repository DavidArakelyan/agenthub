import React, { useState, KeyboardEvent, useRef, useEffect } from 'react';
import './App.css';

interface Message {
    text: string;
    type: 'user' | 'reply';
    files?: File[];
}

interface AttachedFile {
    file: File;
    id: string;
}

interface Chat {
    id: string;
    name: string;
    messages: Message[];
    createdAt: Date;
    updatedAt: Date;
}

function App() {
    const [chats, setChats] = useState<Chat[]>([]);
    const [currentChatId, setCurrentChatId] = useState<string | null>(null);
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([]);
    const [canvas, setCanvas] = useState<string[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [isDragging, setIsDragging] = useState(false);
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
                setMessages(parsedChats[0].messages);
            }
        }
    }, []);

    // Save chats to localStorage whenever they change
    useEffect(() => {
        localStorage.setItem('chats', JSON.stringify(chats));
    }, [chats]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const generateChatName = (firstMessage: string) => {
        // Truncate the first message to create a chat name
        const maxLength = 30;
        const truncatedMessage = firstMessage.length > maxLength
            ? firstMessage.substring(0, maxLength) + '...'
            : firstMessage;
        return truncatedMessage;
    };

    const createNewChat = () => {
        const newChat: Chat = {
            id: Math.random().toString(36).substr(2, 9),
            name: 'New Chat',
            messages: [],
            createdAt: new Date(),
            updatedAt: new Date()
        };
        setChats(prev => [newChat, ...prev]);
        setCurrentChatId(newChat.id);
        setMessages([]);
        setCanvas([]);
        setAttachedFiles([]);
    };

    const switchChat = (chatId: string) => {
        const chat = chats.find(c => c.id === chatId);
        if (chat) {
            setCurrentChatId(chatId);
            setMessages(chat.messages);
            setCanvas([]); // Reset canvas when switching chats
            setAttachedFiles([]);
        }
    };

    const handleSend = async () => {
        if (input.trim() || attachedFiles.length > 0) {
            const newMessage: Message = {
                text: input,
                type: 'user',
                files: attachedFiles.map(f => f.file)
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
            } else {
                // Update existing chat
                setChats(prev => prev.map(chat =>
                    chat.id === currentChatId
                        ? { ...chat, messages: updatedMessages, updatedAt: new Date() }
                        : chat
                ));
            }

            setIsLoading(true);

            // Simulate API delay
            await new Promise(resolve => setTimeout(resolve, 1000));

            // Simulate a response
            const response: Message = {
                text: `Response to: ${input}${attachedFiles.length > 0 ? ' (with files)' : ''}`,
                type: 'reply'
            };

            const finalMessages = [...updatedMessages, response];
            setMessages(finalMessages);
            setChats(prev => prev.map(chat =>
                chat.id === currentChatId
                    ? { ...chat, messages: finalMessages, updatedAt: new Date() }
                    : chat
            ));

            // Only update canvas if there's generated content
            const generatedContent = Math.random() > 0.5 ? `Generated content for: ${input}` : null;
            if (generatedContent) {
                setCanvas([...canvas, generatedContent]);
            }

            setInput('');
            setAttachedFiles([]);
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

    const clearChat = () => {
        setMessages([]);
        setCanvas([]);
        setAttachedFiles([]);
    };

    const formatFileSize = (bytes: number) => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    const deleteChat = (chatId: string, event: React.MouseEvent) => {
        event.stopPropagation();
        setChats(prev => prev.filter(chat => chat.id !== chatId));
        if (currentChatId === chatId) {
            if (chats.length > 1) {
                const remainingChats = chats.filter(chat => chat.id !== chatId);
                switchChat(remainingChats[0].id);
            } else {
                createNewChat();
            }
        }
    };

    return (
        <div className="App">
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
                    <h2>Canvas</h2>
                    {canvas.map((content, index) => (
                        <div key={index} className="canvas-content">{content}</div>
                    ))}
                </div>
            </div>
        </div>
    );
}

export default App; 