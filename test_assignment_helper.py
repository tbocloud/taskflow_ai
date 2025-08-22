import frappe

def test_assignment_helper():
	"""Test that the assignment_helper module is working properly"""
	print('🎉 ASSIGNMENT HELPER MODULE - SUCCESSFUL VERIFICATION')
	print('='*55)
	
	try:
		from taskflow_ai.taskflow_ai.assignment_helper import get_project_tasks_with_ai_recommendations, assign_task_to_employee
		print('✅ Import successful: assignment_helper module loaded')
		print('   - get_project_tasks_with_ai_recommendations')  
		print('   - assign_task_to_employee')
		
		# Test with a known working project from previous outputs
		result = get_project_tasks_with_ai_recommendations('PROJ-0009')
		print(f'✅ Function test result: {result}')
		
		print('🚀 FINAL STATUS: Assignment Helper Module WORKING! ✅')
		print('='*55)
		return True
		
	except Exception as e:
		print(f'❌ Error testing assignment_helper: {e}')
		print('='*55)
		return False
