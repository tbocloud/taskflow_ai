// Copyright (c) 2025, sammish and contributors
// For license information, please see license.txt

frappe.listview_settings['Employee Task Assignment'] = {
    add_fields: ["assignment_status", "assigned_employee", "task", "assignment_date"],
    filters: [["assignment_status", "!=", "Cancelled"]],
    get_indicator: function(doc) {
        var status_color = {
            "Draft": "grey",
            "Assigned": "orange", 
            "In Progress": "blue",
            "Completed": "green",
            "On Hold": "yellow",
            "Cancelled": "red"
        };
        return [doc.assignment_status, status_color[doc.assignment_status], "assignment_status,=," + doc.assignment_status];
    },
    
    onload: function(listview) {
        // Add custom buttons for Project Managers
        if (frappe.user.has_role(['Projects Manager', 'System Manager', 'HR Manager'])) {
            
            // Add button to view unassigned tasks
            listview.page.add_menu_item(__("Show Unassigned Tasks"), function() {
                show_unassigned_tasks_dashboard();
            });
            
            // Add button to bulk assign tasks
            listview.page.add_menu_item(__("Bulk Task Assignment"), function() {
                show_bulk_assignment_dialog();
            });
        }
        
        // Add refresh button with assignment summary
        listview.page.add_inner_button(__("Assignment Summary"), function() {
            show_assignment_summary_dialog();
        });
        listview.page.add_inner_button(__('Create from AI Profile'), function() {
            show_ai_profile_selection_dialog();
        });
        
        listview.page.add_inner_button(__('Bulk Timesheet'), function() {
            show_bulk_timesheet_dialog(listview);
        });
    }
};

