import { useState } from 'react';
import { View } from 'react-native';

import { t } from './locale';
import { categories, groups, products, type Item } from './mockData';
import { Button, Copy, Field, layout, ProductImage, Quantity, Section } from './ui';

export function SearchScreen({ initialQuery, items, onQuantity }: {
  initialQuery: string;
  items: Item[];
  onQuantity: (productId: string, quantity: number) => void;
}) {
  const [query, setQuery] = useState(initialQuery);
  const [category, setCategory] = useState('');
  const [browsing, setBrowsing] = useState(false);
  const [suggesting, setSuggesting] = useState(false);
  const term = query.trim().toLocaleLowerCase();
  const visible = groups.filter((group) =>
    (!category || group.category === category) &&
    [group.label, group.category, ...group.brands.map((brand) => brand.label)]
      .some((label) => label.toLocaleLowerCase().includes(term)),
  );

  return (
    <>
      <Field
        value={query}
        accessibilityLabel={t.searchPrompt}
        placeholder={t.searchPrompt}
        autoCorrect={false}
        returnKeyType="search"
        onChangeText={(value) => { setQuery(value); setSuggesting(true); }}
        onSubmitEditing={() => setSuggesting(false)}
      />
      {suggesting && term && visible.length > 0 ? (
        <Section title={t.suggestions}>
          {visible.slice(0, 4).map((group) => (
            <Button key={group.id} label={group.label} onPress={() => {
              setQuery(group.label);
              setSuggesting(false);
            }} />
          ))}
        </Section>
      ) : null}
      <View style={layout.wrap}>
        <Button label={t.categories} selected={browsing} onPress={() => setBrowsing(!browsing)} />
        {browsing && ['', ...categories].map((option) => (
          <Button
            key={option}
            label={option || t.allCategories}
            selected={category === option}
            onPress={() => { setCategory(option); setSuggesting(false); }}
          />
        ))}
      </View>
      {visible.length === 0 && <Copy kind="muted">{t.noResults}</Copy>}
      {visible.map((group) => (
        <View key={group.id} style={layout.card}>
          <Section title={group.label}>
            {[{ id: group.id, label: t.allBrands }, ...group.brands].map(({ id, label }) => {
              const item = items.find((entry) => entry.productId === id);
              return (
                <View key={id} style={layout.wrap}>
                  <ProductImage product={products[id]} />
                  <Copy kind="strong" style={layout.grow}>{label}</Copy>
                  {item ? (
                    <Quantity label={products[id].label} value={item.quantity} onChange={(value) => onQuantity(id, value)} />
                  ) : (
                    <Button label={t.add} accessibilityLabel={t.add + ' · ' + group.label + ' · ' + label} onPress={() => onQuantity(id, 1)} />
                  )}
                </View>
              );
            })}
          </Section>
        </View>
      ))}
    </>
  );
}
