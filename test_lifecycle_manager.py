#!/usr/bin/env python3
"""
Test Script for NetworkEyes Lifecycle Manager (New Architecture)

This script tests the NetworkEyes plugin lifecycle manager to ensure
it works correctly with the new multi-user plugin system.
"""

import asyncio
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any
import structlog

# Mock database session for testing
class MockAsyncSession:
    """Mock database session for testing purposes"""
    
    def __init__(self):
        self.data = {
            'plugins': {},
            'modules': {}
        }
        self.committed = False
        self.rolled_back = False
    
    async def execute(self, query, params=None):
        """Mock execute method"""
        query_str = str(query)
        
        if "INSERT INTO plugin" in query_str:
            plugin_id = params['id']
            self.data['plugins'][plugin_id] = params
            return MockResult(rowcount=1)
        elif "INSERT INTO module" in query_str:
            module_id = params['id']
            self.data['modules'][module_id] = params
            return MockResult(rowcount=1)
        elif "DELETE FROM module" in query_str:
            deleted = 0
            for module_id in list(self.data['modules'].keys()):
                if self.data['modules'][module_id]['plugin_id'] == params['plugin_id']:
                    del self.data['modules'][module_id]
                    deleted += 1
            return MockResult(rowcount=deleted)
        elif "DELETE FROM plugin" in query_str:
            plugin_id = params['plugin_id']
            if plugin_id in self.data['plugins']:
                del self.data['plugins'][plugin_id]
                return MockResult(rowcount=1)
            return MockResult(rowcount=0)
        elif "SELECT" in query_str and "plugin" in query_str:
            plugin_id = f"{params['user_id']}_{params['plugin_slug']}"
            if plugin_id in self.data['plugins']:
                plugin_data = self.data['plugins'][plugin_id]
                return MockResult(fetchone_data=MockRow(plugin_data))
            return MockResult(fetchone_data=None)
        elif "SELECT" in query_str and "module" in query_str:
            modules = []
            for module_id, module_data in self.data['modules'].items():
                if module_data['plugin_id'] == params['plugin_id']:
                    modules.append(MockRow(module_data))
            return MockResult(fetchall_data=modules)
        
        return MockResult()
    
    async def commit(self):
        """Mock commit method"""
        self.committed = True
    
    async def rollback(self):
        """Mock rollback method"""
        self.rolled_back = True

class MockResult:
    """Mock database result"""
    
    def __init__(self, rowcount=0, fetchone_data=None, fetchall_data=None):
        self.rowcount = rowcount
        self._fetchone_data = fetchone_data
        self._fetchall_data = fetchall_data or []
    
    def fetchone(self):
        return self._fetchone_data
    
    def fetchall(self):
        return self._fetchall_data

class MockRow:
    """Mock database row"""
    
    def __init__(self, data):
        for key, value in data.items():
            setattr(self, key, value)

logger = structlog.get_logger()

