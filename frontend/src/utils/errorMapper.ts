/**
 * Error Mapper for Shopperflox API errors.
 * Extracts backend error details and maps them into clear, human-readable Russian messages.
 * Conforms to .agent/rules/DESIGN.md.
 */

interface ErrorPayloadWithDetails {
  response?: {
    status?: number;
    data?: {
      detail?: string;
      errors?: Array<{
        detail?: string;
        message?: string;
        msg?: string;
        [key: string]: unknown;
      }>;
      [key: string]: unknown;
    };
  };
  data?: {
    detail?: string;
    errors?: Array<{
      detail?: string;
      message?: string;
      msg?: string;
      [key: string]: unknown;
    }>;
    [key: string]: unknown;
  };
  errors?: Array<{
    detail?: string;
    message?: string;
    msg?: string;
    [key: string]: unknown;
  }>;
  statusCode?: number;
  message?: string;
}

export function extractApiErrorDetail(error: unknown): { detail: string | null; statusCode?: number } {
  if (!error) {
    return { detail: null };
  }

  if (typeof error === 'string') {
    return { detail: error.trim() };
  }

  const err = error as ErrorPayloadWithDetails;
  const statusCode = err.response?.status ?? err.statusCode;

  // 1. Check response.data.errors[0].detail, message, or msg
  const respErrors = err.response?.data?.errors;
  if (Array.isArray(respErrors) && respErrors.length > 0) {
    const first = respErrors[0];
    if (typeof first?.detail === 'string' && first.detail.trim()) {
      return { detail: first.detail.trim(), statusCode };
    }
    if (typeof first?.message === 'string' && first.message.trim()) {
      return { detail: first.message.trim(), statusCode };
    }
    if (typeof first?.msg === 'string' && first.msg.trim()) {
      return { detail: first.msg.trim(), statusCode };
    }
  }

  // 2. Check response.data.detail
  if (typeof err.response?.data?.detail === 'string' && err.response.data.detail.trim()) {
    return { detail: err.response.data.detail.trim(), statusCode };
  }

  // 3. Check data.errors[0]
  const dataErrors = err.data?.errors;
  if (Array.isArray(dataErrors) && dataErrors.length > 0) {
    const first = dataErrors[0];
    if (typeof first?.detail === 'string' && first.detail.trim()) {
      return { detail: first.detail.trim(), statusCode };
    }
    if (typeof first?.message === 'string' && first.message.trim()) {
      return { detail: first.message.trim(), statusCode };
    }
    if (typeof first?.msg === 'string' && first.msg.trim()) {
      return { detail: first.msg.trim(), statusCode };
    }
  }

  // 4. Check data.detail
  if (typeof err.data?.detail === 'string' && err.data.detail.trim()) {
    return { detail: err.data.detail.trim(), statusCode };
  }

  // 5. Check direct errors array on error object
  if (Array.isArray(err.errors) && err.errors.length > 0) {
    const first = err.errors[0];
    if (typeof first?.detail === 'string' && first.detail.trim()) {
      return { detail: first.detail.trim(), statusCode };
    }
    if (typeof first?.message === 'string' && first.message.trim()) {
      return { detail: first.message.trim(), statusCode };
    }
    if (typeof first?.msg === 'string' && first.msg.trim()) {
      return { detail: first.msg.trim(), statusCode };
    }
  }

  // 6. Check err.message
  if (typeof err.message === 'string' && err.message.trim()) {
    const msg = err.message.trim();
    if (msg !== 'Ошибка выполнения запроса' && !msg.startsWith('API Error with status')) {
      return { detail: msg, statusCode };
    }
  }

  return { detail: null, statusCode };
}

