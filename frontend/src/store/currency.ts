import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type CurrencyCode = 'RUB' | 'USD' | 'EUR' | 'CNY';

interface CurrencyStore {
  currency: CurrencyCode;
  setCurrency: (currency: CurrencyCode) => void;
}

export const useCurrencyStore = create<CurrencyStore>()(
  persist(
    (set) => ({
      currency: 'RUB',
      setCurrency: (currency) => set({ currency }),
    }),
    {
      name: 'shopperflox_currency',
    }
  )
);
