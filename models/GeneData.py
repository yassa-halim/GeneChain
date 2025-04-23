import time
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, String, BigInteger, Boolean
from sqlalchemy.orm import relationship
from database.db_init import JSONField
from database.connection import Base, get_db
from utils.helper_functions import get_custom_logger

log = get_custom_logger(name=__name__)

class GeneDataSchema(BaseModel):
    sequence: str
    source: str
    attributes: dict

class GeneDataModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    gene_data: GeneDataSchema
    created_at: int
    updated_at: int
    is_deleted: bool = False

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
        self.is_deleted = True
        self.updated_at = int(time.time() * 1000)
        db_session.commit()
        log.info(f"Soft deleted GeneData with id={self.id}")
        return self

    @classmethod
    def get_by_id(cls, db_session, gene_data_id: str) -> Optional['GeneData']:
        try:
            gene_data = db_session.query(cls).filter_by(id=gene_data_id, is_deleted=False).first()
            if not gene_data:
                log.warning(f"GeneData with id={gene_data_id} not found.")
            return gene_data
        except Exception as e:
            log.exception(f"Error fetching GeneData with id={gene_data_id}: {str(e)}")
            return None

    @classmethod
    def create(cls, db_session, gene_data_id: str, gene_data_schema: GeneDataSchema) -> Optional['GeneData']:
        try:
            gene_data = cls(
                id=gene_data_id,
                gene_data=gene_data_schema.dict(),
                created_at=int(time.time() * 1000),
                updated_at=int(time.time() * 1000)
            )
            db_session.add(gene_data)
            db_session.commit()
            db_session.refresh(gene_data)
            log.info(f"Inserted GeneData with id={gene_data.id}")
            return gene_data
        except Exception as e:
            log.exception(f"Error inserting GeneData with id={gene_data_id}: {str(e)}")
            return None

    @classmethod
    def update(cls, db_session, gene_data_id: str, gene_data_schema: GeneDataSchema) -> Optional['GeneData']:
        try:
            gene_data = db_session.query(cls).filter_by(id=gene_data_id).first()
            if not gene_data or gene_data.is_deleted:
                log.warning(f"GeneData with id={gene_data_id} not found or already deleted.")
                return None
            gene_data.gene_data = gene_data_schema.dict()
            gene_data.updated_at = int(time.time() * 1000)
            db_session.commit()
            db_session.refresh(gene_data)
            log.info(f"Updated GeneData with id={gene_data.id}")
            return gene_data
        except Exception as e:
            log.exception(f"Error updating GeneData with id={gene_data_id}: {str(e)}")
            return None

class GeneDataTable:
    def insert_new_gene_data(self, gene_data_id: str, gene_data: GeneDataSchema) -> Optional[GeneDataModel]:
        with get_db() as db:
            if not gene_data_id:
                log.error("Cannot Insert gene data without ID. Insertion failed.")
                return None

            gene_data_id = str(gene_data_id)
            log.info(f"Inserting new gene data with ID: {gene_data_id}")
            gene_data_model = GeneDataModel(
                **{
                    "id": gene_data_id,
                    "gene_data": gene_data,
                    "created_at": int(time.time() * 1000),
                    "updated_at": int(time.time() * 1000),
                }
            )

            result = GeneData.create(db, gene_data_id, gene_data)
            return GeneDataModel.model_validate(result) if result else None
