// Copyright (c) 2025, sammish and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Task Assignment', {
    refresh: function(frm) {
        // Add Project Manager Assignment Tools
        if (frappe.user.has_role(['Projects Manager', 'System Manager', 'HR Manager'])) {
            add_assignment_tools(frm);
        }
        
        // Add custom buttons based on status
        if (frm.doc.assigned_employee) {
            frm.add_custom_button(__('Create Timesheet'), function() {
                create_timesheet_dialog(frm);
            }, __('Actions'));
            
            frm.add_custom_button(__('View Timesheets'), function() {
                frappe.route_options = {
                    "employee": frm.doc.assigned_employee,
                    "task": frm.doc.task
                };
                frappe.set_route("List", "Timesheet");
            }, __('Actions'));
        }
        
        if (frm.doc.ai_task_profile) {
            frm.add_custom_button(__('View AI Recommendations'), function() {
                show_ai_recommendations(frm);
            }, __('AI Tools'));
        }
        
        // Add status-specific buttons
        if (frm.doc.assignment_status === 'Assigned') {
            frm.add_custom_button(__('Start Work'), function() {
                frm.set_value('assignment_status', 'In Progress');
                frm.set_value('start_date', frappe.datetime.get_today());
                frm.save();
            }).addClass('btn-primary');
        }
        
        if (frm.doc.assignment_status === 'In Progress') {
            frm.add_custom_button(__('Mark Complete'), function() {
                frm.set_value('assignment_status', 'Completed');
                frm.set_value('completion_date', frappe.datetime.get_today());
                frm.set_value('completion_percentage', 100);
                frm.save();
            }).addClass('btn-success');
        }
        
        // Update timesheet info
        if (frm.doc.task && frm.doc.assigned_employee) {
            update_timesheet_summary(frm);
        }
    },
        
        if (frm.doc.ai_task_profile) {
            frm.add_custom_button(__('View AI Recommendations'), function() {
                show_ai_recommendations(frm);
            }, __('AI Tools'));
        }
        
        // Add status-specific buttons
        if (frm.doc.assignment_status === 'Assigned') {
            frm.add_custom_button(__('Start Work'), function() {
                frm.set_value('assignment_status', 'In Progress');
                frm.set_value('start_date', frappe.datetime.get_today());
                frm.save();
            }).addClass('btn-primary');
        }
        
        if (frm.doc.assignment_status === 'In Progress') {
            frm.add_custom_button(__('Mark Complete'), function() {
                frm.set_value('assignment_status', 'Completed');
                frm.set_value('completion_date', frappe.datetime.get_today());
                frm.set_value('completion_percentage', 100);
                frm.save();
            }).addClass('btn-success');
        }
        
        // Update timesheet info
        if (frm.doc.task && frm.doc.assigned_employee) {
            update_timesheet_summary(frm);
        }
    },
    
    // When task is selected, check for AI recommendations
    task: function(frm) {
        if (frm.doc.task) {
            load_task_ai_profile(frm);
            load_task_project_info(frm);
        }
    },
    
    // When employee is assigned, update the Task module
    assigned_employee: function(frm) {
        if (frm.doc.assigned_employee && frm.doc.task) {
            update_task_assigned_employee(frm);
        }
        
        if (frm.doc.assigned_employee) {
            // Get employee details
            frappe.db.get_doc("Employee", frm.doc.assigned_employee).then(function(emp) {
                frm.set_value('assignment_notes', 
                    `Task assigned to: ${emp.employee_name}\n` +
                    `Employee ID: ${emp.name}\n` +
                    `Department: ${emp.department || 'Not specified'}\n` +
                    `Assignment Date: ${frappe.datetime.get_today()}`
                );
            });
        }
    },
    
    ai_task_profile: function(frm) {
        if (frm.doc.ai_task_profile) {
            // Get AI profile recommendations
            frappe.db.get_doc("AI Task Profile", frm.doc.ai_task_profile).then(function(profile) {
                if (profile.predicted_duration_hours) {
                    frm.set_value('expected_duration', profile.predicted_duration_hours);
                }
                
                // Add AI insights to notes
                let ai_notes = `\nAI Task Profile Insights:\n`;
                if (profile.confidence_score) {
                    ai_notes += `Confidence Score: ${profile.confidence_score}%\n`;
                }
                if (profile.complexity_score) {
                    ai_notes += `Complexity Score: ${profile.complexity_score}\n`;
                }
                if (profile.predicted_duration_hours) {
                    ai_notes += `Predicted Duration: ${profile.predicted_duration_hours} hours\n`;
                }
                
                frm.set_value('assignment_notes', 
                    (frm.doc.assignment_notes || '') + ai_notes
                );
            });
        }
    },
    
    assignment_status: function(frm) {
        // Update dates based on status
        if (frm.doc.assignment_status === 'In Progress' && !frm.doc.start_date) {
            frm.set_value('start_date', frappe.datetime.get_today());
        } else if (frm.doc.assignment_status === 'Completed' && !frm.doc.completion_date) {
            frm.set_value('completion_date', frappe.datetime.get_today());
            frm.set_value('completion_percentage', 100);
        }
    }
});

