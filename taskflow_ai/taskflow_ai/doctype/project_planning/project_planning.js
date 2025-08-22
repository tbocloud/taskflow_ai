// Copyright (c) 2025, TaskFlow AI and contributors
// For license information, please see license.txt

frappe.ui.form.on('Project Planning', {
    refresh: function(frm) {
        // Show success message for converted leads
        if (frm.doc.lead && frm.doc.lead_status === "Converted" && frm.doc.docstatus === 0) {
            frm.dashboard.set_headline_alert(
                `<div class="alert alert-success" role="alert">
                    <i class="fa fa-check-circle"></i> 
                    <strong>Project Planning Created Successfully!</strong> 
                    This converted lead now has Project Planning for manager review and approval. 
                    Click "Create Project" once approved to generate the actual project and tasks.
                </div>`,
                'green'
            );
        }
        
        // Add custom buttons based on status
        if (frm.doc.docstatus === 0) {
            if (frm.doc.planning_status === "Draft") {
                frm.add_custom_button(__('Submit for Review'), function() {
                    frm.set_value('planning_status', 'Under Review');
                    frm.save();
                }, __('Actions'));
            }
            
            if (frm.doc.planning_status === "Under Review" && frappe.user.has_role('Projects Manager')) {
                frm.add_custom_button(__('Approve'), function() {
                    show_approval_dialog(frm);
                }, __('Review'));
                
                frm.add_custom_button(__('Reject'), function() {
                    show_rejection_dialog(frm);
                }, __('Review'));
            }
            
            if (frm.doc.planning_status === "Approved") {
                frm.add_custom_button(__('Create Project'), function() {
                    frm.submit();
                }, __('Actions')).addClass('btn-primary');
            }
            
            if (frm.doc.planning_status === "Rejected") {
                frm.add_custom_button(__('Resubmit for Review'), function() {
                    frm.set_value('planning_status', 'Under Review');
                    frm.save();
                }, __('Actions'));
            }
        }
        
        // Add helpful workflow guidance
        if (frm.doc.docstatus === 0) {
            let workflow_help = "";
            
            switch(frm.doc.planning_status) {
                case "Draft":
                    workflow_help = `<div class="alert alert-info">
                        <i class="fa fa-info-circle"></i> 
                        <strong>Next Step:</strong> Review the planning details below, then click "Submit for Review" when ready.
                    </div>`;
                    break;
                case "Under Review":
                    workflow_help = `<div class="alert alert-warning">
                        <i class="fa fa-clock-o"></i> 
                        <strong>Status:</strong> Waiting for Project Manager approval. The planning is under review.
                    </div>`;
                    break;
                case "Approved":
                    workflow_help = `<div class="alert alert-success">
                        <i class="fa fa-thumbs-up"></i> 
                        <strong>Ready to Create:</strong> Planning approved! Click "Create Project" to generate the actual project and tasks.
                    </div>`;
                    break;
                case "Rejected":
                    workflow_help = `<div class="alert alert-danger">
                        <i class="fa fa-times-circle"></i> 
                        <strong>Needs Updates:</strong> Please review the feedback below and resubmit when ready.
                    </div>`;
                    break;
            }
            
            if (workflow_help) {
                frm.dashboard.add_comment(workflow_help, 'blue', true);
            }
        }
        
        // Show project link if created
        if (frm.doc.generated_project) {
            frm.add_custom_button(__('View Project'), function() {
                frappe.set_route('Form', 'Project', frm.doc.generated_project);
            }, __('View'));
            
            frm.add_custom_button(__('View Tasks'), function() {
                frappe.set_route('List', 'Task', {'project': frm.doc.generated_project});
            }, __('View'));
        }
        
        // Set status indicator colors
        set_status_indicator(frm);
        
        // Show warnings/info
        show_form_alerts(frm);
    },
    
    lead: function(frm) {
        // Auto-populate lead details when lead is selected
        if (frm.doc.lead) {
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Lead',
                    name: frm.doc.lead
                },
                callback: function(r) {
                    if (r.message) {
                        let lead = r.message;
                        frm.set_value('lead_name', lead.lead_name);
                        frm.set_value('company_name', lead.company_name);
                        frm.set_value('lead_status', lead.status);
                        
                        if (lead.custom_lead_segment) {
                            frm.set_value('lead_segment', lead.custom_lead_segment);
                        }
                        
                        // Auto-set project title
                        if (!frm.doc.project_title && lead.company_name) {
                            frm.set_value('project_title', `Project - ${lead.company_name}`);
                        }
                        
                        // Set expected budget from lead annual revenue (10% estimate)
                        if (!frm.doc.expected_budget && lead.annual_revenue) {
                            let estimated_budget = lead.annual_revenue * 0.1;
                            frm.set_value('expected_budget', estimated_budget);
                        }
                        
                        // Check if lead is already converted
                        if (lead.status === 'Converted') {
                            frappe.msgprint({
                                title: __('Warning'),
                                message: __('This lead has already been converted to a project'),
                                indicator: 'orange'
                            });
                        }
                    }
                }
            });
        }
    },
    
    estimated_duration_months: function(frm) {
        // Auto-calculate end date when duration changes
        if (frm.doc.expected_start_date && frm.doc.estimated_duration_months) {
            let start_date = frappe.datetime.str_to_obj(frm.doc.expected_start_date);
            let end_date = frappe.datetime.add_months(start_date, frm.doc.estimated_duration_months);
            frm.set_value('expected_end_date', frappe.datetime.obj_to_str(end_date));
        }
    },
    
    expected_start_date: function(frm) {
        // Auto-calculate end date when start date changes
        if (frm.doc.expected_start_date && frm.doc.estimated_duration_months) {
            let start_date = frappe.datetime.str_to_obj(frm.doc.expected_start_date);
            let end_date = frappe.datetime.add_months(start_date, frm.doc.estimated_duration_months);
            frm.set_value('expected_end_date', frappe.datetime.obj_to_str(end_date));
        }
    },
    
    planning_status: function(frm) {
        // Update form appearance based on status change
        set_status_indicator(frm);
        show_form_alerts(frm);
    },
    
});

