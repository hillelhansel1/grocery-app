import { StyleSheet, View } from 'react-native';

import { t } from './locale';
import { products, type ShoppingList } from './mockData';
import { Button, colors, Copy, layout, ProductImage, Quantity, Section, space } from './ui';

export function ListScreen({ list, removed, onUndo, onQuantity, onToggle, onRemove, onSearch, onCompare }: {
  list: ShoppingList;
  removed?: string;
  onUndo: () => void;
  onQuantity: (id: string, value: number) => void;
  onToggle: (id: string) => void;
  onRemove: (id: string) => void;
  onSearch: () => void;
  onCompare: () => void;
}) {
  const pending = list.items.filter((item) => !item.purchased);
  const purchased = list.items.filter((item) => item.purchased);
  const renderItems = (items: ShoppingList['items']) => items.map((item) => {
    const product = products[item.productId];
    const toggleLabel = item.purchased ? t.markPending : t.markPurchased;
    return (
      <View key={item.productId} style={[layout.card, item.purchased && styles.purchased]}>
        <View style={layout.row}>
          <ProductImage product={product} />
          <Copy kind="strong" style={[layout.grow, item.purchased && styles.struck]}>{product.label}</Copy>
        </View>
        <View style={layout.wrap}>
          <Quantity label={product.label} value={item.quantity} onChange={(value) => onQuantity(item.productId, value)} />
          <Button label={toggleLabel} accessibilityLabel={toggleLabel + ' · ' + product.label} onPress={() => onToggle(item.productId)} />
          <Button label={t.remove} accessibilityLabel={t.remove + ' · ' + product.label} variant="plain" onPress={() => onRemove(item.productId)} />
        </View>
      </View>
    );
  });

  return (
    <>
      <View style={layout.wrap}>
        <Button label={t.addProducts} onPress={onSearch} variant="primary" />
        <Button label={t.compareBasket} onPress={onCompare} />
      </View>
      {removed && (
        <View style={[layout.wrap, styles.notice]}>
          <Copy accessibilityLiveRegion="polite" style={layout.grow}>{products[removed].label + ' · ' + t.removed}</Copy>
          <Button label={t.undo} onPress={onUndo} />
        </View>
      )}
      {list.items.length === 0 && <Copy kind="muted">{t.emptyList}</Copy>}
      {renderItems(pending)}
      {purchased.length > 0 && <Section title={t.purchased}>{renderItems(purchased)}</Section>}
    </>
  );
}

const styles = StyleSheet.create({
  purchased: { backgroundColor: colors.canvas },
  struck: { color: colors.muted, textDecorationLine: 'line-through' },
  notice: { padding: space.sm, backgroundColor: colors.paleWarning },
});
