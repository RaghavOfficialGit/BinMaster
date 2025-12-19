#!/bin/bash
# Script to set up SAP CAP Warehouse Bin Project

echo "Setting up SAP CAP Warehouse Bin Lookup Project..."

# Create directory structure
mkdir -p db
mkdir -p srv
mkdir -p app

# Create package.json
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
        "kind": "sql"
      },
      "[production]": {
        "db": {
          "kind": "postgres"
        },
        "auth": {
          "kind": "xsuaa"
        }
      }
    }
  }
}
EOF

# Create data model
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

# Create service definition
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

# Create service implementation
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

echo "✅ Project structure created!"
echo ""
echo "Next steps:"
echo "1. Run: npm install"
echo "2. Run: cds build --production"
echo "3. Run: mbt build -t ./"
