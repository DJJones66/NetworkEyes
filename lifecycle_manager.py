#!/usr/bin/env python3
"""
NetworkEyes Plugin Lifecycle Manager (New Architecture)

This script handles install/update/delete operations for the NetworkEyes plugin
using the new multi-user plugin lifecycle management architecture.
"""

import json
import logging
import datetime
import os
import shutil
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import structlog

logger = structlog.get_logger()

# Import the new base lifecycle manager
try:
    # Try to import from the BrainDrive system first (when running in production)
    from app.plugins.base_lifecycle_manager import BaseLifecycleManager
    logger.info("Using new architecture: BaseLifecycleManager imported from app.plugins")
except ImportError:
    try:
        # Try local import for development
        import sys
        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_path = os.path.join(current_dir, "..", "..", "backend", "app", "plugins")
        backend_path = os.path.abspath(backend_path)
        
        if os.path.exists(backend_path):
            if backend_path not in sys.path:
                sys.path.insert(0, backend_path)
            from base_lifecycle_manager import BaseLifecycleManager
            logger.info(f"Using new architecture: BaseLifecycleManager imported from local backend: {backend_path}")
        else:
            # For remote installation, the base class might not be available
            # In this case, we'll create a minimal implementation
            logger.warning(f"BaseLifecycleManager not found at {backend_path}, using minimal implementation")
            from abc import ABC, abstractmethod
            from datetime import datetime
            from pathlib import Path
            from typing import Set
            
            class BaseLifecycleManager(ABC):
                """Minimal base class for remote installations"""
                def __init__(self, plugin_slug: str, version: str, shared_storage_path: Path):
                    self.plugin_slug = plugin_slug
                    self.version = version
                    self.shared_path = shared_storage_path
                    self.active_users: Set[str] = set()
                    self.instance_id = f"{plugin_slug}_{version}"
                    self.created_at = datetime.now()
                    self.last_used = datetime.now()
                
                async def install_for_user(self, user_id: str, db, shared_plugin_path: Path):
                    if user_id in self.active_users:
                        return {'success': False, 'error': 'Plugin already installed for user'}
                    result = await self._perform_user_installation(user_id, db, shared_plugin_path)
                    if result['success']:
                        self.active_users.add(user_id)
                        self.last_used = datetime.now()
                    return result
                
                async def uninstall_for_user(self, user_id: str, db):
                    if user_id not in self.active_users:
                        return {'success': False, 'error': 'Plugin not installed for user'}
                    result = await self._perform_user_uninstallation(user_id, db)
                    if result['success']:
                        self.active_users.discard(user_id)
                        self.last_used = datetime.now()
                    return result
                
                @abstractmethod
                async def get_plugin_metadata(self): pass
                @abstractmethod
                async def get_module_metadata(self): pass
                @abstractmethod
                async def _perform_user_installation(self, user_id, db, shared_plugin_path): pass
                @abstractmethod
                async def _perform_user_uninstallation(self, user_id, db): pass
            
            logger.info("Using minimal BaseLifecycleManager implementation for remote installation")
            
    except ImportError as e:
        logger.error(f"Failed to import BaseLifecycleManager: {e}")
        raise ImportError("NetworkEyes plugin requires the new architecture BaseLifecycleManager")


