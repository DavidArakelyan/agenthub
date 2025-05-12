import { setupServer } from 'msw/node';
import { handlers } from './handlers';

export const server = setupServer(...handlers);

// Proper error handling for request failures during tests
server.events.on('request:unhandled', (req) => {
    console.error(
        `Found an unhandled ${req.request.method} ${req.request.url} request.\n\n` +
        'Please check your request handler definitions.'
    );
});