import { render, screen } from '@testing-library/react-native';

import App from './App';

jest.mock('react-native-safe-area-context', () =>
  jest.requireActual('react-native-safe-area-context/jest/mock').default,
);

test('shows the Hebrew heading and welcome text', async () => {
  await render(<App />);

  expect(screen.getByRole('header', { name: 'קניות חכמות' })).toBeVisible();
  expect(screen.getByText('ברוכים הבאים')).toBeVisible();
});
