import frappe
from frappe.modules.import_file import import_file_by_path

def restore_task_assignment_item():
	"""Restore the Task Assignment Item DocType that was deleted as orphaned"""
	print('🔧 RESTORING TASK ASSIGNMENT ITEM DOCTYPE')
	print('='*50)
	
	try:
		# Import the DocType from JSON file
		doctype_path = 'apps/taskflow_ai/taskflow_ai/taskflow_ai/doctype/task_assignment_item/task_assignment_item.json'
		result = import_file_by_path(doctype_path, data_import=True)
		print('✅ Successfully imported Task Assignment Item DocType')
		
		# Commit the transaction
		frappe.db.commit()
		print('✅ Changes committed to database')
		
		# Clear cache
		frappe.clear_cache()
		print('✅ Cache cleared')
		
		print('🎉 TASK ASSIGNMENT ITEM DOCTYPE RESTORED!')
		return True
		
	except Exception as e:
		print(f'❌ Error restoring DocType: {e}')
		frappe.db.rollback()
		return False
	
	finally:
		print('='*50)
