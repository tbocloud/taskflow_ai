// Copyright (c) 2025, sammish and contributors
// For license information, please see license.txt

frappe.ui.form.on('Task Template Group', {
    refresh: function(frm) {
        // Add custom buttons for dynamic template management
        if (frm.doc.name && frappe.user.has_role(['System Manager', 'Projects Manager'])) {
            frm.add_custom_button(__('Manage Templates'), function() {
                show_templates_management_dialog(frm);
            }, __('Actions'));
            
            frm.add_custom_button(__('Add Existing Template'), function() {
                show_add_template_dialog(frm);
            }, __('Actions'));
            
            frm.add_custom_button(__('Preview Group'), function() {
                show_group_preview_dialog(frm);
            }, __('Actions'));
        }
        
        // Show group statistics
        if (frm.doc.name) {
            show_group_statistics(frm);
        }
    }
});

function show_group_statistics(frm) {
    frappe.call({
        method: 'taskflow_ai.taskflow_ai.dynamic_template_system.get_group_templates_summary',
        args: {
            group_name: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                let summary = r.message;
                
                frm.dashboard.add_comment(
                    `<div class="group-stats" style="background: #f8f9fa; padding: 12px; border-radius: 6px;">
                        <h6 style="margin: 0 0 8px 0; color: #2c3e50;">📊 Group Statistics</h6>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px;">
                            <div>
                                <strong style="color: #007bff;">${summary.total_templates}</strong>
                                <br><small>Templates</small>
                            </div>
                            <div>
                                <strong style="color: #28a745;">${summary.total_duration}</strong>
                                <br><small>Total Hours</small>
                            </div>
                            <div>
                                <strong style="color: #6f42c1;">${summary.categories.length}</strong>
                                <br><small>Categories</small>
                            </div>
                            <div>
                                <strong style="color: #fd7e14;">${Math.ceil(summary.total_duration / 8)}</strong>
                                <br><small>Est. Days</small>
                            </div>
                        </div>
                        ${summary.categories.length > 0 ? `<div style="margin-top: 10px;"><small><strong>Categories:</strong> ${summary.categories.join(', ')}</small></div>` : ''}
                    </div>`,
                    'blue'
                );
            }
        }
    });
}

function show_templates_management_dialog(frm) {
    frappe.call({
        method: 'taskflow_ai.taskflow_ai.dynamic_template_system.get_templates_by_group',
        args: {
            template_group: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                let templates = r.message;
                show_templates_list_with_actions(templates, frm);
            }
        }
    });
}

function show_templates_list_with_actions(templates, frm) {
    let template_html = '';
    
    if (templates.length === 0) {
        template_html = '<div style="text-align: center; padding: 20px; color: #6c757d;">No templates found in this group</div>';
    } else {
        template_html = templates.map(template => `
            <div class="template-management-item" style="border: 1px solid #dee2e6; margin: 8px 0; padding: 12px; border-radius: 6px; background: #fff;">
                <div style="display: flex; justify-content: between; align-items: start;">
                    <div style="flex: 1;">
                        <div style="display: flex; align-items: center; margin-bottom: 8px;">
                            <input type="number" class="form-control" value="${template.sequence_in_group || 1}" 
                                   style="width: 60px; margin-right: 10px;" 
                                   data-template="${template.name}"
                                   onchange="update_template_sequence('${template.name}', this.value)">
                            <h6 style="margin: 0; flex: 1;">${template.template_name}</h6>
                            <button class="btn btn-sm btn-danger" onclick="remove_template_from_group('${template.name}', '${frm.doc.name}')" 
                                    style="margin-left: 10px;">
                                <i class="fa fa-trash"></i>
                            </button>
                        </div>
                        <div style="font-size: 13px; color: #6c757d;">
                            <strong>Category:</strong> ${template.category || 'N/A'} | 
                            <strong>Duration:</strong> ${template.default_duration_hours || 0} hours |
                            <strong>Priority:</strong> ${template.priority || 'Medium'}
                        </div>
                        ${template.description ? `<div style="margin-top: 5px; font-size: 12px; color: #868e96;">${template.description}</div>` : ''}
                    </div>
                </div>
            </div>
        `).join('');
    }
    
    let d = new frappe.ui.Dialog({
        title: __('Manage Templates in Group: {0}', [frm.doc.name]),
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'templates_html',
                options: `
                    <div id="templates-container" style="max-height: 500px; overflow-y: auto;">
                        ${template_html}
                    </div>
                    <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #dee2e6;">
                        <button class="btn btn-primary btn-sm" onclick="reorder_all_templates('${frm.doc.name}')">
                            <i class="fa fa-sort"></i> Apply Sequence Changes
                        </button>
                        <span style="margin-left: 15px; font-size: 12px; color: #6c757d;">
                            Change sequence numbers and click "Apply Sequence Changes"
                        </span>
                    </div>
                `
            }
        ],
        size: 'large'
    });
    
    d.show();
    
    // Make functions globally available for the dialog
    window.update_template_sequence = function(template_name, sequence) {
        // Store the change, will be applied when user clicks "Apply Sequence Changes"
        console.log(`Template ${template_name} sequence changed to ${sequence}`);
    };
    
    window.remove_template_from_group = function(template_name, group_name) {
        frappe.confirm(
            __('Remove template "{0}" from this group?', [template_name]),
            function() {
                frappe.call({
                    method: 'taskflow_ai.taskflow_ai.dynamic_template_system.remove_template_from_group',
                    args: {
                        template_name: template_name
                    },
                    callback: function(r) {
                        if (r.message && r.message.success) {
                            frappe.show_alert({
                                message: r.message.message,
                                indicator: 'green'
                            });
                            d.hide();
                            frm.reload_doc();
                        } else {
                            frappe.msgprint({
                                title: __('Error'),
                                message: r.message ? r.message.message : __('Failed to remove template'),
                                indicator: 'red'
                            });
                        }
                    }
                });
            }
        );
    };
    
    window.reorder_all_templates = function(group_name) {
        // Collect all sequence changes
        let template_orders = [];
        let inputs = document.querySelectorAll('#templates-container input[data-template]');
        
        inputs.forEach(input => {
            template_orders.push({
                template_name: input.getAttribute('data-template'),
                sequence: parseInt(input.value) || 1
            });
        });
        
        frappe.call({
            method: 'taskflow_ai.taskflow_ai.dynamic_template_system.reorder_templates_in_group',
            args: {
                group_name: group_name,
                template_orders: template_orders
            },
            callback: function(r) {
                if (r.message && r.message.success) {
                    frappe.show_alert({
                        message: r.message.message,
                        indicator: 'green'
                    });
                    d.hide();
                    frm.reload_doc();
                } else {
                    frappe.msgprint({
                        title: __('Error'),
                        message: r.message ? r.message.message : __('Failed to reorder templates'),
                        indicator: 'red'
                    });
                }
            }
        });
    };
}

