export function formatPrice(price: string | number | null | undefined): string {
  if (price === null || price === undefined || price === '') return '0 ₽';
  const num = typeof price === 'string' ? parseFloat(price) : price;
  if (isNaN(num)) return '0 ₽';
  return `${Math.round(num).toLocaleString('ru-RU')} ₽`;
}

export function formatImageUrl(url?: string | null, fallbackText = 'SHOPPERFLOX'): string {
  if (!url) {
    const safeText = (fallbackText || 'SHOPPERFLOX')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="600" height="900" viewBox="0 0 600 900" fill="#E8DEC9">
      <rect width="600" height="900" fill="#E8DEC9"/>
      <rect x="20" y="20" width="560" height="860" fill="none" stroke="#3F2021" stroke-width="1" stroke-opacity="0.3"/>
      <text x="300" y="440" font-family="&quot;Times New Roman&quot;, serif" font-size="32" fill="#3F2021" text-anchor="middle" letter-spacing="3">${safeText}</text>
      <text x="300" y="480" font-family="sans-serif" font-size="12" fill="#5F5F5F" text-anchor="middle" letter-spacing="2">SHOPPERFLOX</text>
    </svg>`;
    return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
  }

  if (url.startsWith('/') || url.startsWith('data:') || url.includes('://')) {
    return url;
  }

  return `/${url}`;
}

export function formatDate(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

export function formatDateTime(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    const dateFormatted = d.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
    const timeFormatted = d.toLocaleTimeString('ru-RU', {
      hour: '2-digit',
      minute: '2-digit',
    });
    return `${dateFormatted}, ${timeFormatted}`;
  } catch {
    return dateStr;
  }
}
