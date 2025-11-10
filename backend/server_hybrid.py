from fastapi import FastAPI, APIRouter, HTTPException, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
import httpx
from base64 import b64encode


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configuration
DATA_SOURCE = os.getenv('DATA_SOURCE', 'mock')  # 'mock' or 'sap'

# MongoDB connection (for mock mode)
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# SAP Configuration
SAP_API_BASE_URL = os.getenv('SAP_API_BASE_URL', '')
SAP_API_USERNAME = os.getenv('SAP_API_USERNAME', '')
SAP_API_PASSWORD = os.getenv('SAP_API_PASSWORD', '')
SAP_ODATA_PATH = os.getenv('SAP_ODATA_PATH', '')

# Create Basic Auth header for SAP
if SAP_API_USERNAME and SAP_API_PASSWORD:
    auth_string = f"{SAP_API_USERNAME}:{SAP_API_PASSWORD}"
    auth_bytes = auth_string.encode('ascii')
    auth_b64 = b64encode(auth_bytes).decode('ascii')
    SAP_AUTH_HEADER = f"Basic {auth_b64}"
else:
    SAP_AUTH_HEADER = ""

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Define Models
class WarehouseBin(BaseModel):
    id: Optional[str] = None
    bin_number: str
    location: str
    capacity: int
    current_stock: int = 0
    status: str = "active"
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


# MongoDB Helper Functions
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


# SAP Helper Functions
def map_sap_to_bin(sap_data: Dict[str, Any]) -> Dict[str, Any]:
    """Map SAP OData fields to our Bin model"""
    return {
        "id": sap_data.get("StorageBin", ""),
        "bin_number": sap_data.get("StorageBin", ""),
        "location": f"Warehouse: {sap_data.get('Warehouse', '')}, {sap_data.get('StorageType', '')}",
        "capacity": int(sap_data.get("MaximumStorageCapacity", 0) or 0),
        "current_stock": int(sap_data.get("CurrentStock", 0) or 0),
        "status": "active" if sap_data.get("BlockingIndicator") == "" else "inactive",
        "barcode": sap_data.get("StorageBin", ""),
        "last_updated": datetime.utcnow().isoformat(),
        "created_at": datetime.utcnow().isoformat()
    }


async def call_sap_api(endpoint: str, method: str = "GET", data: Dict = None) -> Any:
    """Generic function to call SAP OData API"""
    url = f"{SAP_API_BASE_URL}{SAP_ODATA_PATH}{endpoint}"
    
    headers = {
        "Authorization": SAP_AUTH_HEADER,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method == "GET":
                response = await client.get(url, headers=headers)
            elif method == "POST":
                response = await client.post(url, headers=headers, json=data)
            elif method == "PATCH":
                response = await client.patch(url, headers=headers, json=data)
            elif method == "DELETE":
                response = await client.delete(url, headers=headers)
            
            logger.info(f"SAP API {method} {url} - Status: {response.status_code}")
            
            if response.status_code >= 400:
                logger.error(f"SAP API Error: {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"SAP API Error: {response.text}"
                )
            
            if method == "DELETE":
                return {"message": "Deleted successfully"}
            
            return response.json()
                
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="SAP API timeout")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"SAP API unavailable: {str(e)}")


# Routes
@api_router.get("/")
async def root():
    return {
        "message": "Warehouse Bin Lookup API - Hybrid Mode",
        "data_source": DATA_SOURCE,
        "info": "Set DATA_SOURCE=sap in .env to use SAP BTP"
    }


@api_router.get("/bins", response_model=List[WarehouseBin])
async def get_bins(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    status: Optional[str] = None
):
    """Get all bins with pagination and filtering"""
    if DATA_SOURCE == 'sap':
        return await get_bins_from_sap(skip, limit, search, status)
    else:
        return await get_bins_from_mongodb(skip, limit, search, status)


async def get_bins_from_mongodb(skip, limit, search, status):
    """Get bins from MongoDB"""
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


async def get_bins_from_sap(skip, limit, search, status):
    """Get bins from SAP"""
    odata_filters = []
    
    if search:
        odata_filters.append(
            f"(substringof('{search}',StorageBin) eq true or "
            f"substringof('{search}',Warehouse) eq true)"
        )
    
    if status == "inactive":
        odata_filters.append("BlockingIndicator ne ''")
    elif status == "active":
        odata_filters.append("BlockingIndicator eq ''")
    
    filter_query = " and ".join(odata_filters) if odata_filters else ""
    endpoint = f"/A_WarehouseStorageBin?$format=json&$top={limit}&$skip={skip}"
    
    if filter_query:
        endpoint += f"&$filter={filter_query}"
    
    result = await call_sap_api(endpoint)
    
    bins = []
    if isinstance(result, dict) and 'd' in result:
        sap_bins = result['d'].get('results', [])
        for sap_bin in sap_bins:
            bins.append(map_sap_to_bin(sap_bin))
    
    return bins


@api_router.get("/bins/count", response_model=BinStats)
async def get_bin_stats():
    """Get warehouse bin statistics"""
    if DATA_SOURCE == 'sap':
        return await get_stats_from_sap()
    else:
        return await get_stats_from_mongodb()


async def get_stats_from_mongodb():
    """Get statistics from MongoDB"""
    total_bins = await db.warehouse_bins.count_documents({})
    active_bins = await db.warehouse_bins.count_documents({"status": "active"})
    inactive_bins = await db.warehouse_bins.count_documents({"status": "inactive"})
    
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


