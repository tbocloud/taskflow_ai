// Copyright (c) 2025, sammish and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Task Assignment', {
    refresh: function(frm) {
        // Add Load Tasks button for Project Managers
        if (frappe.user.has_role(['Projects Manager', 'System Manager', 'HR Manager'])) {
            frm.add_custom_button(__('Load Project Tasks'), function() {
                load_project_tasks(frm);
            }, __('Actions')).addClass('btn-primary');
            
            frm.add_custom_button(__('Bulk Assign'), function() {
                bulk_assign_tasks(frm);
            }, __('Actions')).addClass('btn-success');
        }
        
        // Add suggestion buttons if tasks are loaded
        add_suggestion_buttons(frm);
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
        frappe.msgprint(__('Please select a project first.'));
        return;
    }
    
    frappe.show_alert({
        message: __('Loading tasks for project...'),
        indicator: 'blue'
    });
    
    frappe.call({
        method: 'taskflow_ai.taskflow_ai.assignment_helper.get_project_tasks_with_ai_recommendations',
        args: {
            project: frm.doc.project
        },
        callback: function(r) {
            if (r.message) {
                // Clear existing task assignments
                frm.clear_table('task_assignments');
                
                // Add each task to the child table
                r.message.forEach(function(task) {
                    let row = frm.add_child('task_assignments');
                    
                    row.task = task.name;
                    row.task_subject = task.subject;
                    row.priority = task.priority || 'Medium';
                    row.current_assignee = task.assigned_employee || 'Unassigned';
                    
                    // Set the top AI recommendation as suggested employee
                    row.suggested_employee = task.top_ai_recommendation || null;
                    
                    // Format AI recommendations for display - ensure it's always a string
                    let ai_recs = task.ai_recommendations;
                    if (Array.isArray(ai_recs)) {
                        // If it's an array, join it into a string
                        row.ai_recommendations = ai_recs.join(' | ');
                    } else if (ai_recs && typeof ai_recs === 'string') {
                        // If it's already a string, use it
                        row.ai_recommendations = ai_recs;
                    } else {
                        // Fallback for null/undefined
                        row.ai_recommendations = 'No AI recommendations available';
                    }
                    
                    // Set assignment status and assigned employee
                    row.assignment_status = task.assigned_employee ? 'Assigned' : 'Draft';
                    row.assigned_employee = task.assigned_employee;
                    row.assignment_date = task.assignment_date || null;
                });
                
                // Refresh the child table
                frm.refresh_field('task_assignments');
                
                frappe.show_alert({
                    message: __('Tasks loaded successfully! ({0} tasks)', [r.message.length]),
                    indicator: 'green'
                });
            } else {
                frappe.msgprint(__('No tasks found for this project.'));
            }
        },
        error: function() {
            frappe.msgprint(__('Error loading tasks. Please try again.'));
        }
    });
}

// Bulk assign tasks to suggested employees
function bulk_assign_tasks(frm) {
    let unassigned_tasks = frm.doc.task_assignments.filter(task => 
        !task.assigned_employee || task.assignment_status === 'Draft'
    );
    
    if (unassigned_tasks.length === 0) {
        frappe.msgprint(__('All tasks are already assigned.'));
        return;
    }
    
    frappe.confirm(
        __('Do you want to bulk assign {0} unassigned tasks to their suggested employees?', [unassigned_tasks.length]),
        function() {
            let promises = [];
            let assigned_count = 0;
            
            unassigned_tasks.forEach(function(task_row) {
                // Use the suggested_employee field which was populated from top AI recommendation
                if (task_row.suggested_employee) {
                    task_row.assigned_employee = task_row.suggested_employee;
                    task_row.assignment_status = 'Assigned';
                    task_row.assignment_date = frappe.datetime.get_today();
                    task_row.assignment_notes = 'Auto-assigned based on AI recommendation';
                    
                    // Update the actual Task record
                    let promise = frappe.call({
                        method: 'taskflow_ai.taskflow_ai.assignment_helper.assign_task_to_employee',
                        args: {
                            task: task_row.task,
                            employee: task_row.assigned_employee,
                            assignment_notes: task_row.assignment_notes
                        }
                    });
                    promises.push(promise);
                    assigned_count++;
                }
            });
            
            // Wait for all assignments to complete
            Promise.all(promises).then(function(results) {
                frm.refresh_field('task_assignments');
                frappe.show_alert({
                    message: __('Bulk assignment completed! {0} tasks assigned.', [assigned_count]),
                    indicator: 'green'
                });
            });
        }
    );
}

// Child table events for Task Assignment Item
frappe.ui.form.on('Task Assignment Item', {
    // When employee is assigned in child table
    assigned_employee: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.assigned_employee && row.task) {
            row.assignment_status = 'Assigned';
            row.assignment_date = frappe.datetime.get_today();
            frm.refresh_field('task_assignments');
            
            // Update the Task record with assignment
            frappe.call({
                method: 'taskflow_ai.taskflow_ai.assignment_helper.assign_task_to_employee',
                args: {
                    task: row.task,
                    employee: row.assigned_employee,
                    assignment_notes: row.assignment_notes || 'Manually assigned through Employee Task Assignment'
                },
                callback: function(r) {
                    if (r.message && r.message.status === 'success') {
                        frappe.show_alert({
                            message: __('Task {0} assigned to {1}', [row.task, r.message.assigned_to]),
                            indicator: 'green'
                        });
                    } else if (r.message && r.message.status === 'error') {
                        frappe.msgprint({
                            title: __('Assignment Error'),
                            message: r.message.message,
                            indicator: 'red'
                        });
                        // Reset the assignment if failed
                        row.assigned_employee = '';
                        row.assignment_status = 'Draft';
                        frm.refresh_field('task_assignments');
                    }
                }
            });
        }
    },
    
    // When task is selected, load task details
    task: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.task) {
            frappe.db.get_doc('Task', row.task)
            .then(function(task_doc) {
                row.task_subject = task_doc.subject;
                row.priority = task_doc.priority || 'Medium';
                frm.refresh_field('task_assignments');
            });
        }
    },
    
    // Add a button to assign suggested employee
    ai_recommendations: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.suggested_employee && !row.assigned_employee) {
            // Auto-populate the suggested employee
            setTimeout(function() {
                frappe.msgprint({
                    title: __('AI Suggestion Available'),
                    message: __('Click on "Assign to Employee" field to assign the AI suggested employee: {0}', [row.suggested_employee]),
                    indicator: 'blue'
                });
            }, 500);
        }
    }
});

// Auto-populate suggested employee button
function add_suggestion_buttons(frm) {
    // Add custom buttons to quickly assign AI suggestions
    if (frm.doc.task_assignments && frm.doc.task_assignments.length > 0) {
        let unassigned_with_suggestions = frm.doc.task_assignments.filter(task => 
            !task.assigned_employee && task.suggested_employee
        );
        
        if (unassigned_with_suggestions.length > 0) {
            frm.add_custom_button(__('Auto-Assign AI Suggestions'), function() {
                unassigned_with_suggestions.forEach(function(task_row) {
                    task_row.assigned_employee = task_row.suggested_employee;
                    task_row.assignment_status = 'Assigned';
                    task_row.assignment_date = frappe.datetime.get_today();
                    task_row.assignment_notes = 'Auto-assigned based on AI recommendation';
                });
                frm.refresh_field('task_assignments');
                frappe.show_alert(__('AI suggestions applied to unassigned tasks!'));
            });
        }
    }
}