class NetworkEyesLifecycleManager(BaseLifecycleManager):
    """Lifecycle manager for NetworkEyes plugin using new architecture"""
    
    def __init__(self, plugins_base_dir: str = None):
        """Initialize the lifecycle manager"""
        # Define plugin-specific data
        self.plugin_data = {
            "name": "BrainDriveNetwork",
            "description": "Network status monitoring and connectivity checking for BrainDrive services",
            "version": "1.0.13",
            "type": "frontend",
            "icon": "NetworkCheck",
            "category": "monitoring",
            "official": False,
            "author": "DJJones66",
            "compatibility": "1.0.0",
            "scope": "BrainDriveNetwork",
            "bundle_method": "webpack",
            "bundle_location": "dist/remoteEntry.js",
            "is_local": False,
            "long_description": "Monitor network connectivity and status of BrainDrive services with real-time monitoring capabilities",
            "plugin_slug": "BrainDriveNetwork",
            # Update tracking fields (matching plugin model)
            "source_type": "github",
            "source_url": "https://github.com/DJJones66/NetworkEyes",
            "update_check_url": "https://api.github.com/repos/DJJones66/NetworkEyes/releases/latest",
            "last_update_check": None,      # Will be set when first checked
            "update_available": False,      # Will be updated by update checker
            "latest_version": None,         # Will be populated by update checker
            "installation_type": "remote",
            "permissions": ["network.read", "storage.read", "storage.write"]
        }
        
        self.module_data = [
            {
                "name": "ComponentNetworkStatus",
                "display_name": "Network Status Monitor",
                "description": "Real-time network connectivity monitoring dashboard",
                "icon": "NetworkCheck",
                "category": "monitoring",
                "priority": 1,
                "props": {},
                "config_fields": {
                    "refresh_interval": {
                        "type": "number",
                        "description": "Auto-refresh interval in seconds",
                        "default": 30
                    },
                    "show_detailed_stats": {
                        "type": "boolean",
                        "description": "Show detailed network statistics",
                        "default": True
                    }
                },
                "messages": {},
                "required_services": {
                    "api": {"methods": ["get"], "version": "1.0.0"},
                    "network": {"methods": ["check", "monitor"], "version": "1.0.0"}
                },
                "dependencies": [],
                "layout": {
                    "minWidth": 3,
                    "minHeight": 2,
                    "defaultWidth": 4,
                    "defaultHeight": 3
                },
                "tags": ["monitoring", "network", "status", "connectivity", "eyes"]
            }
        ]
        
        # Initialize base class with required parameters
        if plugins_base_dir:
            shared_path = Path(plugins_base_dir) / "shared" / self.plugin_data['plugin_slug'] / f"v{self.plugin_data['version']}"
        else:
            shared_path = Path(__file__).parent.parent.parent / "backend" / "plugins" / "shared" / self.plugin_data['plugin_slug'] / f"v{self.plugin_data['version']}"
        
        super().__init__(
            plugin_slug=self.plugin_data['plugin_slug'],
            version=self.plugin_data['version'],
            shared_storage_path=shared_path
        )
    
    @property
    def PLUGIN_DATA(self):
        """Compatibility property for remote installer validation"""
        return self.plugin_data
    
    async def get_plugin_metadata(self) -> Dict[str, Any]:
        """Return plugin metadata and configuration"""
        return self.plugin_data
    
    async def get_module_metadata(self) -> list:
        """Return module definitions for this plugin"""
        return self.module_data
    
    async def _perform_user_installation(self, user_id: str, db: AsyncSession, shared_plugin_path: Path) -> Dict[str, Any]:
        """Perform user-specific installation using shared plugin path"""
        try:
            # Create database records for this user
            db_result = await self._create_database_records(user_id, db)
            if not db_result['success']:
                return db_result
            
            logger.info(f"NetworkEyes: User installation completed for {user_id}")
            return {
                'success': True,
                'plugin_id': db_result['plugin_id'],
                'modules_created': db_result['modules_created']
            }
            
        except Exception as e:
            logger.error(f"NetworkEyes: User installation failed for {user_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _perform_user_uninstallation(self, user_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Perform user-specific uninstallation"""
        try:
            # Check if plugin exists for user
            existing_check = await self._check_existing_plugin(user_id, db)
            if not existing_check['exists']:
                return {'success': False, 'error': 'Plugin not found for user'}
            
            plugin_id = existing_check['plugin_id']
            
            # Delete database records
            delete_result = await self._delete_database_records(user_id, plugin_id, db)
            if not delete_result['success']:
                return delete_result
            
            logger.info(f"NetworkEyes: User uninstallation completed for {user_id}")
            return {
                'success': True,
                'plugin_id': plugin_id,
                'deleted_modules': delete_result['deleted_modules']
            }
            
        except Exception as e:
            logger.error(f"NetworkEyes: User uninstallation failed for {user_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _copy_plugin_files_impl(self, user_id: str, target_dir: Path, update: bool = False) -> Dict[str, Any]:
        """
        NetworkEyes-specific implementation of file copying.
        This method is called by the base class during installation.
        Copies all files from the plugin source directory to the target directory.
        """
        try:
            source_dir = Path(__file__).parent
            copied_files = []
            
            # Define files and directories to exclude (similar to build_archive.py)
            exclude_patterns = {
                'node_modules',
                'package-lock.json',
                '.git',
                '.gitignore',
                '__pycache__',
                '*.pyc',
                '.DS_Store',
                'Thumbs.db'
            }
            
            def should_copy(path: Path) -> bool:
                """Check if a file/directory should be copied"""
                # Check if any part of the path matches exclude patterns
                for part in path.parts:
                    if part in exclude_patterns:
                        return False
                # Check for pattern matches
                for pattern in exclude_patterns:
                    if '*' in pattern and path.name.endswith(pattern.replace('*', '')):
                        return False
                return True
            
            # Copy all files and directories recursively
            for item in source_dir.rglob('*'):
                # Skip the lifecycle_manager.py file itself to avoid infinite recursion
                if item.name == 'lifecycle_manager.py' and item == Path(__file__):
                    continue
                    
                # Get relative path from source directory
                relative_path = item.relative_to(source_dir)
                
                # Check if we should copy this item
                if not should_copy(relative_path):
                    continue
                
                target_path = target_dir / relative_path
                
                try:
                    if item.is_file():
                        # Create parent directories if they don't exist
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, target_path)
                        copied_files.append(str(target_path))
                        logger.info(f"NetworkEyes: Copied file {item} to {target_path}")
                    elif item.is_dir():
                        # Create directory if it doesn't exist
                        target_path.mkdir(parents=True, exist_ok=True)
                        logger.info(f"NetworkEyes: Created directory {target_path}")
                except Exception as e:
                    logger.error(f"NetworkEyes: Failed to copy {item} to {target_path}: {e}")
                    continue
            
            # Copy the lifecycle_manager.py file itself
            lifecycle_manager_source = Path(__file__)
            lifecycle_manager_target = target_dir / 'lifecycle_manager.py'
            try:
                shutil.copy2(lifecycle_manager_source, lifecycle_manager_target)
                copied_files.append(str(lifecycle_manager_target))
                logger.info(f"NetworkEyes: Copied lifecycle_manager.py to {lifecycle_manager_target}")
            except Exception as e:
                logger.error(f"NetworkEyes: Failed to copy lifecycle_manager.py: {e}")
            
            logger.info(f"NetworkEyes: Copied {len(copied_files)} files/directories to {target_dir}")
            return {'success': True, 'copied_files': copied_files}
            
        except Exception as e:
            logger.error(f"NetworkEyes: Error copying plugin files: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _validate_installation_impl(self, user_id: str, plugin_dir: Path) -> Dict[str, Any]:
        """
        NetworkEyes-specific validation logic.
        This method is called by the base class during installation.
        """
        try:
            # Check for NetworkEyes-specific required files
            required_files = ["package.json", "dist/remoteEntry.js"]
            missing_files = []
            
            for file_path in required_files:
                if not (plugin_dir / file_path).exists():
                    missing_files.append(file_path)
            
            if missing_files:
                return {
                    'valid': False,
                    'error': f"NetworkEyes: Missing required files: {', '.join(missing_files)}"
                }
            
            # Validate package.json structure
            package_json_path = plugin_dir / "package.json"
            try:
                with open(package_json_path, 'r') as f:
                    package_data = json.load(f)
                
                # Check for required package.json fields
                required_fields = ["name", "version"]
                for field in required_fields:
                    if field not in package_data:
                        return {
                            'valid': False,
                            'error': f'NetworkEyes: package.json missing required field: {field}'
                        }
                        
            except (json.JSONDecodeError, FileNotFoundError) as e:
                return {
                    'valid': False,
                    'error': f'NetworkEyes: Invalid or missing package.json: {e}'
                }
            
            # Validate bundle file exists and is not empty
            bundle_path = plugin_dir / "dist" / "remoteEntry.js"
            if bundle_path.stat().st_size == 0:
                return {
                    'valid': False,
                    'error': 'NetworkEyes: Bundle file (remoteEntry.js) is empty'
                }
            
            logger.info(f"NetworkEyes: Installation validation passed for user {user_id}")
            return {'valid': True}
            
        except Exception as e:
            logger.error(f"NetworkEyes: Error validating installation: {e}")
            return {'valid': False, 'error': str(e)}
    
    async def _get_plugin_health_impl(self, user_id: str, plugin_dir: Path) -> Dict[str, Any]:
        """
        NetworkEyes-specific health check logic.
        This method is called by the base class during status checks.
        """
        try:
            health_info = {
                'bundle_exists': False,
                'bundle_size': 0,
                'package_json_valid': False,
                'assets_present': False
            }
            
            # Check bundle file
            bundle_path = plugin_dir / "dist" / "remoteEntry.js"
            if bundle_path.exists():
                health_info['bundle_exists'] = True
                health_info['bundle_size'] = bundle_path.stat().st_size
            
            # Check package.json
            package_json_path = plugin_dir / "package.json"
            if package_json_path.exists():
                try:
                    with open(package_json_path, 'r') as f:
                        json.load(f)
                    health_info['package_json_valid'] = True
                except json.JSONDecodeError:
                    pass
            
            # Check for assets directory
            assets_path = plugin_dir / "assets"
            if assets_path.exists() and assets_path.is_dir():
                health_info['assets_present'] = True
            
            # Determine overall health
            is_healthy = (
                health_info['bundle_exists'] and 
                health_info['bundle_size'] > 0 and
                health_info['package_json_valid']
            )
            
            return {
                'healthy': is_healthy,
                'details': health_info
            }
            
        except Exception as e:
            logger.error(f"NetworkEyes: Error checking plugin health: {e}")
            return {
                'healthy': False,
                'details': {'error': str(e)}
            }
    
    async def _check_existing_plugin(self, user_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Check if plugin already exists for user"""
        try:
            plugin_query = text("""
            SELECT id, name, version, enabled, created_at, updated_at
            FROM plugin 
            WHERE user_id = :user_id AND plugin_slug = :plugin_slug
            """)
            
            result = await db.execute(plugin_query, {
                'user_id': user_id,
                'plugin_slug': self.plugin_data['plugin_slug']
            })
            
            plugin_row = result.fetchone()
            if plugin_row:
                return {
                    'exists': True,
                    'plugin_id': plugin_row.id,
                    'plugin_info': {
                        'id': plugin_row.id,
                        'name': plugin_row.name,
                        'version': plugin_row.version,
                        'enabled': plugin_row.enabled,
                        'created_at': plugin_row.created_at,
                        'updated_at': plugin_row.updated_at
                    }
                }
            else:
                return {'exists': False}
                
        except Exception as e:
            logger.error(f"Error checking existing plugin: {e}")
            return {'exists': False, 'error': str(e)}
    
    async def _create_database_records(self, user_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Create plugin and module records in database"""
        try:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            plugin_slug = self.plugin_data['plugin_slug']
            plugin_id = f"{user_id}_{plugin_slug}"
            
            plugin_stmt = text("""
            INSERT INTO plugin
            (id, name, description, version, type, enabled, icon, category, status,
            official, author, last_updated, compatibility, downloads, scope,
            bundle_method, bundle_location, is_local, long_description,
            config_fields, messages, dependencies, created_at, updated_at, user_id,
            plugin_slug, source_type, source_url, update_check_url, last_update_check,
            update_available, latest_version, installation_type, permissions)
            VALUES
            (:id, :name, :description, :version, :type, :enabled, :icon, :category,
            :status, :official, :author, :last_updated, :compatibility, :downloads,
            :scope, :bundle_method, :bundle_location, :is_local, :long_description,
            :config_fields, :messages, :dependencies, :created_at, :updated_at, :user_id,
            :plugin_slug, :source_type, :source_url, :update_check_url, :last_update_check,
            :update_available, :latest_version, :installation_type, :permissions)
            """)
            
            await db.execute(plugin_stmt, {
                'id': plugin_id,
                'name': self.plugin_data['name'],
                'description': self.plugin_data['description'],
                'version': self.plugin_data['version'],
                'type': self.plugin_data['type'],
                'enabled': True,
                'icon': self.plugin_data['icon'],
                'category': self.plugin_data['category'],
                'status': 'activated',
                'official': self.plugin_data['official'],
                'author': self.plugin_data['author'],
                'last_updated': current_time,
                'compatibility': self.plugin_data['compatibility'],
                'downloads': 0,
                'scope': self.plugin_data['scope'],
                'bundle_method': self.plugin_data['bundle_method'],
                'bundle_location': self.plugin_data['bundle_location'],
                'is_local': self.plugin_data['is_local'],
                'long_description': self.plugin_data['long_description'],
                'config_fields': json.dumps({}),
                'messages': None,
                'dependencies': None,
                'created_at': current_time,
                'updated_at': current_time,
                'user_id': user_id,
                'plugin_slug': plugin_slug,
                'source_type': self.plugin_data['source_type'],
                'source_url': self.plugin_data['source_url'],
                'update_check_url': self.plugin_data['update_check_url'],
                'last_update_check': self.plugin_data['last_update_check'],
                'update_available': self.plugin_data['update_available'],
                'latest_version': self.plugin_data['latest_version'],
                'installation_type': self.plugin_data['installation_type'],
                'permissions': json.dumps(self.plugin_data['permissions'])
            })
            
            modules_created = []
            for module_data in self.module_data:
                module_id = f"{user_id}_{plugin_slug}_{module_data['name']}"
                
                module_stmt = text("""
                INSERT INTO module
                (id, plugin_id, name, display_name, description, icon, category,
                enabled, priority, props, config_fields, messages, required_services,
                dependencies, layout, tags, created_at, updated_at, user_id)
                VALUES
                (:id, :plugin_id, :name, :display_name, :description, :icon, :category,
                :enabled, :priority, :props, :config_fields, :messages, :required_services,
                :dependencies, :layout, :tags, :created_at, :updated_at, :user_id)
                """)
                
                await db.execute(module_stmt, {
                    'id': module_id,
                    'plugin_id': plugin_id,
                    'name': module_data['name'],
                    'display_name': module_data['display_name'],
                    'description': module_data['description'],
                    'icon': module_data['icon'],
                    'category': module_data['category'],
                    'enabled': True,
                    'priority': module_data['priority'],
                    'props': json.dumps(module_data['props']),
                    'config_fields': json.dumps(module_data['config_fields']),
                    'messages': json.dumps(module_data['messages']),
                    'required_services': json.dumps(module_data['required_services']),
                    'dependencies': json.dumps(module_data['dependencies']),
                    'layout': json.dumps(module_data['layout']),
                    'tags': json.dumps(module_data['tags']),
                    'created_at': current_time,
                    'updated_at': current_time,
                    'user_id': user_id
                })
                
                modules_created.append(module_id)
            
            # Commit the transaction to persist changes
            await db.commit()
            
            logger.info(f"Created database records for plugin {plugin_id} with {len(modules_created)} modules")
            return {'success': True, 'plugin_id': plugin_id, 'modules_created': modules_created}
            
        except Exception as e:
            logger.error(f"Error creating database records: {e}")
            # Rollback on error
            await db.rollback()
            return {'success': False, 'error': str(e)}
    
    async def _delete_database_records(self, user_id: str, plugin_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Delete plugin and module records from database"""
        try:
            module_delete_stmt = text("""
            DELETE FROM module 
            WHERE plugin_id = :plugin_id AND user_id = :user_id
            """)
            
            module_result = await db.execute(module_delete_stmt, {
                'plugin_id': plugin_id,
                'user_id': user_id
            })
            
            deleted_modules = module_result.rowcount
            
            plugin_delete_stmt = text("""
            DELETE FROM plugin 
            WHERE id = :plugin_id AND user_id = :user_id
            """)
            
            plugin_result = await db.execute(plugin_delete_stmt, {
                'plugin_id': plugin_id,
                'user_id': user_id
            })
            
            if plugin_result.rowcount == 0:
                return {'success': False, 'error': 'Plugin not found or not owned by user'}
            
            # Commit the transaction to persist changes
            await db.commit()
            
            logger.info(f"Deleted database records for plugin {plugin_id} ({deleted_modules} modules)")
            return {'success': True, 'deleted_modules': deleted_modules}
            
        except Exception as e:
            logger.error(f"Error deleting database records: {e}")
            # Rollback on error
            await db.rollback()
            return {'success': False, 'error': str(e)}
    
    async def _export_user_data(self, user_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Export user-specific data for migration during updates"""
        try:
            # Get user's plugin configuration and settings
            user_data = {
                'shared_plugin_path': self.shared_path,
                'user_id': user_id,
                'plugin_slug': self.plugin_slug,
                'version': self.version,
                'user_config': {},
                'module_configs': {}
            }
            
            # Export user-specific plugin configuration
            from sqlalchemy import text
            plugin_query = text("""
            SELECT config_fields FROM plugin
            WHERE user_id = :user_id AND plugin_slug = :plugin_slug
            """)
            
            result = await db.execute(plugin_query, {
                'user_id': user_id,
                'plugin_slug': self.plugin_data['plugin_slug']
            })
            
            plugin_row = result.fetchone()
            if plugin_row and plugin_row.config_fields:
                try:
                    import json
                    user_data['user_config'] = json.loads(plugin_row.config_fields)
                except (json.JSONDecodeError, TypeError):
                    user_data['user_config'] = {}
            
            # Export module-specific configurations
            module_query = text("""
            SELECT name, config_fields FROM module
            WHERE plugin_id = :plugin_id AND user_id = :user_id
            """)
            
            plugin_id = f"{user_id}_{self.plugin_data['plugin_slug']}"
            result = await db.execute(module_query, {
                'plugin_id': plugin_id,
                'user_id': user_id
            })
            
            modules = result.fetchall()
            for module in modules:
                if module.config_fields:
                    try:
                        import json
                        user_data['module_configs'][module.name] = json.loads(module.config_fields)
                    except (json.JSONDecodeError, TypeError):
                        user_data['module_configs'][module.name] = {}
            
            logger.info(f"NetworkEyes: Exported user data for {user_id} during update")
            return user_data
            
        except Exception as e:
            logger.error(f"NetworkEyes: Error exporting user data for {user_id}: {e}")
            # Return minimal data to allow update to continue
            return {
                'shared_plugin_path': self.shared_path,
                'user_id': user_id,
                'plugin_slug': self.plugin_slug,
                'version': self.version,
                'user_config': {},
                'module_configs': {}
            }
    
    async def _import_user_data(self, user_id: str, db: AsyncSession, user_data: Dict[str, Any]):
        """Import user-specific data after migration during updates"""
        try:
            # Import user plugin configuration
            if user_data.get('user_config'):
                from sqlalchemy import text
                import json
                
                plugin_id = f"{user_id}_{self.plugin_data['plugin_slug']}"
                update_plugin_query = text("""
                UPDATE plugin SET config_fields = :config_fields
                WHERE id = :plugin_id AND user_id = :user_id
                """)
                
                await db.execute(update_plugin_query, {
                    'config_fields': json.dumps(user_data['user_config']),
                    'plugin_id': plugin_id,
                    'user_id': user_id
                })
            
            # Import module configurations
            if user_data.get('module_configs'):
                from sqlalchemy import text
                import json
                
                for module_name, module_config in user_data['module_configs'].items():
                    module_id = f"{user_id}_{self.plugin_data['plugin_slug']}_{module_name}"
                    update_module_query = text("""
                    UPDATE module SET config_fields = :config_fields
                    WHERE id = :module_id AND user_id = :user_id
                    """)
                    
                    await db.execute(update_module_query, {
                        'config_fields': json.dumps(module_config),
                        'module_id': module_id,
                        'user_id': user_id
                    })
            
            logger.info(f"NetworkEyes: Imported user data for {user_id} after update")
            
        except Exception as e:
            logger.error(f"NetworkEyes: Error importing user data for {user_id}: {e}")
            # Don't fail the update if data import fails
            pass
    
    def get_plugin_info(self) -> Dict[str, Any]:
        """Get basic plugin information"""
        return {
            'name': self.plugin_data['name'],
            'version': self.plugin_data['version'],
            'description': self.plugin_data['description'],
            'author': self.plugin_data['author'],
            'plugin_slug': self.plugin_data['plugin_slug'],
            'type': self.plugin_data['type'],
            'category': self.plugin_data['category']
        }
    
    # Compatibility property for remote installer
    @property
    def PLUGIN_DATA(self) -> Dict[str, Any]:
        """Compatibility property for remote installer"""
        return self.plugin_data
    
    # Compatibility methods for old interface (for testing)
    async def install_plugin(self, user_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Install NetworkEyes plugin for specific user (compatibility method)"""
        try:
            # For testing, we'll use a mock shared path
            shared_path = self.shared_path
            shared_path.mkdir(parents=True, exist_ok=True)
            
            # Copy files to shared path for testing
            copy_result = await self._copy_plugin_files_impl(user_id, shared_path)
            if not copy_result['success']:
                return copy_result
            
            # Use the new architecture method
            result = await self.install_for_user(user_id, db, shared_path)
            return result
            
        except Exception as e:
            logger.error(f"Plugin installation failed for user {user_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def delete_plugin(self, user_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Delete NetworkEyes plugin for user (compatibility method)"""
        try:
            # Use the new architecture method
            result = await self.uninstall_for_user(user_id, db)
            return result
            
        except Exception as e:
            logger.error(f"Plugin deletion failed for user {user_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_plugin_status(self, user_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Get current status of NetworkEyes plugin installation (compatibility method)"""
        try:
            existing_check = await self._check_existing_plugin(user_id, db)
            if not existing_check['exists']:
                return {'exists': False, 'status': 'not_installed'}
            
            plugin_id = existing_check['plugin_id']
            
            # Check if user is in active users
            is_active = user_id in self.active_users
            
            return {
                'exists': True,
                'status': 'healthy' if is_active else 'inactive',
                'plugin_id': plugin_id,
                'plugin_info': existing_check['plugin_info'],
                'files_exist': True,  # Assume files exist in shared storage
                'plugin_directory': str(self.shared_path)
            }
            
        except Exception as e:
            logger.error(f"Error checking plugin status for user {user_id}: {e}")
            return {'exists': False, 'status': 'error', 'error': str(e)}
    
    async def update_plugin(self, user_id: str, db: AsyncSession, new_version_manager: 'NetworkEyesLifecycleManager') -> Dict[str, Any]:
        """Update NetworkEyes plugin for user (compatibility method)"""
        try:
            # Use the new architecture method
            result = await self.update_for_user(user_id, db, new_version_manager)
            return result
            
        except Exception as e:
            logger.error(f"Plugin update failed for user {user_id}: {e}")
            return {'success': False, 'error': str(e)}


# Compatibility functions for direct script usage
async def install_plugin(user_id: str, db: AsyncSession, plugins_base_dir: str = None) -> Dict[str, Any]:
    """Install NetworkEyes plugin for specific user"""
    manager = NetworkEyesLifecycleManager(plugins_base_dir)
    return await manager.install_plugin(user_id, db)

async def delete_plugin(user_id: str, db: AsyncSession, plugins_base_dir: str = None) -> Dict[str, Any]:
    """Delete NetworkEyes plugin for user"""
    manager = NetworkEyesLifecycleManager(plugins_base_dir)
    return await manager.delete_plugin(user_id, db)

async def get_plugin_status(user_id: str, db: AsyncSession, plugins_base_dir: str = None) -> Dict[str, Any]:
    """Get current status of NetworkEyes plugin installation"""
    manager = NetworkEyesLifecycleManager(plugins_base_dir)
    return await manager.get_plugin_status(user_id, db)

async def update_plugin(user_id: str, db: AsyncSession, new_version_manager: 'NetworkEyesLifecycleManager', plugins_base_dir: str = None) -> Dict[str, Any]:
    """Update NetworkEyes plugin for user"""
    current_manager = NetworkEyesLifecycleManager(plugins_base_dir)
    return await current_manager.update_plugin(user_id, db, new_version_manager)


if __name__ == "__main__":
    import sys
    import asyncio
    
    async def main():
        if len(sys.argv) < 3:
            print("Usage: python lifecycle_manager.py <operation> <user_id>")
            print("Operations: install, delete, status")
            sys.exit(1)
        
        operation = sys.argv[1]
        user_id = sys.argv[2]
        
        manager = NetworkEyesLifecycleManager()
        
        print(f"NetworkEyes Plugin Lifecycle Manager (New Architecture)")
        print(f"Operation: {operation}")
        print(f"User ID: {user_id}")
        print(f"Plugin: {manager.plugin_data['name']} v{manager.plugin_data['version']}")
        print(f"Plugin Slug: {manager.plugin_data['plugin_slug']}")
        print("\nNote: This script requires database connection for actual operations.")
        print("Use the new Plugin Lifecycle Service for full functionality.")
    
    asyncio.run(main())