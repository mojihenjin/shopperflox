from .analytics import (
    AnalyticsRepositoryProtocol,
    AnalyticsUnitOfWorkProtocol,
)
from .brand import (
    BrandRepositoryProtocol,
    BrandUnitOfWorkProtocol,
)
from .cart import (
    CartRepositoryProtocol,
    CartUnitOfWorkProtocol,
)
from .catalog import (
    CatalogUnitOfWorkProtocol,
    CategoryRepositoryProtocol,
    FavoriteRepositoryProtocol,
    ProductImageRepositoryProtocol,
    ProductRepositoryProtocol,
    ProductVariantRepositoryProtocol,
)
from .integrations import (
    EmailTransportProtocol,
    EmailVerificationStoreProtocol,
    FileStorageProtocol,
    PaymentGatewayProtocol,
    PaymentSessionResult,
    TaskQueueProtocol,
)
from .notification import (
    NotificationRepositoryProtocol,
    NotificationUnitOfWorkProtocol,
)
from .order import (
    OrderRepositoryProtocol,
    OrderUnitOfWorkProtocol,
    PaymentRepositoryProtocol,
    ReviewRepositoryProtocol,
    ReviewUnitOfWorkProtocol,
)
from .queue import (
    FulfillmentQueueRepositoryProtocol,
    QueueUnitOfWorkProtocol,
)
from .security import (
    PasswordHasherProtocol,
    TokenBlacklistProtocol,
    TokenProviderProtocol,
)
from .uow import UnitOfWorkProtocol
from .user import (
    UserAddressRepositoryProtocol,
    UserBanRepositoryProtocol,
    UserPersonalRepositoryProtocol,
    UserRepositoryProtocol,
    UserUnitOfWorkProtocol,
)

__all__ = [
    "AnalyticsRepositoryProtocol",
    "AnalyticsUnitOfWorkProtocol",
    "BrandRepositoryProtocol",
    "BrandUnitOfWorkProtocol",
    "CartRepositoryProtocol",
    "CartUnitOfWorkProtocol",
    "CatalogUnitOfWorkProtocol",
    "CategoryRepositoryProtocol",
    "EmailTransportProtocol",
    "EmailVerificationStoreProtocol",
    "FavoriteRepositoryProtocol",
    "FileStorageProtocol",
    "FulfillmentQueueRepositoryProtocol",
    "NotificationRepositoryProtocol",
    "NotificationUnitOfWorkProtocol",
    "OrderRepositoryProtocol",
    "OrderUnitOfWorkProtocol",
    "PasswordHasherProtocol",
    "PaymentGatewayProtocol",
    "PaymentRepositoryProtocol",
    "PaymentSessionResult",
    "ProductImageRepositoryProtocol",
    "ProductRepositoryProtocol",
    "ProductVariantRepositoryProtocol",
    "QueueUnitOfWorkProtocol",
    "ReviewRepositoryProtocol",
    "ReviewUnitOfWorkProtocol",
    "TaskQueueProtocol",
    "TokenBlacklistProtocol",
    "TokenProviderProtocol",
    "UnitOfWorkProtocol",
    "UserAddressRepositoryProtocol",
    "UserBanRepositoryProtocol",
    "UserPersonalRepositoryProtocol",
    "UserRepositoryProtocol",
    "UserUnitOfWorkProtocol",
]
