# Quick Fix: MTA Build Error

## The Problem
```
ERROR: could not read the "mta.yaml" file: no such file or directory
```

## The Solution (3 Steps)

### Step 1: Go to the Right Directory
```bash
cd /home/user/projects/BINMASTER/BinMasterAPP/BinMaster
```

### Step 2: Copy These Files to Your BAS Project

**From this environment to your BAS project:**

**File 1: `mta.yaml`**
Location: Copy the content from `/app/mta.yaml` to your BAS project

**File 2: `xs-security.json`**
Location: Copy the content from `/app/xs-security.json` to your BAS project

### Step 3: Build
```bash
# Install dependencies first
npm install

# Build CDS
cds build --production

# Build MTA
mbt build -t ./
```

---

## How to Copy Files to BAS

### Option A: Manual Copy (Recommended)
1. In BAS, create new file: `mta.yaml`
2. Copy content from the mta.yaml I created
3. Paste into your BAS file
4. Repeat for `xs-security.json`

### Option B: Create via Terminal in BAS
```bash
# In your BAS terminal at /home/user/projects/BINMASTER/BinMasterAPP/BinMaster/

cat > mta.yaml << 'EOF'
_schema-version: '3.1'
ID: BinMaster
version: 1.0.0
description: "SAP CAP Warehouse Bin Lookup Application"
parameters:
  enable-parallel-deployments: true
  
build-parameters:
  before-all:
    - builder: custom
      commands:
        - npm ci
        - npx cds build --production

modules:
  - name: BinMaster-srv
    type: nodejs
    path: gen/srv
    parameters:
      buildpack: nodejs_buildpack
      readiness-health-check-type: http
      readiness-health-check-http-endpoint: /health
    build-parameters:
      builder: npm
    provides:
      - name: srv-api
        properties:
          srv-url: ${default-url}
    requires:
      - name: BinMaster-db
      - name: BinMaster-auth

  - name: BinMaster-db-deployer
    type: hdb
    path: gen/db
    parameters:
      buildpack: nodejs_buildpack
    requires:
      - name: BinMaster-db

resources:
  - name: BinMaster-db
    type: org.cloudfoundry.managed-service
    parameters:
      service: postgresql
      service-plan: standard
      
  - name: BinMaster-auth
    type: org.cloudfoundry.managed-service
    parameters:
      service: xsuaa
      service-plan: application
      path: ./xs-security.json
      config:
        xsappname: BinMaster-${org}-${space}
        tenant-mode: dedicated
EOF

cat > xs-security.json << 'EOF'
{
  "xsappname": "BinMaster",
  "tenant-mode": "dedicated",
  "description": "Security profile for Warehouse Bin Lookup Application",
  "scopes": [
    {
      "name": "$XSAPPNAME.BinRead",
      "description": "Read warehouse bins"
    },
    {
      "name": "$XSAPPNAME.BinWrite",
      "description": "Create and update warehouse bins"
    },
    {
      "name": "$XSAPPNAME.BinDelete",
      "description": "Delete warehouse bins"
    }
  ],
  "role-templates": [
    {
      "name": "WarehouseWorker",
      "description": "Warehouse worker with read and write access",
      "scope-references": [
        "$XSAPPNAME.BinRead",
        "$XSAPPNAME.BinWrite"
      ]
    },
    {
      "name": "WarehouseManager",
      "description": "Warehouse manager with full access",
      "scope-references": [
        "$XSAPPNAME.BinRead",
        "$XSAPPNAME.BinWrite",
        "$XSAPPNAME.BinDelete"
      ]
    }
  ]
}
EOF
```

---

## Verify Files Exist

```bash
# Check if files are in the right place
ls -la | grep -E "mta.yaml|xs-security.json"

# Should see:
# -rw-r--r-- 1 user group  xxx Nov 14 06:xx mta.yaml
# -rw-r--r-- 1 user group  xxx Nov 14 06:xx xs-security.json
```

---

## Full Build Command Sequence

```bash
# 1. Navigate to project
cd /home/user/projects/BINMASTER/BinMasterAPP/BinMaster

# 2. Clean previous build (optional)
rm -rf gen/ mta_archives/

# 3. Install dependencies
npm install

# 4. Build CDS models
cds build --production

# 5. Build MTA archive
mbt build -t ./

# 6. Check output
ls -la mta_archives/
# Should see: BinMaster_1.0.0.mtar
```

---

## Deploy to Cloud Foundry

```bash
# Login
cf login -a https://api.cf.us10-001.hana.ondemand.com

# Deploy
cf deploy mta_archives/BinMaster_1.0.0.mtar

# Check status
cf apps
cf services
```

---

## Common Errors & Fixes

### Error: "gen/srv not found"
```bash
cds build --production
```

### Error: "npm not found"
```bash
npm install
```

### Error: "Module could not be built"
```bash
# Check package.json exists
cat package.json

# If missing, create basic one
npm init -y
npm install @sap/cds express
```

### Error: "PostgreSQL service not available"
Change in mta.yaml:
```yaml
service: hana  # instead of postgresql
service-plan: hdi-shared
```

---

**That's it!** Your MTA build should now work. 🚀
