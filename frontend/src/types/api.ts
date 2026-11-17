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
  brand_id?: string | null;
  brand?: string | null;
  brand_slug?: string | null;
  brand_logo_url?: string | null;
  brand_his_url?: string | null;
  brand_is_verified?: boolean;
  brand_is_deleted?: boolean;
  is_self_worked?: boolean;
  title: string;
  slug: string;
  base_price: string;
  price_usd?: string | null;
  price_eur?: string | null;
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
  views_count?: number;
  orders_count?: number;
  moderation_status?: 'pending' | 'approved' | 'rejected';
  request_type?: 'CREATE' | 'EDIT';
  rejection_reason?: string | null;
  variants?: ProductVariantResponse[];
  images?: ProductImageResponse[];
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
  brand_id?: string | null;
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
  brand_id?: string | null;
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

export interface ProductVariantCreateRequest {
  sku: string;
  size?: string | null;
  color_name?: string | null;
  color?: string | null;
  color_hex?: string | null;
  price_override?: number | string | null;
  stock_quantity?: number;
}

export interface ProductVariantUpdateRequest {
  sku?: string | null;
  size?: string | null;
  color_name?: string | null;
  color?: string | null;
  color_hex?: string | null;
  price_override?: number | string | null;
  stock_quantity?: number | null;
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
  orders_count?: number;
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
  product_slug?: string;
  image_url?: string | null;
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

export interface CreateAddressRequest {
  city: string;
  street: string;
  postal_code: string;
  is_default?: boolean;
}

export interface UserAddressResponse {
  id: string;
  user_id: string;
  city: string;
  street: string;
  postal_code: string;
  is_default: boolean;
  created_at: string;
}

export interface BrandResponse {
  id: string;
  name: string;
  slug: string;
  his_url?: string | null;
  logo_url?: string | null;
  is_deleted?: boolean;
  views_count?: number;
  orders_count?: number;
  moderation_status?: 'pending' | 'approved' | 'rejected' | string;
  rejection_reason?: string | null;
  is_verified?: boolean;
  created_at: string;
}

export interface BrandRejectRequest {
  reason?: string | null;
}

export interface BrandVerifyRequest {
  is_verified: boolean;
}

export interface MyBrandResponse {
  brand: BrandResponse;
  role: 'representative' | 'moderator' | string;
}

export interface BrandCreateRequest {
  name: string;
  his_url?: string | null;
}

export interface BrandUpdateRequest {
  name?: string | null;
  his_url?: string | null;
}

export interface BrandMemberResponse {
  brand_id: string;
  user_id: string;
  user_login?: string | null;
  role: 'representative' | 'moderator' | string;
  created_at: string;
}

export interface AddBrandMemberRequest {
  login: string;
  role: 'representative' | 'moderator';
}

export interface RemoveMemberResponse {
  removed?: boolean;
  brand_deleted?: boolean;
}

export interface AdminUserBanResponse {
  id: string;
  reason: string;
  ended_at?: string | null;
}

export interface AdminUserResponse {
  id: string;
  login: string;
  email?: string | null;
  verified_profile: boolean;
  verified_email: boolean;
  global_permissions: string[];
  is_deleted: boolean;
  deleted_at?: string | null;
  active_ban?: AdminUserBanResponse | null;
  created_at: string;
}

export interface AdminUserUpdateRequest {
  login?: string | null;
  global_permissions?: string[] | null;
  verified_profile?: boolean | null;
}

export interface AdminBanUserRequest {
  reason: string;
  ended_at?: string | null;
}

export interface AdminBrandResponse {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  logo_url?: string | null;
  his_url?: string | null;
  moderation_status?: 'pending' | 'approved' | 'rejected' | string;
  rejection_reason?: string | null;
  is_verified?: boolean;
  views_count?: number;
  orders_count?: number;
  is_deleted?: boolean;
  created_at: string;
  members?: BrandMemberResponse[];
}

export interface AdminCategoryCreateRequest {
  name: string;
  slug?: string | null;
  parent_id?: string | null;
  sort_order?: number;
}

export interface AdminCategoryUpdateRequest {
  name?: string | null;
  slug?: string | null;
  parent_id?: string | null;
  sort_order?: number | null;
}

export interface AdminReviewResponse {
  id: string;
  user_id: string;
  product_id: string;
  rating: number;
  comment?: string | null;
  fit_feedback?: 'true_to_size' | 'runs_small' | 'runs_large' | string | null;
  is_published: boolean;
  user_login: string;
  product_title: string;
  product_slug: string;
  created_at: string;
}

