from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class ProductRequestStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUOTED = "quoted"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Product(Base):
    """
    Product catalogue table.

    Used for cleaning products, fumigation products, equipment, supplies,
    and any other Astra Group products that should display on the frontend.
    """

    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(280), nullable=False, unique=True, index=True)
    category = Column(String(120), nullable=True, index=True)

    short_description = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)

    price = Column(Numeric(12, 2), nullable=True)
    currency = Column(String(10), nullable=False, default="TZS")
    unit = Column(String(100), nullable=True)  # item, litre, kg, carton, service pack, etc.
    price_note = Column(String(255), nullable=True)

    stock_quantity = Column(Integer, nullable=True)
    sku = Column(String(120), nullable=True, unique=True, index=True)

    is_featured = Column(Boolean, nullable=False, default=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    display_order = Column(Integer, nullable=False, default=0, index=True)

    meta_title = Column(String(255), nullable=True)
    meta_description = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    images = relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ProductImage.display_order.asc(), ProductImage.id.asc()",
    )
    requests = relationship("ProductRequest", back_populates="product")
    created_by = relationship("User", foreign_keys=[created_by_user_id])

    def __repr__(self) -> str:
        return f"<Product id={self.id} name={self.name!r}>"


class ProductImage(Base):
    """
    Stores images for products.
    """

    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    image_url = Column(String(1000), nullable=False)
    image_path = Column(String(1000), nullable=True)
    original_filename = Column(String(255), nullable=True)
    alt_text = Column(String(255), nullable=True)

    image_type = Column(String(50), nullable=False, default="gallery", index=True)  # primary, banner, gallery
    is_primary = Column(Boolean, nullable=False, default=False, index=True)
    is_banner = Column(Boolean, nullable=False, default=False, index=True)
    display_order = Column(Integer, nullable=False, default=0, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    product = relationship("Product", back_populates="images")
    created_by = relationship("User", foreign_keys=[created_by_user_id])

    __table_args__ = (
        UniqueConstraint("product_id", "image_url", name="uq_product_image_url_per_product"),
    )

    def __repr__(self) -> str:
        return f"<ProductImage id={self.id} product_id={self.product_id}>"


class ProductRequest(Base):
    """
    Customer product request / quotation request.

    It can point to an existing product or contain a free-text product_name.
    """

    __tablename__ = "product_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)

    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(100), nullable=True, index=True)
    company_name = Column(String(255), nullable=True)

    product_name = Column(String(255), nullable=False, index=True)
    quantity = Column(String(100), nullable=True)
    destination = Column(String(255), nullable=True)
    delivery_required = Column(Boolean, nullable=False, default=False)
    message = Column(Text, nullable=True)

    status = Column(String(50), nullable=False, default=ProductRequestStatus.NEW.value, index=True)
    admin_notes = Column(Text, nullable=True)
    source = Column(String(100), nullable=False, default="website")
    whatsapp_link = Column(String(1500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user = relationship("User", foreign_keys=[user_id])
    product = relationship("Product", back_populates="requests")

    def __repr__(self) -> str:
        return f"<ProductRequest id={self.id} product_name={self.product_name!r} status={self.status}>"
