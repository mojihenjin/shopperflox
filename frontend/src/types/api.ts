export interface PaginationMetadata {
  total?: number;
  limit?: number;
  offset?: number;
  length?: number;
  [key: string]: unknown;
}

export interface ApiErrorDetail {
  message?: string;
  field?: string;
  code?: string;
  [key: string]: unknown;
}

export interface BaseResponse<T> {
  body: T;
  status_code: number;
  errors: ApiErrorDetail[];
  metadata?: PaginationMetadata;
}

export interface UnpackedResponse<T> {
  data: T;
  metadata?: PaginationMetadata;
  statusCode: number;
}

export interface UserResponse {
  id: string;
  login: string;
  email?: string | null;
  global_permissions?: string[];
  verified_email?: boolean;
  verified_profile?: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserPersonalResponse {
  id?: string;
  firstname?: string | null;
  lastname?: string | null;
  phone_number?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface UserProfileResponse {
  user: UserResponse;
  personal?: UserPersonalResponse | null;
}

export interface RegisterRequest {
  login: string;
  password: string;
  email?: string | null;
}

export interface RegisterResponse {
  requires_verification: boolean;
  verification_token?: string | null;
  user?: UserResponse | null;
}

export interface VerifyCodeRequest {
  verification_token: string;
  code: string;
}

export interface SendEmailCodeRequest {
  email: string;
}

export interface VerificationInitResponse {
  requires_verification: boolean;
  verification_token: string;
}

export interface UpdatePersonalRequest {
  firstname?: string | null;
  lastname?: string | null;
  phone_number?: string | null;
}

export interface LoginRequest {
  identifier: string;
  password: string;
}

export interface TokenPairResponse {
  access_token: string;
  refresh_token: string;
  token_type?: string;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface CategoryResponse {
  id: string;
  name: string;
  slug: string;
  parent_id?: string | null;
  sort_order?: number;
  created_at: string;
}

export interface ProductResponse {
  id: string;
  category_id: string;
  creator_id?: string | null;
  title: string;
  slug: string;
  base_price: string;
  price_usd?: string | null;
  price_eur?: string | null;
  brand?: string | null;
  is_self_worked?: boolean;
  material?: string | null;
  density?: string | null;
  composition?: string | null;
  print_method?: string | null;
  note?: string | null;
  description?: string | null;
  attributes?: Record<string, unknown> | null;
  is_published?: boolean;
  is_hidden?: 0 | 1 | 2;
  is_limited?: boolean;
  moderation_status?: 'pending' | 'approved' | 'rejected';
  request_type?: 'CREATE' | 'EDIT';
  rejection_reason?: string | null;
  created_at: string;
  updated_at: string;
}

export interface VariantCreateItem {
  color?: string | null;
  color_name?: string | null;
  size?: string | null;
  stock_quantity?: number;
  sku?: string | null;
  price_override?: number | string | null;
  color_hex?: string | null;
}

export interface ProductCreateRequest {
  category_id: string;
  title: string;
  slug: string;
  brand?: string | null;
  is_self_worked?: boolean;
  base_price: number | string;
  price_usd?: number | string | null;
  price_eur?: number | string | null;
  material?: string | null;
  density?: string | null;
  composition?: string | null;
  print_method?: string | null;
  note?: string | null;
  description?: string | null;
  attributes?: Record<string, unknown>;
  is_published?: boolean;
  is_hidden?: 0 | 1 | 2;
  is_limited?: boolean;
  variants?: VariantCreateItem[];
}

export interface ProductUpdateRequest {
  category_id?: string | null;
  title?: string | null;
  slug?: string | null;
  brand?: string | null;
  is_self_worked?: boolean | null;
  base_price?: number | string | null;
  price_usd?: number | string | null;
  price_eur?: number | string | null;
  material?: string | null;
  density?: string | null;
  composition?: string | null;
  print_method?: string | null;
  note?: string | null;
  description?: string | null;
  attributes?: Record<string, unknown> | null;
  is_published?: boolean | null;
  is_hidden?: 0 | 1 | 2 | null;
  is_limited?: boolean | null;
}

export interface ProductVariantResponse {
  id: string;
  product_id: string;
  sku: string;
  size?: string | null;
  color_name?: string | null;
  color?: string | null;
  color_hex?: string | null;
  price_override?: string | null;
  stock_quantity?: number;
  created_at: string;
  updated_at: string;
}

export interface ProductImageResponse {
  id: string;
  product_id: string;
  url: string;
  color?: string | null;
  alt_text?: string | null;
  is_main?: boolean;
  sort_order?: number;
  variant_id?: string | null;
  created_at: string;
}

export interface ProductDetailResponse {
  product: ProductResponse;
  variants: ProductVariantResponse[];
  images: ProductImageResponse[];
}

export interface BrandSearchResponse {
  name: string;
  products_count: number;
}

export interface SearchResultResponse {
  products: ProductResponse[];
  brands: BrandSearchResponse[];
  variants: ProductVariantResponse[];
}

export type FitFeedback = 'runs_small' | 'true_to_size' | 'runs_large';

export interface ReviewResponse {
  id: string;
  user_id: string;
  product_id: string;
  rating: number;
  comment?: string | null;
  fit_feedback?: FitFeedback | null;
  created_at: string;
}

export interface CreateReviewRequest {
  rating: number;
  comment?: string | null;
  fit_feedback?: FitFeedback | null;
}

export interface CartItemResponse {
  id: string;
  variant_id: string;
  quantity: number;
  unit_price: string;
  total_price: string;
  is_available: boolean;
  color_name?: string | null;
  size?: string | null;
  sku?: string | null;
  title?: string | null;
  product_id?: string | null;
}

export interface CartResponse {
  id: string;
  user_id?: string | null;
  total_amount: string;
  items: CartItemResponse[];
}

export interface CartItemRequest {
  quantity: number;
}

export interface NotificationResponse {
  id: string;
  title: string;
  body: string;
  link?: string | null;
  is_read: boolean;
  created_at: string;
}

export interface UnreadCountResponse {
  count: number;
}

export interface ReadAllNotificationsResponse {
  marked_count: number;
}

export type OrderStatus =
  | 'pending_payment'
  | 'paid'
  | 'processing'
  | 'shipped'
  | 'delivered'
  | 'cancelled'
  | 'refunded';

export interface OrderItemResponse {
  id: string;
  variant_id?: string | null;
  title_snapshot: string;
  sku_snapshot: string;
  size_snapshot: string;
  color_snapshot: string;
  unit_price: string;
  quantity: number;
  product_slug?: string | null;
}

export interface OrderResponse {
  id: string;
  user_id: string;
  total_amount: string;
  shipping_address: Record<string, unknown>;
  status: OrderStatus;
  tracking_number?: string | null;
  post_code?: string | null;
  created_at: string;
  items?: OrderItemResponse[] | null;
  payment?: unknown | null;
}

export type ModerationRequestType = 'CREATE' | 'EDIT';
export type ModerationStatus = 'pending' | 'approved' | 'rejected';

export interface PendingCountResponse {
  pending_count: number;
}

export interface RejectProductRequest {
  reason?: string | null;
}
