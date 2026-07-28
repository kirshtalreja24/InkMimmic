import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { SessionHeader } from '../components/workspace/SessionHeader.jsx';
import { ChatPanel } from '../components/workspace/ChatPanel.jsx';
import { ArtifactPreview } from '../components/workspace/ArtifactPreview.jsx';
import { useAuth } from '../hooks/useAuth.js';

export default function ChatWorkspace() {
  const [state, setState] = useState('idle');
  const [artifact, setArtifact] = useState(null);
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  async function handleCloseSession() {
    await signOut();
    navigate('/');
  }

  function handleNewRequest() {
    setArtifact(null);
    setState('idle');
  }

  return (
    <div className="min-h-screen bg-ink-950 bg-ink-grain px-6 py-10 md:px-10">
      <div className="mx-auto max-w-6xl">
        <SessionHeader userEmail={user?.email} state={state} onCloseSession={handleCloseSession} />

        <div className="mt-8 grid gap-6 md:grid-cols-2 md:items-stretch">
          <div className="ink-panel p-6 md:p-8">
            <ChatPanel state={state} onStateChange={setState} onArtifact={setArtifact} />
          </div>
          <div className="min-h-[420px]">
            <ArtifactPreview artifact={artifact} onNewRequest={handleNewRequest} />
          </div>
        </div>
      </div>
    </div>
  );
}
