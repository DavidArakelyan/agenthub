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

export interface Chat {
    id: string;
    name: string;
    messages: ChatMessage[];
    createdAt: string;
    updatedAt: string;
}

export interface ChatResponse {
    message: string;
    canvas_content?: string;
    task_status?: {
        status: 'completed' | 'processing' | 'failed';
        steps: string[];
    };
}

export interface DocumentResponse {
    id: string;
    content: string;
    metadata: Record<string, any>;
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
            (response) => response,
            (error: AxiosError) => {
                if (error.response?.status === 401) {
                    // Handle unauthorized access
                    localStorage.removeItem('auth_token');
                    window.location.href = '/login';
                }
                return Promise.reject(error);
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
            const response = await this.client.post<{ chatId: string }>('/chat/new');
            if (!response.data || !response.data.chatId) {
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
            formData.append('message', message);
            formData.append('chatId', chatId);

            files.forEach((file, index) => {
                formData.append(`file${index}`, file);
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
}

// Export singleton instance
export const apiClient = new ApiClient(); 