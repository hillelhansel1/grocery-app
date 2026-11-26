import { View } from 'react-native';

import { money, number, t } from './locale';
import { demoBasket, offers, products, referencePrice, type Item } from './mockData';
import { Copy, layout, Section } from './ui';

export function CompareScreen({ items }: { items: Item[] }) {
  const matchesDemo = items.length === demoBasket.length && demoBasket.every((demo) =>
    items.some((item) => item.productId === demo.productId && item.quantity === demo.quantity),
  );
  if (!matchesDemo) return <Copy kind="muted">{t.unavailable}</Copy>;

  const ranked = offers.filter((offer) => !offer.missing.length).sort((a, b) => a.price - b.price);
  const partial = offers.filter((offer) => offer.missing.length);
  const renderOffer = (offer: (typeof offers)[number]) => (
    <View key={offer.name} style={layout.card}>
      <View style={layout.wrap}>
        <Copy kind="strong" style={layout.grow}>{offer.name}</Copy>
        <Copy kind="price">{money.format(offer.price)}</Copy>
      </View>
      <Copy kind="muted">{t[offer.kind] + ' · ' + t.distance(number.format(offer.distance))}</Copy>
      {!offer.missing.length && <Copy>{t.savings(money.format(referencePrice - offer.price))}</Copy>}
      <Copy kind="muted">
        {t.missing + ' · ' + (offer.missing.map((id) => products[id].label).join('، ') || t.none)}
      </Copy>
    </View>
  );
  return (
    <>
      <Copy kind="muted">{t.demoComparison}</Copy>
      <Section title={t.ranked}>{ranked.map(renderOffer)}</Section>
      <Section title={t.partial}>{partial.map(renderOffer)}</Section>
    </>
  );
}