function show_ai_profile_selection_dialog() {
    let dialog = new frappe.ui.Dialog({
        title: __('Create Assignment from AI Profile'),
        fields: [
            {
                fieldname: 'ai_task_profile',
                label: __('AI Task Profile'),
                fieldtype: 'Link',
                options: 'AI Task Profile',
                reqd: 1,
                get_query: function() {
                    return {
                        filters: {
                            'task': ['not in', 
                                frappe.db.get_list('Employee Task Assignment', {
                                    fields: ['task'],
                                    filters: [['assignment_status', '!=', 'Cancelled']]
                                }).map(d => d.task)
                            ]
                        }
                    };
                }
            },
            {
                fieldname: 'selected_employee',
                label: __('Select Employee'),
                fieldtype: 'Link',
                options: 'Employee',
                reqd: 1
            }
        ],
        primary_action: function(data) {
            frappe.call({
                method: 'taskflow_ai.taskflow_ai.doctype.employee_task_assignment.employee_task_assignment.create_assignment_from_ai_profile',
                args: {
                    ai_profile_name: data.ai_task_profile,
                    selected_employee: data.selected_employee
                },
                callback: function(r) {
                    if (r.message.status === 'success') {
                        frappe.msgprint({
                            title: __('Success'),
                            message: r.message.message,
                            indicator: 'green'
                        });
                        dialog.hide();
                        location.reload();
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
        primary_action_label: __('Create Assignment')
    });
    
    // When AI profile is selected, show recommendations
    dialog.fields_dict.ai_task_profile.df.onchange = function() {
        let profile_name = dialog.get_value('ai_task_profile');
        if (profile_name) {
            frappe.db.get_doc('AI Task Profile', profile_name).then(function(profile) {
                if (profile.recommended_assignees && profile.recommended_assignees.length > 0) {
                    let recommendations_html = '<div class="text-muted"><small><strong>AI Recommendations:</strong><br>';
                    profile.recommended_assignees.forEach(function(rec, index) {
                        recommendations_html += `${index + 1}. ${rec.employee} - ${rec.overall_fit_score || rec.fit_score}%<br>`;
                    });
                    recommendations_html += '</small></div>';
                    
                    // Add recommendations display
                    if (!dialog.$wrapper.find('.ai-recommendations').length) {
                        dialog.$wrapper.find('.form-section').append(recommendations_html);
                        dialog.$wrapper.find('.ai-recommendations').addClass('ai-recommendations');
                    }
                }
            });
        }
    };
    
    dialog.show();
}

function show_bulk_timesheet_dialog(listview) {
    let selected = listview.get_checked_items();
    if (selected.length === 0) {
        frappe.msgprint(__('Please select assignments first'));
        return;
    }
    
    let dialog = new frappe.ui.Dialog({
        title: __('Bulk Timesheet Creation'),
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
                default: 'Bulk timesheet entry'
            }
        ],
        primary_action: function(data) {
            let promises = selected.map(function(assignment) {
                return frappe.call({
                    method: 'taskflow_ai.taskflow_ai.doctype.employee_task_assignment.employee_task_assignment.create_timesheet_for_assignment',
                    args: {
                        assignment_name: assignment.name,
                        hours_worked: data.hours_worked,
                        description: data.description,
                        activity_type: data.activity_type
                    }
                });
            });
            
            Promise.all(promises).then(function(responses) {
                let success_count = responses.filter(r => r.message.status === 'success').length;
                frappe.msgprint({
                    title: __('Bulk Timesheet Created'),
                    message: `Successfully created timesheets for ${success_count}/${selected.length} assignments`,
                    indicator: success_count === selected.length ? 'green' : 'yellow'
                });
                dialog.hide();
                location.reload();
            });
        },
        primary_action_label: __('Create Timesheets')
    });
    
    dialog.show();
}

// ===== PROJECT MANAGER ASSIGNMENT TOOLS =====

// Show unassigned tasks dashboard
function show_unassigned_tasks_dashboard() {
    frappe.route_options = {
        "status": ["!=", "Completed"],
        "_assign": ["is", "not set"]
    };
    frappe.set_route("List", "Task");
}

// Show bulk assignment dialog
function show_bulk_assignment_dialog() {
    let d = new frappe.ui.Dialog({
        title: __('🎯 Task Assignment by Project'),
        size: 'large',
        fields: [
            {
                fieldname: 'info_html',
                fieldtype: 'HTML',
                options: '<div class="alert alert-info"><strong>Project Manager Tool:</strong> Select a project to view unassigned tasks and create Employee Task Assignment records.</div>'
            },
            {
                fieldname: 'project',
                fieldtype: 'Link',
                label: __('Select Project'),
                options: 'Project',
                reqd: 1,
                change: function() {
                    if (d.get_value('project')) {
                        load_project_unassigned_tasks(d);
                    }
                }
            },
            {
                fieldname: 'tasks_html',
                fieldtype: 'HTML'
            }
        ],
        primary_action: function() { d.hide(); },
        primary_action_label: __('Close')
    });
    d.show();
}

// Load unassigned tasks
function load_project_unassigned_tasks(dialog) {
    let project = dialog.get_value('project');
    frappe.call({
        method: 'taskflow_ai.taskflow_ai.api.assignment_helper.get_unassigned_tasks_by_project',
        args: { project: project },
        callback: function(r) {
            if (r.message) {
                let html = build_task_assignment_html(r.message);
                dialog.fields_dict.tasks_html.$wrapper.html(html);
            }
        }
    });
}

// Build task assignment HTML
function build_task_assignment_html(tasks) {
    if (!tasks || tasks.length === 0) {
        return '<div class="alert alert-success">✅ All tasks in this project are assigned!</div>';
    }
    
    let html = '<div class="task-assignment-list" style="margin-top: 15px;">';
    html += `<h6>📋 Found ${tasks.length} Unassigned Tasks:</h6>`;
    html += '<table class="table table-sm table-bordered">';
    html += '<thead><tr><th>Task</th><th>Subject</th><th>Priority</th><th>🤖 AI</th><th>Action</th></tr></thead><tbody>';
    
    tasks.forEach(function(task) {
        html += '<tr>';
        html += `<td><a href="/app/task/${task.name}" target="_blank">${task.name}</a></td>`;
        html += `<td>${task.subject}</td>`;
        html += `<td><span class="badge badge-info">${task.priority}</span></td>`;
        html += `<td><small>${task.ai_recommendations || '❌ No AI'}</small></td>`;
        html += `<td><button class="btn btn-sm btn-success create-assignment" data-task="${task.name}">👤 Assign</button></td>`;
        html += '</tr>';
    });
    
    html += '</tbody></table></div>';
    
    setTimeout(function() {
        $('.create-assignment').click(function() {
            let task_name = $(this).data('task');
            frappe.route_options = {"task": task_name};
            frappe.new_doc("Employee Task Assignment");
        });
    }, 100);
    
    return html;
}

// Show assignment summary
function show_assignment_summary_dialog() {
    frappe.call({
        method: 'taskflow_ai.taskflow_ai.api.assignment_helper.get_project_assignment_summary',
        callback: function(r) {
            if (r.message) {
                show_summary_results(r.message);
            }
        }
    });
}

function show_summary_results(summary_data) {
    if (!summary_data || summary_data.length === 0) {
        frappe.msgprint('No data found.');
        return;
    }
    
    let html = '<table class="table table-sm">';
    html += '<thead><tr><th>Project</th><th>Total</th><th>✅ Assigned</th><th>⚠️ Unassigned</th><th>✅ Done</th><th>🔄 Progress</th></tr></thead><tbody>';
    
    summary_data.forEach(function(row) {
        html += '<tr>';
        html += `<td><strong>${row.project || 'No Project'}</strong></td>`;
        html += `<td><span class="badge badge-secondary">${row.total_tasks}</span></td>`;
        html += `<td><span class="badge badge-success">${row.assigned_tasks}</span></td>`;
        html += `<td><span class="badge badge-warning">${row.unassigned_tasks}</span></td>`;
        html += `<td><span class="badge badge-info">${row.completed_tasks}</span></td>`;
        html += `<td><span class="badge badge-primary">${row.in_progress_tasks}</span></td>`;
        html += '</tr>';
    });
    
    html += '</tbody></table>';
    
    frappe.msgprint({
        title: __('📊 Assignment Summary'),
        message: html,
        wide: true
    });
}
