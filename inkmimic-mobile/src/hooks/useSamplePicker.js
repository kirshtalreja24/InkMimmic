import { useCallback, useState } from 'react';
import * as ImagePicker from 'expo-image-picker';
import * as DocumentPicker from 'expo-document-picker';

/**
 * Mobile has no drag-and-drop, so this is the equivalent intake point:
 * take a photo, pick one from the library, or pick a PDF/image file from
 * the device. Returns a normalized asset shape so the rest of the app
 * (uploadHandwritingSample, the AI prototype call) doesn't need to know
 * which picker produced it.
 */
export function useSamplePicker() {
  const [asset, setAsset] = useState(null);
  const [error, setError] = useState(null);

  const normalizeImageAsset = (picked) => ({
    uri: picked.uri,
    mimeType: picked.mimeType ?? 'image/jpeg',
    fileName: picked.fileName ?? picked.uri.split('/').pop(),
    width: picked.width,
    height: picked.height,
  });

  const takePhoto = useCallback(async () => {
    setError(null);
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (!permission.granted) {
      setError('Camera access is needed to photograph a handwriting sample.');
      return;
    }
    const result = await ImagePicker.launchCameraAsync({ quality: 0.8 });
    if (!result.canceled) setAsset(normalizeImageAsset(result.assets[0]));
  }, []);

  const pickFromLibrary = useCallback(async () => {
    setError(null);
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      setError('Photo library access is needed to choose a handwriting sample.');
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.8,
    });
    if (!result.canceled) setAsset(normalizeImageAsset(result.assets[0]));
  }, []);

  const pickDocument = useCallback(async () => {
    setError(null);
    const result = await DocumentPicker.getDocumentAsync({
      type: ['image/png', 'image/jpeg', 'image/webp', 'application/pdf'],
    });
    if (!result.canceled) {
      const file = result.assets[0];
      setAsset({
        uri: file.uri,
        mimeType: file.mimeType ?? 'application/octet-stream',
        fileName: file.name,
      });
    }
  }, []);

  const reset = useCallback(() => {
    setAsset(null);
    setError(null);
  }, []);

  return { asset, error, takePhoto, pickFromLibrary, pickDocument, reset };
}
