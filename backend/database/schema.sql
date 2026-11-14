CREATE TABLE users (
  id UUID PRIMARY KEY,
  login VARCHAR(100) NOT NULL,
  email VARCHAR(255),
  password_hash TEXT,
  verified_profile BOOLEAN NOT NULL DEFAULT FALSE,
  verified_email BOOLEAN NOT NULL DEFAULT FALSE,
  global_permissions JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_by UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  deleted_at TIMESTAMPTZ,
  CONSTRAINT fk_users_created_by FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX ix_users_login ON users(login) WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX ix_users_email ON users(email) WHERE deleted_at IS NULL AND email IS NOT NULL;


CREATE TABLE user_personal (
  id UUID PRIMARY KEY,
  firstname VARCHAR(255),
  lastname VARCHAR(255),
  phone_number VARCHAR(100),
  created_by UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_user_personal_user FOREIGN KEY (id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_user_personal_created_by FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT
);


CREATE TABLE user_bans (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  reason TEXT NOT NULL,
  created_by UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ended_at TIMESTAMPTZ,
  CONSTRAINT fk_user_bans_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_user_bans_created_by FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT
);

CREATE INDEX ix_user_bans_user_id ON user_bans(user_id);
CREATE INDEX ix_user_bans_active ON user_bans(user_id) WHERE ended_at IS NULL;


CREATE TABLE user_addresses (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  city TEXT NOT NULL,
  street TEXT NOT NULL,
  postal_code TEXT NOT NULL,
  is_default BOOLEAN NOT NULL DEFAULT FALSE,
  created_by UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_user_addresses_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_user_addresses_created_by FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT
);

CREATE INDEX ix_user_addresses_user_id ON user_addresses(user_id);
CREATE UNIQUE INDEX ix_user_addresses_default ON user_addresses(user_id) WHERE is_default = TRUE;


CREATE TABLE categories (
  id UUID PRIMARY KEY,
  parent_id UUID,
  name VARCHAR(150) NOT NULL,
  slug VARCHAR(150) NOT NULL UNIQUE,
  sort_order INT NOT NULL DEFAULT 0,
  created_by UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_categories_parent FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE SET NULL,
  CONSTRAINT fk_categories_created_by FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT
);

CREATE INDEX ix_categories_parent_id ON categories(parent_id);
CREATE INDEX ix_categories_sort_order ON categories(sort_order);


CREATE TABLE products (
  id UUID PRIMARY KEY,
  category_id UUID NOT NULL,
  title VARCHAR(255) NOT NULL,
  slug VARCHAR(255) NOT NULL UNIQUE,
  description TEXT,
  base_price NUMERIC(10, 2) NOT NULL CHECK (base_price >= 0),
  attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
  is_published BOOLEAN NOT NULL DEFAULT FALSE,
  created_by UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  deleted_at TIMESTAMPTZ,
  CONSTRAINT fk_products_category FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT,
  CONSTRAINT fk_products_created_by FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT
);

CREATE INDEX ix_products_category_published ON products(category_id, is_published) WHERE deleted_at IS NULL;
CREATE INDEX ix_products_slug ON products(slug) WHERE deleted_at IS NULL;
CREATE INDEX ix_products_created_at ON products(created_at DESC) WHERE deleted_at IS NULL;


CREATE TABLE product_variants (
  id UUID PRIMARY KEY,
  product_id UUID NOT NULL,
  sku VARCHAR(100) NOT NULL UNIQUE,
  size VARCHAR(32) NOT NULL,
  color_name VARCHAR(64) NOT NULL,
  color_hex VARCHAR(7),
  price_override NUMERIC(10, 2) CHECK (price_override IS NULL OR price_override >= 0),
  stock_quantity INT NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),
  created_by UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_product_variants_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
  CONSTRAINT fk_product_variants_created_by FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT,
  CONSTRAINT uq_product_variants_size_color UNIQUE (product_id, size, color_name)
);

CREATE INDEX ix_product_variants_product_id ON product_variants(product_id);
CREATE INDEX ix_product_variants_sku ON product_variants(sku);


CREATE TABLE product_images (
  id UUID PRIMARY KEY,
  product_id UUID NOT NULL,
  variant_id UUID,
  url TEXT NOT NULL,
  alt_text VARCHAR(255),
  sort_order INT NOT NULL DEFAULT 0,
  is_main BOOLEAN NOT NULL DEFAULT FALSE,
  created_by UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_product_images_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
  CONSTRAINT fk_product_images_variant FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE SET NULL,
  CONSTRAINT fk_product_images_created_by FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT
);

CREATE INDEX ix_product_images_product_sort ON product_images(product_id, sort_order);
CREATE INDEX ix_product_images_variant_id ON product_images(variant_id);


CREATE TABLE carts (
  id UUID PRIMARY KEY,
  user_id UUID UNIQUE,
  session_token VARCHAR(128) UNIQUE,
  created_by UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_carts_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_carts_created_by FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX ix_carts_user_id ON carts(user_id);
CREATE INDEX ix_carts_session_token ON carts(session_token);


CREATE TABLE cart_items (
  id UUID PRIMARY KEY,
  cart_id UUID NOT NULL,
  variant_id UUID NOT NULL,
  quantity INT NOT NULL CHECK (quantity > 0),
  created_by UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_cart_items_cart FOREIGN KEY (cart_id) REFERENCES carts(id) ON DELETE CASCADE,
  CONSTRAINT fk_cart_items_variant FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE CASCADE,
  CONSTRAINT fk_cart_items_created_by FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
  CONSTRAINT uq_cart_items_cart_variant UNIQUE (cart_id, variant_id)
);

CREATE INDEX ix_cart_items_cart_id ON cart_items(cart_id);
CREATE INDEX ix_cart_items_variant_id ON cart_items(variant_id);


CREATE TABLE favorites (
  user_id UUID NOT NULL,
  product_id UUID NOT NULL,
  created_by UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id, product_id),
  CONSTRAINT fk_favorites_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_favorites_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
  CONSTRAINT fk_favorites_created_by FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT
);

CREATE INDEX ix_favorites_product_id ON favorites(product_id);


CREATE TABLE orders (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending_payment'
    CHECK (status IN ('pending_payment', 'paid', 'processing', 'shipped', 'delivered', 'cancelled')),
  total_amount NUMERIC(10, 2) NOT NULL CHECK (total_amount >= 0),
  shipping_address JSONB NOT NULL,
  tracking_number VARCHAR(128),
  created_by UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_orders_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT,
  CONSTRAINT fk_orders_created_by FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT
);

CREATE INDEX ix_orders_user_created ON orders(user_id, created_at DESC);
CREATE INDEX ix_orders_status ON orders(status);


CREATE TABLE order_items (
  id UUID PRIMARY KEY,
  order_id UUID NOT NULL,
  variant_id UUID,
  title_snapshot VARCHAR(255) NOT NULL,
  sku_snapshot VARCHAR(100) NOT NULL,
  size_snapshot VARCHAR(32) NOT NULL,
  color_snapshot VARCHAR(64) NOT NULL,
  unit_price NUMERIC(10, 2) NOT NULL CHECK (unit_price >= 0),
  quantity INT NOT NULL CHECK (quantity > 0),
  created_by UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_order_items_order FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
  CONSTRAINT fk_order_items_variant FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE SET NULL,
  CONSTRAINT fk_order_items_created_by FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT
);

CREATE INDEX ix_order_items_order_id ON order_items(order_id);
CREATE INDEX ix_order_items_variant_id ON order_items(variant_id);


CREATE TABLE payments (
  id UUID PRIMARY KEY,
  order_id UUID NOT NULL,
  provider VARCHAR(64) NOT NULL,
  external_id VARCHAR(255),
  status VARCHAR(32) NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'succeeded', 'failed', 'refunded')),
  amount NUMERIC(10, 2) NOT NULL CHECK (amount >= 0),
  created_by UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  paid_at TIMESTAMPTZ,
  CONSTRAINT fk_payments_order FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE RESTRICT,
  CONSTRAINT fk_payments_created_by FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX ix_payments_order_id ON payments(order_id);
CREATE INDEX ix_payments_provider_external ON payments(provider, external_id);
CREATE INDEX ix_payments_status ON payments(status);


CREATE TABLE reviews (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  product_id UUID NOT NULL,
  order_item_id UUID NOT NULL UNIQUE,
  rating SMALLINT NOT NULL CHECK (rating >= 1 AND rating <= 5),
  fit_feedback VARCHAR(20),
  comment TEXT,
  is_published BOOLEAN NOT NULL DEFAULT TRUE,
  created_by UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_reviews_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_reviews_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
  CONSTRAINT fk_reviews_order_item FOREIGN KEY (order_item_id) REFERENCES order_items(id) ON DELETE RESTRICT,
  CONSTRAINT fk_reviews_created_by FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT,
  CONSTRAINT uq_reviews_user_product UNIQUE (user_id, product_id)
);

CREATE INDEX ix_reviews_product_published ON reviews(product_id) WHERE is_published = TRUE;
CREATE INDEX ix_reviews_user_id ON reviews(user_id);
