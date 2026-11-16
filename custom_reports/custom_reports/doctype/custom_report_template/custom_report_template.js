// Copyright (c) 2026
frappe.ui.form.on("Custom Report Template", {
	refresh(frm) {
		if (window.custom_reports && custom_reports.mount_editor) {
			custom_reports.mount_editor(frm, { field: "blocks", html_field: "editor", preview: false });
		}
	},
});
