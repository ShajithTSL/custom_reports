import frappe


def boot_session(bootinfo):
	try:
		bootinfo.custom_reports_doctypes = [
			r.document_type for r in frappe.get_cached_doc("Custom Reports Settings").get("doctypes") or [] if r.document_type
		]
	except Exception:
		bootinfo.custom_reports_doctypes = []
