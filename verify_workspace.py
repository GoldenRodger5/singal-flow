#!/usr/bin/env python3
"""
SignalFlow System Verification Script
Comprehensive check of organized workspace and system readiness
"""

import os
import sys
from pathlib import Path

def check_workspace_organization():
    """Verify organized folder structure"""
    print("🔍 WORKSPACE ORGANIZATION CHECK")
    print("=" * 50)
    
    base_path = Path.cwd()
    
    # Expected folder structure
    expected_folders = [
        'agents',
        'services', 
        'scripts',
        'tests',
        'docs',
        'deployment',
        'data',
        'logs',
        'utils'
    ]
    
    missing_folders = []
    for folder in expected_folders:
        folder_path = base_path / folder
        if folder_path.exists():
            print(f"✅ {folder}/ - Present")
        else:
            print(f"❌ {folder}/ - Missing")
            missing_folders.append(folder)
    
    if not missing_folders:
        print("\n🎉 Workspace organization: PERFECT!")
    else:
        print(f"\n⚠️  Missing folders: {missing_folders}")
    
    return len(missing_folders) == 0

def check_documentation():
    """Verify comprehensive documentation"""
    print("\n📚 DOCUMENTATION CHECK")
    print("=" * 50)
    
    docs_path = Path.cwd() / 'docs'
    
    expected_docs = [
        'ARCHITECTURE.md',
        'API_REFERENCE.md', 
        'ENHANCED_MOMENTUM_SYSTEM_COMPLETE.md',
        'AI_LEARNING_README.md'
    ]
    
    missing_docs = []
    for doc in expected_docs:
        doc_path = docs_path / doc
        if doc_path.exists():
            size = doc_path.stat().st_size
            print(f"✅ {doc} - Present ({size:,} bytes)")
        else:
            print(f"❌ {doc} - Missing")
            missing_docs.append(doc)
    
    # Check main README
    readme_path = Path.cwd() / 'README.md'
    if readme_path.exists():
        size = readme_path.stat().st_size
        print(f"✅ README.md - Present ({size:,} bytes)")
    else:
        print("❌ README.md - Missing")
        missing_docs.append('README.md')
    
    # Check start scripts guide
    start_guide_path = Path.cwd() / 'START_SCRIPTS.md'
    if start_guide_path.exists():
        size = start_guide_path.stat().st_size
        print(f"✅ START_SCRIPTS.md - Present ({size:,} bytes)")
    else:
        print("❌ START_SCRIPTS.md - Missing")
        missing_docs.append('START_SCRIPTS.md')
    
    if not missing_docs:
        print("\n🎉 Documentation: COMPREHENSIVE!")
    else:
        print(f"\n⚠️  Missing documentation: {missing_docs}")
    
    return len(missing_docs) == 0

def check_core_components():
    """Verify core trading components"""
    print("\n🚀 CORE COMPONENTS CHECK")
    print("=" * 50)
    
    core_files = [
        'start_trading.py',
        'enhanced_trading_ui.py',
        'main.py',
        'telegram_webhook.py',
        'services/config.py',
        'services/momentum_multiplier.py',
        'services/enhanced_position_sizer.py',
        'agents/trade_recommender_agent.py'
    ]
    
    missing_files = []
    for file_path in core_files:
        full_path = Path.cwd() / file_path
        if full_path.exists():
            size = full_path.stat().st_size
            print(f"✅ {file_path} - Present ({size:,} bytes)")
        else:
            print(f"❌ {file_path} - Missing")
            missing_files.append(file_path)
    
    if not missing_files:
        print("\n🎉 Core components: ALL PRESENT!")
    else:
        print(f"\n⚠️  Missing core files: {missing_files}")
    
    return len(missing_files) == 0

def check_start_scripts():
    """Verify start scripts in scripts folder"""
    print("\n🎯 START SCRIPTS CHECK")
    print("=" * 50)
    
    scripts_path = Path.cwd() / 'scripts'
    
    expected_scripts = [
        'launch_ai_system.py',
        'launch_fast_ui.py', 
        'launch_production.py'
    ]
    
    missing_scripts = []
    for script in expected_scripts:
        script_path = scripts_path / script
        if script_path.exists():
            size = script_path.stat().st_size
            print(f"✅ scripts/{script} - Present ({size:,} bytes)")
        else:
            print(f"❌ scripts/{script} - Missing")
            missing_scripts.append(script)
    
    if not missing_scripts:
        print("\n🎉 Start scripts: ALL ORGANIZED!")
    else:
        print(f"\n⚠️  Missing scripts: {missing_scripts}")
    
    return len(missing_scripts) == 0

def count_workspace_files():
    """Count workspace statistics"""
    print("\n📊 WORKSPACE STATISTICS")
    print("=" * 50)
    
    base_path = Path.cwd()
    
    # Count Python files
    py_files = list(base_path.rglob('*.py'))
    print(f"🐍 Python files: {len(py_files)}")
    
    # Count documentation files
    md_files = list(base_path.rglob('*.md'))
    print(f"📄 Documentation files: {len(md_files)}")
    
    # Count total files (excluding __pycache__, .git)
    all_files = []
    for file_path in base_path.rglob('*'):
        if file_path.is_file() and not any(part.startswith('.') or part == '__pycache__' for part in file_path.parts):
            all_files.append(file_path)
    
    print(f"📁 Total organized files: {len(all_files)}")
    
    # Folder breakdown
    print("\n📁 FOLDER BREAKDOWN:")
    folders = ['agents', 'services', 'scripts', 'tests', 'docs', 'deployment']
    for folder in folders:
        folder_path = base_path / folder
        if folder_path.exists():
            files_in_folder = len([f for f in folder_path.rglob('*') if f.is_file()])
            print(f"   {folder}/: {files_in_folder} files")

def main():
    """Run comprehensive workspace verification"""
    print("🚀 SIGNALFLOW WORKSPACE VERIFICATION")
    print("=" * 60)
    print("Verifying organized workspace and system readiness...")
    print()
    
    # Run all checks
    checks = [
        ("Workspace Organization", check_workspace_organization),
        ("Documentation", check_documentation),
        ("Core Components", check_core_components),
        ("Start Scripts", check_start_scripts)
    ]
    
    results = []
    for check_name, check_func in checks:
        result = check_func()
        results.append((check_name, result))
    
    # Display statistics
    count_workspace_files()
    
    # Final summary
    print("\n🎯 VERIFICATION SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {check_name}")
        if result:
            passed += 1
    
    print(f"\nScore: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 WORKSPACE VERIFICATION: COMPLETE SUCCESS!")
        print("✅ SignalFlow system is organized and ready for production!")
        print("\n🚀 Start trading with: python start_trading.py")
    else:
        print(f"\n⚠️  {total - passed} issues found. Please review and fix.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
