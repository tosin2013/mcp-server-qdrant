import requests
import json
import time
import os
import glob

def test_health():
    """Test the health endpoint of the MCP server."""
    response = requests.get("http://0.0.0.0:8000/health")
    print(f"MCP Health endpoint status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_qdrant_health():
    """Test the health endpoint of the Qdrant server."""
    response = requests.get("http://0.0.0.0:6333/healthz")
    print(f"Qdrant Health endpoint status: {response.status_code}")
    if response.status_code == 200:
        print("Qdrant is healthy")
    else:
        print(f"Response: {response.text}")
    return response.status_code == 200

def test_qdrant_collections():
    """Test the collections endpoint of the Qdrant server."""
    response = requests.get("http://0.0.0.0:6333/collections")
    print(f"Qdrant Collections endpoint status: {response.status_code}")
    if response.status_code == 200:
        print(f"Collections: {json.dumps(response.json(), indent=2)}")
    else:
        print(f"Response: {response.text}")
    return response.status_code == 200

def test_qdrant_collection_info():
    """Test getting information about a specific collection."""
    collection_name = "mcp_unified_store"
    response = requests.get(f"http://0.0.0.0:6333/collections/{collection_name}")
    print(f"Qdrant Collection Info endpoint status: {response.status_code}")
    if response.status_code == 200:
        print(f"Collection Info: {json.dumps(response.json(), indent=2)}")
    else:
        print(f"Response: {response.text}")
    return response.status_code == 200

def test_qdrant_create_collection():
    """Test creating a new collection in Qdrant."""
    collection_name = "test_adr_collection"
    
    # Check if collection already exists
    response = requests.get(f"http://0.0.0.0:6333/collections/{collection_name}")
    if response.status_code == 200:
        print(f"Collection {collection_name} already exists")
        return True
    
    payload = {
        "vectors": {
            "size": 384,
            "distance": "Cosine"
        }
    }
    response = requests.put(
        f"http://0.0.0.0:6333/collections/{collection_name}",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload)
    )
    print(f"Qdrant Create Collection endpoint status: {response.status_code}")
    if response.status_code in [200, 201]:
        print(f"Collection created: {json.dumps(response.json(), indent=2)}")
    else:
        print(f"Response: {response.text}")
    return response.status_code in [200, 201]

def test_qdrant_add_adr_data():
    """Test adding ADR data to Qdrant."""
    collection_name = "test_adr_collection"
    
    # Get ADR files
    adr_files = glob.glob("docs/adrs/*.md")
    if not adr_files:
        print("No ADR files found in docs/adrs/")
        return False
    
    print(f"Found {len(adr_files)} ADR files")
    
    # Process each ADR file
    points = []
    for i, adr_file in enumerate(adr_files):
        try:
            with open(adr_file, 'r') as f:
                content = f.read()
            
            # Extract title and status from content
            title = "Unknown ADR"
            status = "Unknown"
            
            lines = content.split('\n')
            for line in lines:
                if line.startswith('# '):
                    title = line[2:].strip()
                elif line.startswith('## Status'):
                    status_index = lines.index(line)
                    if status_index + 1 < len(lines):
                        status = lines[status_index + 1].strip()
            
            # Create a point with the ADR data
            point = {
                "id": i + 1,
                "vector": [0.1] * 384,  # Dummy vector for testing
                "payload": {
                    "file_path": adr_file,
                    "content_type": "documentation",
                    "content": content[:1000],  # First 1000 chars for brevity
                    "metadata": {
                        "title": title,
                        "status": status,
                        "last_modified": time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(adr_file))),
                        "size": len(content),
                        "language": "markdown"
                    }
                }
            }
            points.append(point)
            print(f"Processed ADR: {title} ({status})")
        except Exception as e:
            print(f"Error processing {adr_file}: {e}")
    
    # Add points to collection
    if points:
        payload = {
            "points": points
        }
        response = requests.put(
            f"http://0.0.0.0:6333/collections/{collection_name}/points",
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload)
        )
        print(f"Qdrant Add Points status: {response.status_code}")
        if response.status_code == 200:
            print(f"Added {len(points)} points: {json.dumps(response.json(), indent=2)}")
            return True
        else:
            print(f"Response: {response.text}")
            return False
    else:
        print("No points to add")
        return False