async def get_stats_from_sap():
    """Get statistics from SAP"""
    endpoint = "/A_WarehouseStorageBin?$format=json&$top=1000"
    result = await call_sap_api(endpoint)
    
    bins = []
    if isinstance(result, dict) and 'd' in result:
        bins = result['d'].get('results', [])
    
    total_bins = len(bins)
    active_bins = sum(1 for b in bins if not b.get('BlockingIndicator'))
    inactive_bins = total_bins - active_bins
    
    total_capacity = sum(int(b.get('MaximumStorageCapacity', 0) or 0) for b in bins)
    total_stock = sum(int(b.get('CurrentStock', 0) or 0) for b in bins)
    
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
    if DATA_SOURCE == 'sap':
        endpoint = f"/A_WarehouseStorageBin('{barcode}')?$format=json"
        result = await call_sap_api(endpoint)
        
        if isinstance(result, dict) and 'd' in result:
            return map_sap_to_bin(result['d'])
        
        raise HTTPException(status_code=404, detail="Bin not found with this barcode")
    else:
        bin_doc = await db.warehouse_bins.find_one({"barcode": barcode})
        if not bin_doc:
            raise HTTPException(status_code=404, detail="Bin not found with this barcode")
        return bin_helper(bin_doc)


@api_router.get("/bins/{bin_id}", response_model=WarehouseBin)
async def get_bin(bin_id: str):
    """Get a single bin by ID"""
    if DATA_SOURCE == 'sap':
        endpoint = f"/A_WarehouseStorageBin('{bin_id}')?$format=json"
        result = await call_sap_api(endpoint)
        
        if isinstance(result, dict) and 'd' in result:
            return map_sap_to_bin(result['d'])
        
        raise HTTPException(status_code=404, detail="Bin not found")
    else:
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
    if bin_data.current_stock > bin_data.capacity:
        raise HTTPException(status_code=400, detail="Current stock cannot exceed capacity")
    
    if DATA_SOURCE == 'sap':
        sap_data = {
            "StorageBin": bin_data.bin_number,
            "Warehouse": bin_data.location.split(":")[1].split(",")[0].strip() if ":" in bin_data.location else "WH01",
            "StorageType": "BULK",
            "MaximumStorageCapacity": str(bin_data.capacity),
            "CurrentStock": str(bin_data.current_stock),
            "BlockingIndicator": "" if bin_data.status == "active" else "X"
        }
        
        endpoint = "/A_WarehouseStorageBin?$format=json"
        result = await call_sap_api(endpoint, method="POST", data=sap_data)
        
        if isinstance(result, dict) and 'd' in result:
            return map_sap_to_bin(result['d'])
        
        return WarehouseBin(**bin_data.dict(), id=bin_data.bin_number)
    else:
        # Check if bin_number already exists
        existing = await db.warehouse_bins.find_one({"bin_number": bin_data.bin_number})
        if existing:
            raise HTTPException(status_code=400, detail="Bin number already exists")
        
        bin_dict = bin_data.dict()
        bin_dict["created_at"] = datetime.utcnow()
        bin_dict["last_updated"] = datetime.utcnow()
        
        result = await db.warehouse_bins.insert_one(bin_dict)
        created_bin = await db.warehouse_bins.find_one({"_id": result.inserted_id})
        
        return bin_helper(created_bin)


@api_router.put("/bins/{bin_id}", response_model=WarehouseBin)
async def update_bin(bin_id: str, bin_update: BinUpdate):
    """Update a warehouse bin"""
    current_bin = await get_bin(bin_id)
    
    capacity = bin_update.capacity if bin_update.capacity is not None else current_bin.capacity
    current_stock = bin_update.current_stock if bin_update.current_stock is not None else current_bin.current_stock
    
    if current_stock > capacity:
        raise HTTPException(status_code=400, detail="Current stock cannot exceed capacity")
    
    if DATA_SOURCE == 'sap':
        sap_data = {}
        if bin_update.capacity is not None:
            sap_data["MaximumStorageCapacity"] = str(bin_update.capacity)
        if bin_update.current_stock is not None:
            sap_data["CurrentStock"] = str(bin_update.current_stock)
        if bin_update.status is not None:
            sap_data["BlockingIndicator"] = "" if bin_update.status == "active" else "X"
        
        if sap_data:
            endpoint = f"/A_WarehouseStorageBin('{bin_id}')?$format=json"
            await call_sap_api(endpoint, method="PATCH", data=sap_data)
        
        return await get_bin(bin_id)
    else:
        try:
            bin_doc = await db.warehouse_bins.find_one({"_id": ObjectId(bin_id)})
        except:
            raise HTTPException(status_code=400, detail="Invalid bin ID format")
        
        if not bin_doc:
            raise HTTPException(status_code=404, detail="Bin not found")
        
        update_data = {k: v for k, v in bin_update.dict().items() if v is not None}
        
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
    if DATA_SOURCE == 'sap':
        endpoint = f"/A_WarehouseStorageBin('{bin_id}')?$format=json"
        await call_sap_api(endpoint, method="DELETE")
        return {"message": "Bin deleted successfully"}
    else:
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

@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting Warehouse Bin Lookup API - Hybrid Mode")
    logger.info(f"Data Source: {DATA_SOURCE}")
    if DATA_SOURCE == 'sap':
        logger.info(f"SAP Base URL: {SAP_API_BASE_URL}")
        logger.info(f"SAP OData Path: {SAP_ODATA_PATH}")
    else:
        logger.info(f"Using MongoDB: {mongo_url}")

@app.on_event("shutdown")
async def shutdown_db_client():
    if DATA_SOURCE == 'mock':
        client.close()
