import React, { useState, useEffect } from 'react';
import LandingPage from './components/LandingPage';
import Auth from './components/Auth';
import Workspace from './components/Workspace';
import { supabase } from './lib/supabase';

export default function App() {
  const [currentView, setCurrentView] = useState('landing');
  const [user, setUser] = useState(null);
  const [savedDocs, setSavedDocs] = useState([]);
  const [authError, setAuthError] = useState('');
  const [loading, setLoading] = useState(false);
  const [isPlaceholderEnv, setIsPlaceholderEnv] = useState(false);

  // Check if env keys are placeholders
  useEffect(() => {
    const url = import.meta.env.VITE_SUPABASE_URL;
    const key = import.meta.env.VITE_SUPABASE_ANON_KEY;
    
    if (!url || !key || url.includes("your-project-id") || key.includes("your-actual-anon-key") || key.startsWith("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")) {
      setIsPlaceholderEnv(true);
    } else {
      setIsPlaceholderEnv(false);
    }
  }, []);

  // Subscribe to Supabase Auth State Changes
  useEffect(() => {
    // 1. Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session?.user) {
        setUser(session.user);
        setCurrentView('workspace');
        fetchDocuments(session.user);
      } else {
        // Fallback check for active demo sessions in localStorage
        const demoUser = localStorage.getItem('scribble_user_demo');
        if (demoUser) {
          try {
            const parsed = JSON.parse(demoUser);
            setUser(parsed);
            setCurrentView('workspace');
            loadDemoDocs();
          } catch (e) {
            console.error("Error parsing demo user", e);
          }
        }
      }
    });

    // 2. Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (session?.user) {
        setUser(session.user);
        setCurrentView('workspace');
        fetchDocuments(session.user);
      } else {
        // Only log out if we are not a demo user
        const demoUser = localStorage.getItem('scribble_user_demo');
        if (!demoUser) {
          setUser(null);
          setSavedDocs([]);
          setCurrentView('landing');
        }
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  // Fetch documents from Supabase
  const fetchDocuments = async (currentUser) => {
    if (!currentUser || currentUser.id === 'demo-user-id') return;
    setLoading(true);
    try {
      const { data, error } = await supabase
        .from('documents')
        .select('*')
        .order('updated_at', { ascending: false });

      if (error) {
        console.error("Error fetching documents from Supabase:", error);
      } else {
        setSavedDocs(data || []);
      }
    } catch (err) {
      console.error("Connection error while fetching documents:", err);
    } finally {
      setLoading(false);
    }
  };

  // Load local demo docs
  const loadDemoDocs = () => {
    const saved = localStorage.getItem('scribble_docs_demo');
    if (saved) {
      try {
        setSavedDocs(JSON.parse(saved));
      } catch (e) {
        console.error("Failed to parse demo docs", e);
      }
    } else {
      setSavedDocs([]);
    }
  };

  // Login handler
  const handleLogin = async (email, password, isDemo = false) => {
    setLoading(true);
    setAuthError('');
    
    if (isDemo) {
      const mockUser = { id: 'demo-user-id', email: 'explorer@scribbleai.com', user_metadata: { full_name: 'Demo Explorer' } };
      setUser(mockUser);
      localStorage.setItem('scribble_user_demo', JSON.stringify(mockUser));
      setCurrentView('workspace');
      loadDemoDocs();
      setLoading(false);
      return;
    }

    if (isPlaceholderEnv) {
      setAuthError("Failed to connect: Your .env file is still using placeholder API keys. Please update it with your real Supabase credentials.");
      setLoading(false);
      return;
    }

    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        setAuthError(error.message);
      } else if (data?.user) {
        localStorage.removeItem('scribble_user_demo');
        localStorage.removeItem('scribble_docs_demo');
        setUser(data.user);
        setCurrentView('workspace');
      }
    } catch (err) {
      setAuthError("Failed to connect to Supabase. Check your connection or .env settings.");
    } finally {
      setLoading(false);
    }
  };

  // Register handler
  const handleRegister = async (email, password, fullName) => {
    setLoading(true);
    setAuthError('');

    if (isPlaceholderEnv) {
      setAuthError("Failed to register: Your .env file is still using placeholder API keys. Please update it with your real Supabase credentials.");
      setLoading(false);
      return;
    }

    try {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            full_name: fullName,
          },
        },
      });

      if (error) {
        setAuthError(error.message);
      } else if (data?.user) {
        if (data.session) {
          localStorage.removeItem('scribble_user_demo');
          localStorage.removeItem('scribble_docs_demo');
          setUser(data.user);
          setCurrentView('workspace');
        } else {
          alert("Account created! Please check your email inbox to verify and log in.");
          setCurrentView('auth');
        }
      }
    } catch (err) {
      setAuthError("Failed to register. Check your connection or .env settings.");
    } finally {
      setLoading(false);
    }
  };

  // Logout handler
  const handleLogout = async () => {
    setLoading(true);
    try {
      localStorage.removeItem('scribble_user_demo');
      localStorage.removeItem('scribble_docs_demo');
      await supabase.auth.signOut();
    } catch (err) {
      console.warn("Error during Supabase signout:", err);
    } finally {
      setUser(null);
      setSavedDocs([]);
      setCurrentView('landing');
      setLoading(false);
    }
  };

  // Document saving handler
  const handleSaveDoc = async (newDoc) => {
    if (!user) return;

    if (user.id === 'demo-user-id') {
      let updatedDocs = [];
      const exists = savedDocs.find(doc => doc.id === newDoc.id);

      if (exists) {
        updatedDocs = savedDocs.map(doc => doc.id === newDoc.id ? newDoc : doc);
      } else {
        updatedDocs = [newDoc, ...savedDocs];
      }

      setSavedDocs(updatedDocs);
      localStorage.setItem('scribble_docs_demo', JSON.stringify(updatedDocs));
      return;
    }

    setLoading(true);
    try {
      const isNewDoc = typeof newDoc.id === 'string' && newDoc.id.length < 30;

      const payload = {
        title: newDoc.title,
        text_content: newDoc.text_content,
        font_style: newDoc.font_style,
        focus_accent: newDoc.focus_accent,
        ink_color: newDoc.ink_color,
        paper_type: newDoc.paper_type,
        font_size: newDoc.font_size,
        line_height: newDoc.line_height,
        margin_left: newDoc.margin_left,
        skew_value: newDoc.skew_value,
        letter_spacing: newDoc.letter_spacing,
        updated_at: new Date().toISOString()
      };

      if (isNewDoc) {
        const { data, error } = await supabase
          .from('documents')
          .insert([{ ...payload, user_id: user.id }])
          .select();

        if (error) throw error;
      } else {
        const { error } = await supabase
          .from('documents')
          .update(payload)
          .eq('id', newDoc.id);

        if (error) throw error;
      }

      await fetchDocuments(user);
    } catch (err) {
      console.error("Error saving document to Supabase:", err);
      alert(`Error saving to cloud: ${err.message || err}`);
    } finally {
      setLoading(false);
    }
  };

  // Document deleting handler
  const handleDeleteDoc = async (id) => {
    if (!user) return;

    if (user.id === 'demo-user-id') {
      const updatedDocs = savedDocs.filter(doc => doc.id !== id);
      setSavedDocs(updatedDocs);
      localStorage.setItem('scribble_docs_demo', JSON.stringify(updatedDocs));
      return;
    }

    setLoading(true);
    try {
      const { error } = await supabase
        .from('documents')
        .delete()
        .eq('id', id);

      if (error) throw error;
      
      await fetchDocuments(user);
    } catch (err) {
      console.error("Error deleting document from Supabase:", err);
      alert(`Error deleting from cloud: ${err.message || err}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      {currentView === 'landing' && (
        <LandingPage 
          onNavigate={setCurrentView} 
          user={user} 
        />
      )}
      
      {currentView === 'auth' && (
        <Auth 
          onLogin={handleLogin} 
          onRegister={handleRegister} 
          onNavigate={setCurrentView} 
          error={authError} 
          loading={loading}
          isPlaceholderEnv={isPlaceholderEnv}
        />
      )}

      {currentView === 'workspace' && (
        <Workspace 
          user={user} 
          onLogout={handleLogout} 
          savedDocs={savedDocs} 
          onSaveDoc={handleSaveDoc} 
          onDeleteDoc={handleDeleteDoc}
          onNavigate={setCurrentView}
        />
      )}
    </div>
  );
}
