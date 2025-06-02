import axios, { AxiosInstance, AxiosError } from 'axios';

// API Configuration
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
const MAX_FILE_SIZE = parseInt(process.env.REACT_APP_MAX_FILE_SIZE || '10485760'); // 10MB default

// Types
export interface ChatMessage {
    id: string;
    text: string;
    type: 'user' | 'reply';
    files?: File[];
    timestamp: string;
}

export interface GeneratedContent {
    type: 'code' | 'document' | string;
    format: string;
    content: string;
}

export interface Chat {
    id: string;
    name: string;
    messages: ChatMessage[];
    createdAt: string;
    updatedAt: string;
    canvas?: GeneratedContent[]; // Add canvas property to store generated content
}

export interface ChatResponse {
    message: string;
    canvas_content?: string;
    target_format?: string;
    task_status?: {
        needs_web_search: boolean;
        needs_document_processing: boolean;
    };
}

// Enhanced response structure with success/data wrapper
export interface ApiChatResponse {
    success: boolean;
    data?: ChatResponse;
    error?: ApiErrorResponse;
}

export interface DocumentResponse {
    id: string;
    content: string;
    metadata: Record<string, any>;
}

export interface ApiErrorResponse {
    code: string;
    message: string;
    data?: any;
}

export interface ApiResponse<T> {
    success: boolean;
    data?: T;
    error?: ApiErrorResponse;
}

export class ApiError extends Error {
    code: string;
    data?: any;

    constructor(code: string, message: string, data?: any) {
        super(message);
        this.name = 'ApiError';
        this.code = code;
        this.data = data;
    }
}

// API Client
export class ApiClient {
    private readonly baseUrl: string;
    private client: AxiosInstance;

    constructor() {
        this.baseUrl = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
        this.client = axios.create({
            baseURL: this.baseUrl,
            headers: {
                'Content-Type': 'application/json',
            },
        });

        // Add request interceptor for authentication
        this.client.interceptors.request.use(
            (config) => {
                const token = localStorage.getItem('auth_token');
                if (token) {
                    config.headers.Authorization = `Bearer ${token}`;
                }
                return config;
            },
            (error) => Promise.reject(error)
        );

        // Add response interceptor for error handling
        this.client.interceptors.response.use(
            (response) => {
                // Check if response has the ApiResponse format with success property
                if (response.data && typeof response.data === 'object' && 'success' in response.data) {
                    const apiResponse = response.data as ApiResponse<any>;
                    if (!apiResponse.success) {
                        throw new ApiError(
                            apiResponse.error?.code || 'UNKNOWN_ERROR',
                            apiResponse.error?.message || 'An unknown error occurred',
                            apiResponse.error?.data
                        );
                    }
                    return apiResponse;
                }
                // If it's a direct response (without success wrapper), return it as is
                return response.data;
            },
            (error: AxiosError) => {
                if (error.response?.status === 401) {
                    localStorage.removeItem('auth_token');
                    window.location.href = '/login';
                }

                const apiError = error.response?.data as ApiResponse<any>;
                if (apiError?.error) {
                    throw new ApiError(
                        apiError.error.code,
                        apiError.error.message,
                        apiError.error.data
                    );
                }

                throw new ApiError(
                    'NETWORK_ERROR',
                    error.message || 'Network error occurred'
                );
            }
        );

        this.client.interceptors.request.use(request => {
            console.log('Starting Request:', request);
            return request;
        });

        this.client.interceptors.response.use(response => {
            console.log('Response:', response);
            return response;
        });
    }

    // Add a getter if you need to access baseUrl from outside
    public getBaseUrl(): string {
        return this.baseUrl;
    }

    async checkConnection(): Promise<boolean> {
        try {
            const response = await fetch(`${this.baseUrl}/health`);
            return response.status === 200;
        } catch (error) {
            return false;
        }
    }

    // Chat Operations
    async createNewChat(): Promise<string> {
        try {
            const response = await this.client.post<any>('/chat/new');

            // Handle the unified response format
            if (response.data && typeof response.data === 'object' && 'success' in response.data) {
                const apiResponse = response.data as ApiResponse<{ chatId: string }>;
                if (apiResponse.success && apiResponse.data?.chatId) {
                    return apiResponse.data.chatId;
                } else if (!apiResponse.success && apiResponse.error) {
                    throw new ApiError(
                        apiResponse.error.code || 'CHAT_CREATION_ERROR',
                        apiResponse.error.message || 'Failed to create new chat',
                        apiResponse.error.data
                    );
                }
            }

            // Handle legacy format
            if (!response.data?.chatId) {
                throw new Error('Invalid response from server: missing chatId');
            }
            return response.data.chatId;
        } catch (error) {
            if (error instanceof AxiosError) {
                console.error('Error creating new chat:', {
                    status: error.response?.status,
                    data: error.response?.data,
                    message: error.message
                });
                if (error.response?.status === 404) {
                    throw new Error('Chat endpoint not found. Please check if the backend server is running.');
                } else if (error.response?.status === 500) {
                    throw new Error('Server error while creating chat. Please try again later.');
                }
            }
            throw new Error('Failed to create new chat. Please check your connection and try again.');
        }
    }

