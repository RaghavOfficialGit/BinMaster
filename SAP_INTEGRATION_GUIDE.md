# SAP BTP Integration Guide

## Overview
Your warehouse bin lookup app supports **Hybrid Mode** - it can work with either:
- **Mock Data** (MongoDB) - Default mode for development and testing
- **SAP BTP API** - Production mode connecting to real SAP systems

## Current Configuration

### Backend: `/app/backend/.env`
```env
# Data Source: "mock" or "sap"
DATA_SOURCE=mock

# SAP BTP Configuration
SAP_API_BASE_URL=https://api.cf.us10-001.hana.ondemand.com
SAP_API_USERNAME=raghav.nookala@mygoconsulting.com
SAP_API_PASSWORD=Raghav@123
SAP_ODATA_PATH=/sap/opu/odata/sap/API_WAREHOUSE_STORAGE_BIN
```

## How to Switch Modes

### Use Mock Data (Current Mode)
```bash
# In /app/backend/.env
DATA_SOURCE=mock
```
- Uses MongoDB for data storage
- Perfect for development and testing
- Works offline
- No SAP credentials needed

### Use SAP BTP API
```bash
# In /app/backend/.env
DATA_SOURCE=sap
```
- Connects to real SAP system
- All CRUD operations go to SAP
- Requires correct SAP endpoint configuration

## SAP Connection Troubleshooting

### Current Issue
The SAP endpoint returns: `"Unknown request"` (404)

### Possible Solutions

#### 1. Verify SAP Application Route
Your SAP BTP apps typically have URLs like:
```
https://[app-name].cfapps.[region].hana.ondemand.com
```

**Check:**
- Is there a specific app name/subdomain?
- Does the OData service need a different base URL?

#### 2. Test SAP Connection Manually
```bash
curl -u "raghav.nookala@mygoconsulting.com:Raghav@123" \
  "https://api.cf.us10-001.hana.ondemand.com/sap/opu/odata/sap/API_WAREHOUSE_STORAGE_BIN/A_WarehouseStorageBin?\$format=json"
```

#### 3. Common SAP Endpoint Formats

**Option A: Direct Service URL**
```
https://myXXXXXX-api.s4hana.cloud.sap/sap/opu/odata/sap/API_WAREHOUSE_STORAGE_BIN
```

**Option B: Cloud Foundry Route**
```
https://[app-name].cfapps.us10-001.hana.ondemand.com/sap/opu/odata/sap/API_WAREHOUSE_STORAGE_BIN
```

**Option C: API Management**
```
https://[api-gateway].us10.apimanagement.hana.ondemand.com/warehouse-api
```

#### 4. Update Configuration
Once you have the correct URL, update `.env`:
```env
SAP_API_BASE_URL=https://[your-correct-sap-url]
SAP_ODATA_PATH=/sap/opu/odata/sap/API_WAREHOUSE_STORAGE_BIN
DATA_SOURCE=sap
```

Then restart backend:
```bash
sudo supervisorctl restart backend
```

## SAP OData Field Mapping

The app maps SAP fields to our bin model:

| App Field       | SAP OData Field           |
|----------------|---------------------------|
| bin_number     | StorageBin                |
| location       | Warehouse + StorageType   |
| capacity       | MaximumStorageCapacity    |
| current_stock  | CurrentStock              |
| status         | BlockingIndicator         |
| barcode        | StorageBin                |

## API Endpoints

All endpoints work in both modes:

```
GET    /api/bins              # List bins with filtering
GET    /api/bins/count        # Statistics
GET    /api/bins/{id}         # Get single bin
GET    /api/bins/barcode/{bc} # Lookup by barcode
POST   /api/bins              # Create bin
PUT    /api/bins/{id}         # Update bin
DELETE /api/bins/{id}         # Delete bin
```

## Testing the Integration

### Check Current Mode
```bash
curl http://localhost:8001/api/
```

Response shows current data source:
```json
{
  "message": "Warehouse Bin Lookup API - Hybrid Mode",
  "data_source": "mock",
  "info": "Set DATA_SOURCE=sap in .env to use SAP BTP"
}
```

### Test Mock Mode
```bash
curl http://localhost:8001/api/bins
```

### Test SAP Mode
1. Update DATA_SOURCE=sap in .env
2. Restart backend
3. Test connection:
```bash
curl http://localhost:8001/api/bins
```

## File Structure

```
/app/backend/
├── server.py                    # Active hybrid mode server
├── server_mongodb_backup.py     # Original MongoDB-only version
├── server_sap_only.py          # Pure SAP integration version
└── .env                        # Configuration
```

## Next Steps

1. **Get Correct SAP URL**: Contact your SAP admin or check SAP BTP cockpit
2. **Test Connection**: Use curl or Postman to verify endpoint
3. **Update Configuration**: Modify .env with correct URL
4. **Switch Mode**: Change DATA_SOURCE to "sap"
5. **Test**: Verify all CRUD operations work

## Support

If you need help:
1. Check SAP BTP Cockpit for correct URLs
2. Verify API credentials in SAP
3. Check SAP API Business Hub for documentation
4. Test with Postman first before updating the app

## Mobile App
The frontend automatically works with both modes - no changes needed!
It simply calls the backend API which handles the data source routing.
