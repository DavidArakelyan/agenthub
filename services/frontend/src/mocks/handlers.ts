import { http, HttpResponse, delay } from 'msw';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

export const handlers = [
    // Chat creation
    http.post(`${API_BASE_URL}/chat/new`, async () => {
        await delay(100);
        return HttpResponse.json({
            success: true,
            data: { chatId: 'test-chat-id' }
        });
    }),

    // Chat history
    http.get(`${API_BASE_URL}/chat/:chatId/history`, async () => {
        await delay(100);
        return HttpResponse.json({
            success: true,
            data: [
                {
                    id: '1',
                    text: 'Hello',
                    type: 'user',
                    timestamp: new Date().toISOString()
                },
                {
                    id: '2',
                    text: 'Hi there!',
                    type: 'reply',
                    timestamp: new Date().toISOString()
                }
            ]
        });
    }),

    // Message sending
    http.post(`${API_BASE_URL}/chat/message`, async ({ request }) => {
        await delay(200);
        const data = await request.formData();
        const message = data.get('message');
        const files = data.getAll('files');

        return HttpResponse.json({
            success: true,
            data: {
                message: 'Message received',
                task_status: {
                    status: 'completed',
                    steps: [
                        'Message processed successfully',
                        files.length > 0 ? 'File(s) processed successfully' : null
                    ].filter(Boolean)
                }
            }
        });
    }),

    // Document upload
    http.post(`${API_BASE_URL}/documents/upload`, async ({ request }) => {
        await delay(300);
        const data = await request.formData();
        const file = data.get('file') as File;
        const metadata = data.get('metadata');

        return HttpResponse.json({
            success: true,
            data: {
                id: 'doc-123',
                content: await file.text(),
                metadata: metadata ? JSON.parse(metadata as string) : {}
            }
        });
    }),

    // Document search
    http.get(`${API_BASE_URL}/documents/search`, async ({ request }) => {
        await delay(200);
        const url = new URL(request.url);
        const query = url.searchParams.get('query');

        return HttpResponse.json({
            success: true,
            data: [
                {
                    id: 'doc-123',
                    content: `Content matching query: ${query}`,
                    metadata: {}
                }
            ]
        });
    })
];