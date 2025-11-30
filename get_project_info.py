#!/usr/bin/env python3
"""
Script to extract project information for README generation.
Run this in your project root directory.
"""

import os
import json
import ast
import subprocess
from pathlib import Path
from typing import Dict, List, Any

try:
    import toml
except ImportError:
    print("Installing toml package...")
    subprocess.run(["pip", "install", "toml"], check=True)
    import toml


def read_pyproject_toml() -> Dict[str, Any]:
    """Extract information from pyproject.toml"""
    try:
        with open("pyproject.toml", "r") as f:
            data = toml.load(f)
        return data
    except FileNotFoundError:
        return {}


def get_project_structure(max_depth=3) -> List[str]:
    """Get project directory structure"""
    structure = []
    ignore_dirs = {'.git', '__pycache__', '.venv', 'venv', 'node_modules', 
                   '.pytest_cache', '.mypy_cache', 'dist', 'build', '.egg-info'}
    
    def should_ignore(path: Path) -> bool:
        parts = path.parts
        return any(ignored in parts for ignored in ignore_dirs)
    
    for root, dirs, files in os.walk('.'):
        root_path = Path(root)
        
        if should_ignore(root_path):
            continue
            
        level = len(root_path.parts) - 1
        if level > max_depth:
            continue
        
        indent = '  ' * level
        folder_name = os.path.basename(root)
        if folder_name == '.':
            folder_name = 'Project Root'
        structure.append(f"{indent}{folder_name}/")
        
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        
        subindent = '  ' * (level + 1)
        for file in sorted(files):
            if not file.startswith('.'):
                structure.append(f"{subindent}{file}")
    
    return structure


def analyze_python_files() -> Dict[str, Any]:
    """Analyze Python files to extract modules, classes, and functions"""
    analysis = {}
    
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', '.venv', 'venv'}]
        
        for file in files:
            if file.endswith('.py'):
                filepath = Path(root) / file
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    tree = ast.parse(content)
                    
                    module_info = {
                        'path': str(filepath),
                        'docstring': ast.get_docstring(tree),
                        'classes': [],
                        'functions': []
                    }
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            module_info['classes'].append({
                                'name': node.name,
                                'docstring': ast.get_docstring(node),
                                'methods': [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
                            })
                        elif isinstance(node, ast.FunctionDef) and node.col_offset == 0:
                            module_info['functions'].append({
                                'name': node.name,
                                'docstring': ast.get_docstring(node)
                            })
                    
                    if module_info['classes'] or module_info['functions'] or module_info['docstring']:
                        analysis[str(filepath)] = module_info
                        
                except Exception as e:
                    print(f"Error analyzing {filepath}: {e}")
    
    return analysis


def get_git_info() -> Dict[str, str]:
    """Get git repository information"""
    info = {}
    try:
        info['remote_url'] = subprocess.check_output(
            ['git', 'config', '--get', 'remote.origin.url'],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        
        info['branch'] = subprocess.check_output(
            ['git', 'branch', '--show-current'],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        
        info['last_commit'] = subprocess.check_output(
            ['git', 'log', '-1', '--pretty=%B'],
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except:
        pass
    
    return info


def check_config_files() -> List[str]:
    """Check for common configuration files"""
    config_files = [
        'pyproject.toml', 'setup.py', 'requirements.txt', 
        'README.md', 'LICENSE', '.gitignore',
        'Dockerfile', 'docker-compose.yml',
        '.env.example', 'Makefile',
        'pytest.ini', 'setup.cfg', 'tox.ini'
    ]
    
    return [f for f in config_files if os.path.exists(f)]


def main():
    """Main function to gather all project information"""
    print("Extracting project information...\n")
    
    project_info = {
        'pyproject_data': read_pyproject_toml(),
        'structure': get_project_structure(),
        'code_analysis': analyze_python_files(),
        'git_info': get_git_info(),
        'config_files': check_config_files()
    }
    
    # Save to JSON file
    output_file = 'project_info.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(project_info, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Project information saved to {output_file}")
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    
    # Print summary
    pyproject = project_info['pyproject_data']
    if 'tool' in pyproject and 'poetry' in pyproject['tool']:
        poetry_data = pyproject['tool']['poetry']
        print(f"\nProject Name: {poetry_data.get('name', 'N/A')}")
        print(f"Version: {poetry_data.get('version', 'N/A')}")
        print(f"Description: {poetry_data.get('description', 'N/A')}")
        
        if 'dependencies' in poetry_data:
            print(f"\nMain Dependencies: {len(poetry_data['dependencies'])}")
            for dep, ver in list(poetry_data['dependencies'].items())[:5]:
                print(f"  - {dep}: {ver}")
    
    print(f"\nPython Files Analyzed: {len(project_info['code_analysis'])}")
    print(f"Configuration Files: {len(project_info['config_files'])}")
    
    if project_info['git_info']:
        print(f"\nGit Repository: {project_info['git_info'].get('remote_url', 'N/A')}")
    
    print("\n" + "="*50)
    print(f"\nNow share the '{output_file}' file content with me,")
    print("and I'll help you create a comprehensive README.md!")
    print("="*50)


if __name__ == "__main__":
    main()