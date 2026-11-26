export type Locale = 'he' | 'en' | 'ar' | 'fr' | 'ru';

const directions: Record<Locale, 'rtl' | 'ltr'> = {
  he: 'rtl',
  en: 'ltr',
  ar: 'rtl',
  fr: 'ltr',
  ru: 'ltr',
};

const he = {
  app: 'קניות חכמות',
  home: 'בית',
  search: 'חיפוש',
  list: 'רשימה',
  compare: 'השוואה',
  activeLists: 'רשימות פעילות',
  createList: 'יצירת רשימה',
  listName: 'שם הרשימה',
  saveList: 'שמירת רשימה',
  cancel: 'ביטול',
  favorites: 'מוצרים אהובים',
  deals: 'מבצעים לדוגמה',
  searchPrompt: 'חיפוש מוצר, מותג או קטגוריה',
  suggestions: 'הצעות חיפוש',
  categories: 'קטגוריות',
  allCategories: 'כל הקטגוריות',
  allBrands: 'כל המותגים',
  noResults: 'אין מוצרים שמתאימים לחיפוש',
  add: 'הוספה',
  increase: 'הגדלת כמות',
  decrease: 'הקטנת כמות',
  remove: 'הסרה',
  undo: 'ביטול הסרה',
  removed: 'הוסר מהרשימה',
  purchased: 'נקנו',
  markPurchased: 'סימון כנקנה',
  markPending: 'סימון כטרם נקנה',
  emptyList: 'הרשימה ריקה',
  addProducts: 'הוספת מוצרים',
  compareBasket: 'השוואת סל',
  demoComparison: 'נתוני הדגמה בלבד',
  unavailable: 'ההשוואה לדוגמה זמינה לסל ההתחלתי בכמויות המקוריות.',
  ranked: 'סלים בכיסוי מלא · לפי מחיר',
  partial: 'סלים עם מוצרים חסרים',
  single: 'חנות אחת',
  multi: 'כמה חנויות',
  distance: (value: string) => value + ' ק״מ',
  savings: (value: string) => 'חיסכון ' + value,
  missing: 'חסרים',
  none: 'אין',
  units: (value: string) => 'כמות ' + value,
  listCount: (value: string) => value + ' מוצרים',
};

type Messages = typeof he;
const catalogs: Partial<Record<Locale, Messages>> = { he };
export const locale: Locale = 'he';
export const direction = directions[locale];
export const t = catalogs[locale] ?? he;
export const number = new Intl.NumberFormat(locale);
export const money = new Intl.NumberFormat(locale, { style: 'currency', currency: 'ILS' });
