#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for Warehouse Bin Lookup System
Tests all CRUD operations, validation, pagination, filtering, and statistics
"""

import requests
import json
import sys
from datetime import datetime
from typing import Dict, List, Any

# Backend URL from frontend environment
BACKEND_URL = "https://capm-storage-bin.preview.emergentagent.com/api"

class BinAPITester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.test_results = []
        self.created_bin_ids = []  # Track created bins for cleanup
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results.append({
            "test": test_name,
            "status": status,
            "success": success,
            "details": details
        })
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
    
    def test_api_health(self):
        """Test if API is accessible"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=10)
            if response.status_code == 200:
                self.log_test("API Health Check", True, f"API responding: {response.json()}")
                return True
            else:
                self.log_test("API Health Check", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("API Health Check", False, f"Connection error: {str(e)}")
            return False
    
    def test_get_bins_basic(self):
        """Test GET /api/bins - basic functionality"""
        try:
            response = requests.get(f"{self.base_url}/bins", timeout=10)
            if response.status_code == 200:
                bins = response.json()
                self.log_test("GET /api/bins - Basic", True, f"Retrieved {len(bins)} bins")
                return bins
            else:
                self.log_test("GET /api/bins - Basic", False, f"Status: {response.status_code}, Response: {response.text}")
                return []
        except Exception as e:
            self.log_test("GET /api/bins - Basic", False, f"Error: {str(e)}")
            return []
    
    def test_get_bins_pagination(self):
        """Test GET /api/bins with pagination parameters"""
        try:
            # Test with skip and limit
            response = requests.get(f"{self.base_url}/bins?skip=0&limit=2", timeout=10)
            if response.status_code == 200:
                bins = response.json()
                self.log_test("GET /api/bins - Pagination", True, f"Limited to 2 bins, got {len(bins)}")
            else:
                self.log_test("GET /api/bins - Pagination", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("GET /api/bins - Pagination", False, f"Error: {str(e)}")
    
    def test_get_bins_search(self):
        """Test GET /api/bins with search functionality"""
        try:
            # Test search by bin number pattern
            response = requests.get(f"{self.base_url}/bins?search=A", timeout=10)
            if response.status_code == 200:
                bins = response.json()
                self.log_test("GET /api/bins - Search", True, f"Search for 'A' returned {len(bins)} bins")
            else:
                self.log_test("GET /api/bins - Search", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("GET /api/bins - Search", False, f"Error: {str(e)}")
    
    def test_get_bins_status_filter(self):
        """Test GET /api/bins with status filtering"""
        try:
            # Test active filter
            response = requests.get(f"{self.base_url}/bins?status=active", timeout=10)
            if response.status_code == 200:
                active_bins = response.json()
                
                # Test inactive filter
                response2 = requests.get(f"{self.base_url}/bins?status=inactive", timeout=10)
                if response2.status_code == 200:
                    inactive_bins = response2.json()
                    self.log_test("GET /api/bins - Status Filter", True, 
                                f"Active: {len(active_bins)}, Inactive: {len(inactive_bins)}")
                else:
                    self.log_test("GET /api/bins - Status Filter", False, f"Inactive filter failed: {response2.status_code}")
            else:
                self.log_test("GET /api/bins - Status Filter", False, f"Active filter failed: {response.status_code}")
        except Exception as e:
            self.log_test("GET /api/bins - Status Filter", False, f"Error: {str(e)}")
    
    def test_get_bin_stats(self):
        """Test GET /api/bins/count - statistics endpoint"""
        try:
            response = requests.get(f"{self.base_url}/bins/count", timeout=10)
            if response.status_code == 200:
                stats = response.json()
                required_fields = ['total_bins', 'active_bins', 'inactive_bins', 
                                 'total_capacity', 'total_stock', 'utilization_percentage']
                
                missing_fields = [field for field in required_fields if field not in stats]
                if not missing_fields:
                    self.log_test("GET /api/bins/count", True, 
                                f"Stats: {stats['total_bins']} bins, {stats['utilization_percentage']}% utilization")
                    return stats
                else:
                    self.log_test("GET /api/bins/count", False, f"Missing fields: {missing_fields}")
            else:
                self.log_test("GET /api/bins/count", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_test("GET /api/bins/count", False, f"Error: {str(e)}")
        return None
    
    def test_get_bin_by_id(self, bins: List[Dict]):
        """Test GET /api/bins/{bin_id}"""
        if not bins:
            self.log_test("GET /api/bins/{id} - Valid ID", False, "No bins available for testing")
            return
        
        try:
            # Test with valid ID
            bin_id = bins[0]['id']
            response = requests.get(f"{self.base_url}/bins/{bin_id}", timeout=10)
            if response.status_code == 200:
                bin_data = response.json()
                self.log_test("GET /api/bins/{id} - Valid ID", True, f"Retrieved bin: {bin_data['bin_number']}")
            else:
                self.log_test("GET /api/bins/{id} - Valid ID", False, f"Status: {response.status_code}")
            
            # Test with invalid ID format
            response = requests.get(f"{self.base_url}/bins/invalid_id", timeout=10)
            if response.status_code == 400:
                self.log_test("GET /api/bins/{id} - Invalid ID", True, "Correctly rejected invalid ID format")
            else:
                self.log_test("GET /api/bins/{id} - Invalid ID", False, f"Expected 400, got {response.status_code}")
            
            # Test with non-existent ID
            fake_id = "507f1f77bcf86cd799439011"  # Valid ObjectId format but non-existent
            response = requests.get(f"{self.base_url}/bins/{fake_id}", timeout=10)
            if response.status_code == 404:
                self.log_test("GET /api/bins/{id} - Non-existent ID", True, "Correctly returned 404 for non-existent bin")
            else:
                self.log_test("GET /api/bins/{id} - Non-existent ID", False, f"Expected 404, got {response.status_code}")
                
        except Exception as e:
            self.log_test("GET /api/bins/{id}", False, f"Error: {str(e)}")
    
    def test_get_bin_by_barcode(self, bins: List[Dict]):
        """Test GET /api/bins/barcode/{barcode}"""
        try:
            # Find a bin with barcode
            bin_with_barcode = None
            for bin_data in bins:
                if bin_data.get('barcode'):
                    bin_with_barcode = bin_data
                    break
            
            if bin_with_barcode:
                # Test with existing barcode
                barcode = bin_with_barcode['barcode']
                response = requests.get(f"{self.base_url}/bins/barcode/{barcode}", timeout=10)
                if response.status_code == 200:
                    self.log_test("GET /api/bins/barcode/{barcode} - Valid", True, f"Found bin by barcode: {barcode}")
                else:
                    self.log_test("GET /api/bins/barcode/{barcode} - Valid", False, f"Status: {response.status_code}")
            
            # Test with non-existent barcode
            response = requests.get(f"{self.base_url}/bins/barcode/NONEXISTENT123", timeout=10)
            if response.status_code == 404:
                self.log_test("GET /api/bins/barcode/{barcode} - Non-existent", True, "Correctly returned 404 for non-existent barcode")
            else:
                self.log_test("GET /api/bins/barcode/{barcode} - Non-existent", False, f"Expected 404, got {response.status_code}")
                
        except Exception as e:
            self.log_test("GET /api/bins/barcode/{barcode}", False, f"Error: {str(e)}")
    
    def test_create_bin(self):
        """Test POST /api/bins - create new bin"""
        try:
            # Test successful creation
            new_bin = {
                "bin_number": f"TEST-{datetime.now().strftime('%H%M%S')}",
                "location": "Warehouse A - Section 5 - Row 3",
                "capacity": 500,
                "current_stock": 150,
                "status": "active",
                "barcode": f"BC{datetime.now().strftime('%H%M%S')}"
            }
            
            response = requests.post(f"{self.base_url}/bins", json=new_bin, timeout=10)
            if response.status_code == 200:
                created_bin = response.json()
                self.created_bin_ids.append(created_bin['id'])
                self.log_test("POST /api/bins - Valid Creation", True, f"Created bin: {created_bin['bin_number']}")
                
                # Test duplicate bin_number rejection
                response2 = requests.post(f"{self.base_url}/bins", json=new_bin, timeout=10)
                if response2.status_code == 400:
                    self.log_test("POST /api/bins - Duplicate Rejection", True, "Correctly rejected duplicate bin_number")
                else:
                    self.log_test("POST /api/bins - Duplicate Rejection", False, f"Expected 400, got {response2.status_code}")
                
                return created_bin
            else:
                self.log_test("POST /api/bins - Valid Creation", False, f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("POST /api/bins", False, f"Error: {str(e)}")
        return None
    
    def test_create_bin_validation(self):
        """Test POST /api/bins validation rules"""
        try:
            # Test stock > capacity validation
            invalid_bin = {
                "bin_number": f"INVALID-{datetime.now().strftime('%H%M%S')}",
                "location": "Test Location",
                "capacity": 100,
                "current_stock": 150,  # Stock exceeds capacity
                "status": "active"
            }
            
            response = requests.post(f"{self.base_url}/bins", json=invalid_bin, timeout=10)
            if response.status_code == 400:
                self.log_test("POST /api/bins - Stock > Capacity Validation", True, "Correctly rejected stock > capacity")
            else:
                self.log_test("POST /api/bins - Stock > Capacity Validation", False, f"Expected 400, got {response.status_code}")
                
            # Test missing required fields
            incomplete_bin = {
                "location": "Test Location"
                # Missing bin_number and capacity
            }
            
            response = requests.post(f"{self.base_url}/bins", json=incomplete_bin, timeout=10)
            if response.status_code == 422:  # FastAPI validation error
                self.log_test("POST /api/bins - Required Fields Validation", True, "Correctly rejected missing required fields")
            else:
                self.log_test("POST /api/bins - Required Fields Validation", False, f"Expected 422, got {response.status_code}")
                
        except Exception as e:
            self.log_test("POST /api/bins - Validation", False, f"Error: {str(e)}")
    
    def test_update_bin(self, created_bin: Dict):
        """Test PUT /api/bins/{bin_id}"""
        if not created_bin:
            self.log_test("PUT /api/bins/{id}", False, "No created bin available for testing")
            return
        
        try:
            bin_id = created_bin['id']
            
            # Test successful update
            update_data = {
                "location": "Updated Warehouse B - Section 2",
                "current_stock": 200
            }
            
            response = requests.put(f"{self.base_url}/bins/{bin_id}", json=update_data, timeout=10)
            if response.status_code == 200:
                updated_bin = response.json()
                self.log_test("PUT /api/bins/{id} - Valid Update", True, f"Updated location: {updated_bin['location']}")
            else:
                self.log_test("PUT /api/bins/{id} - Valid Update", False, f"Status: {response.status_code}")
            
            # Test stock > capacity validation
            invalid_update = {
                "current_stock": 1000  # Exceeds capacity of 500
            }
            
            response = requests.put(f"{self.base_url}/bins/{bin_id}", json=invalid_update, timeout=10)
            if response.status_code == 400:
                self.log_test("PUT /api/bins/{id} - Stock > Capacity Validation", True, "Correctly rejected stock > capacity")
            else:
                self.log_test("PUT /api/bins/{id} - Stock > Capacity Validation", False, f"Expected 400, got {response.status_code}")
            
            # Test with invalid bin ID
            response = requests.put(f"{self.base_url}/bins/invalid_id", json=update_data, timeout=10)
            if response.status_code == 400:
                self.log_test("PUT /api/bins/{id} - Invalid ID", True, "Correctly rejected invalid ID format")
            else:
                self.log_test("PUT /api/bins/{id} - Invalid ID", False, f"Expected 400, got {response.status_code}")
                
        except Exception as e:
            self.log_test("PUT /api/bins/{id}", False, f"Error: {str(e)}")
    
    def test_delete_bin(self):
        """Test DELETE /api/bins/{bin_id}"""
        if not self.created_bin_ids:
            self.log_test("DELETE /api/bins/{id}", False, "No created bins available for deletion testing")
            return
        
        try:
            bin_id = self.created_bin_ids[0]
            
            # Test successful deletion
            response = requests.delete(f"{self.base_url}/bins/{bin_id}", timeout=10)
            if response.status_code == 200:
                self.log_test("DELETE /api/bins/{id} - Valid Deletion", True, "Successfully deleted bin")
                self.created_bin_ids.remove(bin_id)
            else:
                self.log_test("DELETE /api/bins/{id} - Valid Deletion", False, f"Status: {response.status_code}")
            
            # Test with invalid ID
            response = requests.delete(f"{self.base_url}/bins/invalid_id", timeout=10)
            if response.status_code == 400:
                self.log_test("DELETE /api/bins/{id} - Invalid ID", True, "Correctly rejected invalid ID format")
            else:
                self.log_test("DELETE /api/bins/{id} - Invalid ID", False, f"Expected 400, got {response.status_code}")
            
            # Test with non-existent ID
            fake_id = "507f1f77bcf86cd799439011"
            response = requests.delete(f"{self.base_url}/bins/{fake_id}", timeout=10)
            if response.status_code == 404:
                self.log_test("DELETE /api/bins/{id} - Non-existent ID", True, "Correctly returned 404 for non-existent bin")
            else:
                self.log_test("DELETE /api/bins/{id} - Non-existent ID", False, f"Expected 404, got {response.status_code}")
                
        except Exception as e:
            self.log_test("DELETE /api/bins/{id}", False, f"Error: {str(e)}")
    
    def cleanup_created_bins(self):
        """Clean up any remaining test bins"""
        for bin_id in self.created_bin_ids:
            try:
                requests.delete(f"{self.base_url}/bins/{bin_id}", timeout=5)
            except:
                pass  # Ignore cleanup errors
    
    def run_all_tests(self):
        """Run comprehensive test suite"""
        print("=" * 60)
        print("WAREHOUSE BIN LOOKUP API - COMPREHENSIVE TESTING")
        print("=" * 60)
        print(f"Testing Backend URL: {self.base_url}")
        print()
        
        # Test API health first
        if not self.test_api_health():
            print("\n❌ API is not accessible. Stopping tests.")
            return False
        
        print("\n" + "=" * 40)
        print("TESTING CRUD OPERATIONS")
        print("=" * 40)
        
        # Get existing bins for testing
        bins = self.test_get_bins_basic()
        
        # Test pagination and filtering
        self.test_get_bins_pagination()
        self.test_get_bins_search()
        self.test_get_bins_status_filter()
        
        # Test statistics
        self.test_get_bin_stats()
        
        # Test individual bin operations
        self.test_get_bin_by_id(bins)
        self.test_get_bin_by_barcode(bins)
        
        # Test create operations
        created_bin = self.test_create_bin()
        self.test_create_bin_validation()
        
        # Test update operations
        self.test_update_bin(created_bin)
        
        # Test delete operations
        self.test_delete_bin()
        
        # Cleanup
        self.cleanup_created_bins()
        
        # Print summary
        self.print_summary()
        
        return self.get_overall_success()
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("TEST RESULTS SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total*100):.1f}%")
        print()
        
        # Show failed tests
        failed_tests = [result for result in self.test_results if not result['success']]
        if failed_tests:
            print("FAILED TESTS:")
            print("-" * 40)
            for test in failed_tests:
                print(f"❌ {test['test']}")
                if test['details']:
                    print(f"   {test['details']}")
            print()
        
        # Show passed tests
        passed_tests = [result for result in self.test_results if result['success']]
        if passed_tests:
            print("PASSED TESTS:")
            print("-" * 40)
            for test in passed_tests:
                print(f"✅ {test['test']}")
    
    def get_overall_success(self):
        """Check if all critical tests passed"""
        failed_tests = [result for result in self.test_results if not result['success']]
        return len(failed_tests) == 0


def main():
    """Main test execution"""
    tester = BinAPITester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 ALL TESTS PASSED! Backend API is working correctly.")
        sys.exit(0)
    else:
        print("\n⚠️  SOME TESTS FAILED. Check the summary above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()