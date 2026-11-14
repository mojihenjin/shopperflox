from uuid import UUID

from src.domain.models import CartDomain, CartItemDomain, FavoriteDomain
from uuid6 import uuid7


def test_cart_domain():
    user_id = uuid7()
    cart = CartDomain(user_id=user_id)

    assert isinstance(cart.id, UUID)
    assert cart.user_id == user_id
    assert cart.session_token is None


def test_cart_item_domain():
    cart_id = uuid7()
    variant_id = uuid7()
    item = CartItemDomain(
        cart_id=cart_id,
        variant_id=variant_id,
        quantity=3,
    )

    assert isinstance(item.id, UUID)
    assert item.cart_id == cart_id
    assert item.variant_id == variant_id
    assert item.quantity == 3


def test_favorite_domain():
    user_id = uuid7()
    prod_id = uuid7()
    author_id = uuid7()

    fav = FavoriteDomain(
        user_id=user_id,
        product_id=prod_id,
        created_by=author_id,
    )

    assert fav.user_id == user_id
    assert fav.product_id == prod_id
    assert fav.created_by == author_id
