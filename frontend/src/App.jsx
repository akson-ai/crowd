import { useEffect, useRef } from 'react';
import './App.css';
import Drawer from './components/Drawer';
import ChatContent from './components/ChatContent';
import KeyboardShortcutsModal from './components/KeyboardShortcutsModal';

// TODO allow editing of messages
// TODO allow forking of chats
// TODO when new chat is persisted, reload chat history
// TODO fix jumping to button when streaming
// TODO add "trim history" button
// TODO add "summarize history" button

// Redirect from root path to /chat with a new UUID
// or generate new UUID if at /chat without ID
if (window.location.pathname === '/' ||
    (window.location.pathname === '/chat' && !new URLSearchParams(window.location.search).get('id'))) {
  const newId = crypto.randomUUID();
  window.location.href = `/chat?id=${newId}`;
}

function App() {
  const abortControllerRef = useRef(null);

  const urlParams = new URLSearchParams(window.location.search);
  const chatId = urlParams.get('id');

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }

      // Add shortcut for keyboard shortcuts modal
      if ((e.metaKey || e.ctrlKey) && e.key === '/') {
        e.preventDefault();
        document.getElementById('shortcuts_modal').showModal();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <>
      <Drawer chatId={chatId}>
        <ChatContent chatId={chatId} abortControllerRef={abortControllerRef} />
      </Drawer>

      <KeyboardShortcutsModal />

      {/* Keyboard shortcuts hint button */}
      <div
        className="fixed bottom-4 right-4 btn btn-sm btn-ghost opacity-60 hover:opacity-100"
        onClick={() => document.getElementById('shortcuts_modal').showModal()}
      >
        <i className="fas fa-keyboard mr-1"></i>
        <span>⌘ + /</span>
      </div>

      {/* Toast notification */}
      <div id="toast" className="toast toast-end hidden">
        <div className="alert alert-success">
          <span id="toast-content"></span>
        </div>
      </div>
    </>
  );
}

export default App;
