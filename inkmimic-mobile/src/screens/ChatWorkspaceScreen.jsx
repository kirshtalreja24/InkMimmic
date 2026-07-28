import { useState } from 'react';
import { ScrollView, View } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { SessionHeader } from '../components/workspace/SessionHeader.jsx';
import { ChatPanel } from '../components/workspace/ChatPanel.jsx';
import { ArtifactPreview } from '../components/workspace/ArtifactPreview.jsx';
import { useAuth } from '../hooks/useAuth.js';

export default function ChatWorkspaceScreen() {
  const [state, setState] = useState('idle');
  const [artifact, setArtifact] = useState(null);
  const { user, signOut } = useAuth();

  // No navigation call here on purpose — same reasoning as AuthScreen.
  // Once signOut() resolves, AuthContext's session becomes null,
  // RootNavigator swaps to the signed-out navigator tree, and Landing
  // becomes the screen automatically.
  async function handleCloseSession() {
    await signOut();
  }

  function handleNewRequest() {
    setArtifact(null);
    setState('idle');
  }

  return (
    <LinearGradient colors={['#080B22', '#0C1030', '#10143B']} className="flex-1">
      <ScrollView contentContainerStyle={{ paddingBottom: 48 }} className="px-6 pt-16">
        <SessionHeader userEmail={user?.email} state={state} onCloseSession={handleCloseSession} />

        <View className="mt-6">
          <ChatPanel state={state} onStateChange={setState} onArtifact={setArtifact} />
        </View>

        <View className="mt-6" style={{ minHeight: 260 }}>
          <ArtifactPreview artifact={artifact} onNewRequest={handleNewRequest} />
        </View>
      </ScrollView>
    </LinearGradient>
  );
}