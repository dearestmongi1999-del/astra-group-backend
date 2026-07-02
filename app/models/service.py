from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
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


class ServiceType(str, Enum):
    CLEANING = "cleaning"
    FUMIGATION = "fumigation"


class ServiceBookingStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Service(Base):
    """
    Main service catalogue table.

    Astra Group mainly offers Cleaning and Fumigation, but this model allows
    many service records under those two service types, for example:
    - Office Cleaning
    - Residential Cleaning
    - Post Construction Cleaning
    - Pest Control
    - Warehouse Fumigation
    """

    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    service_type = Column(String(50), nullable=False, default=ServiceType.CLEANING.value, index=True)
    title = Column(String(255), nullable=False, index=True)
    slug = Column(String(280), nullable=False, unique=True, index=True)

    short_description = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)

    starting_price = Column(Numeric(12, 2), nullable=True)
    currency = Column(String(10), nullable=False, default="TZS")
    price_note = Column(String(255), nullable=True)
    duration = Column(String(120), nullable=True)

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
        "ServiceImage",
        back_populates="service",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ServiceImage.display_order.asc(), ServiceImage.id.asc()",
    )
    bookings = relationship("ServiceBooking", back_populates="service")
    created_by = relationship("User", foreign_keys=[created_by_user_id])

    def __repr__(self) -> str:
        return f"<Service id={self.id} type={self.service_type} title={self.title!r}>"


class ServiceImage(Base):
    """
    Stores images for a service.

    One service can have:
    - a primary image
    - a banner image
    - many gallery images
    """

    __tablename__ = "service_images"

    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False, index=True)
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

    service = relationship("Service", back_populates="images")
    created_by = relationship("User", foreign_keys=[created_by_user_id])

    __table_args__ = (
        UniqueConstraint("service_id", "image_url", name="uq_service_image_url_per_service"),
    )

    def __repr__(self) -> str:
        return f"<ServiceImage id={self.id} service_id={self.service_id}>"


class ServiceBooking(Base):
    """
    Customer service booking request.

    It can be submitted by a logged-in user or a public visitor.
    """

    __tablename__ = "service_bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="SET NULL"), nullable=True, index=True)

    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(100), nullable=True, index=True)
    company_name = Column(String(255), nullable=True)

    service_type = Column(String(50), nullable=False, default=ServiceType.CLEANING.value, index=True)
    preferred_date = Column(Date, nullable=True)
    preferred_time = Column(String(100), nullable=True)

    address = Column(String(500), nullable=True)
    city = Column(String(120), nullable=True)
    message = Column(Text, nullable=True)

    status = Column(String(50), nullable=False, default=ServiceBookingStatus.NEW.value, index=True)
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
    service = relationship("Service", back_populates="bookings")

    def __repr__(self) -> str:
        return f"<ServiceBooking id={self.id} service_type={self.service_type} status={self.status}>"
