import time
from typing import List, Optional
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, BigInteger, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from database.connection import JSONField, get_db
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import SQLAlchemyError
from utils.helper_functions import get_custom_logger

Base = declarative_base()

log = get_custom_logger(name=__name__)

class GeneData(Base):
    __tablename__ = "gene_data"

    id = Column(String(255), primary_key=True)
    gene_data = Column(JSONField, nullable=False)
    created_at = Column(BigInteger, default=lambda: int(time.time() * 1000))
    updated_at = Column(BigInteger, default=lambda: int(time.time() * 1000), onupdate=lambda: int(time.time() * 1000))
    is_deleted = Column(Boolean, default=False)

    def __repr__(self):
        return f"<GeneData(id={self.id}, created_at={self.created_at}, is_deleted={self.is_deleted})>"

    def soft_delete(self, db_session):
        """Soft delete the gene data record."""
        self.is_deleted = True
        self.updated_at = int(time.time() * 1000)
        db_session.commit()
        log.info(f"Soft deleted GeneData with id={self.id}")
        return self

    @classmethod
    def get_by_id(cls, db_session, gene_data_id: str) -> Optional['GeneData']:
        """Get a GeneData by ID."""
        try:
            gene_data = db_session.query(cls).filter_by(id=gene_data_id, is_deleted=False).first()
            if not gene_data:
                log.warning(f"GeneData with id={gene_data_id} not found.")
            return gene_data
        except SQLAlchemyError as e:
            log.exception(f"Error fetching GeneData with id={gene_data_id}: {str(e)}")
            return None

    @classmethod
    def create(cls, db_session, gene_data_id: str, gene_data: dict) -> 'GeneData':
        """Create a new GeneData entry."""
        new_gene_data = cls(id=gene_data_id, gene_data=gene_data)
        db_session.add(new_gene_data)
        db_session.commit()
        db_session.refresh(new_gene_data)
        log.info(f"Created new GeneData with id={gene_data_id}")
        return new_gene_data


class GeneDataModel(BaseModel):
    id: str
    gene_data: dict
    created_at: int
    updated_at: int
    is_deleted: bool = False

    class Config:
        orm_mode = True


class GeneDataCreateRequest(BaseModel):
    gene_data: dict = Field(..., example={"gene_sequence": "AGCTGACGTA", "mutations": []})

    class Config:
        orm_mode = True


class GeneDataUpdateRequest(BaseModel):
    gene_data: Optional[dict] = Field(None, example={"gene_sequence": "AGCTGACGTAGCTG", "mutations": [{"location": "5", "mutation": "A->T"}]})

    class Config:
        orm_mode = True


class GeneDataTable:
    def create_gene_data(self, db_session, gene_data_id: str, gene_data: dict) -> Optional[GeneDataModel]:
        """Create a new GeneData entry."""
        try:
            gene_data_entry = GeneData.create(db_session, gene_data_id, gene_data)
            return GeneDataModel.from_orm(gene_data_entry)
        except Exception as e:
            log.error(f"Error creating GeneData: {str(e)}")
            return None

    def update_gene_data(self, db_session, gene_data_id: str, gene_data: dict) -> Optional[GeneDataModel]:
        """Update an existing GeneData entry."""
        try:
            gene_data_entry = GeneData.get_by_id(db_session, gene_data_id)
            if gene_data_entry:
                gene_data_entry.gene_data = gene_data
                gene_data_entry.updated_at = int(time.time() * 1000)
                db_session.commit()
                db_session.refresh(gene_data_entry)
                return GeneDataModel.from_orm(gene_data_entry)
            else:
                log.warning(f"GeneData with id={gene_data_id} not found for update.")
                return None
        except SQLAlchemyError as e:
            log.error(f"Error updating GeneData with id={gene_data_id}: {str(e)}")
            return None

    def get_gene_data(self, db_session, gene_data_id: str) -> Optional[GeneDataModel]:
        """Get a GeneData by ID."""
        try:
            gene_data_entry = GeneData.get_by_id(db_session, gene_data_id)
            if gene_data_entry:
                return GeneDataModel.from_orm(gene_data_entry)
            return None
        except SQLAlchemyError as e:
            log.error(f"Error retrieving GeneData with id={gene_data_id}: {str(e)}")
            return None

    def soft_delete_gene_data(self, db_session, gene_data_id: str) -> Optional[GeneDataModel]:
        """Soft delete a GeneData record."""
        try:
            gene_data_entry = GeneData.get_by_id(db_session, gene_data_id)
            if gene_data_entry:
                gene_data_entry.soft_delete(db_session)
                return GeneDataModel.from_orm(gene_data_entry)
            log.warning(f"GeneData with id={gene_data_id} not found for soft delete.")
            return None
        except SQLAlchemyError as e:
            log.error(f"Error soft deleting GeneData with id={gene_data_id}: {str(e)}")
            return None


class GeneDataQueryParams(BaseModel):
    page: int = 1
    page_size: int = 10
    order_by: Optional[str] = "created_at"
    descending: bool = False

    class Config:
        orm_mode = True


def get_gene_data_list(db_session, query_params: GeneDataQueryParams) -> List[GeneDataModel]:
    """Retrieve a list of GeneData entries with pagination, sorting, and filtering."""
    try:
        query = db_session.query(GeneData).filter_by(is_deleted=False)
        
        if query_params.order_by:
            order_column = getattr(GeneData, query_params.order_by, None)
            if order_column:
                if query_params.descending:
                    query = query.order_by(order_column.desc())
                else:
                    query = query.order_by(order_column)

        # Apply pagination
        offset = (query_params.page - 1) * query_params.page_size
        limit = query_params.page_size
        results = query.offset(offset).limit(limit).all()

        return [GeneDataModel.from_orm(item) for item in results]
    except SQLAlchemyError as e:
        log.error(f"Error fetching GeneData list: {str(e)}")
        return []


def example_function(db_session):
    """Example function showing how to use the CRUD operations."""
    # Create GeneData
    gene_data = {
        "gene_sequence": "AGCTGACGTA",
        "mutations": []
    }
    created_data = GeneDataTable().create_gene_data(db_session, "unique_id_123", gene_data)
    log.info(f"Created GeneData: {created_data}")

    # Update GeneData
    updated_data = GeneDataTable().update_gene_data(db_session, "unique_id_123", {"gene_sequence": "AGCTGACGTAGCTG", "mutations": [{"location": "5", "mutation": "A->T"}]})
    log.info(f"Updated GeneData: {updated_data}")

    # Get GeneData
    retrieved_data = GeneDataTable().get_gene_data(db_session, "unique_id_123")
    log.info(f"Retrieved GeneData: {retrieved_data}")

    # Soft delete GeneData
    soft_deleted_data = GeneDataTable().soft_delete_gene_data(db_session, "unique_id_123")
    log.info(f"Soft deleted GeneData: {soft_deleted_data}")