function create_timesheet_dialog(frm) {
    let dialog = new frappe.ui.Dialog({
        title: __('Create Timesheet Entry'),
        fields: [
            {
                fieldname: 'hours_worked',
                label: __('Hours Worked'),
                fieldtype: 'Float',
                reqd: 1,
                default: 1.0
            },
            {
                fieldname: 'activity_type',
                label: __('Activity Type'),
                fieldtype: 'Link',
                options: 'Activity Type',
                default: 'Task Work'
            },
            {
                fieldname: 'description',
                label: __('Work Description'),
                fieldtype: 'Small Text',
                default: `Work on task: ${frm.doc.task}`
            }
        ],
        primary_action: function(data) {
            frappe.call({
                method: 'taskflow_ai.taskflow_ai.doctype.employee_task_assignment.employee_task_assignment.create_timesheet_for_assignment',
                args: {
                    assignment_name: frm.doc.name,
                    hours_worked: data.hours_worked,
                    description: data.description,
                    activity_type: data.activity_type
                },
                callback: function(r) {
                    if (r.message.status === 'success') {
                        frappe.msgprint({
                            title: __('Success'),
                            message: r.message.message,
                            indicator: 'green'
                        });
                        dialog.hide();
                        frm.reload_doc();
                    } else {
                        frappe.msgprint({
                            title: __('Error'),
                            message: r.message.message,
                            indicator: 'red'
                        });
                    }
                }
            });
        },
        primary_action_label: __('Create Timesheet')
    });
    
    dialog.show();
}

function update_timesheet_summary(frm) {
    // Get timesheet summary for this assignment
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Timesheet Detail',
            filters: {
                task: frm.doc.task,
                parenttype: 'Timesheet'
            },
            fields: ['parent', 'hours']
        },
        callback: function(r) {
            if (r.message) {
                let total_hours = 0;
                let unique_timesheets = new Set();
                
                r.message.forEach(function(detail) {
                    total_hours += detail.hours;
                    unique_timesheets.add(detail.parent);
                });
                
                // Update fields
                frm.set_value('total_time_logged', total_hours);
                frm.set_value('timesheets_created', unique_timesheets.size);
                
                // Update completion percentage
                if (frm.doc.expected_duration && frm.doc.expected_duration > 0) {
                    let completion = Math.min((total_hours / frm.doc.expected_duration) * 100, 100);
                    frm.set_value('completion_percentage', completion);
                }
            }
        }
    });
}

// Project Manager Assignment Tools
function add_assignment_tools(frm) {
    // Add button to show unassigned tasks by project
    frm.add_custom_button(__('Show Unassigned Tasks'), function() {
        show_unassigned_tasks_dialog();
    }, __('Assignment Tools'));
    
    // Add button to view project task summary
    if (frm.doc.task) {
        frm.add_custom_button(__('Project Task Summary'), function() {
            show_project_task_summary(frm);
        }, __('Assignment Tools'));
    }
}

// Show unassigned tasks dialog
function show_unassigned_tasks_dialog() {
    let d = new frappe.ui.Dialog({
        title: __('Unassigned Tasks by Project'),
        size: 'large',
        fields: [
            {
                fieldname: 'project',
                fieldtype: 'Link',
                label: __('Project'),
                options: 'Project',
                reqd: 1,
                change: function() {
                    if (d.get_value('project')) {
                        load_unassigned_tasks(d);
                    }
                }
            },
            {
                fieldname: 'tasks_html',
                fieldtype: 'HTML'
            }
        ],
        primary_action: function() {
            d.hide();
        },
        primary_action_label: __('Close')
    });
    
    d.show();
}

// Load unassigned tasks for selected project
function load_unassigned_tasks(dialog) {
    let project = dialog.get_value('project');
    
    frappe.call({
        method: 'taskflow_ai.taskflow_ai.api.assignment_helper.get_unassigned_tasks_by_project',
        args: {
            project: project
        },
        callback: function(r) {
            if (r.message) {
                let html = build_unassigned_tasks_html(r.message);
                dialog.fields_dict.tasks_html.$wrapper.html(html);
            }
        }
    });
}

// Build HTML for unassigned tasks with assign buttons
function build_unassigned_tasks_html(tasks) {
    if (!tasks || tasks.length === 0) {
        return '<div class="text-muted">No unassigned tasks found for this project.</div>';
    }
    
    let html = '<div class="unassigned-tasks-list">';
    html += '<table class="table table-bordered">';
    html += '<thead><tr><th>Task</th><th>Subject</th><th>Priority</th><th>AI Recommendations</th><th>Action</th></tr></thead>';
    html += '<tbody>';
    
    tasks.forEach(function(task) {
        html += '<tr>';
        html += `<td><a href="/app/task/${task.name}" target="_blank">${task.name}</a></td>`;
        html += `<td>${task.subject}</td>`;
        html += `<td><span class="badge badge-${get_priority_color(task.priority)}">${task.priority}</span></td>`;
        html += `<td>${task.ai_recommendations || 'No AI profile found'}</td>`;
        html += `<td><button class="btn btn-sm btn-primary assign-task" data-task="${task.name}">Assign Task</button></td>`;
        html += '</tr>';
    });
    
    html += '</tbody></table></div>';
    
    // Add click handlers for assign buttons
    setTimeout(function() {
        $('.assign-task').click(function() {
            let task_name = $(this).data('task');
            create_task_assignment_dialog(task_name);
        });
    }, 100);
    
    return html;
}