function show_add_template_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: __('Add Template to Group'),
        fields: [
            {
                label: __('Select Template'),
                fieldname: 'template_name',
                fieldtype: 'Link',
                options: 'Task Template',
                reqd: 1,
                get_query: function() {
                    return {
                        filters: {
                            'active': 1,
                            'task_template_group': ['in', ['', null, frm.doc.name]]  // Show templates not in any group or already in this group
                        }
                    };
                }
            },
            {
                label: __('Sequence in Group'),
                fieldname: 'sequence',
                fieldtype: 'Int',
                default: 1,
                description: __('Order of execution within the group')
            }
        ],
        primary_action_label: __('Add Template'),
        primary_action: function(values) {
            frappe.call({
                method: 'taskflow_ai.taskflow_ai.dynamic_template_system.add_template_to_group',
                args: {
                    template_name: values.template_name,
                    group_name: frm.doc.name,
                    sequence: values.sequence
                },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frappe.show_alert({
                            message: r.message.message,
                            indicator: 'green'
                        });
                        d.hide();
                        frm.reload_doc();
                    } else {
                        frappe.msgprint({
                            title: __('Error'),
                            message: r.message ? r.message.message : __('Failed to add template'),
                            indicator: 'red'
                        });
                    }
                }
            });
        }
    });
    
    d.show();
}

function show_group_preview_dialog(frm) {
    frappe.call({
        method: 'taskflow_ai.taskflow_ai.dynamic_template_system.get_templates_by_group',
        args: {
            template_group: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                let templates = r.message;
                show_templates_execution_preview(templates, frm.doc.name);
            }
        }
    });
}

function show_templates_execution_preview(templates, group_name) {
    if (templates.length === 0) {
        frappe.msgprint({
            title: __('No Templates'),
            message: __('This group has no templates to preview'),
            indicator: 'yellow'
        });
        return;
    }
    
    let execution_html = templates.map((template, index) => {
        let duration = template.default_duration_hours || 0;
        let days = Math.ceil(duration / 8);
        
        return `
            <div class="execution-step" style="display: flex; align-items: center; margin: 10px 0; padding: 10px; border-left: 3px solid #007bff; background: #f8f9fa;">
                <div style="flex: 0 0 40px; text-align: center;">
                    <span style="background: #007bff; color: white; padding: 5px 10px; border-radius: 50%; font-weight: bold;">
                        ${template.sequence_in_group || index + 1}
                    </span>
                </div>
                <div style="flex: 1; margin-left: 15px;">
                    <h6 style="margin: 0 0 5px 0;">${template.template_name}</h6>
                    <div style="font-size: 13px; color: #6c757d;">
                        <strong>Duration:</strong> ${duration} hours (≈${days} day${days !== 1 ? 's' : ''}) | 
                        <strong>Category:</strong> ${template.category} | 
                        <strong>Priority:</strong> ${template.priority || 'Medium'}
                    </div>
                </div>
                <div style="margin-left: 15px;">
                    <span class="badge badge-secondary">${template.level || 'Basic'}</span>
                </div>
            </div>
        `;
    }).join('');
    
    let total_duration = templates.reduce((sum, t) => sum + (t.default_duration_hours || 0), 0);
    let total_days = Math.ceil(total_duration / 8);
    
    let d = new frappe.ui.Dialog({
        title: __('Execution Preview: {0}', [group_name]),
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'preview_html',
                options: `
                    <div style="margin-bottom: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px; border-radius: 8px;">
                        <h5 style="margin: 0 0 10px 0;">🚀 Project Timeline</h5>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 15px;">
                            <div><strong>${templates.length}</strong><br><small>Total Tasks</small></div>
                            <div><strong>${total_duration}</strong><br><small>Total Hours</small></div>
                            <div><strong>${total_days}</strong><br><small>Estimated Days</small></div>
                            <div><strong>${new Set(templates.map(t => t.category)).size}</strong><br><small>Phases</small></div>
                        </div>
                    </div>
                    <h6>📋 Execution Sequence:</h6>
                    <div style="max-height: 400px; overflow-y: auto;">
                        ${execution_html}
                    </div>
                `
            }
        ],
        size: 'large'
    });
    
    d.show();
}