class NetworkEyesLifecycleManagerTester:
    """Test suite for NetworkEyes lifecycle manager"""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="networkeyes_test_"))
        self.test_user_id = "test_user_123"
        self.test_results = []
        
        # Create mock plugin files
        self._setup_mock_plugin_files()
        
        logger.info(f"NetworkEyes test environment created at: {self.temp_dir}")
    
    def _setup_mock_plugin_files(self):
        """Create mock plugin files for testing"""
        plugin_source_dir = self.temp_dir / "NetworkEyes"
        plugin_source_dir.mkdir(parents=True)
        
        # Create mock package.json
        package_json = {
            "name": "networkeyes-plugin",
            "version": "1.0.6",
            "description": "Network monitoring plugin",
            "main": "dist/remoteEntry.js"
        }
        
        with open(plugin_source_dir / "package.json", 'w') as f:
            json.dump(package_json, f, indent=2)
        
        # Create mock dist directory and bundle
        dist_dir = plugin_source_dir / "dist"
        dist_dir.mkdir()
        
        with open(dist_dir / "remoteEntry.js", 'w') as f:
            f.write("// Mock NetworkEyes bundle\nconsole.log('NetworkEyes plugin loaded');")
        
        # Create mock src directory
        src_dir = plugin_source_dir / "src"
        src_dir.mkdir()
        
        with open(src_dir / "index.js", 'w') as f:
            f.write("// Mock NetworkEyes source")
        
        # Create mock public directory
        public_dir = plugin_source_dir / "public"
        public_dir.mkdir()
        
        with open(public_dir / "manifest.json", 'w') as f:
            json.dump({"name": "NetworkEyes"}, f)
        
        # Create README
        with open(plugin_source_dir / "README.md", 'w') as f:
            f.write("# NetworkEyes Plugin\n\nNetwork monitoring for BrainDrive")
        
        logger.info(f"Mock plugin files created in: {plugin_source_dir}")
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all test cases for NetworkEyes lifecycle manager"""
        try:
            logger.info("Starting NetworkEyes lifecycle manager tests")
            
            # Import the lifecycle manager
            import sys
            sys.path.append(str(Path(__file__).parent))
            from lifecycle_manager import NetworkEyesLifecycleManager
            
            # Initialize manager with test directory
            manager = NetworkEyesLifecycleManager(str(self.temp_dir))
            
            # Test 1: Plugin Installation
            await self._test_plugin_installation(manager)
            
            # Test 2: Plugin Status Check
            await self._test_plugin_status(manager)
            
            # Test 3: Plugin Deletion
            await self._test_plugin_deletion(manager)
            
            # Test 4: Plugin Info
            await self._test_plugin_info(manager)
            
            # Test 5: File Operations
            await self._test_file_operations(manager)
            
            # Compile results
            passed_tests = sum(1 for result in self.test_results if result['passed'])
            total_tests = len(self.test_results)
            
            summary = {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': total_tests - passed_tests,
                'success_rate': (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
                'test_results': self.test_results
            }
            
            logger.info(f"NetworkEyes tests completed: {passed_tests}/{total_tests} passed")
            return summary
            
        except Exception as e:
            logger.error(f"Error running NetworkEyes tests: {e}")
            return {
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 1,
                'success_rate': 0,
                'error': str(e),
                'test_results': self.test_results
            }
        finally:
            # Cleanup
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
    
    async def _test_plugin_installation(self, manager):
        """Test plugin installation"""
        try:
            db = MockAsyncSession()
            result = await manager.install_plugin(self.test_user_id, db)
            
            success = result.get('success', False)
            self.test_results.append({
                'test_name': 'Plugin Installation',
                'passed': success,
                'details': result,
                'error': None if success else result.get('error', 'Unknown error')
            })
            
            if success:
                logger.info("✓ Plugin installation test passed")
            else:
                logger.error(f"✗ Plugin installation test failed: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"✗ Plugin installation test error: {e}")
            self.test_results.append({
                'test_name': 'Plugin Installation',
                'passed': False,
                'details': {},
                'error': str(e)
            })
    
    async def _test_plugin_status(self, manager):
        """Test plugin status check"""
        try:
            db = MockAsyncSession()
            
            # First install the plugin
            await manager.install_plugin(self.test_user_id, db)
            
            # Then check status
            result = await manager.get_plugin_status(self.test_user_id, db)
            
            success = result.get('exists', False)
            self.test_results.append({
                'test_name': 'Plugin Status Check',
                'passed': success,
                'details': result,
                'error': None if success else result.get('error', 'Plugin not found')
            })
            
            if success:
                logger.info("✓ Plugin status check test passed")
            else:
                logger.error(f"✗ Plugin status check test failed: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"✗ Plugin status check test error: {e}")
            self.test_results.append({
                'test_name': 'Plugin Status Check',
                'passed': False,
                'details': {},
                'error': str(e)
            })
    
    async def _test_plugin_deletion(self, manager):
        """Test plugin deletion"""
        try:
            db = MockAsyncSession()
            
            # First install the plugin
            await manager.install_plugin(self.test_user_id, db)
            
            # Then delete it
            result = await manager.delete_plugin(self.test_user_id, db)
            
            success = result.get('success', False)
            self.test_results.append({
                'test_name': 'Plugin Deletion',
                'passed': success,
                'details': result,
                'error': None if success else result.get('error', 'Unknown error')
            })
            
            if success:
                logger.info("✓ Plugin deletion test passed")
            else:
                logger.error(f"✗ Plugin deletion test failed: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"✗ Plugin deletion test error: {e}")
            self.test_results.append({
                'test_name': 'Plugin Deletion',
                'passed': False,
                'details': {},
                'error': str(e)
            })
    
    async def _test_plugin_info(self, manager):
        """Test plugin info retrieval"""
        try:
            info = manager.get_plugin_info()
            
            required_fields = ['name', 'version', 'description', 'plugin_slug']
            has_required_fields = all(field in info for field in required_fields)
            
            success = has_required_fields and info['name'] == 'BrainDriveNetwork'
            
            self.test_results.append({
                'test_name': 'Plugin Info Retrieval',
                'passed': success,
                'details': info,
                'error': None if success else 'Missing required fields or incorrect data'
            })
            
            if success:
                logger.info("✓ Plugin info retrieval test passed")
            else:
                logger.error("✗ Plugin info retrieval test failed")
                
        except Exception as e:
            logger.error(f"✗ Plugin info retrieval test error: {e}")
            self.test_results.append({
                'test_name': 'Plugin Info Retrieval',
                'passed': False,
                'details': {},
                'error': str(e)
            })
    
    async def _test_file_operations(self, manager):
        """Test file operations"""
        try:
            # Test file copying
            target_dir = self.temp_dir / "test_target"
            target_dir.mkdir()
            
            result = await manager._copy_plugin_files_impl(self.test_user_id, target_dir)
            
            success = result.get('success', False)
            
            if success:
                # Verify files were copied
                expected_files = ['package.json', 'README.md']
                files_exist = all((target_dir / f).exists() for f in expected_files)
                
                expected_dirs = ['dist/', 'src/', 'public/']
                dirs_exist = all((target_dir / d.rstrip('/')).exists() for d in expected_dirs)
                
                success = files_exist and dirs_exist
            
            self.test_results.append({
                'test_name': 'File Operations',
                'passed': success,
                'details': result,
                'error': None if success else 'File copying failed or files missing'
            })
            
            if success:
                logger.info("✓ File operations test passed")
            else:
                logger.error("✗ File operations test failed")
                
        except Exception as e:
            logger.error(f"✗ File operations test error: {e}")
            self.test_results.append({
                'test_name': 'File Operations',
                'passed': False,
                'details': {},
                'error': str(e)
            })


async def main():
    """Run NetworkEyes lifecycle manager tests"""
    print("NetworkEyes Plugin Lifecycle Manager Test Suite")
    print("=" * 50)
    
    tester = NetworkEyesLifecycleManagerTester()
    results = await tester.run_all_tests()
    
    print(f"\nTest Results:")
    print(f"Total Tests: {results['total_tests']}")
    print(f"Passed: {results['passed_tests']}")
    print(f"Failed: {results['failed_tests']}")
    print(f"Success Rate: {results['success_rate']:.1f}%")
    
    if results['failed_tests'] > 0:
        print(f"\nFailed Tests:")
        for result in results['test_results']:
            if not result['passed']:
                print(f"  - {result['test_name']}: {result['error']}")
    
    print(f"\nDetailed Results:")
    for result in results['test_results']:
        status = "✓ PASS" if result['passed'] else "✗ FAIL"
        print(f"  {status}: {result['test_name']}")
        if result['error']:
            print(f"    Error: {result['error']}")


if __name__ == "__main__":
    asyncio.run(main())