// Create task assignment dialog with AI recommendations
function create_task_assignment_dialog(task_name) {
    let d = new frappe.ui.Dialog({
        title: __('Assign Task: {0}', [task_name]),
        size: 'large',
        fields: [
            {
                fieldname: 'task',
                fieldtype: 'Link',
                label: __('Task'),
                options: 'Task',
                default: task_name,
                read_only: 1
            },
            {
                fieldname: 'assigned_employee',
                fieldtype: 'Link',
                label: __('Assign to Employee'),
                options: 'Employee',
                reqd: 1
            },
            {
                fieldname: 'priority',
                fieldtype: 'Select',
                label: __('Priority'),
                options: 'Low\nMedium\nHigh\nCritical',
                default: 'Medium'
            },
            {
                fieldname: 'expected_duration',
                fieldtype: 'Float',
                label: __('Expected Duration (Hours)')
            },
            {
                fieldname: 'assignment_notes',
                fieldtype: 'Small Text',
                label: __('Assignment Notes')
            },
            {
                fieldname: 'ai_recommendations_html',
                fieldtype: 'HTML'
            }
        ],
        primary_action: function() {
            let values = d.get_values();
            create_employee_task_assignment(values, d);
        },
        primary_action_label: __('Assign Task')
    });
    
    // Load AI recommendations when dialog opens
    load_ai_recommendations_for_task(task_name, d);
    
    d.show();
}

// Load AI recommendations for task assignment
function load_ai_recommendations_for_task(task_name, dialog) {
    frappe.call({
        method: 'taskflow_ai.taskflow_ai.api.assignment_helper.get_ai_recommendations_for_task',
        args: {
            task: task_name
        },
        callback: function(r) {
            if (r.message && r.message.recommendations) {
                let html = build_ai_recommendations_html(r.message.recommendations);
                dialog.fields_dict.ai_recommendations_html.$wrapper.html(html);
                
                // Add click handlers to select recommended employees
                setTimeout(function() {
                    $('.select-employee').click(function() {
                        let employee = $(this).data('employee');
                        dialog.set_value('assigned_employee', employee);
                    });
                }, 100);
            }
        }
    });
}

// Build AI recommendations HTML
function build_ai_recommendations_html(recommendations) {
    let html = '<div class="ai-recommendations" style="margin: 10px 0;">';
    html += '<h6>🤖 AI Recommendations:</h6>';
    html += '<div class="row">';
    
    recommendations.forEach(function(rec, index) {
        let color = index === 0 ? 'success' : (index === 1 ? 'info' : 'secondary');
        html += '<div class="col-md-4">';
        html += `<div class="card border-${color}">`;
        html += '<div class="card-body" style="padding: 10px;">';
        html += `<h6 class="card-title">${rec.employee_name}</h6>`;
        html += `<p class="card-text">Fit Score: ${rec.fit_score}%</p>`;
        html += `<button class="btn btn-sm btn-${color} select-employee" data-employee="${rec.employee}">Select</button>`;
        html += '</div></div></div>';
    });
    
    html += '</div></div>';
    return html;
}

// Create Employee Task Assignment record
function create_employee_task_assignment(values, dialog) {
    frappe.call({
        method: 'taskflow_ai.taskflow_ai.api.assignment_helper.create_manual_assignment',
        args: values,
        callback: function(r) {
            if (r.message) {
                frappe.msgprint(__('Task assigned successfully!'));
                dialog.hide();
                
                // Refresh current form if it exists
                if (cur_frm && cur_frm.doctype === 'Employee Task Assignment') {
                    cur_frm.reload_doc();
                }
            }
        }
    });
}

// Update Task module's assigned employee field
function update_task_assigned_employee(frm) {
    frappe.call({
        method: 'taskflow_ai.taskflow_ai.api.assignment_helper.update_task_assignment',
        args: {
            task: frm.doc.task,
            assigned_employee: frm.doc.assigned_employee
        },
        callback: function(r) {
            if (r.message) {
                frappe.show_alert({
                    message: __('Task assignment updated in Task module'),
                    indicator: 'green'
                });
            }
        }
    });
}

// Helper functions
function get_priority_color(priority) {
    switch(priority) {
        case 'Critical': return 'danger';
        case 'High': return 'warning';
        case 'Medium': return 'info';
        case 'Low': return 'secondary';
        default: return 'secondary';
    }
}

function show_project_task_summary(frm) {
    frappe.route_options = {
        "project": frm.doc.project
    };
    frappe.set_route("List", "Task");
}
