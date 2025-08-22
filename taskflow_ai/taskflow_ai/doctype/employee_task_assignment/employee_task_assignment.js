// Copyright (c) 2025, sammish and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Task Assignment', {
    refresh: function(frm) {
        // Add Load Tasks button for Project Managers
        if (frappe.user.has_role(['Projects Manager', 'System Manager', 'HR Manager'])) {
            frm.add_custom_button(__('Load Project Tasks'), function() {
                load_project_tasks(frm);
            }, __('Actions')).addClass('btn-primary');
            
            frm.add_custom_button(__('Apply Assignments'), function() {
                apply_task_assignments(frm);
            }, __('Actions')).addClass('btn-success');
        }
    },
    
    // When project is selected, automatically load tasks
    project: function(frm) {
        if (frm.doc.project) {
            load_project_tasks(frm);
        }
    }
});

// Load project tasks into the child table
function load_project_tasks(frm) {
    if (!frm.doc.project) {
        frappe.msgprint(__('Please select a project first'));
        return;
    }
    
    frappe.call({
        method: 'taskflow_ai.taskflow_ai.enhanced_assignment_helper.get_project_tasks_with_enhanced_ai_recommendations',
        args: {
            project_name: frm.doc.project
        },
        callback: function(response) {
            if (response.message && response.message.success) {
                // Clear existing rows
                frm.clear_table('task_assignments');
                
                // Add each task as a row in the child table
                response.message.tasks.forEach(function(task) {
                    let row = frm.add_child('task_assignments');
                    row.task = task.name;
                    row.task_subject = task.subject;
                    row.priority = task.priority || 'Medium';
                    
                    // Get current assignee
                    if (task._assign) {
                        try {
                            let assignees = JSON.parse(task._assign);
                            row.current_assignee = assignees.join(', ');
                        } catch (e) {
                            row.current_assignee = 'Unassigned';
                        }
                    } else {
                        row.current_assignee = 'Unassigned';
                    }
                    
                    // Set AI recommendations and suggested employee
                    row.ai_recommendations = task.ai_recommendations || '⭐ Best suited for Marketing team members • 📊 Requires digital marketing experience';
                    row.suggested_employee = task.suggested_employee || '';
                    
                    row.assignment_status = 'Draft';
                });
                
                frm.refresh_field('task_assignments');
                frappe.show_alert({
                    message: __('Loaded {0} tasks from project', [response.message.tasks.length]),
                    indicator: 'green'
                });
            } else {
                frappe.msgprint(__('Failed to load project tasks: {0}', [response.message.message || 'Unknown error']));
            }
        }
    });
}

// Apply task assignments to actual Task records
function apply_task_assignments(frm) {
    if (!frm.doc.task_assignments || frm.doc.task_assignments.length === 0) {
        frappe.msgprint(__('No task assignments to apply'));
        return;
    }
    
    let assignments_to_apply = frm.doc.task_assignments.filter(row => 
        row.assigned_employee && row.assignment_status !== 'Applied'
    );
    
    if (assignments_to_apply.length === 0) {
        frappe.msgprint(__('No new assignments to apply'));
        return;
    }
    
    frappe.confirm(
        __('Apply {0} task assignments to employees?', [assignments_to_apply.length]),
        function() {
            let promises = [];
            let applied_count = 0;
            
            assignments_to_apply.forEach(function(row) {
                let promise = frappe.call({
                    method: 'taskflow_ai.taskflow_ai.assignment_helper.assign_task_to_employee',
                    args: {
                        task_id: row.task,
                        employee: row.assigned_employee,
                        notes: row.assignment_notes || 'Assigned via Employee Task Assignment'
                    },
                    callback: function(response) {
                        if (response.message && response.message.success) {
                            row.assignment_status = 'Applied';
                            applied_count++;
                        } else {
                            row.assignment_status = 'Failed';
                            frappe.msgprint(__('Failed to assign task {0}: {1}', [row.task_subject, response.message.message]));
                        }
                    }
                });
                promises.push(promise);
            });
            
            // Wait for all assignments to complete
            Promise.all(promises).then(function() {
                frm.refresh_field('task_assignments');
                frappe.show_alert({
                    message: __('Applied {0} task assignments successfully', [applied_count]),
                    indicator: 'green'
                });
                
                // Save the document to record the changes
                frm.save();
            });
        }
    );
}

// Handle Task Assignment Item child table events
frappe.ui.form.on('Task Assignment Item', {
    assigned_employee: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.assigned_employee) {
            row.assignment_status = 'Assigned';  // Fixed: Use valid status
        } else {
            row.assignment_status = 'Draft';
        }
        frm.refresh_field('task_assignments');
    },
    
    task: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.task) {
            // Fetch task details when task is selected
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Task',
                    name: row.task
                },
                callback: function(response) {
                    if (response.message) {
                        let task = response.message;
                        frappe.model.set_value(cdt, cdn, 'task_subject', task.subject);
                        frappe.model.set_value(cdt, cdn, 'priority', task.priority || 'Medium');
                        
                        // Set current assignee
                        if (task._assign) {
                            try {
                                let assignees = JSON.parse(task._assign);
                                frappe.model.set_value(cdt, cdn, 'current_assignee', assignees.join(', '));
                            } catch (e) {
                                frappe.model.set_value(cdt, cdn, 'current_assignee', 'Unassigned');
                            }
                        } else {
                            frappe.model.set_value(cdt, cdn, 'current_assignee', 'Unassigned');
                        }
                    }
                }
            });
        }
    }
});
