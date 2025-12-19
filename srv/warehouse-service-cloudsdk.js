const cds = require('@sap/cds');
const { executeHttpRequest } = require('@sap-cloud-sdk/http-client');
const { getDestination } = require('@sap-cloud-sdk/connectivity');

// Get destination name from environment variable
const DESTINATION_NAME = process.env.S4_DESTINATION_NAME || 'HMF';
const ODATA_PATH = '/sap/opu/odata/sap/API_WAREHOUSE_STORAGE_BIN';

module.exports = cds.service.impl(async function() {
  const { Bins } = this.entities;

  /**
   * Get destination configuration
   */
  async function getS4Destination() {
    try {
      const destination = await getDestination({ destinationName: DESTINATION_NAME });
      console.log(`Connected to destination: ${DESTINATION_NAME}`);
      return destination;
    } catch (error) {
      console.error(`Failed to get destination ${DESTINATION_NAME}:`, error);
      throw new Error(`Destination ${DESTINATION_NAME} not found or not configured`);
    }
  }

  /**
   * Call S/4HANA OData API via Cloud SDK
   */
  async function callS4API(path, method = 'get', data = null) {
    try {
      const destination = await getS4Destination();
      
      const requestConfig = {
        method: method.toUpperCase(),
        url: `${ODATA_PATH}${path}`,
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        }
      };

      if (data && ['POST', 'PATCH', 'PUT'].includes(method.toUpperCase())) {
        requestConfig.data = data;
      }

      const response = await executeHttpRequest(destination, requestConfig);
      return response.data;
    } catch (error) {
      console.error('S/4HANA API Error:', error);
      throw error;
    }
  }

  /**
   * Map S/4HANA OData response to CAP entity format
   */
  function mapS4ToBin(s4Bin) {
    return {
      ID: s4Bin.StorageBin,
      binNumber: s4Bin.StorageBin,
      location: `${s4Bin.Warehouse || ''} - ${s4Bin.StorageType || ''}`.trim(),
      capacity: parseInt(s4Bin.MaximumStorageCapacity || 0),
      currentStock: parseInt(s4Bin.CurrentStock || 0),
      status: s4Bin.BlockingIndicator ? 'inactive' : 'active',
      barcode: s4Bin.StorageBin || '',
      lastUpdated: new Date().toISOString(),
      createdAt: s4Bin.CreationDate || new Date().toISOString()
    };
  }

  /**
   * Map CAP entity to S/4HANA OData format
   */
  function mapBinToS4(bin) {
    return {
      StorageBin: bin.binNumber,
      Warehouse: bin.location.split('-')[0].trim(),
      StorageType: bin.location.split('-')[1]?.trim() || 'BULK',
      MaximumStorageCapacity: bin.capacity.toString(),
      CurrentStock: bin.currentStock.toString(),
      BlockingIndicator: bin.status === 'active' ? '' : 'X'
    };
  }

  /**
   * READ: Get all bins
   */
  this.on('READ', 'Bins', async (req) => {
    try {
      // Build OData query parameters
      let query = '/A_WarehouseStorageBin?$format=json';
      
      // Add $top and $skip for pagination
      const top = req.query.SELECT?.limit || 100;
      const skip = req.query.SELECT?.from?.ref?.[0]?.where?.$skip || 0;
      query += `&$top=${top}&$skip=${skip}`;

      // Add filters
      const filters = [];
      
      // Search filter
      if (req.query.SELECT?.where) {
        const where = req.query.SELECT.where;
        // Handle search across multiple fields
        if (Array.isArray(where) && where.includes('or')) {
          const searchTerm = where.find(w => w.val)?.val;
          if (searchTerm) {
            filters.push(
              `(substringof('${searchTerm}',StorageBin) eq true or ` +
              `substringof('${searchTerm}',Warehouse) eq true)`
            );
          }
        }
        // Handle status filter
        if (where.status) {
          const status = where.status === 'active' ? '' : 'X';
          filters.push(`BlockingIndicator eq '${status}'`);
        }
      }

      if (filters.length > 0) {
        query += '&$filter=' + filters.join(' and ');
      }

      // Call S/4HANA
      const response = await callS4API(query);
      
      // Map response
      const bins = response.d?.results?.map(mapS4ToBin) || [];
      return bins;
    } catch (error) {
      console.error('Error reading bins from S/4HANA:', error);
      req.error(500, `Failed to read bins: ${error.message}`);
    }
  });

  /**
   * CREATE: Create a new bin
   */
  this.on('CREATE', 'Bins', async (req) => {
    try {
      const { capacity, currentStock } = req.data;
      
      // Validate
      if (currentStock > capacity) {
        return req.error(400, 'Current stock cannot exceed capacity');
      }

      // Map to S/4 format
      const s4Data = mapBinToS4(req.data);
      
      // Call S/4HANA
      const response = await callS4API('/A_WarehouseStorageBin', 'post', s4Data);
      
      // Return mapped response
      return mapS4ToBin(response.d || s4Data);
    } catch (error) {
      console.error('Error creating bin in S/4HANA:', error);
      req.error(500, `Failed to create bin: ${error.message}`);
    }
  });

  /**
   * UPDATE: Update an existing bin
   */
  this.on('UPDATE', 'Bins', async (req) => {
    try {
      const binId = req.data.ID;
      
      // Get current bin first
      const currentResponse = await callS4API(`/A_WarehouseStorageBin('${binId}')?$format=json`);
      const currentBin = mapS4ToBin(currentResponse.d);
      
      // Validate
      const capacity = req.data.capacity !== undefined ? req.data.capacity : currentBin.capacity;
      const currentStock = req.data.currentStock !== undefined ? req.data.currentStock : currentBin.currentStock;
      
      if (currentStock > capacity) {
        return req.error(400, 'Current stock cannot exceed capacity');
      }

      // Merge and map to S/4 format
      const updatedData = { ...currentBin, ...req.data };
      const s4Data = mapBinToS4(updatedData);
      
      // Call S/4HANA
      await callS4API(`/A_WarehouseStorageBin('${binId}')`, 'patch', s4Data);
      
      // Return updated bin
      const updatedResponse = await callS4API(`/A_WarehouseStorageBin('${binId}')?$format=json`);
      return mapS4ToBin(updatedResponse.d);
    } catch (error) {
      console.error('Error updating bin in S/4HANA:', error);
      req.error(500, `Failed to update bin: ${error.message}`);
    }
  });

  /**
   * DELETE: Delete a bin
   */
  this.on('DELETE', 'Bins', async (req) => {
    try {
      const binId = req.data.ID;
      await callS4API(`/A_WarehouseStorageBin('${binId}')`, 'delete');
    } catch (error) {
      console.error('Error deleting bin in S/4HANA:', error);
      req.error(500, `Failed to delete bin: ${error.message}`);
    }
  });

  /**
   * Function: Get bin statistics
   */
  this.on('getBinStatistics', async (req) => {
    try {
      // Get all bins for statistics
      const response = await callS4API('/A_WarehouseStorageBin?$format=json&$top=1000');
      const allBins = response.d?.results?.map(mapS4ToBin) || [];
      
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
    } catch (error) {
      console.error('Error getting statistics from S/4HANA:', error);
      req.error(500, `Failed to get statistics: ${error.message}`);
    }
  });

  // Log startup
  console.log(`Warehouse Service initialized with S/4HANA destination: ${DESTINATION_NAME}`);
});
