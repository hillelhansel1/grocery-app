import type { ImageSourcePropType } from 'react-native';

export type Product = { id: string; label: string; image?: ImageSourcePropType };
type Group = { id: string; label: string; category: string; brands: Product[] };

export const categories = ['חלב וביצים', 'פירות וירקות', 'לחם ומאפים'];
export const groups: Group[] = [
  {
    id: 'milk',
    label: 'חלב 3% 1 ליטר',
    category: categories[0],
    brands: [{ id: 'milk-tnuva', label: 'תנובה' }, { id: 'milk-yotvata', label: 'יטבתה' }],
  },
  {
    id: 'eggs',
    label: 'ביצים 12 יחידות',
    category: categories[0],
    brands: [{ id: 'eggs-brand', label: 'משק ארצי' }],
  },
  {
    id: 'apple',
    label: 'תפוחים אדומים 1 ק״ג',
    category: categories[1],
    brands: [{ id: 'apple-brand', label: 'פרי הגליל' }],
  },
  {
    id: 'bread',
    label: 'לחם מלא 750 גרם',
    category: categories[2],
    brands: [{ id: 'bread-brand', label: 'אנג׳ל' }, { id: 'bread-berman', label: 'ברמן' }],
  },
];

export const products = Object.fromEntries(
  groups.flatMap((group) => [
    [group.id, { id: group.id, label: group.label }],
    ...group.brands.map((brand) => [
      brand.id,
      { ...brand, label: group.label + ' · ' + brand.label },
    ]),
  ]),
) as Record<string, Product>;

export type Item = { productId: string; quantity: number; purchased: boolean };
export type ShoppingList = { id: number; name: string; items: Item[] };

export const demoBasket = [
  { productId: 'milk', quantity: 2, purchased: false },
  { productId: 'bread', quantity: 1, purchased: false },
];

export const initialLists: ShoppingList[] = [
  { id: 1, name: 'קניות לשבוע', items: demoBasket },
  { id: 2, name: 'השלמות לבית', items: [] },
];

export const favorites = ['milk', 'bread'];
export const deals = [{ productId: 'apple', price: 8.9 }];

export const offers = [
  { name: 'שוק העיר', kind: 'single', price: 21.8, distance: 1.2, missing: [] },
  { name: 'שוק העיר + סופר השכונה', kind: 'multi', price: 19.9, distance: 2.4, missing: [] },
  { name: 'סופר השכונה', kind: 'single', price: 12.9, distance: 0.6, missing: ['bread'] },
] as const;
export const referencePrice = 23.9;
