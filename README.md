# Complete Deploy Tool

A comprehensive deployment tool that automates the complete deployment pipeline including code push, Docker builds, and container registry deployment.

## Features

- 🚀 **One-Click Deployment**: Complete deployment pipeline with a single click
- 📦 **Git Integration**: Automatic code push to GitHub repositories
- 🐳 **Docker Support**: Automatic Docker image building and pushing
- 📊 **Real-time Logs**: Live progress tracking during deployment
- 🔧 **Multi-Project Support**: Deploy multiple projects with different configurations

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application**:
   ```bash
   python app.py
   ```

3. **Access the Web Interface**:
   Open your browser and go to `http://localhost:5000`

## Configuration

The tool uses a configuration file to store:
- GitHub credentials
- Selected projects and repositories
- Deployment preferences

## Deployment Pipeline

1. **Project Selection**: Choose the project to deploy
2. **Git Operations**: Commit and push code changes
3. **Docker Build**: Build Docker image if Dockerfile exists
4. **Registry Push**: Push to GitHub Container Registry

## License

MIT License 