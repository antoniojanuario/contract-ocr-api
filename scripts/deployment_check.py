#!/usr/bin/env python3
"""
Deployment readiness check script
Validates that the application is ready for deployment on free platforms
"""
import asyncio
import sys
import os
import tempfile
import shutil
from pathlib import Path
import subprocess
import json

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.monitoring import resource_monitor
from app.db.init_db import check_database_connection, init_database

import logging
logger = logging.getLogger(__name__)
setup_logging()  # Initialize logging system


class DeploymentChecker:
    """Check deployment readiness"""
    
    def __init__(self):
        self.checks = []
        self.warnings = []
        self.errors = []
    
    def add_check(self, name: str, status: str, message: str = ""):
        """Add a check result"""
        self.checks.append({
            "name": name,
            "status": status,  # "pass", "warn", "fail"
            "message": message
        })
        
        if status == "warn":
            self.warnings.append(f"{name}: {message}")
        elif status == "fail":
            self.errors.append(f"{name}: {message}")
    
    async def check_environment_config(self):
        """Check environment configuration"""
        logger.info("Checking environment configuration...")
        
        # Check environment detection
        if settings.ENVIRONMENT == "local":
            self.add_check("Environment Detection", "warn", 
                          "Running in local environment - ensure production env vars are set")
        else:
            self.add_check("Environment Detection", "pass", 
                          f"Detected environment: {settings.ENVIRONMENT}")
        
        # Check database URL
        if settings.DATABASE_URL.startswith("sqlite://"):
            if settings.ENVIRONMENT in ["render", "railway"]:
                self.add_check("Database Configuration", "warn",
                              "Using SQLite in production - consider PostgreSQL for better performance")
            else:
                self.add_check("Database Configuration", "pass", "SQLite configured")
        else:
            self.add_check("Database Configuration", "pass", "PostgreSQL configured")
        
        # Check Redis configuration
        if settings.USE_REDIS:
            self.add_check("Redis Configuration", "pass", "Redis enabled for task queue")
        else:
            self.add_check("Redis Configuration", "warn", 
                          "Redis disabled - using in-memory queue (not persistent)")
        
        # Check resource limits
        if settings.is_free_platform:
            if settings.optimized_max_file_size > 25 * 1024 * 1024:
                self.add_check("File Size Limits", "warn",
                              f"File size limit ({settings.optimized_max_file_size/1024/1024:.0f}MB) may be too high for free platforms")
            else:
                self.add_check("File Size Limits", "pass",
                              f"File size optimized for free platforms ({settings.optimized_max_file_size/1024/1024:.0f}MB)")
        
        # Check timeouts
        if settings.optimized_ocr_timeout > 180:
            self.add_check("OCR Timeout", "warn",
                          f"OCR timeout ({settings.optimized_ocr_timeout}s) may be too high for free platforms")
        else:
            self.add_check("OCR Timeout", "pass",
                          f"OCR timeout optimized ({settings.optimized_ocr_timeout}s)")
    
    async def check_database_connectivity(self):
        """Check database connectivity"""
        logger.info("Checking database connectivity...")
        
        try:
            await check_database_connection()
            self.add_check("Database Connection", "pass", "Database connection successful")
        except Exception as e:
            self.add_check("Database Connection", "fail", f"Database connection failed: {e}")
    
    async def check_database_schema(self):
        """Check database schema"""
        logger.info("Checking database schema...")
        
        try:
            await init_database()
            self.add_check("Database Schema", "pass", "Database schema initialized successfully")
        except Exception as e:
            self.add_check("Database Schema", "fail", f"Database schema initialization failed: {e}")
    
    async def check_system_resources(self):
        """Check system resources"""
        logger.info("Checking system resources...")
        
        try:
            metrics = await resource_monitor.get_system_metrics()
            
            # Check CPU
            cpu_percent = metrics.get("cpu", {}).get("percent", 0)
            if cpu_percent > 80:
                self.add_check("CPU Usage", "warn", f"High CPU usage: {cpu_percent:.1f}%")
            else:
                self.add_check("CPU Usage", "pass", f"CPU usage normal: {cpu_percent:.1f}%")
            
            # Check memory
            memory_percent = metrics.get("memory", {}).get("percent", 0)
            available_mb = metrics.get("memory", {}).get("available_mb", 0)
            
            if memory_percent > 85:
                self.add_check("Memory Usage", "warn", f"High memory usage: {memory_percent:.1f}%")
            elif available_mb < 100:
                self.add_check("Memory Usage", "warn", f"Low available memory: {available_mb:.0f}MB")
            else:
                self.add_check("Memory Usage", "pass", f"Memory usage normal: {memory_percent:.1f}%")
            
            # Check disk
            disk_percent = metrics.get("disk", {}).get("percent", 0)
            if disk_percent > 90:
                self.add_check("Disk Usage", "warn", f"High disk usage: {disk_percent:.1f}%")
            else:
                self.add_check("Disk Usage", "pass", f"Disk usage normal: {disk_percent:.1f}%")
                
        except Exception as e:
            self.add_check("System Resources", "fail", f"Failed to check system resources: {e}")
    
    def check_required_files(self):
        """Check required deployment files exist"""
        logger.info("Checking required deployment files...")
        
        required_files = [
            "requirements.txt",
            "Dockerfile",
            "render.yaml",
            "railway.json",
            ".env.example"
        ]
        
        for file_path in required_files:
            if os.path.exists(file_path):
                self.add_check(f"File: {file_path}", "pass", "File exists")
            else:
                self.add_check(f"File: {file_path}", "fail", "File missing")
    
    def check_dependencies(self):
        """Check Python dependencies"""
        logger.info("Checking Python dependencies...")
        
        try:
            # Check if requirements.txt exists and is readable
            if os.path.exists("requirements.txt"):
                with open("requirements.txt", "r") as f:
                    requirements = f.read()
                    
                # Check for critical dependencies
                critical_deps = ["fastapi", "uvicorn", "sqlalchemy", "pydantic"]
                missing_deps = []
                
                for dep in critical_deps:
                    if dep not in requirements.lower():
                        missing_deps.append(dep)
                
                if missing_deps:
                    self.add_check("Critical Dependencies", "fail",
                                  f"Missing dependencies: {', '.join(missing_deps)}")
                else:
                    self.add_check("Critical Dependencies", "pass", "All critical dependencies present")
            else:
                self.add_check("Requirements File", "fail", "requirements.txt not found")
                
        except Exception as e:
            self.add_check("Dependencies Check", "fail", f"Failed to check dependencies: {e}")
    
    def check_docker_config(self):
        """Check Docker configuration"""
        logger.info("Checking Docker configuration...")
        
        if os.path.exists("Dockerfile"):
            try:
                with open("Dockerfile", "r") as f:
                    dockerfile_content = f.read()
                
                # Check for security best practices
                if "USER app" in dockerfile_content:
                    self.add_check("Docker Security", "pass", "Non-root user configured")
                else:
                    self.add_check("Docker Security", "warn", "Consider using non-root user")
                
                # Check for health check
                if "HEALTHCHECK" in dockerfile_content:
                    self.add_check("Docker Health Check", "pass", "Health check configured")
                else:
                    self.add_check("Docker Health Check", "warn", "Consider adding health check")
                    
            except Exception as e:
                self.add_check("Docker Configuration", "fail", f"Failed to read Dockerfile: {e}")
        else:
            self.add_check("Docker Configuration", "fail", "Dockerfile not found")
    
    async def run_all_checks(self):
        """Run all deployment checks"""
        logger.info("Starting deployment readiness checks...")
        
        # Run all checks
        await self.check_environment_config()
        await self.check_database_connectivity()
        await self.check_database_schema()
        await self.check_system_resources()
        self.check_required_files()
        self.check_dependencies()
        self.check_docker_config()
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate deployment readiness report"""
        logger.info("Generating deployment readiness report...")
        
        passed = len([c for c in self.checks if c["status"] == "pass"])
        warned = len([c for c in self.checks if c["status"] == "warn"])
        failed = len([c for c in self.checks if c["status"] == "fail"])
        
        print("\n" + "="*60)
        print("DEPLOYMENT READINESS REPORT")
        print("="*60)
        print(f"Total Checks: {len(self.checks)}")
        print(f"Passed: {passed}")
        print(f"Warnings: {warned}")
        print(f"Failed: {failed}")
        print()
        
        # Show all checks
        for check in self.checks:
            status_symbol = {
                "pass": "✓",
                "warn": "⚠",
                "fail": "✗"
            }.get(check["status"], "?")
            
            print(f"{status_symbol} {check['name']}")
            if check["message"]:
                print(f"  {check['message']}")
        
        print("\n" + "="*60)
        
        if failed > 0:
            print("❌ DEPLOYMENT NOT READY")
            print("Please fix the failed checks before deploying.")
            return False
        elif warned > 0:
            print("⚠️  DEPLOYMENT READY WITH WARNINGS")
            print("Consider addressing the warnings for optimal performance.")
            return True
        else:
            print("✅ DEPLOYMENT READY")
            print("All checks passed successfully!")
            return True


async def main():
    """Main function"""
    checker = DeploymentChecker()
    
    try:
        ready = await checker.run_all_checks()
        
        # Exit with appropriate code
        if not ready and len(checker.errors) > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Deployment check failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())