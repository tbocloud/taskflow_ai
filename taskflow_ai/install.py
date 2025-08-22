# Copyright (c) 2025, sammish and contributors
# For license information, please see license.txt

"""
TaskFlow AI Installation Handler
Handles package dependencies and app installation requirements
"""

import os
import sys
import subprocess
import frappe
from frappe import _


def before_install():
	"""
	Execute before app installation
	Install required packages and dependencies
	"""
	try:
		print("🚀 Starting TaskFlow AI Installation...")
		print("=" * 50)
		
		# Check Python version
		check_python_version()
		
		# Install required Python packages
		install_required_packages()
		
		# Check system dependencies
		check_system_dependencies()
		
		# Verify Frappe/ERPNext compatibility
		verify_framework_compatibility()
		
		print("✅ Pre-installation checks completed successfully!")
		
	except Exception as e:
		frappe.throw(_("Installation failed: {0}").format(str(e)))


def after_install():
	"""
	Execute after app installation
	Setup default configurations and data
	"""
	try:
		print("🔧 Configuring TaskFlow AI...")
		
		# Create default AI profiles
		setup_default_ai_profiles()
		
		# Install sample templates
		install_sample_templates()
		
		# Setup default permissions
		setup_default_permissions()
		
		# Create default task categories
		setup_default_task_categories()
		
		# Setup system configurations
		setup_system_configurations()
		
		print("✅ TaskFlow AI installation completed successfully!")
		print("🎉 Ready for use!")
		
	except Exception as e:
		print(f"⚠️ Post-installation setup error: {e}")
		# Don't fail installation for post-setup errors


def check_python_version():
	"""Check if Python version meets requirements"""
	python_version = sys.version_info
	
	if python_version < (3, 10):
		raise Exception("Python 3.10 or higher is required. Current version: {}.{}".format(
			python_version.major, python_version.minor))
	
	print(f"✅ Python version check passed: {python_version.major}.{python_version.minor}")


def install_required_packages():
	"""Install required Python packages via pip"""
	
	# Define required packages (keeping minimal as per system design)
	required_packages = [
		# Core packages (already available in Frappe)
		"python-dateutil>=2.8.0",  # Date utilities
		"requests>=2.25.0",        # HTTP requests (if needed for future AI APIs)
	]
	
	print("📦 Checking required packages...")
	
	for package in required_packages:
		try:
			# Try importing to check if package exists
			package_name = package.split('>=')[0].split('==')[0]
			
			if package_name == "python-dateutil":
				import dateutil
			elif package_name == "requests":
				import requests
				
			print(f"   ✅ {package_name}: Already installed")
			
		except ImportError:
			print(f"   📥 Installing {package}...")
			
			try:
				subprocess.check_call([
					sys.executable, "-m", "pip", "install", package, "--quiet"
				])
				print(f"   ✅ {package}: Installed successfully")
				
			except subprocess.CalledProcessError as e:
				print(f"   ⚠️ {package}: Installation failed - {e}")
				# Continue with installation as these are optional


def check_system_dependencies():
	"""Check system-level dependencies"""
	
	print("🔍 Checking system dependencies...")
	
	# Check if running in Frappe environment
	try:
		import frappe
		print("   ✅ Frappe Framework: Available")
	except ImportError:
		raise Exception("Frappe Framework is required but not found")
	
	# Check ERPNext availability
	try:
		import erpnext
		print("   ✅ ERPNext: Available")
	except ImportError:
		raise Exception("ERPNext is required but not found")


def verify_framework_compatibility():
	"""Verify Frappe/ERPNext version compatibility"""
	
	print("🔧 Verifying framework compatibility...")
	
	try:
		frappe_version = frappe.__version__
		print(f"   ✅ Frappe Framework: v{frappe_version}")
		
		# Check minimum Frappe version (15.0.0)
		version_parts = frappe_version.split('.')
		major_version = int(version_parts[0])
		
		if major_version < 15:
			print(f"   ⚠️ Warning: Frappe v15+ recommended (current: v{frappe_version})")
		
	except Exception as e:
		print(f"   ⚠️ Could not verify Frappe version: {e}")


def setup_default_ai_profiles():
	"""Create default AI Task Profiles"""
	
	print("🤖 Setting up default AI profiles...")
	
	try:
		from taskflow_ai.taskflow_ai.install_templates import install_sample_templates
		install_sample_templates()
		print("   ✅ AI profiles and templates installed")
		
	except Exception as e:
		print(f"   ⚠️ AI profiles setup error: {e}")


