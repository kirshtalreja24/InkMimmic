import { NavigationContainer, DarkTheme } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import LandingScreen from '../screens/LandingScreen.jsx';
import AboutScreen from '../screens/AboutScreen.jsx';
import AuthScreen from '../screens/AuthScreen.jsx';
import ChatWorkspaceScreen from '../screens/ChatWorkspaceScreen.jsx';
import { useAuth } from '../hooks/useAuth.js';
import { isSupabaseConfigured } from '../config/env.js';

const Stack = createNativeStackNavigator();

// React Navigation v7 requires a `fonts` object on any theme passed to
// NavigationContainer — base ours on DarkTheme so that comes for free,
// and only override the colors to match Inkmimic's palette.
const navTheme = {
  ...DarkTheme,
  colors: {
    ...DarkTheme.colors,
    primary: '#FFC93C',
    background: '#080B22',
    card: '#0C1030',
    text: '#F6F1E6',
    border: '#1D2359',
    notification: '#FFC93C',
  },
};

export function RootNavigator() {
  const { isAuthenticated, loading } = useAuth();

  // Without Supabase configured there's no session to check — let Workspace
  // through so the UI (and the ai-prototype chat) can still be exercised
  // during setup, same fallback the webapp uses.
  const showWorkspace = !isSupabaseConfigured || isAuthenticated;

  if (isSupabaseConfigured && loading) return null; // brief splash-equivalent

  return (
    <NavigationContainer theme={navTheme}>
      {showWorkspace ? (
        // Signed-in tree: swapping to this entirely separate Stack.Navigator
        // (rather than conditionally adding one screen to a shared tree) is
        // what lets React Navigation land on Workspace automatically the
        // moment auth state changes — no manual navigate() call needed or
        // safe to make, since the screen doesn't exist until this swap.
        <Stack.Navigator screenOptions={{ headerShown: false }}>
          <Stack.Screen name="Workspace" component={ChatWorkspaceScreen} />
        </Stack.Navigator>
      ) : (
        <Stack.Navigator screenOptions={{ headerShown: false }}>
          <Stack.Screen name="Landing" component={LandingScreen} />
          <Stack.Screen name="About" component={AboutScreen} />
          <Stack.Screen name="Auth" component={AuthScreen} />
        </Stack.Navigator>
      )}
    </NavigationContainer>
  );
}