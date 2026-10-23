from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    source_url: Mapped[str | None] = mapped_column(String(2000), default=None)
    # SHA-256 of the file bytes, hex encoded. Unique so the database itself
    # refuses a second copy of the same file: checking first and inserting
    # after leaves a gap where two simultaneous uploads both pass the check.
    sha256: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pages: Mapped[list[Page]] = relationship(
        back_populates="document",
        order_by="Page.number",
        cascade="all, delete-orphan",
        # The foreign key already cascades in the database, so SQLAlchemy does
        # not need to load every page just to delete them one by one.
        passive_deletes=True,
    )


class Page(Base):
    __tablename__ = "pages"
    __table_args__ = (UniqueConstraint("document_id", "number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    # Physical position in the file, starting at 1. Not the number printed on
    # the page, which skips covers and restarts in appendices: the physical
    # one is what a reader types into the PDF viewer to get there.
    number: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)

    document: Mapped[Document] = relationship(back_populates="pages")
