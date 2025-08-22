#!/bin/bash

# TaskFlow AI Installation Script
# This script installs TaskFlow AI app with all dependencies and configurations

set -e  # Exit on any error

echo "🚀 TaskFlow AI Installation Script"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
}

# Check if running in Frappe bench directory
if [ ! -f "sites/common_site_config.json" ]; then
    print_error "This script must be run from the Frappe bench directory"
    exit 1
fi

print_info "Checking system requirements..."

# Check Python version
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    print_warning "Python 3.10+ recommended. Current version: $python_version"
fi

print_status "Python version check passed: $python_version"

# Get site name
if [ -z "$1" ]; then
    echo "Available sites:"
    ls sites/ | grep -v common_site_config.json | grep -v assets
    echo
    read -p "Enter site name: " site_name
else
    site_name=$1
fi

if [ ! -d "sites/$site_name" ]; then
    print_error "Site '$site_name' does not exist"
    exit 1
fi

print_info "Installing required Python packages..."

# Install packages from requirements.txt if it exists
if [ -f "apps/taskflow_ai/requirements.txt" ]; then
    pip3 install -r apps/taskflow_ai/requirements.txt --quiet
    print_status "Python packages installed"
else
    print_warning "requirements.txt not found, using minimal dependencies"
fi

print_info "Installing TaskFlow AI app on site: $site_name"

# Install the app
print_info "Installing TaskFlow AI app..."
bench --site $site_name install-app taskflow_ai

if [ $? -eq 0 ]; then
    print_status "App installation successful!"
else
    print_error "App installation failed!"
    exit 1
fi

# Run database migrations
print_info "Running database migrations..."
bench --site $site_name migrate

# Install sample templates
print_info "Installing sample ERPNext implementation templates..."
bench --site $site_name execute taskflow_ai.install_templates.install_sample_templates

# Set up required custom fields (for ERPNext integration)
print_info "Setting up custom fields..."
bench --site $site_name execute "
import frappe

# Add custom fields to Lead
if not frappe.db.exists('Custom Field', {'fieldname': 'custom_project_generated', 'dt': 'Lead'}):
    frappe.get_doc({
        'doctype': 'Custom Field',
        'dt': 'Lead',
        'fieldname': 'custom_project_generated',
        'label': 'AI Project Generated',
        'fieldtype': 'Check',
        'hidden': 1
    }).insert()

# Add custom fields to Opportunity  
if not frappe.db.exists('Custom Field', {'fieldname': 'custom_project_generated', 'dt': 'Opportunity'}):
    frappe.get_doc({
        'doctype': 'Custom Field',
        'dt': 'Opportunity', 
        'fieldname': 'custom_project_generated',
        'label': 'AI Project Generated',
        'fieldtype': 'Check',
        'hidden': 1
    }).insert()

# Add custom fields to Project
project_fields = [
    {'fieldname': 'custom_ai_generated', 'label': 'AI Generated', 'fieldtype': 'Check'},
    {'fieldname': 'custom_template_group', 'label': 'Template Group', 'fieldtype': 'Link', 'options': 'Task Template Group'},
    {'fieldname': 'custom_source_lead', 'label': 'Source Lead', 'fieldtype': 'Link', 'options': 'Lead'},
    {'fieldname': 'custom_source_opportunity', 'label': 'Source Opportunity', 'fieldtype': 'Link', 'options': 'Opportunity'}
]

for field in project_fields:
    if not frappe.db.exists('Custom Field', {'fieldname': field['fieldname'], 'dt': 'Project'}):
        field['dt'] = 'Project'
        field['doctype'] = 'Custom Field'
        frappe.get_doc(field).insert()

# Add custom fields to Task
task_fields = [
    {'fieldname': 'custom_ai_generated', 'label': 'AI Generated', 'fieldtype': 'Check'},
    {'fieldname': 'custom_template_source', 'label': 'Template Source', 'fieldtype': 'Link', 'options': 'Task Template'},
    {'fieldname': 'custom_phase', 'label': 'Phase', 'fieldtype': 'Data'},
    {'fieldname': 'custom_sequence', 'label': 'Sequence', 'fieldtype': 'Int'},
    {'fieldname': 'custom_assigned_employee', 'label': 'Assigned Employee', 'fieldtype': 'Link', 'options': 'Employee'}
]

for field in task_fields:
    if not frappe.db.exists('Custom Field', {'fieldname': field['fieldname'], 'dt': 'Task'}):
        field['dt'] = 'Task'
        field['doctype'] = 'Custom Field'
        frappe.get_doc(field).insert()

frappe.db.commit()
print('✅ Custom fields created')
"

# Create user roles and permissions
print_info "Setting up roles and permissions..."
bench --site $site_name execute "
import frappe

# Create TaskFlow AI Manager role if it doesn't exist
if not frappe.db.exists('Role', 'TaskFlow AI Manager'):
    frappe.get_doc({
        'doctype': 'Role',
        'role_name': 'TaskFlow AI Manager',
        'desk_access': 1
    }).insert()

# Create TaskFlow AI User role
if not frappe.db.exists('Role', 'TaskFlow AI User'):
    frappe.get_doc({
        'doctype': 'Role', 
        'role_name': 'TaskFlow AI User',
        'desk_access': 1
    }).insert()

frappe.db.commit()
print('✅ Roles created')
"

# Clear cache and restart
print_info "Clearing cache..."
bench --site $site_name clear-cache

# Final completion message
echo
print_status "TaskFlow AI installed successfully on site: $site_name"
echo
echo "� Installation Complete!"
echo "========================"
echo
print_info "Key Features Available:"
echo "  • AI Task Profiles - Smart task recommendations"
echo "  • Employee Task Assignment - Bulk assignment with AI suggestions"
echo "  • Project Planning - Manual control over Lead-to-Project conversion"
echo "  • Task Templates - Pre-defined task structures"
echo "  • Skills Management - Employee skills tracking"
echo
print_info "Quick Start Guide:"
echo "  1. Go to TaskFlow AI > Task Templates to view installed templates"
echo "  2. Create a Lead and convert to Project Planning for review"
echo "  3. Use Employee Task Assignment for AI-powered task distribution"
echo "  4. Check AI Task Profiles for intelligent recommendations"
echo
print_info "Access Information:"
echo "  • Site: $site_name"
echo "  • URL: http://localhost:8000"
echo "  • Default Login: Administrator"
echo
echo "🤖 Happy automating with TaskFlow AI! ✨"
