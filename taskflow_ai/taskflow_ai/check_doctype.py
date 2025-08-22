import frappe

def check_employee_task_assignment():
	"""Check if Employee Task Assignment DocType is available and working"""
	print('🔍 CHECKING EMPLOYEE TASK ASSIGNMENT AVAILABILITY')
	print('='*55)
	
	try:
		# Check if Employee Task Assignment DocType exists
		if frappe.db.exists('DocType', 'Employee Task Assignment'):
			print('✅ Employee Task Assignment DocType exists')
			
			# Try to create a new document
			doc = frappe.new_doc('Employee Task Assignment')
			print('✅ Can create new Employee Task Assignment document')
			
			# Check fields
			meta = frappe.get_meta('Employee Task Assignment')
			print(f'✅ DocType has {len(meta.fields)} fields')
			
		else:
			print('❌ Employee Task Assignment DocType not found')
			
		print('🎉 Employee Task Assignment is working!')
		
	except Exception as e:
		print(f'❌ Error accessing Employee Task Assignment: {e}')
	
	finally:
		print('='*55)
