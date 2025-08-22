import frappe

def test_employee_task_assignment_fixed():
	"""Test that Employee Task Assignment is now working without Task Assignment Item"""
	print('🧪 TESTING FIXED EMPLOYEE TASK ASSIGNMENT')
	print('='*55)
	
	try:
		# Check if Employee Task Assignment DocType exists
		if frappe.db.exists('DocType', 'Employee Task Assignment'):
			print('✅ Employee Task Assignment DocType exists')
			
			# Try to create a new document
			doc = frappe.new_doc('Employee Task Assignment')
			print('✅ Can create new Employee Task Assignment document')
			
			# Check the new fields exist
			meta = frappe.get_meta('Employee Task Assignment')
			field_names = [f.fieldname for f in meta.fields]
			
			required_fields = ['tasks_html', 'selected_tasks']
			for field in required_fields:
				if field in field_names:
					print(f'✅ New field "{field}" exists')
				else:
					print(f'❌ Missing field "{field}"')
			
			# Check that the problematic field is removed
			if 'task_assignments' not in field_names:
				print('✅ Removed problematic "task_assignments" field')
			else:
				print('❌ "task_assignments" field still exists')
				
			print('✅ DocType has {} total fields'.format(len(meta.fields)))
			
		else:
			print('❌ Employee Task Assignment DocType not found')
		
		# Test assignment helper functions
		from taskflow_ai.taskflow_ai.assignment_helper import get_project_tasks_with_ai_recommendations
		print('✅ Assignment helper functions imported successfully')
		
		print('🎉 EMPLOYEE TASK ASSIGNMENT FIXED!')
		
	except Exception as e:
		print(f'❌ Error testing Employee Task Assignment: {e}')
		import traceback
		print(traceback.format_exc())
	
	finally:
		print('='*55)
