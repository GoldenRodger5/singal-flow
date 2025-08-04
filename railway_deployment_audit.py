#!/usr/bin/env python3
"""
RAILWAY DEPLOYMENT AUDIT - Identify potential deployment issues
Checks for common Railway deployment problems and missing configurations
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

class RailwayDeploymentAuditor:
    def __init__(self):
        self.issues = []
        self.successes = []
        self.warnings = []
        
    def log_issue(self, issue: str):
        self.issues.append(f"❌ {issue}")
        print(f"❌ {issue}")
    
    def log_success(self, success: str):
        self.successes.append(f"✅ {success}")
        print(f"✅ {success}")
    
    def log_warning(self, warning: str):
        self.warnings.append(f"⚠️ {warning}")
        print(f"⚠️ {warning}")

    def check_requirements_file(self):
        """Check requirements.txt for Railway compatibility"""
        print("\n📦 1. CHECKING REQUIREMENTS.TXT...")
        
        req_file = Path("requirements.txt")
        if not req_file.exists():
            self.log_issue("requirements.txt file missing")
            return
        
        self.log_success("requirements.txt exists")
        
        with open(req_file, 'r') as f:
            content = f.read()
        
        # Check for common problematic packages
        problematic_packages = [
            'tensorflow',
            'torch',
            'pytorch',
            'jupyter-lab',
            'notebook'
        ]
        
        for package in problematic_packages:
            if package in content.lower():
                self.log_warning(f"Heavy package '{package}' may cause build timeouts")
        
        # Check for version conflicts
        if 'pandas>=2.1.0' in content:
            self.log_warning("pandas>=2.1.0 may conflict with pandas-ta")
        
        if 'uvicorn[standard]' in content:
            self.log_success("uvicorn with standard dependencies included")
        else:
            self.log_warning("Consider using uvicorn[standard] for better Railway compatibility")

    def check_python_version(self):
        """Check Python version compatibility"""
        print("\n🐍 2. CHECKING PYTHON VERSION...")
        
        runtime_file = Path("runtime.txt")
        if runtime_file.exists():
            with open(runtime_file, 'r') as f:
                version = f.read().strip()
            
            if version == "python-3.12":
                self.log_success("Python 3.12 specified in runtime.txt")
            else:
                self.log_warning(f"Python version {version} - consider 3.12 for best Railway support")
        else:
            self.log_warning("runtime.txt missing - Railway will use default Python version")

    def check_startup_commands(self):
        """Check Railway startup configuration"""
        print("\n🚀 3. CHECKING STARTUP CONFIGURATION...")
        
        # Check Procfile
        procfile = Path("Procfile")
        if procfile.exists():
            with open(procfile, 'r') as f:
                content = f.read().strip()
            
            if "uvicorn" in content and "production_api" in content:
                self.log_success("Procfile configured correctly for FastAPI")
            else:
                self.log_warning(f"Procfile content may be incorrect: {content}")
        else:
            self.log_warning("Procfile missing - relying on railway.json")
        
        # Check railway.json
        railway_file = Path("railway.json")
        if railway_file.exists():
            try:
                with open(railway_file, 'r') as f:
                    config = json.load(f)
                
                start_command = config.get('deploy', {}).get('startCommand', '')
                if "uvicorn" in start_command:
                    self.log_success("railway.json has correct start command")
                else:
                    self.log_warning(f"railway.json start command unclear: {start_command}")
                    
            except json.JSONDecodeError:
                self.log_issue("railway.json has invalid JSON syntax")
        else:
            self.log_warning("railway.json missing")

    def check_environment_variables(self):
        """Check for required environment variables"""
        print("\n🔐 4. CHECKING ENVIRONMENT VARIABLES...")
        
        required_vars = [
            'MONGODB_URL',
            'POLYGON_API_KEY',
            'ALPACA_API_KEY',
            'ALPACA_SECRET',
            'OPENAI_API_KEY',
            'TELEGRAM_BOT_TOKEN',
            'TELEGRAM_CHAT_ID'
        ]
        
        for var in required_vars:
            if os.getenv(var):
                self.log_success(f"{var} is configured")
            else:
                self.log_issue(f"Missing environment variable: {var}")

    def check_import_safety(self):
        """Check for potential import issues"""
        print("\n🔄 5. CHECKING IMPORT SAFETY...")
        
        backend_dir = Path("backend")
        if not backend_dir.exists():
            self.log_issue("backend directory missing")
            return
        
        # Check production_api.py
        api_file = backend_dir / "scripts" / "production_api.py"
        if api_file.exists():
            with open(api_file, 'r') as f:
                content = f.read()
            
            # Check for immediate imports that could fail
            if "from main import" in content:
                self.log_warning("Direct import from main.py - consider lazy loading")
            
            if "db_manager = get_db_manager()" in content:
                self.log_success("Database manager uses lazy loading")
            elif "from services.database_manager import db_manager" in content:
                self.log_issue("Database manager uses immediate loading - will cause Railway failure")
        
        # Check for circular imports
        try:
            sys.path.insert(0, str(backend_dir))
            from services.database_manager import get_db_manager
            self.log_success("Database manager imports successfully")
        except Exception as e:
            self.log_issue(f"Database manager import failed: {e}")

    def check_port_configuration(self):
        """Check port configuration for Railway"""
        print("\n🚪 6. CHECKING PORT CONFIGURATION...")
        
        backend_dir = Path("backend")
        api_file = backend_dir / "scripts" / "production_api.py"
        
        if api_file.exists():
            with open(api_file, 'r') as f:
                content = f.read()
            
            if "port=$PORT" in content or "PORT" in content:
                self.log_success("PORT environment variable used correctly")
            else:
                self.log_warning("PORT environment variable usage not found")
        
        # Check if hardcoded ports exist
        if "port=8000" in content or "port=3000" in content:
            self.log_warning("Hardcoded port found - ensure $PORT is used for Railway")

    def check_file_structure(self):
        """Check critical file structure"""
        print("\n📁 7. CHECKING FILE STRUCTURE...")
        
        critical_files = [
            "backend/scripts/production_api.py",
            "backend/services/database_manager.py",
            "backend/services/config.py",
            "backend/main.py"
        ]
        
        for file_path in critical_files:
            if Path(file_path).exists():
                self.log_success(f"{file_path} exists")
            else:
                self.log_issue(f"Critical file missing: {file_path}")

    def check_memory_usage(self):
        """Check for potential memory issues"""
        print("\n💾 8. CHECKING MEMORY USAGE PATTERNS...")
        
        backend_dir = Path("backend")
        
        # Check for memory-intensive operations
        memory_issues = []
        
        for py_file in backend_dir.rglob("*.py"):
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                
                # Check for potential memory issues
                if "pandas.read_csv" in content and "chunksize" not in content:
                    memory_issues.append(f"{py_file}: Large CSV reads without chunking")
                
                if "while True:" in content and "time.sleep" not in content:
                    memory_issues.append(f"{py_file}: Infinite loop without sleep")
                
            except Exception:
                continue
        
        if memory_issues:
            for issue in memory_issues:
                self.log_warning(issue)
        else:
            self.log_success("No obvious memory usage issues found")

    def generate_final_report(self):
        """Generate comprehensive final report"""
        print("\n" + "="*80)
        print("📋 RAILWAY DEPLOYMENT AUDIT REPORT")  
        print("="*80)
        
        print(f"\n✅ PASSED CHECKS ({len(self.successes)}):")
        for success in self.successes:
            print(f"  {success}")
        
        print(f"\n⚠️ WARNINGS ({len(self.warnings)}):")
        for warning in self.warnings:
            print(f"  {warning}")
        
        print(f"\n❌ ISSUES ({len(self.issues)}):")
        for issue in self.issues:
            print(f"  {issue}")
        
        critical_issues = [i for i in self.issues if any(word in i.lower() for word in ['missing', 'failed', 'invalid'])]
        
        print(f"\n🚨 DEPLOYMENT STATUS:")
        if len(self.issues) == 0:
            print("  🟢 READY FOR RAILWAY DEPLOYMENT")
            print("  🎯 All checks passed")
        elif len(critical_issues) == 0:
            print("  🟡 LIKELY TO DEPLOY SUCCESSFULLY")
            print("  ⚠️ Address warnings for optimal performance")
        else:
            print("  🔴 DEPLOYMENT ISSUES PRESENT")
            print("  🛑 Fix critical issues before deploying")
        
        return len(critical_issues) == 0

def main():
    auditor = RailwayDeploymentAuditor()
    
    print("🚀 RAILWAY DEPLOYMENT AUDIT - SIGNAL FLOW TRADING SYSTEM")
    print(f"⏰ Audit Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Run all audit checks
    auditor.check_requirements_file()
    auditor.check_python_version()
    auditor.check_startup_commands()
    auditor.check_environment_variables()
    auditor.check_import_safety()
    auditor.check_port_configuration()
    auditor.check_file_structure()
    auditor.check_memory_usage()
    
    # Generate final report
    is_ready = auditor.generate_final_report()
    
    if is_ready:
        print("\n🎉 SYSTEM IS READY FOR RAILWAY DEPLOYMENT!")
        print("🚀 Deploy with confidence")
        print("📊 Monitor logs during initial deployment")
    else:
        print("\n⚠️ SYSTEM NEEDS FIXES BEFORE RAILWAY DEPLOYMENT!")
        print("🔧 Address critical issues above")
    
    return is_ready

if __name__ == "__main__":
    main()
