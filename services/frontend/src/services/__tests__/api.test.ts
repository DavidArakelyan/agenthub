import { http, HttpResponse } from 'msw';
import { server } from '../../mocks/server';
import { apiClient, ApiClient } from '../api';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

describe('API Tests', () => {
    test('createNewChat - successful request', async () => {
        server.use(
            http.post(`${API_BASE_URL}/chat/new`, () => {
                return HttpResponse.json({
                    success: true,
                    data: { chatId: '123' }
                });
            })
        );

        const result = await apiClient.createNewChat();
        expect(result).toBe('123');
    });

    test('createNewChat - network error', async () => {
        server.use(
            http.post(`${API_BASE_URL}/chat/new`, () => {
                return new HttpResponse(null, { status: 0 });
            })
        );

        await expect(apiClient.createNewChat()).rejects.toThrow('Failed to create new chat');
    });

    test('createNewChat - server error', async () => {
        server.use(
            http.post(`${API_BASE_URL}/chat/new`, async () => {
                return HttpResponse.json(
                    {
                        success: false,
                        error: { code: 'SERVER_ERROR', message: 'Server error' }
                    },
                    { status: 500 }
                );
            })
        );

        await expect(apiClient.createNewChat()).rejects.toThrow('Server error while creating chat');
    });

    test('uploadDocument - file size validation', async () => {
        const largeFile = new File(['x'.repeat(11 * 1024 * 1024)], 'large.txt');
        await expect(apiClient.uploadDocument(largeFile)).rejects.toThrow('File exceeds maximum size limit of 10MB');
    });
});