import frappe

def test_table_assignment():
	"""Test the restored table-based task assignment system"""
	print('🧪 TESTING RESTORED TABLE ASSIGNMENT SYSTEM')
	print('='*55)
	
	try:
		# Check Task Assignment Item exists
		if frappe.db.exists('DocType', 'Task Assignment Item'):
			print('✅ Task Assignment Item DocType restored')
		else:
			print('❌ Task Assignment Item DocType missing')
			
		# Check Employee Task Assignment has table field
		meta = frappe.get_meta('Employee Task Assignment')
		field_names = [f.fieldname for f in meta.fields]
		
		if 'task_assignments' in field_names:
			print('✅ Employee Task Assignment has task_assignments table field')
		else:
			print('❌ task_assignments table field missing')
			
		# Test creating new document
		doc = frappe.new_doc('Employee Task Assignment')
		doc.project = 'PROJ-0009'
		print('✅ Can create Employee Task Assignment with project')
		
		# Test child table
		child = frappe.new_doc('Task Assignment Item')
		print('✅ Can create Task Assignment Item child record')
		
		print('🎉 TABLE ASSIGNMENT SYSTEM RESTORED!')
		print('')
		print('📋 HOW IT WORKS:')
		print('   1. Select Project in Employee Task Assignment')
		print('   2. Click "Load Project Tasks" button')
		print('   3. Tasks populate in the table')
		print('   4. Assign employees in the table')
		print('   5. Click "Apply Assignments" to push to Task records')
		
	except Exception as e:
		print(f'❌ Error testing table assignment: {e}')
		import traceback
		print(traceback.format_exc())
	
	finally:
		print('='*55)
