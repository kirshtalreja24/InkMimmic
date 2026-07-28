import { createBrowserRouter } from 'react-router-dom';
import LandingPage from './pages/LandingPage.jsx';
import AboutUsPage from './pages/AboutUsPage.jsx';
import AuthPage from './pages/AuthPage.jsx';
import ChatWorkspace from './pages/ChatWorkspace.jsx';
import { ProtectedRoute } from './components/layout/ProtectedRoute.jsx';

export const router = createBrowserRouter([
  { path: '/', element: <LandingPage /> },
  { path: '/about', element: <AboutUsPage /> },
  { path: '/auth', element: <AuthPage /> },
  {
    path: '/workspace',
    element: (
      <ProtectedRoute>
        <ChatWorkspace />
      </ProtectedRoute>
    ),
  },
]);
