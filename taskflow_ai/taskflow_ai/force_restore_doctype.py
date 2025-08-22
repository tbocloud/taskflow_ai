import frappe
import json

def force_restore_task_assignment_item():
	"""Force restore Task Assignment Item DocType"""
	print('🔧 FORCE RESTORING TASK ASSIGNMENT ITEM DOCTYPE')
	print('='*55)
	
	try:
		# First check if it exists in database
		if frappe.db.exists('DocType', 'Task Assignment Item'):
			print('⚠️  Task Assignment Item exists in DB but may be corrupted')
			# Delete it completely first
			frappe.delete_doc('DocType', 'Task Assignment Item', force=True)
			frappe.db.commit()
			print('✅ Removed corrupted version')
		
		# Import fresh from JSON file
		doctype_path = '/Users/sammishthundiyil/frappe-bench-deco/apps/taskflow_ai/taskflow_ai/taskflow_ai/doctype/task_assignment_item/task_assignment_item.json'
		
		# Read the JSON manually
		with open(doctype_path, 'r') as f:
			doctype_dict = json.load(f)
		
		# Create new DocType document
		doc = frappe.get_doc(doctype_dict)
		doc.insert(ignore_permissions=True)
		frappe.db.commit()
		
		print('✅ Successfully created Task Assignment Item DocType')
		
		# Clear cache to refresh everything
		frappe.clear_cache()
		print('✅ Cache cleared')
		
		print('🎉 TASK ASSIGNMENT ITEM FORCEFULLY RESTORED!')
		return True
		
	except Exception as e:
		print(f'❌ Error: {e}')
		import traceback
		traceback.print_exc()
		return False
	
	finally:
		print('='*55)
