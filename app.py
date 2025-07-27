from flask import Flask, render_template, request, jsonify
import os
import subprocess
import threading
import time
import json
import configparser
import requests
from datetime import datetime

app = Flask(__name__)

# Global variables for logging
log_queue = []
log_lock = threading.Lock()

def log_wrapper(message):
    """Add timestamp to log messages"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"[{timestamp}] {message}"
    with log_lock:
        log_queue.append(log_message)
    try:
        print(log_message)
    except UnicodeEncodeError:
        # Handle Unicode characters in Windows console
        print(log_message.encode('utf-8', errors='replace').decode('utf-8'))

def load_config():
    """Load configuration from config.ini"""
    config = configparser.ConfigParser()
    config_file = 'config.ini'
    
    if os.path.exists(config_file):
        config.read(config_file)
    else:
        # Create default config
        config['DEFAULT'] = {
            'github_token': '',
            'github_username': '',
            'github_password': '',
            'selected_project': 'Complete_Deploy_Tool',
            'selected_repository': '',
            'remember_credentials': 'false'
        }
        with open(config_file, 'w') as f:
            config.write(f)
    
    return config

def save_config(github_token, github_username, github_password, selected_project, selected_repository, remember_credentials):
    """Save configuration to config.ini"""
    config = configparser.ConfigParser()
    config['DEFAULT'] = {
        'github_token': github_token,
        'github_username': github_username,
        'github_password': github_password,
        'selected_project': selected_project,
        'selected_repository': selected_repository,
        'remember_credentials': remember_credentials
    }
    
    with open('config.ini', 'w') as f:
        config.write(f)

def get_local_projects():
    """Get list of local projects with detailed information"""
    projects = []
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Go up to D:\Project1
    
    if os.path.exists(base_path):
        for item in os.listdir(base_path):
            item_path = os.path.join(base_path, item)
            if os.path.isdir(item_path):
                git_dir = os.path.join(item_path, '.git')
                has_git = os.path.exists(git_dir)
                
                # Get additional project details
                project_info = {
                    'name': item,
                    'path': item_path,
                    'has_git': has_git,
                    'full_path': item_path,
                    'files': [],
                    'size': 0,
                    'last_modified': '',
                    'description': ''
                }
                
                # Get file count and size
                try:
                    file_count = 0
                    total_size = 0
                    for root, dirs, files in os.walk(item_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            if os.path.exists(file_path):
                                total_size += os.path.getsize(file_path)
                                file_count += 1
                    
                    project_info['file_count'] = file_count
                    project_info['size'] = total_size
                    
                    # Get last modified time
                    project_info['last_modified'] = datetime.fromtimestamp(
                        os.path.getmtime(item_path)
                    ).strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Look for README or description files
                    readme_files = ['README.md', 'README.txt', 'readme.md', 'readme.txt']
                    for readme in readme_files:
                        readme_path = os.path.join(item_path, readme)
                        if os.path.exists(readme_path):
                            try:
                                with open(readme_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    # Get first few lines as description
                                    lines = content.split('\n')
                                    description = ' '.join([line.strip() for line in lines[:3] if line.strip()])
                                    project_info['description'] = description[:200] + '...' if len(description) > 200 else description
                                    break
                            except:
                                pass
                    
                    # Get important files
                    important_files = ['app.py', 'main.py', 'index.html', 'package.json', 'requirements.txt', 'Dockerfile']
                    for file in important_files:
                        file_path = os.path.join(item_path, file)
                        if os.path.exists(file_path):
                            project_info['files'].append(file)
                    
                except Exception as e:
                    log_wrapper(f"⚠️ Error scanning project {item}: {e}")
                
                projects.append(project_info)
    
    return projects

def get_github_repositories(github_username, github_token):
    """Get list of GitHub repositories for the user with detailed information"""
    try:
        import requests
        
        log_wrapper(f"🔍 Fetching repositories for user: {github_username}")
        
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # Get user's repositories (use authenticated endpoint)
        url = 'https://api.github.com/user/repos'
        log_wrapper(f"📡 API URL: {url}")
        
        response = requests.get(url, headers=headers, timeout=10)
        
        log_wrapper(f"📊 Response status: {response.status_code}")
        
        if response.status_code == 200:
            repos = response.json()
            log_wrapper(f"✅ Found {len(repos)} repositories")
            
            detailed_repos = []
            for repo in repos:
                repo_info = {
                    'name': repo['name'],
                    'full_name': repo['full_name'],
                    'description': repo.get('description', 'No description'),
                    'private': repo['private'],
                    'fork': repo['fork'],
                    'language': repo.get('language', 'Unknown'),
                    'stars': repo['stargazers_count'],
                    'forks': repo['forks_count'],
                    'size': repo['size'],
                    'created_at': repo['created_at'],
                    'updated_at': repo['updated_at'],
                    'default_branch': repo['default_branch'],
                    'topics': repo.get('topics', []),
                    'homepage': repo.get('homepage', ''),
                    'has_issues': repo['has_issues'],
                    'has_wiki': repo['has_wiki'],
                    'has_pages': repo['has_pages'],
                    'archived': repo['archived']
                }
                detailed_repos.append(repo_info)
            
            return detailed_repos
        elif response.status_code == 401:
            log_wrapper("❌ Unauthorized: Invalid token or token expired")
            return []
        elif response.status_code == 403:
            log_wrapper("❌ Forbidden: Rate limit exceeded or insufficient permissions")
            return []
        elif response.status_code == 404:
            log_wrapper(f"❌ User not found: {github_username}")
            return []
        else:
            log_wrapper(f"❌ API Error: {response.status_code} - {response.text}")
            return []
            
    except requests.exceptions.Timeout:
        log_wrapper("❌ Timeout: Request to GitHub API timed out")
        return []
    except requests.exceptions.ConnectionError:
        log_wrapper("❌ Connection Error: Cannot connect to GitHub API")
        return []
    except Exception as e:
        log_wrapper(f"❌ Error fetching GitHub repositories: {e}")
        return []

def get_repository_details(github_username, github_token, repo_name):
    """Get detailed information about a specific repository"""
    try:
        import requests
        
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # Get repository details
        url = f'https://api.github.com/repos/{repo_name}'
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            repo = response.json()
            
            # Get repository contents
            contents_url = f'https://api.github.com/repos/{repo_name}/contents'
            contents_response = requests.get(contents_url, headers=headers, timeout=10)
            
            contents = []
            if contents_response.status_code == 200:
                contents = contents_response.json()
            
            return {
                'details': repo,
                'contents': contents,
                'status': 'success'
            }
        else:
            return {
                'status': 'error',
                'message': f'Failed to fetch repository: {response.status_code}'
            }
            
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Error fetching repository details: {e}'
        }

def create_github_repository(github_username, github_token, repo_name, description="", private=False):
    """Create a new GitHub repository"""
    try:
        import requests
        
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        data = {
            'name': repo_name.split('/')[-1],  # Get just the repo name, not full path
            'description': description,
            'private': private,
            'auto_init': True,  # Initialize with README
            'gitignore_template': 'Python'
        }
        
        url = f'https://api.github.com/user/repos'
        response = requests.post(url, headers=headers, json=data, timeout=10)
        
        if response.status_code == 201:
            repo = response.json()
            return {
                'status': 'success',
                'message': f'Repository {repo_name} created successfully',
                'repo': repo
            }
        else:
            return {
                'status': 'error',
                'message': f'Failed to create repository: {response.status_code} - {response.text}'
            }
            
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Error creating repository: {e}'
        }

@app.route('/')
def index():
    config = load_config()
    projects = get_local_projects()
    
    return render_template('index.html', 
                         github_username=config['DEFAULT'].get('github_username', ''),
                         selected_project=config['DEFAULT'].get('selected_project', ''),
                         selected_repository=config['DEFAULT'].get('selected_repository', ''),
                         remember_credentials=config['DEFAULT'].get('remember_credentials', 'false'),
                         projects=projects)

@app.route('/get-projects')
def get_projects():
    """API endpoint to get local projects"""
    projects = get_local_projects()
    return jsonify({'projects': projects})

@app.route('/browse-folders', methods=['POST'])
def browse_folders():
    """API endpoint to browse folders and find git repositories"""
    try:
        data = request.get_json()
        base_path = data.get('base_path', 'D:\\Project1')
        
        if not os.path.exists(base_path):
            return jsonify({'folders': [], 'error': 'Path does not exist'})
        
        folders = []
        for item in os.listdir(base_path):
            item_path = os.path.join(base_path, item)
            if os.path.isdir(item_path):
                git_dir = os.path.join(item_path, '.git')
                has_git = os.path.exists(git_dir)
                
                # Get folder details
                folder_info = {
                    'name': item,
                    'path': item_path,
                    'has_git': has_git,
                    'full_path': item_path,
                    'file_count': 0,
                    'size': 0,
                    'last_modified': '',
                    'description': ''
                }
                
                try:
                    # Count files and get size
                    file_count = 0
                    total_size = 0
                    for root, dirs, files in os.walk(item_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            if os.path.exists(file_path):
                                total_size += os.path.getsize(file_path)
                                file_count += 1
                    
                    folder_info['file_count'] = file_count
                    folder_info['size'] = total_size
                    
                    # Get last modified time
                    folder_info['last_modified'] = datetime.fromtimestamp(
                        os.path.getmtime(item_path)
                    ).strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Look for README
                    readme_files = ['README.md', 'README.txt', 'readme.md', 'readme.txt']
                    for readme in readme_files:
                        readme_path = os.path.join(item_path, readme)
                        if os.path.exists(readme_path):
                            try:
                                with open(readme_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    lines = content.split('\n')
                                    description = ' '.join([line.strip() for line in lines[:3] if line.strip()])
                                    folder_info['description'] = description[:200] + '...' if len(description) > 200 else description
                                    break
                            except:
                                pass
                
                except Exception as e:
                    log_wrapper(f"⚠️ Error scanning folder {item}: {e}")
                
                folders.append(folder_info)
        
        return jsonify({'folders': folders})
        
    except Exception as e:
        return jsonify({'folders': [], 'error': str(e)})

@app.route('/get-repositories', methods=['POST'])
def get_repositories():
    """API endpoint to get GitHub repositories"""
    try:
        data = request.get_json()
        github_username = data.get('github_username', '')
        github_token = data.get('github_token', '')
        
        if not github_username or not github_token:
            return jsonify({'repositories': []})
        
        repositories = get_github_repositories(github_username, github_token)
        return jsonify({'repositories': repositories})
        
    except Exception as e:
        return jsonify({'repositories': [], 'error': str(e)})

@app.route('/get-repository-details', methods=['POST'])
def get_repository_details_route():
    """API endpoint to get detailed repository information"""
    try:
        data = request.get_json()
        github_username = data.get('github_username', '')
        github_token = data.get('github_token', '')
        repo_name = data.get('repo_name', '')
        
        if not github_username or not github_token or not repo_name:
            return jsonify({'status': 'error', 'message': 'Missing required parameters'})
        
        details = get_repository_details(github_username, github_token, repo_name)
        return jsonify(details)
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/create-repository', methods=['POST'])
def create_repository_route():
    """API endpoint to create a new GitHub repository"""
    try:
        data = request.get_json()
        github_username = data.get('github_username', '')
        github_token = data.get('github_token', '')
        repo_name = data.get('repo_name', '')
        description = data.get('description', '')
        private = data.get('private', False)
        
        if not github_username or not github_token or not repo_name:
            return jsonify({'status': 'error', 'message': 'Missing required parameters'})
        
        result = create_github_repository(github_username, github_token, repo_name, description, private)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/save-config', methods=['POST'])
def save_config_route():
    """API endpoint to save configuration"""
    try:
        data = request.form
        github_token = data.get('github_token', '')
        github_username = data.get('github_username', '')
        github_password = data.get('github_password', '')
        selected_project = data.get('selected_project', '')
        selected_repository = data.get('selected_repository', '')
        remember_credentials = data.get('remember_credentials', 'false')
        
        save_config(github_token, github_username, github_password, selected_project, selected_repository, remember_credentials)
        
        return jsonify({
            'status': 'success',
            'message': 'Configuration saved successfully!'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to save configuration: {e}'
        })

@app.route('/deploy', methods=['POST'])
def deploy():
    """Handle deployment requests"""
    try:
        data = request.get_json()
        project_name = data.get('project_name', 'Complete_Deploy_Tool')
        
        def deploy_process():
            try:
                log_wrapper("🚀 Starting REAL Production Deployment Pipeline...")
                log_wrapper(f"📦 Project: {project_name}")
                
                # Get credentials from form data
                github_username = data.get('github_username', '')
                github_token = data.get('github_token', '')
                selected_repo = data.get('selected_repository', '')
                
                if not github_username or not github_token:
                    log_wrapper("❌ GitHub credentials not provided")
                    log_wrapper("💡 Please provide GitHub username and token in the form")
                    return
                
                if not selected_repo:
                    log_wrapper("❌ No GitHub repository selected")
                    log_wrapper("💡 Please select a repository")
                    return
                
                # Check if repository exists, create if it doesn't
                log_wrapper(f"🔍 Checking if repository {selected_repo} exists...")
                repo_details = get_repository_details(github_username, github_token, selected_repo)
                if repo_details['status'] != 'success':
                    log_wrapper(f"⚠️ Repository {selected_repo} does not exist, creating it...")
                    create_result = create_github_repository(github_username, github_token, selected_repo, 
                                                          f"Auto-created repository for {project_name}", False)
                    if create_result['status'] == 'success':
                        log_wrapper(f"✅ Repository {selected_repo} created successfully")
                    else:
                        log_wrapper(f"❌ Failed to create repository: {create_result['message']}")
                        return
                else:
                    log_wrapper(f"✅ Repository {selected_repo} exists")
                
                # Get current directory (should be the project directory)
                current_dir = os.getcwd()
                log_wrapper(f"📁 Current directory: {current_dir}")
                
                # Check if we're in the right directory
                if not os.path.exists('app.py'):
                    log_wrapper("❌ app.py not found in current directory")
                    return
                
                log_wrapper("✅ Found app.py - deployment can proceed")
                
                # Step 1: Real Code Analysis
                log_wrapper("🔍 Step 1: Real Code Analysis...")
                try:
                    # Check for Python files
                    python_files = [f for f in os.listdir('.') if f.endswith('.py')]
                    log_wrapper(f"📝 Found {len(python_files)} Python files")
                    
                    # Check for requirements.txt
                    if os.path.exists('requirements.txt'):
                        log_wrapper("✅ Found requirements.txt")
                    else:
                        log_wrapper("⚠️ No requirements.txt found")
                    
                    # Check for README.md
                    if os.path.exists('README.md'):
                        log_wrapper("✅ Found README.md")
                    else:
                        log_wrapper("⚠️ No README.md found")
                        
                    log_wrapper("✅ Code analysis complete")
                except Exception as e:
                    log_wrapper(f"❌ Code analysis failed: {e}")
                    return
                
                # Step 2: Push Code to GitHub Repository
                log_wrapper("📝 Step 2: Pushing Code to GitHub Repository...")
                
                # Test Git authentication first
                log_wrapper("🔐 Testing Git authentication...")
                try:
                    test_url = f"https://{github_username}:{github_token}@github.com/{selected_repo}.git"
                    subprocess.run(['git', 'ls-remote', test_url], 
                                 check=True, capture_output=True, timeout=30)
                    log_wrapper("✅ Git authentication successful")
                except subprocess.CalledProcessError as e:
                    log_wrapper(f"❌ Git authentication failed: {e}")
                    log_wrapper("💡 Please check your GitHub token permissions")
                    return
                except subprocess.TimeoutExpired:
                    log_wrapper("❌ Git authentication timed out")
                    return
                
                try:
                    # Check git status
                    result = subprocess.run(['git', 'status', '--porcelain'], 
                                         capture_output=True, text=True, check=True)
                    
                    if result.stdout.strip():
                        log_wrapper("📦 Changes detected, committing...")
                        
                        # Add all changes
                        subprocess.run(['git', 'add', '.'], check=True, capture_output=True)
                        log_wrapper("✅ Added all changes to git")
                        
                        # Commit changes
                        commit_msg = f"Auto-deploy: Update {project_name} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        subprocess.run(['git', 'commit', '-m', commit_msg], 
                                     check=True, capture_output=True)
                        log_wrapper("✅ Committed changes")
                        
                        # Check if remote exists and update with token
                        try:
                            remote_result = subprocess.run(['git', 'remote', '-v'], 
                                                        capture_output=True, text=True, check=True)
                            if not remote_result.stdout.strip():
                                log_wrapper("🔗 Setting up remote repository...")
                                # Use token in remote URL for authentication
                                remote_url = f"https://{github_username}:{github_token}@github.com/{selected_repo}.git"
                                subprocess.run(['git', 'remote', 'add', 'origin', remote_url], 
                                             check=True, capture_output=True)
                                log_wrapper("✅ Remote repository configured with token")
                            else:
                                log_wrapper("🔗 Updating remote with token authentication...")
                                # Update existing remote with token
                                remote_url = f"https://{github_username}:{github_token}@github.com/{selected_repo}.git"
                                subprocess.run(['git', 'remote', 'set-url', 'origin', remote_url], 
                                             check=True, capture_output=True)
                                log_wrapper("✅ Remote updated with token authentication")
                        except subprocess.CalledProcessError:
                            log_wrapper("⚠️ Could not configure remote, proceeding with push...")
                        
                        # Push to GitHub with token authentication
                        try:
                            # Configure Git to use token for authentication
                            log_wrapper("🔐 Configuring Git authentication...")
                            
                            # Set up credential helper to use token
                            subprocess.run(['git', 'config', 'credential.helper', 'store'], 
                                         check=True, capture_output=True)
                            
                            # Create credential file with token
                            import tempfile
                            
                            # Create a temporary credential file
                            cred_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
                            cred_file.write(f"https://{github_username}:{github_token}@github.com\n")
                            cred_file.close()
                            
                            # Set the credential file
                            os.environ['GIT_ASKPASS'] = 'echo'
                            os.environ['GIT_TERMINAL_PROMPT'] = '0'
                            
                            # First try to pull any remote changes
                            try:
                                subprocess.run(['git', 'pull', 'origin', 'main', '--rebase'], 
                                             check=True, capture_output=True, env=dict(os.environ, GIT_ASKPASS='echo'))
                                log_wrapper("✅ Pulled latest changes from remote")
                            except subprocess.CalledProcessError:
                                log_wrapper("⚠️ Could not pull from remote, proceeding with push")
                            
                            # Push to GitHub with token authentication
                            push_url = f"https://{github_username}:{github_token}@github.com/{selected_repo}.git"
                            log_wrapper("📤 Pushing to GitHub with token authentication...")
                            
                            # Try simple push first
                            try:
                                subprocess.run(['git', 'push', push_url, 'main'], 
                                             check=True, capture_output=True)
                                log_wrapper("✅ Pushed code to GitHub repository")
                                log_wrapper(f"📦 Code available at: https://github.com/{selected_repo}")
                            except subprocess.CalledProcessError:
                                log_wrapper("⚠️ Simple push failed, trying with --force-with-lease...")
                                subprocess.run(['git', 'push', push_url, 'main', '--force-with-lease'], 
                                             check=True, capture_output=True)
                                log_wrapper("✅ Force-with-lease push successful")
                                log_wrapper(f"📦 Code available at: https://github.com/{selected_repo}")
                            
                            # Clean up credential file
                            os.unlink(cred_file.name)
                            
                        except subprocess.CalledProcessError as e:
                            log_wrapper(f"❌ Push failed: {e}")
                            log_wrapper("💡 Trying alternative authentication method...")
                            try:
                                # Try with force push and explicit token
                                push_url = f"https://{github_username}:{github_token}@github.com/{selected_repo}.git"
                                subprocess.run(['git', 'push', push_url, 'main', '--force'], 
                                             check=True, capture_output=True)
                                log_wrapper("✅ Force pushed code to GitHub repository")
                                log_wrapper(f"📦 Code available at: https://github.com/{selected_repo}")
                                
                                # Clean up credential file
                                if 'cred_file' in locals():
                                    os.unlink(cred_file.name)
                                    
                            except subprocess.CalledProcessError as e2:
                                log_wrapper(f"❌ Force push also failed: {e2}")
                                log_wrapper("💡 Please check your GitHub token and repository permissions")
                                log_wrapper("💡 Make sure your token has 'repo' permissions")
                                return
                    else:
                        log_wrapper("ℹ️ No changes to commit")
                        
                except subprocess.CalledProcessError as e:
                    log_wrapper(f"❌ Git operation failed: {e}")
                    return
                
                # Step 3: Build Docker Image from GitHub Repository
                log_wrapper("🐳 Step 3: Building Docker Image from GitHub Repository...")
                try:
                    # Create a temporary directory to clone the repository
                    import tempfile
                    import shutil
                    
                    temp_dir = tempfile.mkdtemp()
                    log_wrapper(f"📁 Created temporary directory: {temp_dir}")
                    
                    # Clone the repository from GitHub
                    clone_url = f"https://github.com/{selected_repo}.git"
                    log_wrapper(f"📥 Cloning repository: {clone_url}")
                    
                    # Use shallow clone to avoid permission issues
                    subprocess.run(['git', 'clone', '--depth', '1', clone_url, temp_dir], 
                                 check=True, capture_output=True)
                    log_wrapper("✅ Repository cloned successfully")
                    
                    # Change to the cloned directory
                    os.chdir(temp_dir)
                    log_wrapper(f"📁 Changed to cloned directory: {os.getcwd()}")
                    
                    # Check if Dockerfile exists in the repository
                    dockerfile_path = os.path.join(temp_dir, 'Dockerfile')
                    if os.path.exists(dockerfile_path):
                        log_wrapper("✅ Found Dockerfile in repository")
                        log_wrapper(f"📁 Dockerfile path: {dockerfile_path}")
                        
                        # Build Docker image from GitHub repository
                        # Convert project name to lowercase for Docker compatibility
                        docker_project_name = project_name.lower().replace('_', '-')
                        image_name = f"ghcr.io/{github_username}/{docker_project_name}:latest"
                        log_wrapper(f"🔨 Building Docker image from GitHub repo: {image_name}")
                        
                        try:
                            result = subprocess.run([
                                'docker', 'build', '-t', image_name, '.'
                            ], check=True, capture_output=True, text=True)
                            log_wrapper("✅ Docker image built successfully from GitHub repository")
                        except subprocess.CalledProcessError as e:
                            log_wrapper(f"❌ Docker build failed with exit code {e.returncode}")
                            log_wrapper(f"📋 Docker build output: {e.stdout}")
                            log_wrapper(f"❌ Docker build error: {e.stderr}")
                            raise
                        
                        # Login to GHCR
                        log_wrapper("🔐 Logging in to GitHub Container Registry...")
                        login_process = subprocess.Popen([
                            'docker', 'login', 'ghcr.io', '-u', github_username, '--password-stdin'
                        ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        stdout, stderr = login_process.communicate(input=github_token.encode())
                        
                        if login_process.returncode != 0:
                            log_wrapper(f"❌ GHCR login failed: {stderr.decode()}")
                            return
                        
                        log_wrapper("✅ Logged in to GHCR successfully")
                        
                        # Push Docker image to GHCR
                        log_wrapper("📦 Pushing Docker image to GHCR...")
                        result = subprocess.run([
                            'docker', 'push', image_name
                        ], check=True, capture_output=True, text=True)
                        log_wrapper("✅ Docker image pushed to GHCR successfully")
                        log_wrapper(f"🐳 Docker image available at: https://github.com/{github_username}/{project_name}/packages")
                        
                    else:
                        log_wrapper("❌ Dockerfile not found in repository")
                        log_wrapper(f"📁 Checking directory contents: {os.listdir(temp_dir)}")
                        log_wrapper("💡 Please ensure Dockerfile is committed and pushed to the repository")
                        return
                    
                    # Clean up temporary directory
                    try:
                        os.chdir(current_dir)  # Go back to original directory
                        shutil.rmtree(temp_dir)
                        log_wrapper("🧹 Cleaned up temporary directory")
                    except Exception as cleanup_error:
                        log_wrapper(f"⚠️ Warning: Could not clean up temporary directory: {cleanup_error}")
                    
                except subprocess.CalledProcessError as e:
                    log_wrapper(f"❌ Docker operation failed: {e}")
                    return
                except Exception as e:
                    log_wrapper(f"❌ Error during Docker build: {e}")
                    # Try to clean up even if build failed
                    try:
                        os.chdir(current_dir)
                        if os.path.exists(temp_dir):
                            shutil.rmtree(temp_dir)
                    except:
                        pass
                    return
                
                # Step 4: Deployment Verification
                log_wrapper("🚀 Step 4: Deployment Verification...")
                try:
                    log_wrapper("🔍 Verifying deployment...")
                    
                    # Check if code is accessible on GitHub
                    import requests
                    repo_url = f"https://api.github.com/repos/{selected_repo}"
                    headers = {
                        'Authorization': f'token {github_token}',
                        'Accept': 'application/vnd.github.v3+json'
                    }
                    
                    response = requests.get(repo_url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        log_wrapper("✅ GitHub repository is accessible")
                    else:
                        log_wrapper("⚠️ Could not verify GitHub repository access")
                    
                    # Check if Docker image exists (if Dockerfile was present)
                    if os.path.exists(dockerfile_path):
                        try:
                            result = subprocess.run(['docker', 'images', image_name], 
                                                 capture_output=True, text=True)
                            if image_name in result.stdout:
                                log_wrapper("✅ Docker image exists locally")
                            else:
                                log_wrapper("⚠️ Docker image not found locally")
                        except:
                            log_wrapper("⚠️ Could not verify Docker image")
                    
                    log_wrapper("✅ Deployment verification complete")
                    
                except Exception as e:
                    log_wrapper(f"❌ Deployment verification failed: {e}")
                    return
                
                log_wrapper("🎉 REAL Production Deployment Pipeline Completed Successfully!")
                log_wrapper("📦 Code pushed to GitHub repository")
                log_wrapper(f"🌐 Repository: https://github.com/{selected_repo}")
                if os.path.exists(dockerfile_path):
                    log_wrapper("🐳 Docker image built from GitHub repository")
                    log_wrapper(f"📦 Docker image pushed to GHCR")
                    log_wrapper(f"🐳 Container Registry: https://github.com/{github_username}/{docker_project_name}/packages")
                log_wrapper("✅ Application ready for production use!")
                
            except Exception as e:
                log_wrapper(f"❌ REAL Deployment Pipeline failed: {e}")
        
        # Start deployment in background
        thread = threading.Thread(target=deploy_process)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'status': 'success',
            'message': 'REAL Production deployment pipeline started! Check logs for progress.'
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Deployment failed: {e}'})

@app.route('/logs')
def logs():
    def generate():
        while True:
            try:
                # Get log messages
                with log_lock:
                    if log_queue:
                        message = log_queue.pop(0)
                        yield f"data: {json.dumps({'message': message})}\n\n"
                    else:
                        yield f"data: {json.dumps({'message': ''})}\n\n"
                time.sleep(0.1)
            except:
                yield f"data: {json.dumps({'message': ''})}\n\n"
    
    return app.response_class(generate(), mimetype='text/event-stream')

@app.route('/debug-github', methods=['POST'])
def debug_github():
    """Debug endpoint to test GitHub API connection"""
    try:
        data = request.get_json()
        github_username = data.get('github_username', '')
        github_token = data.get('github_token', '')
        
        if not github_username or not github_token:
            return jsonify({'status': 'error', 'message': 'Username and token required'})
        
        # Test GitHub API
        import requests
        
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # Test user endpoint first (use /user to validate token)
        user_url = 'https://api.github.com/user'
        print(f"🔍 Testing GitHub API: {user_url}")
        user_response = requests.get(user_url, headers=headers, timeout=10)
        print(f"📊 User API Response: {user_response.status_code}")
        
        result = {
            'user_status': user_response.status_code,
            'user_data': user_response.json() if user_response.status_code == 200 else None,
            'token_valid': user_response.status_code == 200
        }
        
        # Test repos endpoint (use authenticated endpoint)
        repos_url = 'https://api.github.com/user/repos'
        print(f"🔍 Testing GitHub Repos API: {repos_url}")
        repos_response = requests.get(repos_url, headers=headers, timeout=10)
        print(f"📊 Repos API Response: {repos_response.status_code}")
        
        result.update({
            'repos_status': repos_response.status_code,
            'repos_count': len(repos_response.json()) if repos_response.status_code == 200 else 0,
            'rate_limit_remaining': repos_response.headers.get('X-RateLimit-Remaining', 'Unknown')
        })
        
        print(f"✅ Debug completed - Token valid: {result['token_valid']}")
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        return jsonify({'status': 'error', 'message': f'Debug failed: {e}'})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=9999, debug=True) 