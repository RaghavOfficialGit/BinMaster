from fastapi import FastAPI, APIRouter, HTTPException, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from bson import ObjectId


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Helper function to convert ObjectId to string
def bin_helper(bin) -> dict:
    return {
        "id": str(bin["_id"]),
        "bin_number": bin["bin_number"],
        "location": bin["location"],
        "capacity": bin["capacity"],
        "current_stock": bin["current_stock"],
        "status": bin["status"],
        "barcode": bin.get("barcode", ""),
        "last_updated": bin["last_updated"],
        "created_at": bin["created_at"]
    }


# Define Models
class WarehouseBin(BaseModel):
    id: Optional[str] = None
    bin_number: str
    location: str
    capacity: int
    current_stock: int = 0
    status: str = "active"  # active, inactive
    barcode: str = ""
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BinCreate(BaseModel):
    bin_number: str
    location: str
    capacity: int
    current_stock: int = 0
    status: str = "active"
    barcode: str = ""


class BinUpdate(BaseModel):
    location: Optional[str] = None
    capacity: Optional[int] = None
    current_stock: Optional[int] = None
    status: Optional[str] = None
    barcode: Optional[str] = None


class BinStats(BaseModel):
    total_bins: int
    active_bins: int
    inactive_bins: int
    total_capacity: int
    total_stock: int
    utilization_percentage: float


# Routes
@api_router.get("/")
async def root():
    return {"message": "Warehouse Bin Lookup API"}


@api_router.get("/bins", response_model=List[WarehouseBin])
async def get_bins(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    status: Optional[str] = None
):
    """Get all bins with pagination and optional filtering"""
    query = {}
    
    if search:
        query["$or"] = [
            {"bin_number": {"$regex": search, "$options": "i"}},
            {"location": {"$regex": search, "$options": "i"}},
            {"barcode": {"$regex": search, "$options": "i"}}
        ]
    
    if status:
        query["status"] = status
    
    bins = await db.warehouse_bins.find(query).skip(skip).limit(limit).to_list(limit)
    return [bin_helper(bin) for bin in bins]


@api_router.get("/bins/count", response_model=BinStats)
async def get_bin_stats():
    """Get warehouse bin statistics"""
    total_bins = await db.warehouse_bins.count_documents({})
    active_bins = await db.warehouse_bins.count_documents({"status": "active"})
    inactive_bins = await db.warehouse_bins.count_documents({"status": "inactive"})
    
    # Calculate total capacity and stock
    pipeline = [
        {
            "$group": {
                "_id": None,
                "total_capacity": {"$sum": "$capacity"},
                "total_stock": {"$sum": "$current_stock"}
            }
        }
    ]
    
    result = await db.warehouse_bins.aggregate(pipeline).to_list(1)
    
    total_capacity = result[0]["total_capacity"] if result else 0
    total_stock = result[0]["total_stock"] if result else 0
    utilization = (total_stock / total_capacity * 100) if total_capacity > 0 else 0
    
    return BinStats(
        total_bins=total_bins,
        active_bins=active_bins,
        inactive_bins=inactive_bins,
        total_capacity=total_capacity,
        total_stock=total_stock,
        utilization_percentage=round(utilization, 2)
    )


@api_router.get("/bins/barcode/{barcode}", response_model=WarehouseBin)
async def get_bin_by_barcode(barcode: str):
    """Lookup bin by barcode"""
    bin_doc = await db.warehouse_bins.find_one({"barcode": barcode})
    if not bin_doc:
        raise HTTPException(status_code=404, detail="Bin not found with this barcode")
    return bin_helper(bin_doc)


@api_router.get("/bins/{bin_id}", response_model=WarehouseBin)
async def get_bin(bin_id: str):
    """Get a single bin by ID"""
    try:
        bin_doc = await db.warehouse_bins.find_one({"_id": ObjectId(bin_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid bin ID format")
    
    if not bin_doc:
        raise HTTPException(status_code=404, detail="Bin not found")
    
    return bin_helper(bin_doc)


@api_router.post("/bins", response_model=WarehouseBin)
async def create_bin(bin_data: BinCreate):
    """Create a new warehouse bin"""
    # Check if bin_number already exists
    existing = await db.warehouse_bins.find_one({"bin_number": bin_data.bin_number})
    if existing:
        raise HTTPException(status_code=400, detail="Bin number already exists")
    
    # Validate stock doesn't exceed capacity
    if bin_data.current_stock > bin_data.capacity:
        raise HTTPException(status_code=400, detail="Current stock cannot exceed capacity")
    
    bin_dict = bin_data.dict()
    bin_dict["created_at"] = datetime.utcnow()
    bin_dict["last_updated"] = datetime.utcnow()
    
    result = await db.warehouse_bins.insert_one(bin_dict)
    created_bin = await db.warehouse_bins.find_one({"_id": result.inserted_id})
    
    return bin_helper(created_bin)


@api_router.put("/bins/{bin_id}", response_model=WarehouseBin)
async def update_bin(bin_id: str, bin_update: BinUpdate):
    """Update a warehouse bin"""
    try:
        bin_doc = await db.warehouse_bins.find_one({"_id": ObjectId(bin_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid bin ID format")
    
    if not bin_doc:
        raise HTTPException(status_code=404, detail="Bin not found")
    
    update_data = {k: v for k, v in bin_update.dict().items() if v is not None}
    
    # Validate stock doesn't exceed capacity
    capacity = update_data.get("capacity", bin_doc["capacity"])
    current_stock = update_data.get("current_stock", bin_doc["current_stock"])
    
    if current_stock > capacity:
        raise HTTPException(status_code=400, detail="Current stock cannot exceed capacity")
    
    if update_data:
        update_data["last_updated"] = datetime.utcnow()
        await db.warehouse_bins.update_one(
            {"_id": ObjectId(bin_id)},
            {"$set": update_data}
        )
    
    updated_bin = await db.warehouse_bins.find_one({"_id": ObjectId(bin_id)})
    return bin_helper(updated_bin)


@api_router.delete("/bins/{bin_id}")
async def delete_bin(bin_id: str):
    """Delete a warehouse bin"""
    try:
        result = await db.warehouse_bins.delete_one({"_id": ObjectId(bin_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid bin ID format")
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Bin not found")
    
    return {"message": "Bin deleted successfully"}


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
