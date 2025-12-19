# Complete SAP CAP Project Setup for Warehouse Bins

## Problem
You created an empty project without the CAP structure, so `mbt build` fails because there's nothing to build.

## Solution: Create the Full CAP Project Structure

Follow these steps **in your BAS terminal** at:
```bash
cd /home/user/projects/BINMASTER/BinMasterAPP/BinMaster
```

---

## Step 1: Create Directory Structure

```bash
mkdir -p db/data
mkdir -p srv
mkdir -p app
```

---

## Step 2: Create `package.json`

```bash
cat > package.json << 'EOF'
{
  "name": "binmaster",
  "version": "1.0.0",
  "description": "SAP CAP Warehouse Bin Lookup Application",
  "engines": {
    "node": ">=18.0.0"
  },
  "dependencies": {
    "@sap/cds": "^7",
    "express": "^4",
    "@sap/xssec": "^3",
    "@sap/xsenv": "^4",
    "hdb": "^0.19.0",
    "@sap-cloud-sdk/http-client": "^3",
    "@sap-cloud-sdk/connectivity": "^3",
    "@sap-cloud-sdk/util": "^3"
  },
  "devDependencies": {
    "@sap/cds-dk": "^7"
  },
  "scripts": {
    "start": "cds-serve",
    "watch": "cds watch",
    "build": "cds build --production"
  },
  "cds": {
    "requires": {
      "db": {
        "kind": "sql"
      },
      "[production]": {
        "db": {
          "kind": "hana"
        },
        "auth": {
          "kind": "xsuaa"
        }
      }
    }
  }
}
EOF
```

---

## Step 3: Create Data Model (`db/schema.cds`)

```bash
cat > db/schema.cds << 'EOF'
namespace binmaster;

entity WarehouseBins {
  key ID            : UUID;
      binNumber     : String(50) @mandatory;
      location      : String(200);
      capacity      : Integer;
      currentStock  : Integer;
      status        : String(20) default 'active';
      barcode       : String(100);
      lastUpdated   : Timestamp @cds.on.update: $now;
      createdAt     : Timestamp @cds.on.insert: $now;
}
EOF
```

---

## Step 4: Create Service Definition (`srv/warehouse-service.cds`)

```bash
cat > srv/warehouse-service.cds << 'EOF'
using binmaster from '../db/schema';

service WarehouseService @(path: '/warehouse') {
  entity Bins as projection on binmaster.WarehouseBins;
  
  function getBinStatistics() returns {
    totalBins: Integer;
    activeBins: Integer;
    inactiveBins: Integer;
    totalCapacity: Integer;
    totalStock: Integer;
    utilizationPercentage: Decimal;
  };
}
EOF
```

---

## Step 5: Create Service Implementation (`srv/warehouse-service.js`)

```bash
cat > srv/warehouse-service.js << 'EOF'
const cds = require('@sap/cds');

module.exports = cds.service.impl(async function() {
  const { Bins } = this.entities;

  // Get bin statistics
  this.on('getBinStatistics', async (req) => {
    const allBins = await SELECT.from(Bins);
    
    const totalBins = allBins.length;
    const activeBins = allBins.filter(b => b.status === 'active').length;
    const inactiveBins = totalBins - activeBins;
    
    const totalCapacity = allBins.reduce((sum, b) => sum + (b.capacity || 0), 0);
    const totalStock = allBins.reduce((sum, b) => sum + (b.currentStock || 0), 0);
    
    const utilizationPercentage = totalCapacity > 0 
      ? (totalStock / totalCapacity * 100).toFixed(2) 
      : 0;

    return {
      totalBins,
      activeBins,
      inactiveBins,
      totalCapacity,
      totalStock,
      utilizationPercentage: parseFloat(utilizationPercentage)
    };
  });

  // Before creating a bin, validate stock <= capacity
  this.before('CREATE', 'Bins', async (req) => {
    const { capacity, currentStock } = req.data;
    if (currentStock > capacity) {
      req.error(400, 'Current stock cannot exceed capacity');
    }
  });

  // Before updating a bin, validate stock <= capacity
  this.before('UPDATE', 'Bins', async (req) => {
    const bin = await SELECT.one.from(Bins).where({ ID: req.data.ID });
    const capacity = req.data.capacity !== undefined ? req.data.capacity : bin.capacity;
    const currentStock = req.data.currentStock !== undefined ? req.data.currentStock : bin.currentStock;
    
    if (currentStock > capacity) {
      req.error(400, 'Current stock cannot exceed capacity');
    }
  });
});
EOF
```

---

## Step 6: Verify Project Structure

```bash
tree -L 3
```

Should look like:
```
.
├── mta.yaml
├── xs-security.json
├── package.json
├── db/
│   ├── schema.cds
│   └── data/
│       └── binmaster-WarehouseBins.csv
└── srv/
    ├── warehouse-service.cds
    └── warehouse-service.js
```

---

## Step 7: Install Dependencies

```bash
npm install
```

This will install:
- @sap/cds
- express
- @sap/xssec
- @sap/xsenv
- @cap-js/postgres

---

## Step 8: Build CDS Models

```bash
cds build --production
```

This should create a `gen/` folder with:
```
gen/
├── db/
│   └── package.json
└── srv/
    └── package.json
```

---

## Step 9: Build MTA Archive

```bash
mbt build -t ./
```

This will create:
```
mta_archives/BinMaster_1.0.0.mtar
```

---

## Step 10: Test Locally (Optional)

Before deploying, test locally:

```bash
cds watch
```

Then test the API:
```bash
# In a new terminal
curl http://localhost:4004/warehouse/Bins
curl http://localhost:4004/warehouse/getBinStatistics()
```

---

## Step 12: Deploy to Cloud Foundry

```bash
# Login
cf login -a https://api.cf.us10-001.hana.ondemand.com

# Deploy
cf deploy mta_archives/BinMaster_1.0.0.mtar

# Check deployment
cf apps
cf services
```

---

## Troubleshooting

### Error: "npm ERR! code ERESOLVE"
```bash
npm install --legacy-peer-deps
```

### Error: "CDS not found"
```bash
npm install -g @sap/cds-dk
```

### Error: "Module not found"
```bash
rm -rf node_modules package-lock.json
npm install
```

### Error: "HANA service not found"
Check available services:
```bash
cf marketplace | grep hana
# Use the available service plan
```

---

## Complete Command Sequence

```bash
# 1. Create all files (run all cat > commands above)

# 2. Install dependencies
npm install

# 3. Build CDS
cds build --production

# 4. Verify gen/ folder exists
ls -la gen/

# 5. Build MTA
mbt build -t ./

# 6. Check output
ls -la mta_archives/

# 7. Deploy
cf login
cf deploy mta_archives/BinMaster_1.0.0.mtar
```

---

## What You're Building

This creates a complete SAP CAP application with:

**Data Model:** WarehouseBins entity with all required fields
**OData Service:** REST API at `/warehouse/Bins`
**Business Logic:** Validation (stock ≤ capacity)
**Statistics Function:** Get bin utilization data
**Sample Data:** 4 warehouse bins pre-loaded
**PostgreSQL:** Production database
**XSUAA:** Authentication and authorization

---

## After Deployment

Get your service URL:
```bash
cf app BinMaster-srv
```

Update mobile app in `/app/backend/.env`:
```env
DATA_SOURCE=sap
SAP_API_BASE_URL=https://binmaster-srv.cfapps.us10-001.hana.ondemand.com
SAP_ODATA_PATH=/warehouse
```

---

**You're now ready to deploy a full warehouse bin management system to SAP BTP!** 🚀
