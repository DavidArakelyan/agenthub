# AgentHub

A modern chat interface application built with React and TypeScript, featuring a ChatGPT-like experience with file attachments and chat history management.

## Features

- Modern chat interface with ChatGPT-like design
- File attachment support with drag-and-drop
- Chat history management with local storage
- Multiple chat sessions
- Real-time message updates
- Responsive design
- Canvas panel for additional content

## Tech Stack

- React
- TypeScript
- CSS3
- Local Storage for data persistence

## Getting Started

### Prerequisites

- Node.js (v14 or higher)
- npm or yarn

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/agenthub.git
cd agenthub
```

2. Install dependencies:
```bash
npm install
# or
yarn install
```

3. Start the development server:
```bash
npm start
# or
yarn start
```

The application will be available at `http://localhost:3000`.

## Project Structure

```
services/
  └── frontend/
      ├── src/
      │   ├── App.tsx        # Main application component
      │   ├── App.css        # Application styles
      │   └── index.tsx      # Application entry point
      └── package.json       # Project dependencies
```

## Usage

1. Click "New Chat" to start a new conversation
2. Type your message in the input area
3. Attach files by clicking the attachment button or dragging files
4. Press Enter or click the send button to send your message
5. View your chat history in the sidebar
6. Switch between different chats by clicking on them in the sidebar

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 