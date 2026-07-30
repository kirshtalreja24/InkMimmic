import Svg, { Path } from 'react-native-svg';

export function InkDivider({ color = '#F6F1E6', width = 160, height = 12 }) {
  return (
    <Svg width={width} height={height} viewBox="0 0 240 16" fill="none">
      <Path
        d="M2 8c20-6 40-6 60 0s40 6 60 0 40-6 60 0 40 6 56 0"
        stroke={color}
        strokeWidth={2.5}
        strokeLinecap="round"
      />
    </Svg>
  );
}
