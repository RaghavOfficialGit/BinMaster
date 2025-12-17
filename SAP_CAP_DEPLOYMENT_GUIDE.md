# SAP CAP Deployment Guide for BinMaster

## Quick Fix for Your Current Error

The error occurs because you're running `mbt build` from the wrong directory. Here's how to fix it:

### 1. Navigate to the Correct Directory
```bash
cd /home/user/projects/BINMASTER/BinMasterAPP/BinMaster
```

### 2. Copy the MTA Files
Copy these files from `/app/` to your BAS project:
- `mta.yaml` → `/home/user/projects/BINMASTER/BinMasterAPP/BinMaster/mta.yaml`
- `xs-security.json` → `/home/user/projects/BINMASTER/BinMasterAPP/BinMaster/xs-security.json`

### 3. Run the Build
```bash
mbt build -t ./
```

---

## Complete SAP CAP Project Structure

Your project should look like this:

```
BinMaster/
├── mta.yaml                    # MTA descriptor (created)
├── xs-security.json            # Security configuration (created)
├── package.json                # Root package.json
├── db/                         # Database layer
│   ├── schema.cds             # Data model
│   └── data/                  # Initial data
├── srv/                        # Service layer
│   ├── warehouse-service.cds  # Service definitions
│   └── warehouse-service.js   # Service implementation
└── app/                        # UI layer (optional)
```

---

## Step-by-Step: Create SAP CAP Project from Scratch

If you need to start fresh, here's how:

### 1. Initialize CAP Project in BAS
```bash
cd /home/user/projects/BINMASTER/BinMasterAPP/
cds init BinMaster --add postgres
cd BinMaster
```

### 2. Create Data Model (`db/schema.cds`)
```cds
namespace binmaster;

entity WarehouseBins {
  key ID            : UUID;
  binNumber         : String(50) @mandatory;
  location          : String(200);
  capacity          : Integer;
  currentStock      : Integer;
  status            : String(20) default 'active';
  barcode           : String(100);
  lastUpdated       : Timestamp;
  createdAt         : Timestamp;
}
```

### 3. Create Service (`srv/warehouse-service.cds`)
```cds
using binmaster from '../db/schema';

service WarehouseService {
  entity Bins as projection on binmaster.WarehouseBins;
  
  action getByBarcode(barcode: String) returns Bins;
  function getBinStatistics() returns {
    totalBins: Integer;
    activeBins: Integer;
    inactiveBins: Integer;
    totalCapacity: Integer;
    totalStock: Integer;
    utilizationPercentage: Decimal;
  };
}
```

### 4. Add Sample Data (`db/data/binmaster-WarehouseBins.csv`)
```csv
ID;binNumber;location;capacity;currentStock;status;barcode
1;BIN-A001;Aisle A Row 1;1000;750;active;1234567890
2;BIN-A002;Aisle A Row 2;800;300;active;1234567891
3;BIN-B001;Aisle B Row 1;1200;1100;active;1234567892
4;BIN-C001;Aisle C Row 1;500;0;inactive;1234567893
```

### 5. Update `package.json`
```json
{
  "name": "binmaster",
  "version": "1.0.0",
  "description": "Warehouse Bin Lookup Application",
  "engines": {
    "node": ">=18.0.0"
  },
  "dependencies": {
    "@sap/cds": "^7",
    "express": "^4",
    "@sap/xssec": "^3",
    "@sap/xsenv": "^4"
  },
  "devDependencies": {
    "@cap-js/postgres": "^1"
  },
  "scripts": {
    "start": "cds-serve",
    "watch": "cds watch",
    "build": "cds build --production"
  },
  "cds": {
    "requires": {
      "db": {
        "kind": "postgres"
      },
      "auth": {
        "kind": "xsuaa"
      }
    }
  }
}
```

### 6. Install Dependencies
```bash
npm install
```

### 7. Build for Production
```bash
cds build --production
```

### 8. Build MTA Archive
```bash
mbt build -t ./
```