    async getChatHistory(chatId: string): Promise<ChatMessage[]> {
        try {
            const response = await this.client.get<any>(`/chat/${chatId}/history`);

            // Handle the unified response format
            if (response.data && typeof response.data === 'object' && 'success' in response.data) {
                const apiResponse = response.data as ApiResponse<ChatMessage[]>;
                if (apiResponse.success && apiResponse.data) {
                    return apiResponse.data;
                } else if (!apiResponse.success && apiResponse.error) {
                    throw new ApiError(
                        apiResponse.error.code || 'CHAT_HISTORY_ERROR',
                        apiResponse.error.message || 'Failed to fetch chat history',
                        apiResponse.error.data
                    );
                }
            }

            // Return legacy format directly
            return response.data;
        } catch (error) {
            console.error('Error loading chat history:', error);
            throw new Error('Failed to fetch chat history');
        }
    }

    async sendMessage(chatId: string, message: string, files: File[] = []): Promise<ChatResponse> {
        try {
            // Validate file sizes
            const oversizedFiles = files.filter(file => file.size > MAX_FILE_SIZE);
            if (oversizedFiles.length > 0) {
                throw new Error(`Files exceed maximum size limit of ${MAX_FILE_SIZE / 1024 / 1024}MB`);
            }

            const formData = new FormData();
            formData.append('chat_id', chatId);
            formData.append('message', message);
            files.forEach(file => {
                formData.append('files', file);
            });

            // Use the unified response format or legacy format
            const response = await this.client.post<any>('/chat/message', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });

            // Handle both response formats
            if (response.data && typeof response.data === 'object' && 'success' in response.data) {
                // New format with success/data wrapper
                const apiResponse = response.data as ApiResponse<ChatResponse>;
                if (apiResponse.success && apiResponse.data) {
                    return apiResponse.data;
                } else if (!apiResponse.success && apiResponse.error) {
                    throw new ApiError(
                        apiResponse.error.code || 'UNKNOWN_ERROR',
                        apiResponse.error.message || 'An unknown error occurred',
                        apiResponse.error.data
                    );
                }
            }

            // Legacy format without wrapper
            return response.data as ChatResponse;
        } catch (error) {
            console.error('Error sending message:', error);
            throw error;
        }
    }

    async deleteChat(chatId: string): Promise<void> {
        try {
            await this.client.delete(`/chat/${chatId}`);
        } catch (error) {
            console.error('Error deleting chat:', error);
            throw new Error('Failed to delete chat');
        }
    }

    // Document Operations
    async uploadDocument(file: File, metadata?: Record<string, any>): Promise<DocumentResponse> {
        try {
            console.log('Uploading document:', file, metadata); // Log the request
            if (file.size > MAX_FILE_SIZE) {
                throw new Error(`File exceeds maximum size limit of ${MAX_FILE_SIZE / 1024 / 1024}MB`);
            }

            const formData = new FormData();
            formData.append('file', file);
            if (metadata) {
                formData.append('metadata', JSON.stringify(metadata));
            }

            const response = await this.client.post<DocumentResponse>('/documents/upload', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });

            console.log('Document uploaded successfully:', response.data); // Log the response
            return response.data;
        } catch (error) {
            console.error('Error uploading document:', error);
            throw error;
        }
    }

    async searchDocuments(query: string, k: number = 4): Promise<DocumentResponse[]> {
        try {
            const response = await this.client.get<DocumentResponse[]>('/documents/search', {
                params: { query, k }
            });
            return response.data;
        } catch (error) {
            console.error('Error searching documents:', error);
            throw new Error('Failed to search documents');
        }
    }

    // Web Search Operations
    async performWebSearch(query: string): Promise<any> {
        try {
            const response = await this.client.get('/websearch/search', {
                params: { query }
            });
            return response.data;
        } catch (error) {
            console.error('Error performing web search:', error);
            throw new Error('Failed to perform web search');
        }
    }

    // Save Content to Server
    async saveContentToServer(content: string, format: string, filename: string): Promise<{ path: string, message: string }> {
        try {
            const response = await this.client.post<any>('/save', {
                content,
                format,
                filename
            });

            // Handle the unified response format
            if (response.data && typeof response.data === 'object' && 'success' in response.data) {
                const apiResponse = response.data as ApiResponse<{ path: string, message: string }>;
                if (apiResponse.success && apiResponse.data) {
                    return apiResponse.data;
                } else if (!apiResponse.success && apiResponse.error) {
                    throw new ApiError(
                        apiResponse.error.code || 'SAVE_CONTENT_ERROR',
                        apiResponse.error.message || 'Failed to save content',
                        apiResponse.error.data
                    );
                }
            }

            // Return legacy format directly
            return response.data;
        } catch (error) {
            console.error('Error saving content:', error);
            throw error;
        }
    }
}

// Export singleton instance
export const apiClient = new ApiClient();