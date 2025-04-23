from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from db_tools import GeneDataService
from database.connection import get_db

app = FastAPI()

@app.post("/gene_data/")
def create_gene_data(gene_data_id: str, gene_data: dict, db: Session = Depends(get_db)):
    gene_data_service = GeneDataService(db)
    result = gene_data_service.insert_gene_data(gene_data_id, gene_data)
    if result:
        return result
    raise HTTPException(status_code=400, detail="Gene data insertion failed")

@app.get("/gene_data/{gene_data_id}")
def get_gene_data(gene_data_id: str, db: Session = Depends(get_db)):
    gene_data_service = GeneDataService(db)
    result = gene_data_service.get_gene_data(gene_data_id)
    if result:
        return result
    raise HTTPException(status_code=404, detail="Gene data not found")

@app.put("/gene_data/{gene_data_id}")
def update_gene_data(gene_data_id: str, gene_data: dict, db: Session = Depends(get_db)):
    gene_data_service = GeneDataService(db)
    result = gene_data_service.update_gene_data(gene_data_id, gene_data)
    if result:
        return result
    raise HTTPException(status_code=404, detail="Gene data not found for update")

@app.delete("/gene_data/{gene_data_id}")
def delete_gene_data(gene_data_id: str, db: Session = Depends(get_db)):
    gene_data_service = GeneDataService(db)
    result = gene_data_service.delete_gene_data(gene_data_id)
    if result:
        return {"message": "Gene data deleted successfully"}
    raise HTTPException(status_code=404, detail="Gene data not found for deletion")

@app.get("/gene_data/")
def get_all_gene_data(db: Session = Depends(get_db)):
    gene_data_service = GeneDataService(db)
    result = gene_data_service.get_all_gene_data()
    if result:
        return result
    raise HTTPException(status_code=404, detail="No gene data found")

@app.get("/gene_data/source/{source}")
def get_gene_data_by_source(source: str, db: Session = Depends(get_db)):
    gene_data_service = GeneDataService(db)
    result = gene_data_service.get_gene_data_by_source(source)
    if result:
        return result
    raise HTTPException(status_code=404, detail="Gene data not found for the specified source")

@app.get("/gene_data/created_after/{timestamp}")
def get_gene_data_created_after(timestamp: int, db: Session = Depends(get_db)):
    gene_data_service = GeneDataService(db)
    result = gene_data_service.get_gene_data_created_after(timestamp)
    if result:
        return result
    raise HTTPException(status_code=404, detail="No gene data found created after the specified timestamp")

@app.get("/gene_data/updated_after/{timestamp}")
def get_gene_data_updated_after(timestamp: int, db: Session = Depends(get_db)):
    gene_data_service = GeneDataService(db)
    result = gene_data_service.get_gene_data_updated_after(timestamp)
    if result:
        return result
    raise HTTPException(status_code=404, detail="No gene data found updated after the specified timestamp")
