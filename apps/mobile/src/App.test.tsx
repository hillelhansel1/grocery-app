import { fireEvent, render, screen, userEvent } from '@testing-library/react-native';

import App from './App';
import { money, t } from './locale';
import { offers, products } from './mockData';

jest.mock('react-native-safe-area-context', () =>
  jest.requireActual('react-native-safe-area-context/jest/mock').default,
);

const button = (name: string) => screen.getByRole('button', { name });
const tab = (name: string) => screen.getByRole('tab', { name });

test('anchors Hebrew content in an RTL shell and opens an active list', async () => {
  await render(<App />);

  expect(screen.getByTestId('app-shell')).toHaveStyle({ direction: 'rtl' });
  expect(screen.getByRole('header', { name: t.app })).toHaveStyle({
    textAlign: 'right',
    writingDirection: 'rtl',
  });
  expect(screen.getByRole('header', { name: t.favorites })).toBeVisible();
  expect(screen.getByRole('header', { name: t.deals })).toBeVisible();
  expect(screen.queryByText(money.format(offers[0].price))).toBeNull();
  await fireEvent.press(button('קניות לשבוע'));
  expect(screen.getByRole('header', { name: 'קניות לשבוע' })).toBeVisible();
});

test('creates a list, selects a suggestion, and adds and adjusts a brand product', async () => {
  await render(<App />);
  const user = userEvent.setup();
  await fireEvent.press(button(t.createList));
  await user.type(screen.getByLabelText(t.listName), 'קניות לסוף השבוע');
  await fireEvent.press(button(t.saveList));
  expect(screen.getByText(t.emptyList)).toBeVisible();
  await fireEvent.press(button(t.addProducts));
  await user.type(screen.getByLabelText(t.searchPrompt), 'תנובה');
  const suggestion = button(products.milk.label);
  await fireEvent.press(suggestion);
  expect(screen.queryByText(t.suggestions)).toBeNull();

  const milkChoices = screen.getAllByText(/^(כל המותגים|תנובה|יטבתה)$/);
  expect(milkChoices.map((choice) => choice.props.children)).toEqual([t.allBrands, 'תנובה', 'יטבתה']);
  await fireEvent.press(button(t.add + ' · ' + products.milk.label + ' · תנובה'));
  const product = products['milk-tnuva'].label;
  await fireEvent.press(button(t.increase + ' · ' + product));
  await fireEvent.press(tab(t.list));
  expect(screen.getByText(product)).toBeVisible();
  expect(screen.getByLabelText(t.units('2'))).toBeVisible();
  await fireEvent.press(button(t.decrease + ' · ' + product));
  expect(screen.getByLabelText(t.units('1'))).toBeVisible();
});

test('browses categories and shows an empty search state', async () => {
  await render(<App />);
  const user = userEvent.setup();
  await fireEvent.press(tab(t.search));
  await fireEvent.press(button(t.categories));
  await fireEvent.press(button('פירות וירקות'));
  expect(screen.getByText(products.apple.label)).toBeVisible();
  expect(screen.queryByText(products.milk.label)).toBeNull();
  await user.type(screen.getByLabelText(t.searchPrompt), 'אורז');
  expect(screen.getByText(t.noResults)).toBeVisible();
});

test('moves purchased items below pending ones and restores deleted items', async () => {
  await render(<App />);
  await fireEvent.press(button('קניות לשבוע'));
  const milk = products.milk.label;
  const bread = products.bread.label;
  await fireEvent.press(button(t.markPurchased + ' · ' + milk));
  expect(screen.getAllByText(/^(לחם מלא 750 גרם|חלב 3% 1 ליטר)$/)
    .map((node) => node.props.children)).toEqual([bread, milk]);
  expect(screen.getByText(milk)).toHaveStyle({ textDecorationLine: 'line-through' });
  await fireEvent.press(button(t.remove + ' · ' + milk));
  expect(screen.queryByText(milk)).toBeNull();
  await fireEvent.press(button(t.undo));
  expect(button(t.markPending + ' · ' + milk)).toBeVisible();
  expect(screen.getByLabelText(t.units('2'))).toBeVisible();
});

test('ranks complete offers by price and places the cheaper partial offer after them', async () => {
  await render(<App />);
  await fireEvent.press(tab(t.compare));
  const displayedStores = screen.getAllByText(/^שוק העיר|^סופר השכונה$/);
  expect(displayedStores.map((node) => node.props.children)).toEqual([
    offers[1].name,
    offers[0].name,
    offers[2].name,
  ]);
  expect(screen.getByRole('header', { name: t.partial })).toBeVisible();
  expect(screen.getByText(t.missing + ' · ' + products.bread.label)).toBeVisible();
  expect(screen.getByText(money.format(offers[2].price))).toBeVisible();
  await fireEvent.press(tab(t.list));
  await fireEvent.press(button(t.increase + ' · ' + products.milk.label));
  await fireEvent.press(button(t.compareBasket));
  expect(screen.getByText(t.unavailable)).toBeVisible();
  expect(screen.queryByText(money.format(offers[2].price))).toBeNull();
  expect(screen.queryByText(offers[0].name)).toBeNull();
});
