frappe.ui.form.on('AI Task Profile', {
    refresh: function(frm) {
        // Add Generate AI Predictions button
        if (frm.doc.task) {
            frm.add_custom_button(__('Generate AI Predictions'), function() {
                frappe.call({
                    method: 'taskflow_ai.taskflow_ai.api.ai_predictions.generate_predictions',
                    args: {
                        task_id: frm.doc.task
                    },
                    callback: function(response) {
                        if (response.message && response.message.status === 'success') {
                            // Update all prediction fields
                            frm.set_value('predicted_duration_hours', response.message.predicted_duration_hours);
                            frm.set_value('predicted_due_date', response.message.predicted_due_date);
                            frm.set_value('slip_risk_percentage', response.message.slip_risk_percentage);
                            frm.set_value('confidence_score', response.message.confidence_score);
                            frm.set_value('complexity_score', response.message.complexity_score);
                            frm.set_value('explanation', response.message.explanation);
                            frm.set_value('model_version', 'TaskFlow_AI_v2.1_2025-08');
                            frm.set_value('last_updated', frappe.datetime.now_datetime());
                            frm.save();
                            frappe.show_alert({
                                message: __('AI Predictions Generated Successfully'),
                                indicator: 'green'
                            }, 5);
                        }
                    },
                    error: function(err) {
                        frappe.show_alert({
                            message: __('Failed to generate AI predictions'),
                            indicator: 'red'
                        }, 5);
                    }
                });
            }, __('Actions'));
        }
        
        // Add button to update all task dates (for admin users)
        if (frappe.user.has_role('System Manager')) {
            frm.add_custom_button(__('Fix Task Dates'), function() {
                frappe.confirm(
                    __('This will update all tasks with staggered dates. Continue?'),
                    function() {
                        frappe.call({
                            method: 'taskflow_ai.taskflow_ai.api.ai_predictions.update_task_dates',
                            callback: function(response) {
                                if (response.message && response.message.status === 'success') {
                                    frappe.show_alert({
                                        message: __('Updated {0} tasks with staggered dates', [response.message.updated_count]),
                                        indicator: 'green'
                                    }, 5);
                                }
                            }
                        });
                    }
                );
            }, __('Admin'));
        }
        
        // Add bulk generate button
        if (frappe.user.has_role('System Manager')) {
            frm.add_custom_button(__('Bulk Generate Predictions'), function() {
                frappe.confirm(
                    __('This will generate AI predictions for all tasks without profiles. Continue?'),
                    function() {
                        frappe.call({
                            method: 'taskflow_ai.taskflow_ai.api.ai_predictions.bulk_generate_predictions',
                            callback: function(response) {
                                if (response.message && response.message.status === 'success') {
                                    frappe.show_alert({
                                        message: __('Generated predictions for {0} tasks', [response.message.created_count]),
                                        indicator: 'green'
                                    }, 5);
                                    frm.reload_doc();
                                }
                            }
                        });
                    }
                );
            }, __('Admin'));
        }
    },
    
    // Auto-generate predictions when task is selected
    task: function(frm) {
        if (frm.doc.task && !frm.doc.predicted_duration_hours) {
            // Auto-generate predictions for new profiles
            setTimeout(function() {
                frm.page.btn_primary.click(); // Trigger Generate AI Predictions
            }, 1000);
        }
    },
    
    // Calculate prediction accuracy when actual data is entered
    actual_duration_hours: function(frm) {
        if (frm.doc.actual_duration_hours && frm.doc.predicted_duration_hours) {
            let predicted = frm.doc.predicted_duration_hours;
            let actual = frm.doc.actual_duration_hours;
            let accuracy = Math.max(0, 100 - (Math.abs(predicted - actual) / actual * 100));
            frm.set_value('prediction_accuracy', Math.min(accuracy, 100));
        }
    },
    
    // Validate fields
    validate: function(frm) {
        // Ensure confidence score is between 0 and 1
        if (frm.doc.confidence_score && (frm.doc.confidence_score < 0 || frm.doc.confidence_score > 1)) {
            frappe.msgprint(__('Confidence Score must be between 0 and 1'));
            frappe.validated = false;
        }
        
        // Ensure complexity score is between 0 and 1
        if (frm.doc.complexity_score && (frm.doc.complexity_score < 0 || frm.doc.complexity_score > 1)) {
            frappe.msgprint(__('Complexity Score must be between 0 and 1'));
            frappe.validated = false;
        }
        
        // Ensure slip risk is between 0 and 100
        if (frm.doc.slip_risk_percentage && (frm.doc.slip_risk_percentage < 0 || frm.doc.slip_risk_percentage > 100)) {
            frappe.msgprint(__('Slip Risk must be between 0 and 100%'));
            frappe.validated = false;
        }
    }
});