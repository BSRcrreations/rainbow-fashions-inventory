from enum import Enum


class UserRole(str, Enum):
    OWNER = "OWNER"
    MANAGER = "MANAGER"
    STAFF = "STAFF"


class PricingType(str, Enum):
    MRP = "MRP"
    OWN_PRICE = "OWN_PRICE"


class PurchaseStatus(str, Enum):
    DRAFT = "DRAFT"
    REVIEWED = "REVIEWED"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class StockMovementType(str, Enum):
    PURCHASE = "PURCHASE"
    SALE = "SALE"
    ADJUSTMENT = "ADJUSTMENT"


class UploadFileType(str, Enum):
    INVOICE_IMAGE = "INVOICE_IMAGE"
    INVOICE_PDF = "INVOICE_PDF"
    PRODUCT_IMAGE = "PRODUCT_IMAGE"
