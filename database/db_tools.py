from sqlalchemy.orm import Session
from typing import Optional
from models import GeneData, GeneDataModel
from datetime import datetime
import time
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class GeneDataService:
    def __init__(self, db: Session):
        self.db = db

    def insert_gene_data(self, gene_data_id: str, gene_data: dict) -> Optional[GeneDataModel]:
        try:
            new_gene_data = GeneData(
                id=gene_data_id,
                gene_data=gene_data,
                created_at=int(time.time() * 1000),
                updated_at=int(time.time() * 1000)
            )
            self.db.add(new_gene_data)
            self.db.commit()
            self.db.refresh(new_gene_data)
            logger.info(f"Successfully inserted gene data with ID: {gene_data_id}")
            return GeneDataModel.from_orm(new_gene_data)
        except Exception as e:
            logger.exception(f"Failed to insert gene data: {str(e)}")
            return None

    def get_gene_data(self, gene_data_id: str) -> Optional[GeneDataModel]:
        try:
            gene_data = self.db.query(GeneData).filter(GeneData.id == gene_data_id).first()
            if gene_data:
                logger.info(f"Successfully retrieved gene data with ID: {gene_data_id}")
                return GeneDataModel.from_orm(gene_data)
            else:
                logger.warning(f"Gene data with ID: {gene_data_id} not found.")
                return None
        except Exception as e:
            logger.exception(f"Failed to get gene data: {str(e)}")
            return None

    def update_gene_data(self, gene_data_id: str, gene_data: dict) -> Optional[GeneDataModel]:
        try:
            existing_gene_data = self.db.query(GeneData).filter(GeneData.id == gene_data_id).first()
            if existing_gene_data:
                existing_gene_data.gene_data = gene_data
                existing_gene_data.updated_at = int(time.time() * 1000)
                self.db.commit()
                self.db.refresh(existing_gene_data)
                logger.info(f"Successfully updated gene data with ID: {gene_data_id}")
                return GeneDataModel.from_orm(existing_gene_data)
            else:
                logger.warning(f"Gene data with ID: {gene_data_id} not found.")
                return None
        except Exception as e:
            logger.exception(f"Failed to update gene data: {str(e)}")
            return None

    def delete_gene_data(self, gene_data_id: str) -> bool:
        try:
            gene_data = self.db.query(GeneData).filter(GeneData.id == gene_data_id).first()
            if gene_data:
                self.db.delete(gene_data)
                self.db.commit()
                logger.info(f"Successfully deleted gene data with ID: {gene_data_id}")
                return True
            else:
                logger.warning(f"Gene data with ID: {gene_data_id} not found for deletion.")
                return False
        except Exception as e:
            logger.exception(f"Failed to delete gene data: {str(e)}")
            return False

    def get_all_gene_data(self) -> list:
        try:
            all_gene_data = self.db.query(GeneData).all()
            logger.info(f"Successfully retrieved all gene data.")
            return [GeneDataModel.from_orm(g) for g in all_gene_data]
        except Exception as e:
            logger.exception(f"Failed to retrieve all gene data: {str(e)}")
            return []

    def get_gene_data_by_source(self, source: str) -> list:
        try:
            gene_data = self.db.query(GeneData).filter(GeneData.gene_data['source'].astext == source).all()
            if gene_data:
                logger.info(f"Successfully retrieved gene data by source: {source}")
                return [GeneDataModel.from_orm(g) for g in gene_data]
            else:
                logger.warning(f"No gene data found for source: {source}")
                return []
        except Exception as e:
            logger.exception(f"Failed to retrieve gene data by source: {str(e)}")
            return []
