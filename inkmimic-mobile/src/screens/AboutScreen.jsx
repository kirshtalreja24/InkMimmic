import { ScrollView, View, Text } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Card } from '../components/ui/Card.jsx';
import { Button } from '../components/ui/Button.jsx';

export default function AboutScreen({ navigation }) {
  return (
    <LinearGradient colors={['#080B22', '#0C1030', '#10143B']} className="flex-1">
      <ScrollView contentContainerStyle={{ paddingBottom: 48 }} className="px-6 pt-16">
        <Text className="font-script text-lg text-royal-400">about us</Text>
        <Text className="mt-2 font-display text-3xl text-parchment">
          We think handwriting is worth keeping.
        </Text>
        <Text className="mt-4 font-body text-base leading-relaxed text-parchment/60">
          Inkmimic started from a simple annoyance: typing feels efficient, but it flattens
          everything to the same font. We wanted a way to keep the personal shape of handwriting
          without redoing the writing by hand every time.
        </Text>

        <View className="mt-8 gap-4">
          <Card>
            <Text className="font-display text-lg text-parchment">What we build</Text>
            <Text className="mt-2 font-body text-sm leading-relaxed text-parchment/55">
              A workspace where you attach one sample of your handwriting, describe what you need,
              and get back a new page — regenerated in that same hand.
            </Text>
          </Card>
          <Card>
            <Text className="font-display text-lg text-parchment">What we don't do</Text>
            <Text className="mt-2 font-body text-sm leading-relaxed text-parchment/55">
              We don't store your samples anywhere you can't see, and we don't use your
              handwriting for anything beyond the request you asked for.
            </Text>
          </Card>
        </View>

        <View className="mt-10 gap-4 border-t border-royal-500/15 pt-8">
          <Text className="font-body text-parchment/50">
            Ready to try it with your own handwriting?
          </Text>
          <Button label="Get started" onPress={() => navigation.navigate('Auth')} />
        </View>
      </ScrollView>
    </LinearGradient>
  );
}
