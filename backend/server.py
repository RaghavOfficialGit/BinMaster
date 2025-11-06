from fastapi import FastAPI, APIRouter, HTTPException, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import httpx
from base64 import b64encode
import xml.etree.ElementTree as ET


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# SAP Configuration
SAP_API_BASE_URL = os.environ['SAP_API_BASE_URL']
SAP_API_USERNAME = os.environ['SAP_API_USERNAME']
SAP_API_PASSWORD = os.environ['SAP_API_PASSWORD']
SAP_ODATA_PATH = os.environ['SAP_ODATA_PATH']

# Create Basic Auth header
auth_string = f"{SAP_API_USERNAME}:{SAP_API_PASSWORD}"
auth_bytes = auth_string.encode('ascii')
auth_b64 = b64encode(auth_bytes).decode('ascii')
SAP_AUTH_HEADER = f"Basic {auth_b64}"

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
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


# SAP OData Helper Functions
def parse_sap_odata_xml(xml_content: str) -> List[Dict[str, Any]]:
    """Parse SAP OData XML response and extract bin data"""
    try:
        root = ET.fromstring(xml_content)
        
        # Define namespaces
        namespaces = {
            'atom': 'http://www.w3.org/2005/Atom',
            'd': 'http://schemas.microsoft.com/ado/2007/08/dataservices',
            'm': 'http://schemas.microsoft.com/ado/2007/08/dataservices/metadata'
        }
        
        bins = []
        entries = root.findall('.//atom:entry', namespaces)
        
        for entry in entries:
            content = entry.find('.//m:properties', namespaces)
            if content is not None:
                bin_data = {}
                for child in content:
                    tag = child.tag.split('}')[-1]
                    bin_data[tag] = child.text or ""
                bins.append(bin_data)
        
        return bins
    except Exception as e:
        logger.error(f"Error parsing SAP XML: {e}")
        return []


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
            
            # Handle different response types
            if method == "DELETE":
                return {"message": "Deleted successfully"}
            
            try:
                return response.json()
            except:
                # If not JSON, try XML
                return parse_sap_odata_xml(response.text)
                
    except httpx.TimeoutException:
        logger.error(f"SAP API timeout for {url}")
        raise HTTPException(status_code=504, detail="SAP API timeout")
    except httpx.RequestError as e:
        logger.error(f"SAP API request error: {e}")
        raise HTTPException(status_code=503, detail=f"SAP API unavailable: {str(e)}")


# Routes
@api_router.get("/")
async def root():
    return {"message": "Warehouse Bin Lookup API - SAP Integration"}


@api_router.get("/bins", response_model=List[WarehouseBin])
async def get_bins(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    status: Optional[str] = None
):
    """Get all bins from SAP with optional filtering"""
    try:
        # Build OData query
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
        
        # Parse SAP response
        bins = []
        if isinstance(result, dict) and 'd' in result:
            sap_bins = result['d'].get('results', [])
            for sap_bin in sap_bins:
                mapped_bin = map_sap_to_bin(sap_bin)
                bins.append(mapped_bin)
        
        return bins
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching bins from SAP: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching bins: {str(e)}")


@api_router.get("/bins/count", response_model=BinStats)
async def get_bin_stats():
    """Get warehouse bin statistics from SAP"""
    try:
        # Get all bins for statistics (SAP OData $count might not be available)
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
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching stats from SAP: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching statistics: {str(e)}")


@api_router.get("/bins/barcode/{barcode}", response_model=WarehouseBin)
async def get_bin_by_barcode(barcode: str):
    """Lookup bin by barcode in SAP"""
    try:
        endpoint = f"/A_WarehouseStorageBin('{barcode}')?$format=json"
        result = await call_sap_api(endpoint)
        
        if isinstance(result, dict) and 'd' in result:
            sap_bin = result['d']
            return map_sap_to_bin(sap_bin)
        
        raise HTTPException(status_code=404, detail="Bin not found with this barcode")
        
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail="Bin not found with this barcode")
        raise
    except Exception as e:
        logger.error(f"Error fetching bin by barcode from SAP: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching bin: {str(e)}")


@api_router.get("/bins/{bin_id}", response_model=WarehouseBin)
async def get_bin(bin_id: str):
    """Get a single bin by ID from SAP"""
    try:
        endpoint = f"/A_WarehouseStorageBin('{bin_id}')?$format=json"
        result = await call_sap_api(endpoint)
        
        if isinstance(result, dict) and 'd' in result:
            sap_bin = result['d']
            return map_sap_to_bin(sap_bin)
        
        raise HTTPException(status_code=404, detail="Bin not found")
        
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail="Bin not found")
        raise
    except Exception as e:
        logger.error(f"Error fetching bin from SAP: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching bin: {str(e)}")


@api_router.post("/bins", response_model=WarehouseBin)
async def create_bin(bin_data: BinCreate):
    """Create a new warehouse bin in SAP"""
    try:
        # Validate stock doesn't exceed capacity
        if bin_data.current_stock > bin_data.capacity:
            raise HTTPException(status_code=400, detail="Current stock cannot exceed capacity")
        
        # Map to SAP format
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
            sap_bin = result['d']
            return map_sap_to_bin(sap_bin)
        
        # Return created data if SAP doesn't return the object
        return WarehouseBin(**bin_data.dict(), id=bin_data.bin_number)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating bin in SAP: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating bin: {str(e)}")


@api_router.put("/bins/{bin_id}", response_model=WarehouseBin)
async def update_bin(bin_id: str, bin_update: BinUpdate):
    """Update a warehouse bin in SAP"""
    try:
        # Get current bin first
        current_bin = await get_bin(bin_id)
        
        # Validate stock doesn't exceed capacity
        capacity = bin_update.capacity if bin_update.capacity is not None else current_bin.capacity
        current_stock = bin_update.current_stock if bin_update.current_stock is not None else current_bin.current_stock
        
        if current_stock > capacity:
            raise HTTPException(status_code=400, detail="Current stock cannot exceed capacity")
        
        # Build SAP update data
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
        
        # Return updated bin
        return await get_bin(bin_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating bin in SAP: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating bin: {str(e)}")


@api_router.delete("/bins/{bin_id}")
async def delete_bin(bin_id: str):
    """Delete a warehouse bin in SAP"""
    try:
        endpoint = f"/A_WarehouseStorageBin('{bin_id}')?$format=json"
        result = await call_sap_api(endpoint, method="DELETE")
        return {"message": "Bin deleted successfully"}
        
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail="Bin not found")
        raise
    except Exception as e:
        logger.error(f"Error deleting bin in SAP: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting bin: {str(e)}")


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
    logger.info("Starting Warehouse Bin Lookup API with SAP Integration")
    logger.info(f"SAP Base URL: {SAP_API_BASE_URL}")
    logger.info(f"SAP OData Path: {SAP_ODATA_PATH}")