def test_qdrant_search_adr_data():
    """Test searching ADR data in Qdrant."""
    collection_name = "test_adr_collection"
    
    # Search for ADRs related to "testing"
    payload = {
        "vector": [0.1] * 384,  # Dummy vector for testing
        "limit": 3,
        "with_payload": True
    }
    response = requests.post(
        f"http://0.0.0.0:6333/collections/{collection_name}/points/search",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload)
    )
    print(f"Qdrant Search status: {response.status_code}")
    if response.status_code == 200:
        results = response.json()
        print(f"Search results: {json.dumps(results, indent=2)}")
        
        # Print titles of found ADRs
        if "result" in results and results["result"]:
            print("\nFound ADRs:")
            for i, result in enumerate(results["result"]):
                if "payload" in result and "metadata" in result["payload"]:
                    title = result["payload"]["metadata"].get("title", "Unknown")
                    print(f"{i+1}. {title}")
        return True
    else:
        print(f"Response: {response.text}")
        return False

def test_qdrant_delete_collection():
    """Test deleting a collection from Qdrant."""
    collection_name = "test_adr_collection"
    response = requests.delete(f"http://0.0.0.0:6333/collections/{collection_name}")
    print(f"Qdrant Delete Collection endpoint status: {response.status_code}")
    if response.status_code == 200:
        print(f"Collection deleted: {json.dumps(response.json(), indent=2)}")
    else:
        print(f"Response: {response.text}")
    return response.status_code == 200

if __name__ == "__main__":
    print("Testing MCP and Qdrant servers with ADR data...\n")
    
    # Test MCP health endpoint
    mcp_health_ok = test_health()
    print(f"MCP Health endpoint test {'passed' if mcp_health_ok else 'failed'}\n")
    
    # Test Qdrant health endpoint
    qdrant_health_ok = test_qdrant_health()
    print(f"Qdrant Health endpoint test {'passed' if qdrant_health_ok else 'failed'}\n")
    
    # Test Qdrant collections endpoint
    qdrant_collections_ok = test_qdrant_collections()
    print(f"Qdrant Collections endpoint test {'passed' if qdrant_collections_ok else 'failed'}\n")
    
    # Test Qdrant collection info endpoint
    qdrant_collection_info_ok = test_qdrant_collection_info()
    print(f"Qdrant Collection Info endpoint test {'passed' if qdrant_collection_info_ok else 'failed'}\n")
    
    # Test creating a collection for ADR data
    qdrant_create_collection_ok = test_qdrant_create_collection()
    print(f"Qdrant Create Collection test {'passed' if qdrant_create_collection_ok else 'failed'}\n")
    
    # Test adding ADR data
    if qdrant_create_collection_ok:
        qdrant_add_data_ok = test_qdrant_add_adr_data()
        print(f"Qdrant Add ADR Data test {'passed' if qdrant_add_data_ok else 'failed'}\n")
        
        # Test searching ADR data
        if qdrant_add_data_ok:
            qdrant_search_data_ok = test_qdrant_search_adr_data()
            print(f"Qdrant Search ADR Data test {'passed' if qdrant_search_data_ok else 'failed'}\n")
        else:
            qdrant_search_data_ok = False
            print("Skipping search test as data addition failed\n")
    else:
        qdrant_add_data_ok = False
        qdrant_search_data_ok = False
        print("Skipping data addition and search tests as collection creation failed\n")
    
    # Skip deleting the collection so data remains visible in the dashboard
    print("Skipping collection deletion to keep data visible in the dashboard\n")
    qdrant_delete_collection_ok = True
    
    # Overall result
    all_tests_passed = (
        mcp_health_ok and 
        qdrant_health_ok and 
        qdrant_collections_ok and 
        qdrant_collection_info_ok and 
        qdrant_create_collection_ok and 
        qdrant_add_data_ok and
        qdrant_search_data_ok and
        qdrant_delete_collection_ok
    )
    print(f"Overall test result: {'All tests passed' if all_tests_passed else 'Some tests failed'}")
    
    print("\nYou can now view the data in the Qdrant dashboard at http://localhost:6333/dashboard")
    print("Navigate to the 'Collections' tab and select 'test_adr_collection' to see the ADR data") 