def install_sample_templates():
	"""Install sample task templates"""
	
	print("📋 Installing sample templates...")
	
	try:
		# Check if templates already exist
		existing_templates = frappe.get_all("Task Template", limit=1)
		
		if not existing_templates:
			from taskflow_ai.taskflow_ai.install_templates import install_sample_templates
			install_sample_templates()
			print("   ✅ Sample templates installed")
		else:
			print("   ✅ Sample templates already exist")
			
	except Exception as e:
		print(f"   ⚠️ Template installation error: {e}")


def setup_default_permissions():
	"""Setup default role permissions"""
	
	print("🔐 Setting up permissions...")
	
	try:
		# Define role permissions for TaskFlow AI doctypes
		role_permissions = {
			"System Manager": ["AI Task Profile", "Employee Task Assignment", "Project Planning", "Task Template"],
			"Projects Manager": ["Employee Task Assignment", "Project Planning", "Task Template"],
			"HR Manager": ["Employee Task Assignment", "Employee Skills"],
			"Employee": ["Employee Skills"]
		}
		
		for role, doctypes in role_permissions.items():
			for doctype in doctypes:
				try:
					# Check if permission already exists
					existing = frappe.get_all("Custom DocPerm", 
						filters={"parent": doctype, "role": role}, limit=1)
					
					if not existing:
						# Add basic permissions (read, write, create)
						frappe.get_doc({
							"doctype": "Custom DocPerm",
							"parent": doctype,
							"parenttype": "DocType",
							"parentfield": "permissions",
							"role": role,
							"read": 1,
							"write": 1,
							"create": 1,
							"delete": 1 if role == "System Manager" else 0
						}).insert(ignore_permissions=True)
						
				except Exception:
					pass  # Permission might already exist
		
		frappe.db.commit()
		print("   ✅ Permissions configured")
		
	except Exception as e:
		print(f"   ⚠️ Permissions setup error: {e}")


def setup_default_task_categories():
	"""Create default task categories"""
	
	print("📂 Setting up task categories...")
	
	try:
		categories = [
			"Development", "Testing", "Documentation", "Training", 
			"Implementation", "Support", "Analysis", "Planning"
		]
		
		for category in categories:
			if not frappe.db.exists("Task Type", category):
				frappe.get_doc({
					"doctype": "Task Type",
					"name": category
				}).insert(ignore_permissions=True)
		
		frappe.db.commit()
		print("   ✅ Task categories created")
		
	except Exception as e:
		print(f"   ⚠️ Task categories setup error: {e}")


def setup_system_configurations():
	"""Setup system-wide configurations"""
	
	print("⚙️ Configuring system settings...")
	
	try:
		# Set up default AI configurations
		settings = {
			"taskflow_ai_enabled": 1,
			"auto_assign_tasks": 0,  # Disabled by default for manual control
			"ai_confidence_threshold": 0.7,
			"max_tasks_per_employee": 10
		}
		
		for key, value in settings.items():
			frappe.db.set_single_value("System Settings", key, value)
		
		frappe.db.commit()
		print("   ✅ System configurations applied")
		
	except Exception as e:
		print(f"   ⚠️ System configuration error: {e}")


def uninstall():
	"""
	Clean up function called during app uninstallation
	"""
	try:
		print("🧹 Cleaning up TaskFlow AI...")
		
		# Remove custom configurations
		cleanup_configurations()
		
		# Note: We don't delete data documents as they might be needed
		print("✅ TaskFlow AI cleanup completed")
		
	except Exception as e:
		print(f"⚠️ Cleanup error: {e}")


def cleanup_configurations():
	"""Clean up system configurations"""
	
	try:
		# Reset system settings
		settings_to_reset = [
			"taskflow_ai_enabled",
			"auto_assign_tasks", 
			"ai_confidence_threshold",
			"max_tasks_per_employee"
		]
		
		for setting in settings_to_reset:
			frappe.db.set_single_value("System Settings", setting, None)
		
		frappe.db.commit()
		
	except Exception as e:
		print(f"Configuration cleanup error: {e}")


# Export functions for bench commands
__all__ = [
	'before_install',
	'after_install', 
	'uninstall',
	'install_required_packages',
	'setup_default_ai_profiles'
]
