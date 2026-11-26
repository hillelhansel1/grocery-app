import { useState, type ReactNode } from 'react';
import { Image, Pressable, StyleSheet, Text, TextInput, View, type TextInputProps, type TextProps } from 'react-native';

import { direction, number, t } from './locale';
import type { Product } from './mockData';

export const colors = {
  canvas: '#F5F7F2',
  surface: '#FFFFFF',
  ink: '#18382A',
  muted: '#4C6357',
  accent: '#216349',
  soft: '#E8F2E9',
  border: '#D8E3DA',
  warning: '#794819',
  paleWarning: '#F9EDDA',
};
export const space = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24 };
export const radius = { control: 12, card: 20 };
export const logicalText = {
  textAlign: direction === 'rtl' ? 'right' : 'left',
  writingDirection: direction,
} as const;

export const layout = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: space.sm },
  wrap: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: space.sm },
  stack: { gap: space.md },
  grow: { flex: 1 },
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.card,
    padding: space.lg,
    gap: space.md,
  },
});

export function Copy({ kind = 'body', style, ...props }: TextProps & {
  kind?: 'title' | 'heading' | 'body' | 'muted' | 'strong' | 'price';
}) {
  return <Text {...props} style={[styles.text, styles[kind], style]} />;
}

export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <View style={layout.stack}>
      <Copy kind="heading" accessibilityRole="header">{title}</Copy>
      {children}
    </View>
  );
}

export function Button({ label, onPress, variant = 'soft', accessibilityLabel, role = 'button', selected, disabled }: {
  label: string;
  onPress: () => void;
  variant?: 'soft' | 'primary' | 'plain';
  accessibilityLabel?: string;
  role?: 'button' | 'tab';
  selected?: boolean;
  disabled?: boolean;
}) {
  return (
    <Pressable
      accessibilityRole={role}
      accessibilityLabel={accessibilityLabel ?? label}
      accessibilityState={{ selected, disabled }}
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button, styles[variant], selected && styles.selected,
        (pressed || disabled) && styles.pressed,
      ]}
    >
      <Copy kind="strong" style={variant === 'primary' ? styles.onPrimary : undefined}>{label}</Copy>
    </Pressable>
  );
}

export function Field(props: TextInputProps) {
  return <TextInput placeholderTextColor={colors.muted} {...props} style={styles.field} />;
}

export function ProductImage({ product }: { product: Product }) {
  const [failed, setFailed] = useState(false);
  return (
    <View style={styles.thumbnail} accessible={false} importantForAccessibility="no-hide-descendants">
      {product.image && !failed ? (
        <Image source={product.image} style={styles.image} onError={() => setFailed(true)} />
      ) : (
        <View style={styles.placeholder}>
          <View style={styles.placeholderHandle} />
        </View>
      )}
    </View>
  );
}

export function Quantity({ label, value, onChange }: {
  label: string;
  value: number;
  onChange: (quantity: number) => void;
}) {
  return (
    <View style={layout.row}>
      <Button
        label="−"
        accessibilityLabel={t.decrease + ' · ' + label}
        disabled={value <= 1}
        onPress={() => onChange(value - 1)}
      />
      <Copy kind="strong" accessibilityLabel={t.units(number.format(value))}>{number.format(value)}</Copy>
      <Button label="+" accessibilityLabel={t.increase + ' · ' + label} onPress={() => onChange(value + 1)} />
    </View>
  );
}

const styles = StyleSheet.create({
  text: { color: colors.ink, fontSize: 16, ...logicalText },
  title: { fontSize: 34, fontWeight: '800' },
  heading: { fontSize: 21, fontWeight: '700' },
  body: { fontSize: 16 },
  muted: { color: colors.muted, fontSize: 14 },
  strong: { fontWeight: '700' },
  price: { fontSize: 25, fontWeight: '800', color: colors.accent },
  button: {
    minWidth: 48,
    minHeight: 48,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radius.control,
    paddingHorizontal: space.md,
    paddingVertical: space.sm,
  },
  soft: { backgroundColor: colors.soft },
  primary: { backgroundColor: colors.accent },
  plain: { backgroundColor: 'transparent' },
  onPrimary: { color: colors.surface },
  selected: { borderWidth: 1, borderColor: colors.accent },
  pressed: { opacity: 0.66 },
  field: {
    ...logicalText,
    minHeight: 52,
    color: colors.ink,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.control,
    paddingHorizontal: space.lg,
    fontSize: 16,
  },
  thumbnail: {
    width: 48,
    height: 48,
    borderRadius: radius.control,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.soft,
    overflow: 'hidden',
  },
  image: { width: '100%', height: '100%', resizeMode: 'contain' },
  placeholder: {
    width: 19,
    height: 16,
    borderWidth: 1.5,
    borderColor: colors.accent,
    borderRadius: 4,
    alignItems: 'center',
    justifyContent: 'center',
  },
  placeholderHandle: { width: 8, height: 1.5, backgroundColor: colors.accent },
});
