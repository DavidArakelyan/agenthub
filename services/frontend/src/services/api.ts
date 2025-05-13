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
    type: 'code' | 'document';
    format: string;
    content: string;
}

export interface Chat {
    id: string;
    name: string;
    messages: ChatMessage[];
    createdAt: string;
    updatedAt: string;
}

export interface ChatResponse {
    message: string;
    canvas_content?: GeneratedContent;
    task_status?: {
        needs_web_search: boolean;
        needs_document_processing: boolean;
    };
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
    private client: AxiosInstance;

    constructor() {
        this.client = axios.create({
            baseURL: API_BASE_URL,
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
                const apiResponse = response.data as ApiResponse<any>;
                if (!apiResponse.success) {
                    throw new ApiError(
                        apiResponse.error?.code || 'UNKNOWN_ERROR',
                        apiResponse.error?.message || 'An unknown error occurred',
                        apiResponse.error?.data
                    );
                }
                return apiResponse.data;
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

    // Chat Operations
    async createNewChat(): Promise<string> {
        try {
            const response = await this.client.post<ApiResponse<{ chatId: string }>>('/chat/new');
            if (!response.data?.success || !response.data.data?.chatId) {
                throw new Error('Invalid response from server: missing chatId');
            }
            return response.data.data.chatId;
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
            const response = await this.client.get<ChatMessage[]>(`/chat/${chatId}/history`);
            return response.data;
        } catch (error) {
            console.error('Error fetching chat history:', error);
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

            const response = await this.client.post<ChatResponse>('/chat/message', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });

            return response.data;
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
        const response = await this.client.post('/save', {
            content,
            format,
            filename
        });
        return response.data;
    }
}

// Export singleton instance
export const apiClient = new ApiClient();