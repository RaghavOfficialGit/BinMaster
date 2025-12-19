# SAP Cloud SDK + Destination Service Setup Guide

## Overview
This guide shows you how to connect your CAP application to S/4HANA using:
- **SAP Cloud SDK** - For HTTP communication
- **SAP BTP Destination Service** - For secure connection management
- **Environment Variables** - For flexible destination configuration

---

## Architecture

```
Mobile App → CAP Service → Cloud SDK → Destination Service → S/4HANA (HMF)
                                                               ↓
                                                    API_WAREHOUSE_STORAGE_BIN
```

---

## Step 1: Configure Destination in SAP BTP Cockpit

### 1.1 Create Destination "HMF"

In SAP BTP Cockpit:
1. Navigate to **Connectivity** → **Destinations**
2. Click **New Destination**
3. Configure:

```
Name: HMF
Type: HTTP
URL: https://your-s4hana-system.com
Proxy Type: Internet
Authentication: BasicAuthentication
User: <your-s4-username>
Password: <your-s4-password>

Additional Properties:
  sap-client: 100
  WebIDEEnabled: true
  WebIDEUsage: odata_gen
```

### 1.2 Test Destination
```bash
# In BTP Cockpit, click "Check Connection"
# Should return: 200 OK - Connection successful
```

---

## Step 2: Update Project Files

### 2.1 Update `package.json`

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

### 2.2 Replace Service Implementation

Replace `srv/warehouse-service.js` with the Cloud SDK version:

```bash
# Copy the content from /app/srv/warehouse-service-cloudsdk.js
cp /app/srv/warehouse-service-cloudsdk.js srv/warehouse-service.js
```

Or copy manually from the file I created: `/app/srv/warehouse-service-cloudsdk.js`

---

## Step 3: Set Environment Variable

### 3.1 For Local Testing

Create `.env` file:
```bash
cat > .env << 'EOF'
S4_DESTINATION_NAME=HMF
EOF
```

### 3.2 For Cloud Foundry Deployment

The `mta.yaml` already includes the environment variable:

```yaml
modules:
  - name: BinMaster-srv
    properties:
      S4_DESTINATION_NAME: HMF
    requires:
      - name: BinMaster-destination
```

**To change destination name:**
1. Update the property in `mta.yaml`:
   ```yaml
   properties:
     S4_DESTINATION_NAME: YOUR_DESTINATION_NAME
   ```

2. Or set via CF environment variable:
   ```bash
   cf set-env BinMaster-srv S4_DESTINATION_NAME YOUR_DESTINATION_NAME
   cf restage BinMaster-srv
   ```

---

## Step 4: Install Dependencies

```bash
npm install
```

This installs:
- `@sap-cloud-sdk/http-client` - HTTP requests to destinations
- `@sap-cloud-sdk/connectivity` - Destination service integration
- `@sap-cloud-sdk/util` - Utility functions

---

## Step 5: Local Testing with Destination

### 5.1 Set Up Local Destination Mock

For local testing without BTP, create `default-env.json`:

```bash
cat > default-env.json << 'EOF'
{
  "destinations": [
    {
      "name": "HMF",
      "url": "https://your-s4hana-system.com",
      "username": "your-username",
      "password": "your-password"
    }
  ]
}
EOF
```

**⚠️ Important:** Add to `.gitignore`:
```bash
echo "default-env.json" >> .gitignore
```

### 5.2 Run Locally

```bash
cds watch
```

Test the API:
```bash
# Get bins
curl http://localhost:4004/warehouse/Bins

# Get statistics  
curl http://localhost:4004/warehouse/getBinStatistics()
```

---

## Step 6: Deploy to Cloud Foundry

### 6.1 Build

```bash
# Install dependencies
npm install

# Build CDS
cds build --production

# Build MTA
mbt build -t ./
```

### 6.2 Deploy

```bash
cf login -a https://api.cf.us10-001.hana.ondemand.com

cf deploy mta_archives/BinMaster_1.0.0.mtar
```

### 6.3 Verify Deployment

```bash
# Check app status
cf app BinMaster-srv

# Check bound services
cf services

# Should see:
# - BinMaster-db (hana)
# - BinMaster-auth (xsuaa)
# - BinMaster-destination (destination)

# Check environment variables
cf env BinMaster-srv | grep S4_DESTINATION_NAME
```

---

## Step 7: Test Deployed Application

### 7.1 Get Application URL

```bash
cf app BinMaster-srv
# Look for "routes:" - e.g., binmaster-srv.cfapps.us10-001.hana.ondemand.com
```

