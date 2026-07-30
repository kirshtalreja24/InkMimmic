import { ScrollView, View, Text } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Button } from '../components/ui/Button.jsx';
import { Card } from '../components/ui/Card.jsx';
import { InkDivider } from '../components/ui/InkDivider.jsx';
import { InkWordmark } from '../components/ui/InkWordmark.jsx';

const STEPS = [
  {
    title: 'Upload a sample',
    body: 'Photograph or attach a page you already wrote. One paragraph is enough.',
  },
  {
    title: 'Tell it what you need',
    body: 'Ask for a cleaner copy, a longer version, or the same note in a steadier hand.',
  },
  {
    title: 'Get your page back',
    body: "Inkmimic hands back a new artifact that still looks unmistakably like your own writing.",
  },
];

export default function LandingScreen({ navigation }) {
  return (
    <LinearGradient colors={['#080B22', '#0C1030', '#10143B']} className="flex-1">
      <ScrollView contentContainerStyle={{ paddingBottom: 48 }} className="px-6 pt-16">
        <View className="items-center">
          <Text className="mb-4 font-script text-lg text-royal-400">
            for people who'd rather write than type
          </Text>
          <InkWordmark fontSize={44} />
          <Text className="mt-4 text-center font-display text-3xl leading-tight text-parchment">
            turns typed words into <Text className="text-gold-300">your</Text> handwriting.
          </Text>
          <Text className="mt-6 text-center font-body text-base leading-relaxed text-parchment/60">
            Attach one sample of how you write. Ask for what you need. Get back a page in the same
            ink, the same slant, the same hand.
          </Text>

          <View className="mt-8 w-full gap-3">
            <Button label="Get started" onPress={() => navigation.navigate('Auth')} />
            <Button
              label="About us"
              variant="outline"
              onPress={() => navigation.navigate('About')}
            />
          </View>
        </View>

        <View className="mt-14">
          <View className="mb-6 flex-row items-center gap-3">
            <InkDivider />
            <Text className="font-body text-xs uppercase tracking-widest text-parchment/40">
              How it works
            </Text>
          </View>

          <View className="gap-4">
            {STEPS.map((step, i) => (
              <Card key={step.title}>
                <Text className="font-script text-2xl text-royal-400">{i + 1}</Text>
                <Text className="mt-2 font-display text-lg text-parchment">{step.title}</Text>
                <Text className="mt-1 font-body text-sm leading-relaxed text-parchment/55">
                  {step.body}
                </Text>
              </Card>
            ))}
          </View>
        </View>

        <View className="mt-10 items-center gap-4 rounded-2xl border border-royal-500/20 bg-ink-900/70 px-6 py-10">
          <Text className="text-center font-display text-2xl text-parchment">
            Your handwriting, on demand.
          </Text>
          <Text className="text-center font-body text-sm text-parchment/55">
            No new alphabet to learn — just the page you meant to write, whenever you need it
            again.
          </Text>
          <Button label="Start writing" onPress={() => navigation.navigate('Auth')} />
        </View>
      </ScrollView>
    </LinearGradient>
  );
}
