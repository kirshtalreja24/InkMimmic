import 'react-native-gesture-handler';
import './global.css';
import { useCallback } from 'react';
import { View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import * as SplashScreen from 'expo-splash-screen';
import { cssInterop } from 'nativewind';
import { LinearGradient } from 'expo-linear-gradient';
import {
  useFonts as useFraunces,
  Fraunces_500Medium_Italic,
  Fraunces_600SemiBold,
} from '@expo-google-fonts/fraunces';
import {
  Manrope_400Regular,
  Manrope_600SemiBold,
  Manrope_700Bold,
} from '@expo-google-fonts/manrope';
import { Caveat_600SemiBold } from '@expo-google-fonts/caveat';

import { AuthProvider } from './src/context/AuthContext.jsx';
import { RootNavigator } from './src/navigation/RootNavigator.jsx';

SplashScreen.preventAutoHideAsync();

// LinearGradient is a third-party native component — NativeWind v4 only
// auto-styles core React Native components, so anything else needs to opt
// in explicitly. This tells it "treat className the same as style" for
// LinearGradient specifically, wherever it's used across the app.
cssInterop(LinearGradient, { className: 'style' });

export default function App() {
  const [fontsLoaded] = useFraunces({
    Fraunces_500Medium_Italic,
    Fraunces_600SemiBold,
    Manrope_400Regular,
    Manrope_600SemiBold,
    Manrope_700Bold,
    Caveat_600SemiBold,
  });

  const onLayoutRootView = useCallback(async () => {
    if (fontsLoaded) await SplashScreen.hideAsync();
  }, [fontsLoaded]);

  if (!fontsLoaded) return null;

  return (
    <View style={{ flex: 1 }} onLayout={onLayoutRootView}>
      <SafeAreaProvider>
        <AuthProvider>
          <StatusBar style="light" />
          <RootNavigator />
        </AuthProvider>
      </SafeAreaProvider>
    </View>
  );
}
