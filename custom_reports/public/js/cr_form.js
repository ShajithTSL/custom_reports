// Custom Reports – form behaviour for every DocType enabled in "Custom Reports Settings".
frappe.provide("custom_reports");

(() => {
	if (custom_reports._form_loaded) return;
	custom_reports._form_loaded = true;

	const TPL = "Custom Report Template";
	const pf_name = (dt) => `Custom Report - ${dt}`.slice(0, 140);

	const cr = {
		async load_template(frm, template, mode) {
			const tpl = await frappe.db.get_doc(TPL, template);
			frm.__cr_loading = true;
			try {
				if (frm.doc.cr_template !== tpl.name) await frm.set_value("cr_template", tpl.name);
				if (mode !== "Append") frm.clear_table("cr_blocks");
				if (frm.fields_dict.cr_header_text && (mode !== "Append" || !frm.doc.cr_header_text) && tpl.header_text)
					await frm.set_value("cr_header_text", tpl.header_text);
				(tpl.blocks || []).forEach((r) => {
					const row = {};
					custom_reports.BLOCK_FIELDS.forEach((f) => { if (r[f] !== undefined && r[f] !== null) row[f] = r[f]; });
					frm.add_child("cr_blocks", row);
				});
				frm.refresh_field("cr_blocks");
				await cr.fill_images(frm);
				cr.mount(frm);
				frappe.show_alert({ message: __("Template {0} loaded", [tpl.name]), indicator: "green" });
			} finally {
				frm.__cr_loading = false;
			}
		},

		async fill_images(frm) {
			if (!(frm.doc.cr_blocks || []).some((b) => b.block_type === "Image" && b.image_from && !b.image)) return;
			const r = await frappe.call({ method: "custom_reports.api.fill_images", args: { doc: frm.doc } });
			(r.message || []).forEach((x) => {
				const b = (frm.doc.cr_blocks || []).find((d) => d.name === x.name);
				if (b && !b.image) b.image = x.image;
			});
		},

		choose_template(frm) {
			const d = new frappe.ui.Dialog({
				title: __("Load Template"),
				fields: [
					{ fieldname: "template", fieldtype: "Link", label: __("Template"), options: TPL, reqd: 1,
					  get_query: () => ({ filters: { disabled: 0, reference_doctype: ["in", [frm.doctype, ""]] } }) },
					{ fieldname: "mode", fieldtype: "Select", label: __("Mode"), options: "Replace\nAppend", default: "Replace",
					  description: __("Replace clears the current blocks. Append adds the template's blocks at the end.") },
				],
				primary_action_label: __("Load"),
				primary_action: (v) => { d.hide(); cr.load_template(frm, v.template, v.mode); },
			});
			d.show();
		},

		save_as_template(frm) {
			frappe.prompt([
				{ fieldname: "template_name", fieldtype: "Data", label: __("Template Name"), reqd: 1 },
				{ fieldname: "description", fieldtype: "Data", label: __("Short description (optional)") },
				{ fieldname: "for_this_doctype", fieldtype: "Check", label: __("Only for {0}", [__(frm.doctype)]), default: 1 },
			], (v) => {
				frappe.call({
					method: "custom_reports.api.save_as_template",
					args: { source_doctype: frm.doctype, source_name: frm.doc.name, template_name: v.template_name,
						description: v.description, for_this_doctype: v.for_this_doctype },
					freeze: true,
					callback: (r) => r.message && frappe.show_alert({ message: __("Template {0} saved", [r.message]), indicator: "green" }),
				});
			}, __("Save as Template"), __("Save"));
		},

		update_template(frm) {
			frappe.confirm(__("Replace the content of template {0} with this document's report?", [frm.doc.cr_template.bold()]), () => {
				frappe.call({
					method: "custom_reports.api.update_template",
					args: { source_doctype: frm.doctype, source_name: frm.doc.name, template_name: frm.doc.cr_template },
					freeze: true,
					callback: (r) => r.message && frappe.show_alert({ message: __("Template {0} updated", [r.message]), indicator: "green" }),
				});
			});
		},

		mount(frm) {
			if (!frm.fields_dict.cr_editor) return;
			custom_reports.mount_editor(frm, {
				field: "cr_blocks", html_field: "cr_editor", preview: true, template_picker: true,
				on_load_template: (frm, name, mode) => cr.load_template(frm, name, mode),
				on_choose_template: (frm) => cr.choose_template(frm),
			});
		},
	};
	custom_reports.form = cr;

	const handlers = {
		refresh(frm) {
			if (!frm.fields_dict.cr_editor) {
				frm.dashboard.set_headline_alert(__("Custom Reports: fields missing – open Custom Reports Settings and save, or run bench migrate."), "orange");
				return;
			}
			cr.mount(frm);
			frm.add_custom_button(__("Edit Report"), () => frappe.utils.scroll_to(frm.fields_dict.cr_editor.$wrapper, true, 120))
				.removeClass("btn-default").addClass("btn-primary");
			frm.add_custom_button(__("Load Template"), () => cr.choose_template(frm), __("Report"));
			if (!frm.is_new()) {
				frm.add_custom_button(__("Save as Template"), () => cr.save_as_template(frm), __("Report"));
				if (frm.doc.cr_template) frm.add_custom_button(__("Update Template {0}", [frm.doc.cr_template]), () => cr.update_template(frm), __("Report"));
				frm.add_custom_button(__("Print / PDF"), () => {
					const q = new URLSearchParams({ doctype: frm.doctype, name: frm.doc.name, format: pf_name(frm.doctype), no_letterhead: 1 });
					window.open(`/printview?${q.toString()}`, "_blank");
				}, __("Report"));
			}
		},
		cr_header_text(frm) {
			if (frm.__tre && frm.__tre.show_preview) frm.__tre.refresh_preview();
		},
		cr_template(frm) {
			if (frm.__cr_loading || !frm.doc.cr_template) return;
			const go = () => cr.load_template(frm, frm.doc.cr_template, "Replace");
			if ((frm.doc.cr_blocks || []).length) frappe.confirm(__("Replace the current report with template {0}?", [frm.doc.cr_template]), go);
			else go();
		},
	};

	const dts = (frappe.boot && frappe.boot.custom_reports_doctypes) || [];
	dts.forEach((dt) => frappe.ui.form.on(dt, handlers));
})();
