import { useState } from 'react';
import { ScrollView, StatusBar, StyleSheet, View } from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';

import { CompareScreen } from './CompareScreen';
import { HomeScreen } from './HomeScreen';
import { ListScreen } from './ListScreen';
import { direction, t } from './locale';
import { initialLists, type Item } from './mockData';
import { SearchScreen } from './SearchScreen';
import { Button, colors, Copy, layout, radius, space } from './ui';

const tabs = ['home', 'search', 'list', 'compare'] as const;
type Tab = (typeof tabs)[number];
type Removal = { listId: number; item: Item; index: number };

export default function App() {
  const [tab, setTab] = useState<Tab>('home');
  const [lists, setLists] = useState(initialLists);
  const [listId, setListId] = useState(initialLists[0].id);
  const [searchQuery, setSearchQuery] = useState('');
  const [removal, setRemoval] = useState<Removal>();
  const list = lists.find((entry) => entry.id === listId) ?? lists[0];
  const availableUndo = removal?.listId === list.id ? removal : undefined;

  function openList(id: number) {
    setListId(id);
    setTab('list');
  }

  function createList(name: string) {
    const id = lists[lists.length - 1].id + 1;
    setLists((current) => [...current, { id, name, items: [] }]);
    openList(id);
  }

  function openSearch(query = '') {
    setSearchQuery(query);
    setTab('search');
  }

  function updateItems(update: (items: Item[]) => Item[]) {
    setLists((current) => current.map((entry) =>
      entry.id === list.id ? { ...entry, items: update(entry.items) } : entry,
    ));
  }

  function changeQuantity(productId: string, quantity: number) {
    updateItems((items) => items.some((item) => item.productId === productId)
      ? items.map((item) => item.productId === productId ? { ...item, quantity } : item)
      : [...items, { productId, quantity, purchased: false }],
    );
  }

  function togglePurchased(productId: string) {
    updateItems((items) => items.map((item) =>
      item.productId === productId ? { ...item, purchased: !item.purchased } : item,
    ));
  }

  function remove(productId: string) {
    const index = list.items.findIndex((item) => item.productId === productId);
    if (index < 0) return;
    setRemoval({ listId: list.id, item: list.items[index], index });
    updateItems((items) => items.filter((item) => item.productId !== productId));
  }

  function undo() {
    if (!availableUndo) return;
    const { item, index } = availableUndo;
    updateItems((items) => {
      if (items.some((entry) => entry.productId === item.productId)) return items;
      return [...items.slice(0, index), item, ...items.slice(index)];
    });
    setRemoval(undefined);
  }

  const heading = { home: t.app, search: t.search, list: list.name, compare: t.compareBasket };

  return (
    <SafeAreaProvider>
      <StatusBar barStyle="dark-content" />
      <SafeAreaView testID="app-shell" style={styles.shell}>
        <View style={styles.header}>
          <Copy accessibilityRole="header" kind="title">{heading[tab]}</Copy>
          {(tab === 'search' || tab === 'compare') && <Copy kind="muted">{list.name}</Copy>}
        </View>
        <ScrollView key={tab} keyboardShouldPersistTaps="handled" contentContainerStyle={styles.content}>
          <View style={styles.column}>
            {tab === 'home' && (
              <>
                <HomeScreen lists={lists} onOpen={openList} onCreate={createList} onSearch={openSearch} />
                <View style={styles.adSpace} accessible={false} />
              </>
            )}
            {tab === 'search' && (
              <SearchScreen initialQuery={searchQuery} items={list.items} onQuantity={changeQuantity} />
            )}
            {tab === 'list' && (
              <ListScreen
                list={list}
                removed={availableUndo?.item.productId}
                onUndo={undo}
                onQuantity={changeQuantity}
                onToggle={togglePurchased}
                onRemove={remove}
                onSearch={() => openSearch()}
                onCompare={() => setTab('compare')}
              />
            )}
            {tab === 'compare' && <CompareScreen items={list.items} />}
          </View>
        </ScrollView>
        <View style={styles.footer}>
          <View accessibilityRole="tablist" style={[layout.wrap, styles.nav]}>
            {tabs.map((entry) => (
              <View key={entry} style={styles.navItem}>
                <Button
                  label={t[entry]}
                  role="tab"
                  variant={tab === entry ? 'primary' : 'plain'}
                  selected={tab === entry}
                  onPress={() => entry === 'search' ? openSearch() : setTab(entry)}
                />
              </View>
            ))}
          </View>
        </View>
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  shell: { flex: 1, direction, backgroundColor: colors.canvas },
  header: {
    width: '100%',
    maxWidth: 680,
    alignSelf: 'center',
    paddingHorizontal: space.lg,
    paddingTop: space.sm,
    gap: space.xs,
  },
  content: { alignItems: 'center', padding: space.lg },
  column: { width: '100%', maxWidth: 648, gap: space.xl },
  adSpace: { height: 36, borderRadius: radius.control, backgroundColor: colors.soft },
  footer: {
    backgroundColor: colors.surface,
    borderTopColor: colors.border,
    borderTopWidth: 1,
    alignItems: 'center',
  },
  nav: { width: '100%', maxWidth: 680, padding: space.sm },
  navItem: { flexGrow: 1, flexBasis: 64 },
});