export function formatApiError(error: unknown, fallbackMessage?: string): string {
  const { detail, statusCode } = extractApiErrorDetail(error);

  if (detail) {
    const lower = detail.toLowerCase();

    // 1. User is banned
    const banMatch = detail.match(/user is banned:\s*(.+)/i);
    if (banMatch) {
      const reason = banMatch[1].trim();
      return `ПОЛЬЗОВАТЕЛЬ ЗАБЛОКИРОВАН.\nПРИЧИНА: ${reason}`;
    }
    if (lower === 'user is banned' || lower.includes('user is banned')) {
      return 'ПОЛЬЗОВАТЕЛЬ ЗАБЛОКИРОВАН';
    }
    if (lower.includes('user is already actively banned')) {
      return 'ПОЛЬЗОВАТЕЛЬ УЖЕ ЗАБЛОКИРОВАН';
    }
    if (lower.includes('cannot ban yourself')) {
      return 'НЕЛЬЗЯ ЗАБЛОКИРОВАТЬ САМОГО СЕБЯ';
    }
    if (lower.includes('ban reason cannot be empty')) {
      return 'ПРИЧИНА БЛОКИРОВКИ НЕ МОЖЕТ БЫТЬ ПУСТОЙ';
    }
    if (lower.includes('no active ban found')) {
      return 'АКТИВНЫХ БЛОКИРОВОК ПОЛЬЗОВАТЕЛЯ НЕ НАЙДЕНО';
    }

    // 2. User account deleted
    if (
      lower.includes('user is deleted') ||
      lower.includes('user account has been deleted') ||
      lower.includes('actor user not found or deleted') ||
      lower.includes('user not found or deleted')
    ) {
      return 'АККАУНТ УДАЛЁН';
    }
    if (lower.includes('cannot delete yourself')) {
      return 'НЕЛЬЗЯ УДАЛИТЬ САМОГО СЕБЯ';
    }

    // 3. Credentials & Auth
    if (lower.includes('invalid credentials')) {
      return 'НЕВЕРНЫЙ ЛОГИН ИЛИ ПАРОЛЬ';
    }
    if (lower.includes('email not verified')) {
      return 'ЭЛЕКТРОННАЯ ПОЧТА НЕ ПОДТВЕРЖДЕНА';
    }
    if (lower.includes('email already verified')) {
      return 'ЭЛЕКТРОННАЯ ПОЧТА УЖЕ ПОДТВЕРЖДЕНА';
    }
    if (
      lower.includes('invalid or expired token') ||
      lower.includes('token has been revoked') ||
      lower.includes('missing bearer token') ||
      lower.includes('authentication required')
    ) {
      return 'СЕССИЯ ИСТЕКЛА ИЛИ ТРЕБУЕТСЯ АВТОРИЗАЦИЯ';
    }
    if (lower.includes('invalid verification code') || lower.includes('invalid verification code format')) {
      return 'НЕВЕРНЫЙ КОД ПОДТВЕРЖДЕНИЯ';
    }
    if (lower.includes('verification session expired or invalid')) {
      return 'СЕССИЯ ПОДТВЕРЖДЕНИЯ ИСТЕКЛА ИЛИ НЕВЕРНА';
    }

    // 4. Permissions & 403
    if (
      lower.includes('insufficient permissions') ||
      lower.includes('missing required permission') ||
      lower.includes('permission denied') ||
      lower.includes('access denied') ||
      lower.includes('membership required for this brand') ||
      lower.includes('representative role required for this brand') ||
      statusCode === 403
    ) {
      return 'НЕДОСТАТОЧНО ПРАВ ДЛЯ ВЫПОЛНЕНИЯ ДЕЙСТВИЯ';
    }

    // 5. Conflict & Already exists
    if (lower.includes('already exists') || lower.includes('conflict') || statusCode === 409) {
      if (lower.includes('login') && lower.includes('email')) {
        return 'ПОЛЬЗОВАТЕЛЬ С ТАКИМ ЛОГИНОМ ИЛИ EMAIL УЖЕ СУЩЕСТВУЕТ';
      }
      if (lower.includes('login')) {
        return 'ПОЛЬЗОВАТЕЛЬ С ТАКИМ ЛОГИНОМ УЖЕ СУЩЕСТВУЕТ';
      }
      if (lower.includes('email')) {
        return 'ПОЛЬЗОВАТЕЛЬ С ТАКИМ EMAIL УЖЕ СУЩЕСТВУЕТ';
      }
      if (lower.includes('phone') || lower.includes('personal profile')) {
        return 'ПРОФИЛЬ С ТАКИМ НОМЕРОМ ТЕЛЕФОНА УЖЕ СУЩЕСТВУЕТ';
      }
      if (lower.includes('sku') || lower.includes('variant')) {
        return 'ВАРИАЦИЯ С ТАКИМ SKU УЖЕ СУЩЕСТВУЕТ';
      }
      if (lower.includes('product') || lower.includes('slug')) {
        if (lower.includes('category')) {
          return 'КАТЕГОРИЯ С ТАКИМ SLUG УЖЕ СУЩЕСТВУЕТ';
        }
        if (lower.includes('brand')) {
          return 'БРЕНД С ТАКИМ НАЗВАНИЕМ ИЛИ SLUG УЖЕ СУЩЕСТВУЕТ';
        }
        return 'ТОВАР С ТАКИМ ЧПУ (SLUG) УЖЕ СУЩЕСТВУЕТ';
      }
      if (lower.includes('brand')) {
        return 'БРЕНД С ТАКИМ НАЗВАНИЕМ ИЛИ SLUG УЖЕ СУЩЕСТВУЕТ';
      }
      if (lower.includes('category')) {
        return 'КАТЕГОРИЯ С ТАКИМ НАЗВАНИЕМ ИЛИ SLUG УЖЕ СУЩЕСТВУЕТ';
      }
      if (lower.includes('review')) {
        return 'ВЫ УЖЕ ОСТАВИЛИ ОТЗЫВ НА ЭТОТ ТОВАР';
      }
      if (lower.includes('image constraint')) {
        return 'ОШИБКА ОГРАНИЧЕНИЙ ИЗОБРАЖЕНИЯ';
      }
      if (lower.includes('address')) {
        return 'КОНФЛИКТ АДРЕСА ПО УМОЛЧАНИЮ';
      }
      return 'ОБЪЕКТ С ТАКИМИ ПАРАМЕТРАМИ УЖЕ СУЩЕСТВУЕТ';
    }

    // 6. Not Found (404)
    if (lower.includes('not found') || statusCode === 404) {
      if (lower.includes('product') && lower.includes('variant')) {
        return 'ВАРИАЦИЯ ТОВАРА НЕ НАЙДЕНА';
      }
      if (lower.includes('product')) {
        return 'ТОВАР НЕ НАЙДЕН ИЛИ НЕДОСТУПЕН';
      }
      if (lower.includes('brand')) {
        return 'БРЕНД НЕ НАЙДЕН';
      }
      if (lower.includes('category')) {
        return 'КАТЕГОРИЯ НЕ НАЙДЕНА';
      }
      if (lower.includes('user')) {
        return 'ПОЛЬЗОВАТЕЛЬ НЕ НАЙДЕН';
      }
      if (lower.includes('order')) {
        return 'ЗАКАЗ НЕ НАЙДЕН';
      }
      if (lower.includes('address')) {
        return 'АДРЕС НЕ НАЙДЕН';
      }
      if (lower.includes('review')) {
        return 'ОТЗЫВ НЕ НАЙДЕН';
      }
      if (lower.includes('ban')) {
        return 'БЛОКИРОВКА НЕ НАЙДЕНА';
      }
      return 'ЗАПРАШИВАЕМЫЙ ОБЪЕКТ НЕ НАЙДЕН';
    }

    // 7. Cart & Orders
    if (lower.includes('cart is empty')) {
      return 'КОРЗИНА ПУСТА';
    }
    if (lower.includes('product is not available for purchase')) {
      return 'ТОВАР НЕДОСТУПЕН ДЛЯ ПОКУПКИ';
    }
    if (lower.includes('бренд снялся с продажи')) {
      return 'ЗАКАЗ НЕВОЗМОЖЕН, БРЕНД СНЯЛСЯ С ПРОДАЖИ';
    }

    // 8. Files and Media
    if (lower.includes('file size exceeds 5 mb limit')) {
      return 'ФАЙЛ ПРЕВЫШАЕТ ЛИМИТ 5 МБ';
    }
    if (lower.includes('invalid or corrupted image file')) {
      return 'ПОВРЕЖДЁННЫЙ ИЛИ НЕПОДДЕРЖИВАЕМЫЙ ФАЙЛ ИЗОБРАЖЕНИЯ';
    }
    if (lower.includes('duplicate image_id in reorder request')) {
      return 'ПОВТОРЯЮЩИЙСЯ ИДЕНТИФИКАТОР ФОТО В ЗАПРОСЕ СОРТИРОВКИ';
    }

    // 9. Search & Reviews
    if (lower.includes('search query must be at least 2 characters')) {
      return 'ПОИСКОВЫЙ ЗАПРОС ДОЛЖЕН СОДЕРЖАТЬ МИНИМУМ 2 СИМВОЛА';
    }
    if (lower.includes('search query must not exceed 100 characters')) {
      return 'ПОИСКОВЫЙ ЗАПРОС НЕ ДОЛЖЕН ПРЕВЫШАТЬ 100 СИМВОЛОВ';
    }
    if (lower.includes('review rating must be between 1 and 5')) {
      return 'ОЦЕНКА ДОЛЖНА БЫТЬ ОТ 1 ДО 5';
    }

    // 10. General backend detail output (show concrete text instead of generic error)
    return detail.trim();
  }

  // If no detail was found, check HTTP status codes
  if (statusCode === 403) {
    return 'НЕДОСТАТОЧНО ПРАВ ДЛЯ ВЫПОЛНЕНИЯ ДЕЙСТВИЯ';
  }
  if (statusCode === 401) {
    return 'СЕССИЯ ИСТЕКЛА ИЛИ ТРЕБУЕТСЯ АВТОРИЗАЦИЯ';
  }
  if (statusCode === 404) {
    return 'ЗАПРАШИВАЕМЫЙ ОБЪЕКТ НЕ НАЙДЕН';
  }
  if (statusCode === 409) {
    return 'ОБЪЕКТ С ТАКИМИ ПАРАМЕТРАМИ УЖЕ СУЩЕСТВУЕТ';
  }
  if (statusCode === 500) {
    return 'ВНУТРЕННЯЯ ОШИБКА СЕРВЕРА';
  }
  if (statusCode === 0) {
    return 'СЕТЕВАЯ ОШИБКА ИЛИ СЕРВЕР НЕДОСТУПЕН';
  }

  return fallbackMessage ? fallbackMessage.trim() : 'ОШИБКА ПРИ ВЫПОЛНЕНИИ ЗАПРОСА';
}
