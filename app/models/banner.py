from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.database import Base


class BannerType(str, Enum):
    HOME = "home"
    SERVICE = "service"
    PRODUCT = "product"
    PROMOTION = "promotion"
    ABOUT = "about"


class BannerTargetType(str, Enum):
    NONE = "none"
    SERVICE = "service"
    PRODUCT = "product"
    CUSTOM = "custom"


class FrontendBanner(Base):
    """
    Frontend banner table.

    Used for homepage hero banners, service banners, product promotional banners,
    and other frontend display sections.
    """

    __tablename__ = "frontend_banners"

    id = Column(Integer, primary_key=True, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    title = Column(String(255), nullable=False, index=True)
    subtitle = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)

    button_text = Column(String(120), nullable=True)
    button_link = Column(String(1000), nullable=True)

    image_url = Column(String(1000), nullable=True)
    image_path = Column(String(1000), nullable=True)
    original_filename = Column(String(255), nullable=True)
    alt_text = Column(String(255), nullable=True)

    banner_type = Column(String(50), nullable=False, default=BannerType.HOME.value, index=True)
    target_type = Column(String(50), nullable=False, default=BannerTargetType.NONE.value, index=True)
    target_id = Column(Integer, nullable=True, index=True)

    display_order = Column(Integer, nullable=False, default=0, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)

    starts_at = Column(DateTime(timezone=True), nullable=True, index=True)
    ends_at = Column(DateTime(timezone=True), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    created_by = relationship("User", foreign_keys=[created_by_user_id])

    def __repr__(self) -> str:
        return f"<FrontendBanner id={self.id} type={self.banner_type} title={self.title!r}>"
