import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/server';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

describe('App Integration Tests', () => {
    const user = userEvent.setup();

    beforeEach(() => {
        // Clear any previous test state
        localStorage.clear();
        sessionStorage.clear();
    });

    test('complete chat flow - send message and receive response', async () => {
        render(<App />);

        const input = await screen.findByPlaceholderText(/type a message/i);
        const sendButton = screen.getByRole('button', { name: /send/i });

        // Type and send a message
        await user.type(input, 'Hello, AI!');
        await user.click(sendButton);

        // Verify message appears in chat
        expect(await screen.findByText('Hello, AI!')).toBeInTheDocument();

        // Wait for the AI response
        await waitFor(
            () => expect(screen.getByText('Message received')).toBeInTheDocument(),
            { timeout: 5000 }
        );
    });

    test('file upload in chat', async () => {
        render(<App />);

        const file = new File(['test content'], 'test.txt', { type: 'text/plain' });
        const input = await screen.findByPlaceholderText(/type a message/i);
        const fileInput = screen.getByLabelText(/upload file/i);

        // Upload file and send message
        await user.upload(fileInput, file);
        await user.type(input, 'Here is a file');
        await user.click(screen.getByRole('button', { name: /send/i }));

        // Verify both message and file appear
        expect(await screen.findByText(/test.txt/i)).toBeInTheDocument();
        expect(screen.getByText('Here is a file')).toBeInTheDocument();

        // Verify successful upload message
        await waitFor(
            () => expect(screen.getByText('Message received')).toBeInTheDocument(),
            { timeout: 5000 }
        );
    });

    test('error handling - network error', async () => {
        server.use(
            http.post(`${API_BASE_URL}/chat/message`, () => {
                return new HttpResponse(null, { status: 0 });
            })
        );

        render(<App />);

        const input = await screen.findByPlaceholderText(/type a message/i);
        await user.type(input, 'This will fail');
        await user.click(screen.getByRole('button', { name: /send/i }));

        // Verify error message appears
        await waitFor(
            () => {
                const errorMessage = screen.getByText(/network error/i);
                expect(errorMessage).toBeInTheDocument();
                expect(errorMessage).toHaveTextContent(/check your internet connection/i);
            },
            { timeout: 3000 }
        );
    });

    test('error handling - server error', async () => {
        server.use(
            http.post(`${API_BASE_URL}/chat/message`, () => {
                return HttpResponse.json(
                    {
                        success: false,
                        error: {
                            code: 'INTERNAL_ERROR',
                            message: 'Internal server error'
                        }
                    },
                    { status: 500 }
                );
            })
        );

        render(<App />);

        const input = await screen.findByPlaceholderText(/type a message/i);
        await user.type(input, 'This will cause a server error');
        await user.click(screen.getByRole('button', { name: /send/i }));

        // Verify error message appears
        await waitFor(
            () => {
                const errorMessage = screen.getByText(/server encountered an error/i);
                expect(errorMessage).toBeInTheDocument();
                expect(errorMessage).toHaveTextContent(/try again later/i);
            },
            { timeout: 3000 }
        );
    });

    test('large file upload rejection', async () => {
        render(<App />);

        const largeFile = new File(['x'.repeat(11 * 1024 * 1024)], 'large.txt');
        const fileInput = screen.getByLabelText(/upload file/i);

        await user.upload(fileInput, largeFile);

        // Verify error message appears immediately (client-side validation)
        const errorMessage = await screen.findByText(/file size limit/i);
        expect(errorMessage).toBeInTheDocument();
        expect(errorMessage).toHaveTextContent(/10MB/i);
    });

    test('retry mechanism for transient errors', async () => {
        // Mock a server that fails twice then succeeds
        let attemptCount = 0;
        server.use(
            http.post(`${API_BASE_URL}/chat/message`, () => {
                attemptCount++;
                if (attemptCount < 3) {
                    return HttpResponse.json(
                        { error: 'Service unavailable' },
                        { status: 503 }
                    );
                }
                return HttpResponse.json({
                    success: true,
                    data: { message: 'Message received after retry' }
                });
            })
        );

        render(<App />);

        const input = await screen.findByPlaceholderText(/type a message/i);
        await user.type(input, 'This should retry and succeed');
        await user.click(screen.getByRole('button', { name: /send/i }));

        // Verify success message appears after retries
        await waitFor(
            () => expect(screen.getByText('Message received after retry')).toBeInTheDocument(),
            { timeout: 10000 }
        );
    });
});