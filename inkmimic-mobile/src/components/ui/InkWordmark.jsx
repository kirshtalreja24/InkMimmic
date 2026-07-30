import { useEffect, useRef, useState } from 'react';
import { Animated, Text, View } from 'react-native';
import Svg, { Path, Circle } from 'react-native-svg';

// The signature element of the app: the wordmark writes itself in on load,
// a small pen nib gliding left to right while the word reveals beneath it —
// same effect as the webapp's animated hero wordmark, done with Animated
// instead of CSS clip-path (RN has no clip-path support).
export function InkWordmark({ fontSize = 40 }) {
  const [measuredWidth, setMeasuredWidth] = useState(0);
  const reveal = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (measuredWidth > 0) {
      Animated.timing(reveal, {
        toValue: 1,
        duration: 1400,
        delay: 200,
        useNativeDriver: false, // animating width/layout, not transform/opacity alone
      }).start();
    }
  }, [measuredWidth]);

  const revealWidth = reveal.interpolate({
    inputRange: [0, 1],
    outputRange: [0, measuredWidth],
  });

  return (
    <View>
      {/* Invisible measuring pass — captures the word's natural width once. */}
      {measuredWidth === 0 && (
        <Text
          onLayout={(e) => setMeasuredWidth(e.nativeEvent.layout.width)}
          style={{ fontFamily: 'Caveat_600SemiBold', fontSize, opacity: 0, position: 'absolute' }}
        >
          Inkmimic
        </Text>
      )}

      {measuredWidth > 0 && (
        <View style={{ height: fontSize * 1.3, justifyContent: 'center' }}>
          <Animated.View style={{ width: revealWidth, overflow: 'hidden' }}>
            <Text
              style={{
                fontFamily: 'Caveat_600SemiBold',
                fontSize,
                color: '#FFC93C',
                width: measuredWidth,
              }}
            >
              Inkmimic
            </Text>
          </Animated.View>

          <Animated.View
            style={{
              position: 'absolute',
              top: -fontSize * 0.35,
              left: Animated.subtract(revealWidth, fontSize * 0.4),
            }}
          >
            <Svg width={fontSize * 0.7} height={fontSize * 0.7} viewBox="0 0 28 28">
              <Path
                d="M14 4 L22 14 L14 24 L6 14 Z"
                fill="none"
                stroke="#FFC93C"
                strokeWidth={2}
                strokeLinejoin="round"
              />
              <Circle cx={14} cy={14} r={1.6} fill="#FFC93C" />
            </Svg>
          </Animated.View>
        </View>
      )}
    </View>
  );
}
