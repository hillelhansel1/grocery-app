import { useState } from 'react';
import { View } from 'react-native';

import { money, number, t } from './locale';
import { deals, favorites, products, type ShoppingList } from './mockData';
import { Button, Copy, Field, layout, ProductImage, Section } from './ui';

export function HomeScreen({ lists, onOpen, onCreate, onSearch }: {
  lists: ShoppingList[];
  onOpen: (id: number) => void;
  onCreate: (name: string) => void;
  onSearch: (query: string) => void;
}) {
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState('');
  const save = () => {
    if (name.trim()) onCreate(name.trim());
  };

  return (
    <>
      <Section title={t.activeLists}>
        {lists.map((list) => (
          <View key={list.id} style={layout.card}>
            <View style={layout.row}>
              <View style={layout.grow}>
                <Copy kind="strong">{list.name}</Copy>
                <Copy kind="muted">{t.listCount(number.format(list.items.length))}</Copy>
              </View>
              <Button label={t.list} accessibilityLabel={list.name} onPress={() => onOpen(list.id)} />
            </View>
          </View>
        ))}
        {creating ? (
          <View style={layout.card}>
            <Field
              accessibilityLabel={t.listName}
              placeholder={t.listName}
              value={name}
              onChangeText={setName}
              onSubmitEditing={save}
              autoFocus
            />
            <View style={layout.wrap}>
              <Button label={t.saveList} onPress={save} variant="primary" disabled={!name.trim()} />
              <Button label={t.cancel} onPress={() => { setName(''); setCreating(false); }} variant="plain" />
            </View>
          </View>
        ) : (
          <Button label={t.createList} variant="primary" onPress={() => setCreating(true)} />
        )}
      </Section>
      <Section title={t.favorites}>
        {favorites.map((id) => (
          <View key={id} style={[layout.card, layout.row]}>
            <ProductImage product={products[id]} />
            <Copy kind="strong" style={layout.grow}>{products[id].label}</Copy>
            <Button label={t.search} accessibilityLabel={t.search + ' · ' + products[id].label} onPress={() => onSearch(products[id].label)} />
          </View>
        ))}
      </Section>
      <Section title={t.deals}>
        {deals.map(({ productId, price }) => (
          <View key={productId} style={[layout.card, layout.row]}>
            <ProductImage product={products[productId]} />
            <Copy kind="strong" style={layout.grow}>{products[productId].label}</Copy>
            <Copy kind="price">{money.format(price)}</Copy>
          </View>
        ))}
      </Section>
    </>
  );
}
