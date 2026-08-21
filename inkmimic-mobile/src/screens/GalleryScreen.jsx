import { useEffect, useState } from 'react';
import { ScrollView, View, Text, Image, ActivityIndicator, Pressable } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { File, Paths } from 'expo-file-system';
import * as Sharing from 'expo-sharing';
import { Card } from '../components/ui/Card.jsx';
import { Button } from '../components/ui/Button.jsx';
import { useAuth } from '../hooks/useAuth.js';
import { listArtifacts, getArtifactUrl } from '../lib/supabase/persistence.js';
import { isSupabaseConfigured } from '../config/env.js';

export default function GalleryScreen({ navigation }) {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (!isSupabaseConfigured || !user?.id) {
        setLoading(false);
        return;
      }
      try {
        const rows = await listArtifacts(user.id);
        const withUrls = await Promise.all(
          rows.map(async (row) => ({
            ...row,
            url: await getArtifactUrl(row.storage_path).catch(() => null),
          }))
        );
        if (!cancelled) setItems(withUrls);
      } catch (err) {
        if (!cancelled) setError(err.message ?? 'Failed to load your past generations.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [user?.id]);

  return (
    <LinearGradient colors={['#080B22', '#0C1030', '#10143B']} className="flex-1">
      <ScrollView contentContainerStyle={{ paddingBottom: 48 }} className="px-6 pt-16">
        <Text className="font-script text-lg text-royal-400">your history</Text>
        <Text className="mt-1 font-display text-2xl text-parchment">Past generations</Text>

        <View className="mt-8">
          {!isSupabaseConfigured ? (
            <EmptyState text="Past generations aren't saved in local mode — connect a real Supabase project to enable this." />
          ) : loading ? (
            <ActivityIndicator color="#FFC93C" />
          ) : error ? (
            <Text className="font-body text-sm text-red-300">{error}</Text>
          ) : items.length === 0 ? (
            <EmptyState text="Nothing here yet — generate a page in the Workspace and it'll show up here." />
          ) : (
            <View className="gap-4">
              {items.map((item) => (
                <GalleryCard key={item.id} item={item} />
              ))}
            </View>
          )}
        </View>

        <View className="mt-10">
          <Button variant="outline" label="Back to Workspace" onPress={() => navigation.goBack()} />
        </View>
      </ScrollView>
    </LinearGradient>
  );
}

function GalleryCard({ item }) {
  const [downloading, setDownloading] = useState(false);

  async function handleDownload() {
    if (!item.url || downloading) return;
    setDownloading(true);
    try {
      // Native has no browser-style download -- pull the file into local
      // cache, then hand it to the OS share sheet (Save Image / Save to
      // Files / share) via expo-sharing, the standard Expo pattern for
      // exposing a generated file to the user.
      const file = await File.downloadFileAsync(item.url, Paths.cache);
      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(file.uri);
      }
    } catch {
      // best-effort -- the preview above already shows the file exists
    } finally {
      setDownloading(false);
    }
  }

  return (
    <Card>
      <View
        className="items-center justify-center overflow-hidden rounded-lg bg-white/60"
        style={{ minHeight: 160 }}
      >
        {item.url ? (
          <Image source={{ uri: item.url }} style={{ width: '100%', height: 160 }} resizeMode="contain" />
        ) : (
          <Text className="font-body text-xs text-ink-950/40">Preview unavailable</Text>
        )}
      </View>
      <Text className="mt-3 font-body text-sm text-parchment/80" numberOfLines={2}>
        {item.prompt}
      </Text>
      <View className="mt-1 flex-row items-center justify-between">
        <Text className="font-body text-xs text-parchment/40">
          {new Date(item.created_at).toLocaleString()}
          {item.paper ? ` · ${item.paper} paper` : ''}
        </Text>
        {item.url && (
          <Pressable
            onPress={handleDownload}
            disabled={downloading}
            className="rounded-full border border-gold-300/40 px-3 py-1"
            style={{ opacity: downloading ? 0.4 : 1 }}
          >
            <Text className="font-bodySemibold text-xs text-gold-300/80">
              {downloading ? 'Downloading…' : 'Download'}
            </Text>
          </Pressable>
        )}
      </View>
    </Card>
  );
}

function EmptyState({ text }) {
  return (
    <View className="items-center justify-center rounded-2xl border border-royal-500/15 px-8 py-16">
      <Text className="max-w-xs text-center font-body text-sm text-parchment/40">{text}</Text>
    </View>
  );
}
