import type { CurrencyCode } from './format';

export interface ConvertCurrenciesParams {
  rub?: string | number | null;
  usd?: string | number | null;
  eur?: string | number | null;
  cny?: string | number | null;
}

export interface ConvertCurrenciesResult {
  rub: string;
  usd: string;
  eur: string;
  cny: string;
  sourceCurrency: CurrencyCode;
  sourceAmount: number;
  isFallback: boolean;
  rateInfo: string;
}

// Fallback rates relative to 1 RUB
const FALLBACK_RATES_FROM_RUB: Record<CurrencyCode, number> = {
  RUB: 1,
  USD: 0.0121,
  EUR: 0.0110,
  CNY: 0.0808,
};

async function fetchRates(base: CurrencyCode): Promise<{ rates: Record<string, number>; isFallback: boolean }> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 4000);

    const res = await fetch(`https://open.er-api.com/v6/latest/${base}`, {
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (data && data.rates && typeof data.rates.USD === 'number') {
      return { rates: data.rates, isFallback: false };
    }
    throw new Error('Invalid rate payload');
  } catch {
    // Built-in fallback cross-rates
    const baseToRub = 1 / FALLBACK_RATES_FROM_RUB[base];
    const rates: Record<string, number> = {
      RUB: baseToRub * FALLBACK_RATES_FROM_RUB.RUB,
      USD: baseToRub * FALLBACK_RATES_FROM_RUB.USD,
      EUR: baseToRub * FALLBACK_RATES_FROM_RUB.EUR,
      CNY: baseToRub * FALLBACK_RATES_FROM_RUB.CNY,
    };
    return { rates, isFallback: true };
  }
}

function roundToTwo(num: number): string {
  return (Math.round((num + Number.EPSILON) * 100) / 100).toFixed(2);
}

export async function autoConvertCurrencies(
  params: ConvertCurrenciesParams
): Promise<ConvertCurrenciesResult> {
  const parseVal = (v: string | number | null | undefined): number | null => {
    if (v == null || v === '') return null;
    const n = typeof v === 'number' ? v : parseFloat(String(v).replace(',', '.'));
    return isNaN(n) || n <= 0 ? null : n;
  };

  const rubVal = parseVal(params.rub);
  const usdVal = parseVal(params.usd);
  const eurVal = parseVal(params.eur);
  const cnyVal = parseVal(params.cny);

  let sourceCurrency: CurrencyCode | null = null;
  let sourceAmount = 0;

  if (rubVal !== null) {
    sourceCurrency = 'RUB';
    sourceAmount = rubVal;
  } else if (usdVal !== null) {
    sourceCurrency = 'USD';
    sourceAmount = usdVal;
  } else if (eurVal !== null) {
    sourceCurrency = 'EUR';
    sourceAmount = eurVal;
  } else if (cnyVal !== null) {
    sourceCurrency = 'CNY';
    sourceAmount = cnyVal;
  }

  if (!sourceCurrency) {
    throw new Error('Укажите цену хотя бы в одной валюте (RUB, USD, EUR или CNY) для выполнения автоперевода.');
  }

  const { rates, isFallback } = await fetchRates(sourceCurrency);

  const rubRate = rates.RUB ?? 1;
  const usdRate = rates.USD ?? (sourceCurrency === 'USD' ? 1 : FALLBACK_RATES_FROM_RUB.USD);
  const eurRate = rates.EUR ?? (sourceCurrency === 'EUR' ? 1 : FALLBACK_RATES_FROM_RUB.EUR);
  const cnyRate = rates.CNY ?? (sourceCurrency === 'CNY' ? 1 : FALLBACK_RATES_FROM_RUB.CNY);

  const convertedRub = sourceCurrency === 'RUB' ? sourceAmount : sourceAmount * rubRate;
  const convertedUsd = sourceCurrency === 'USD' ? sourceAmount : sourceAmount * usdRate;
  const convertedEur = sourceCurrency === 'EUR' ? sourceAmount : sourceAmount * eurRate;
  const convertedCny = sourceCurrency === 'CNY' ? sourceAmount : sourceAmount * cnyRate;

  const rateInfo = isFallback
    ? 'Использован справочный курс'
    : 'Курс обновлён по рыночным котировкам';

  return {
    rub: roundToTwo(convertedRub),
    usd: roundToTwo(convertedUsd),
    eur: roundToTwo(convertedEur),
    cny: roundToTwo(convertedCny),
    sourceCurrency,
    sourceAmount,
    isFallback,
    rateInfo,
  };
}