### 7.2 Test Endpoints

```bash
# Replace with your actual URL
APP_URL="https://binmaster-srv.cfapps.us10-001.hana.ondemand.com"

# Get bins
curl "$APP_URL/warehouse/Bins"

# Get single bin
curl "$APP_URL/warehouse/Bins('BIN-A001')"

# Get statistics
curl "$APP_URL/warehouse/getBinStatistics()"
```

---

## How It Works

### Cloud SDK Flow:

1. **CAP Service receives request** → `srv/warehouse-service.js`
2. **Get Destination** → `getDestination({ destinationName: 'HMF' })`
   - Reads from Destination Service
   - Retrieves URL, auth credentials
3. **Execute HTTP Request** → `executeHttpRequest(destination, config)`
   - Calls S/4HANA OData API
   - Handles authentication automatically
4. **Map Response** → Convert S/4 format to CAP entity
5. **Return to Mobile App**

### Environment Variable Usage:

```javascript
// In warehouse-service.js
const DESTINATION_NAME = process.env.S4_DESTINATION_NAME || 'HMF';
```

**Benefits:**
- ✅ Easy to change destination without code changes
- ✅ Different destinations for dev/test/prod
- ✅ Can override per environment

---

## Changing Destination Name

### Option 1: Update mta.yaml (Recommended)

```yaml
modules:
  - name: BinMaster-srv
    properties:
      S4_DESTINATION_NAME: NEW_DESTINATION_NAME
```

Rebuild and redeploy:
```bash
mbt build -t ./
cf deploy mta_archives/BinMaster_1.0.0.mtar
```

### Option 2: Set CF Environment Variable

```bash
cf set-env BinMaster-srv S4_DESTINATION_NAME NEW_DESTINATION_NAME
cf restage BinMaster-srv
```

### Option 3: Local Testing

```bash
# In .env file
S4_DESTINATION_NAME=MY_TEST_DESTINATION
```

---

## Troubleshooting

### Error: "Destination HMF not found"

**Solution 1:** Check destination exists
```bash
# In BTP Cockpit → Destinations
# Verify "HMF" destination is created
```

**Solution 2:** Check service binding
```bash
cf services
# Verify BinMaster-destination is bound to BinMaster-srv
```

**Solution 3:** Check environment variable
```bash
cf env BinMaster-srv
# Look for S4_DESTINATION_NAME
```

### Error: "401 Unauthorized"

**Solution:** Check destination credentials
```bash
# In BTP Cockpit → Destinations → HMF
# Verify username and password are correct
# Test connection
```

### Error: "Cannot find module @sap-cloud-sdk"

**Solution:** Install dependencies
```bash
npm install @sap-cloud-sdk/http-client @sap-cloud-sdk/connectivity
```

### Error: "Destination service not bound"

**Solution:** Check mta.yaml
```yaml
requires:
  - name: BinMaster-destination  # Must be present
```

Redeploy if missing.

---

## Connect Mobile App

After deployment, update your mobile app's backend:

In `/app/backend/.env`:
```env
DATA_SOURCE=sap
SAP_API_BASE_URL=https://binmaster-srv.cfapps.us10-001.hana.ondemand.com
SAP_ODATA_PATH=/warehouse
```

Restart backend:
```bash
sudo supervisorctl restart backend
```

---

## Advanced: Multiple Destinations

To support multiple S/4HANA systems:

### 1. Create Multiple Destinations
- `HMF_DEV` - Development system
- `HMF_TEST` - Test system  
- `HMF_PROD` - Production system

### 2. Use Environment Variables Per Space

```bash
# Dev space
cf set-env BinMaster-srv S4_DESTINATION_NAME HMF_DEV

# Test space
cf set-env BinMaster-srv S4_DESTINATION_NAME HMF_TEST

# Prod space
cf set-env BinMaster-srv S4_DESTINATION_NAME HMF_PROD
```

---

## Security Best Practices

✅ **DO:**
- Store credentials in BTP Destination Service (not in code)
- Use environment variables for destination names
- Use XSUAA for authentication
- Enable audit logging

❌ **DON'T:**
- Hardcode URLs or credentials in code
- Commit `default-env.json` to git
- Share destination credentials
- Disable SSL/TLS verification

---

## Summary

You now have:
- ✅ Cloud SDK integration with S/4HANA
- ✅ Destination Service configuration  
- ✅ Environment variable for flexible destination
- ✅ Secure credential management
- ✅ Production-ready architecture

**Next:** Deploy to BTP and test with your mobile app! 🚀