function set_status_indicator(frm) {
    // Set dashboard indicator colors based on status
    let status = frm.doc.planning_status;
    let color = 'grey';
    
    switch(status) {
        case 'Draft':
            color = 'blue';
            break;
        case 'Under Review':
            color = 'orange';
            break;
        case 'Approved':
            color = 'green';
            break;
        case 'Rejected':
            color = 'red';
            break;
        case 'On Hold':
            color = 'yellow';
            break;
    }
    
    frm.dashboard.set_headline_alert(
        `<div class="row">
            <div class="col-md-12">
                <span class="indicator ${color}">${__(status)}</span>
            </div>
        </div>`
    );
}

function show_form_alerts(frm) {
    // Show relevant alerts based on status and data
    let alerts = [];
    
    if (frm.doc.lead && frm.doc.lead_status === 'Converted') {
        alerts.push({
            message: __('Warning: This lead has already been converted'),
            indicator: 'orange'
        });
    }
    
    if (frm.doc.planning_status === 'Under Review') {
        alerts.push({
            message: __('This project planning is under review by the Project Manager'),
            indicator: 'blue'
        });
    }
    
    if (frm.doc.planning_status === 'Approved' && frm.doc.docstatus === 0) {
        alerts.push({
            message: __('Project planning is approved. Click "Create Project" to generate the actual project and tasks.'),
            indicator: 'green'
        });
    }
    
    if (frm.doc.planning_status === 'Rejected') {
        alerts.push({
            message: __('Project planning was rejected. Please review comments and make necessary changes.'),
            indicator: 'red'
        });
    }
    
    if (frm.doc.generated_project) {
        alerts.push({
            message: __(`Project created successfully: ${frm.doc.generated_project} with ${frm.doc.tasks_generated_count || 0} tasks`),
            indicator: 'green'
        });
    }
    
    // Display alerts
    alerts.forEach(alert => {
        frm.dashboard.add_comment(alert.message, alert.indicator, true);
    });
}

function show_approval_dialog(frm) {
    let dialog = new frappe.ui.Dialog({
        title: __('Approve Project Planning'),
        fields: [
            {
                fieldname: 'assigned_project_manager',
                fieldtype: 'Link',
                label: __('Assign Project Manager'),
                options: 'User',
                reqd: 1,
                default: frm.doc.assigned_project_manager
            },
            {
                fieldname: 'review_comments',
                fieldtype: 'Text',
                label: __('Review Comments'),
                description: __('Add any comments or feedback for the approval')
            }
        ],
        primary_action_label: __('Approve'),
        primary_action: function(values) {
            // Set values on form
            frm.set_value('assigned_project_manager', values.assigned_project_manager);
            frm.set_value('planning_status', 'Approved');
            frm.set_value('reviewed_by', frappe.session.user);
            frm.set_value('review_date', frappe.datetime.now_datetime());
            
            if (values.review_comments) {
                frm.set_value('review_comments', values.review_comments);
            }
            
            frm.save().then(() => {
                frappe.msgprint({
                    title: __('Approved'),
                    message: __('Project planning has been approved successfully'),
                    indicator: 'green'
                });
                dialog.hide();
            });
        }
    });
    
    dialog.show();
}

function show_rejection_dialog(frm) {
    let dialog = new frappe.ui.Dialog({
        title: __('Reject Project Planning'),
        fields: [
            {
                fieldname: 'rejection_reason',
                fieldtype: 'Select',
                label: __('Rejection Reason'),
                options: 'Insufficient Budget\\nUnclear Requirements\\nResource Constraints\\nTiming Issues\\nOther',
                reqd: 1
            },
            {
                fieldname: 'review_comments',
                fieldtype: 'Text',
                label: __('Review Comments'),
                reqd: 1,
                description: __('Provide detailed feedback for the rejection')
            }
        ],
        primary_action_label: __('Reject'),
        primary_action: function(values) {
            // Set values on form
            frm.set_value('planning_status', 'Rejected');
            frm.set_value('rejection_reason', values.rejection_reason);
            frm.set_value('review_comments', values.review_comments);
            frm.set_value('reviewed_by', frappe.session.user);
            frm.set_value('review_date', frappe.datetime.now_datetime());
            
            frm.save().then(() => {
                frappe.msgprint({
                    title: __('Rejected'),
                    message: __('Project planning has been rejected'),
                    indicator: 'red'
                });
                dialog.hide();
            });
        }
    });
    
    dialog.show();
}