---

## Deployment to SAP BTP Cloud Foundry

### 1. Login to Cloud Foundry
```bash
cf login -a https://api.cf.us10-001.hana.ondemand.com
```

### 2. Deploy the MTA
```bash
cf deploy mta_archives/BinMaster_1.0.0.mtar
```

### 3. Check Services
```bash
cf services
cf apps
```

---

## MTA Configuration Explained

### `mta.yaml` Structure:

**Modules:**
1. **BinMaster-srv**: Node.js service module
   - Runs your CAP service
   - Exposes REST APIs
   - Connects to PostgreSQL

2. **BinMaster-db-deployer**: Database deployer
   - Deploys schema to PostgreSQL
   - Runs data initialization

**Resources:**
1. **BinMaster-db**: PostgreSQL service instance
2. **BinMaster-auth**: XSUAA authentication service

---

## Troubleshooting Common Errors

### Error: "No such file or directory"
**Solution:** You're in the wrong directory
```bash
cd /home/user/projects/BINMASTER/BinMasterAPP/BinMaster
ls -la  # Should see mta.yaml
```

### Error: "Module BinMaster-srv could not be built"
**Solution:** Run CDS build first
```bash
cds build --production
ls gen/  # Should see srv/ and db/
```

### Error: "Could not find package.json"
**Solution:** Initialize project properly
```bash
npm init -y
npm install @sap/cds --save
```

### Error: "HANA service not found"
**Solution:** Check service marketplace
```bash
cf marketplace | grep hana
# Verify you have access to HANA Cloud
```

---

## Database Configuration

The project is configured to use **SAP HANA Cloud** for production deployment.

Current `mta.yaml` configuration:

```yaml
resources:
  - name: BinMaster-db
    type: com.sap.xs.hdi-container
    parameters:
      service: hana
      service-plan: hdi-shared
```

The `package.json` is configured with:
```json
"cds": {
  "requires": {
    "[production]": {
      "db": {
        "kind": "hana"
      }
    }
  }
}
```

---

## Testing Locally Before Deployment

### 1. Use SQLite for Local Testing
```bash
cds watch
```

### 2. Test APIs
```bash
# List bins
curl http://localhost:4004/warehouse/Bins

# Get statistics
curl http://localhost:4004/warehouse/getBinStatistics()

# Search by barcode
curl http://localhost:4004/warehouse/Bins?$filter=barcode eq '1234567890'
```

---

## Integration with Mobile App

Once deployed, update your mobile app's backend URL:

**In `/app/backend/.env`:**
```env
# Change to SAP mode
DATA_SOURCE=sap

# Update with your deployed CAP service URL
SAP_API_BASE_URL=https://binmaster-srv.cfapps.us10-001.hana.ondemand.com
SAP_ODATA_PATH=/warehouse
```

---

## Next Steps After Deployment

1. **Get Service URL:**
   ```bash
   cf app BinMaster-srv
   ```

2. **Test Deployed API:**
   ```bash
   curl https://binmaster-srv.cfapps.us10-001.hana.ondemand.com/warehouse/Bins
   ```

3. **Configure Mobile App:**
   - Update DATA_SOURCE to "sap"
   - Set SAP_API_BASE_URL to your deployed URL
   - Restart mobile app backend

4. **Assign Roles:**
   - Go to BTP Cockpit
   - Navigate to Role Collections
   - Assign WarehouseWorker or WarehouseManager roles to users

---

## Resources

- [SAP CAP Documentation](https://cap.cloud.sap/docs/)
- [MTA Documentation](https://www.sap.com/documents/2016/06/e2f618e4-757c-0010-82c7-eda71af511fa.html)
- [Cloud Foundry CLI](https://docs.cloudfoundry.org/cf-cli/)
- [SAP BTP PostgreSQL](https://help.sap.com/docs/postgresql-hyperscaler-option)

---

**Need Help?** 
Check logs: `cf logs BinMaster-srv --recent`
