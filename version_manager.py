import json
import os
import subprocess
import shutil
from datetime import datetime
from typing import Dict, List, Optional

class VersionManager:
    def __init__(self, project_name: str, github_username: str, github_token: str):
        self.project_name = project_name
        self.github_username = github_username
        self.github_token = github_token
        self.versions_file = 'deployment_versions.json'
        self.load_versions()
    
    def load_versions(self):
        """Load existing version history"""
        if os.path.exists(self.versions_file):
            with open(self.versions_file, 'r') as f:
                self.versions = json.load(f)
        else:
            self.versions = {
                'project': self.project_name,
                'deployments': [],
                'current_version': None
            }
    
    def save_versions(self):
        """Save version history to file"""
        with open(self.versions_file, 'w') as f:
            json.dump(self.versions, f, indent=2)
    
    def create_version(self, version_type: str = 'auto') -> Dict:
        """Create a new version entry"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        version_id = f"v{timestamp}"
        
        # Get current Git commit hash
        try:
            result = subprocess.run(['git', 'rev-parse', 'HEAD'], 
                                 capture_output=True, text=True, check=True)
            commit_hash = result.stdout.strip()[:8]
        except:
            commit_hash = "unknown"
        
        # Get current branch
        try:
            result = subprocess.run(['git', 'branch', '--show-current'], 
                                 capture_output=True, text=True, check=True)
            branch = result.stdout.strip()
        except:
            branch = "main"
        
        version_info = {
            'version_id': version_id,
            'timestamp': datetime.now().isoformat(),
            'type': version_type,  # 'auto', 'manual', 'rollback'
            'commit_hash': commit_hash,
            'branch': branch,
            'github_repo': f"{self.github_username}/{self.project_name.lower().replace('_', '-')}",
            'docker_image': f"ghcr.io/{self.github_username}/{self.project_name.lower().replace('_', '-')}:{version_id}",
            'status': 'deploying',
            'rollback_available': False,
            'notes': ''
        }
        
        self.versions['deployments'].append(version_info)
        self.versions['current_version'] = version_id
        self.save_versions()
        
        return version_info
    
    def update_version_status(self, version_id: str, status: str, notes: str = ''):
        """Update version status"""
        for version in self.versions['deployments']:
            if version['version_id'] == version_id:
                version['status'] = status
                if notes:
                    version['notes'] = notes
                break
        self.save_versions()
    
    def mark_rollback_available(self, version_id: str):
        """Mark a version as available for rollback"""
        for version in self.versions['deployments']:
            if version['version_id'] == version_id:
                version['rollback_available'] = True
                break
        self.save_versions()
    
    def get_available_rollbacks(self) -> List[Dict]:
        """Get list of versions available for rollback"""
        return [v for v in self.versions['deployments'] 
                if v['rollback_available'] and v['status'] == 'success']
    
    def rollback_to_version(self, target_version_id: str) -> Dict:
        """Rollback to a specific version"""
        # Create rollback version
        rollback_version = self.create_version('rollback')
        rollback_version['rollback_to'] = target_version_id
        
        # Find target version
        target_version = None
        for version in self.versions['deployments']:
            if version['version_id'] == target_version_id:
                target_version = version
                break
        
        if not target_version:
            raise ValueError(f"Target version {target_version_id} not found")
        
        rollback_info = {
            'version_id': rollback_version['version_id'],
            'target_version': target_version,
            'rollback_commit': target_version['commit_hash'],
            'rollback_branch': target_version['branch'],
            'docker_image': target_version['docker_image']
        }
        
        return rollback_info
    
    def get_version_history(self, limit: int = 10) -> List[Dict]:
        """Get recent version history"""
        return self.versions['deployments'][-limit:]
    
    def get_current_version(self) -> Optional[Dict]:
        """Get current version info"""
        if self.versions['current_version']:
            for version in self.versions['deployments']:
                if version['version_id'] == self.versions['current_version']:
                    return version
        return None
    
    def cleanup_old_versions(self, keep_count: int = 5):
        """Clean up old versions, keeping only the most recent ones"""
        if len(self.versions['deployments']) > keep_count:
            # Keep the most recent versions
            self.versions['deployments'] = self.versions['deployments'][-keep_count:]
            self.save_versions() 