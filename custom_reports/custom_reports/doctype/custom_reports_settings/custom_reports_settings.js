frappe.ui.form.on("Custom Reports Settings", {
	refresh(frm) {
		frm.set_intro(__("Add the DocType that should get the report editor (e.g. your Maintenance Contract DocType) and save. Then reload the page (Ctrl+Shift+R) and open a document of that type."));
	},
	after_save() {
		frappe.msgprint(__("Saved. Reload the page (Ctrl+Shift+R) so the editor appears on the enabled DocTypes."));
	},
});
