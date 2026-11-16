"""Enable the report editor on DocTypes and install starter templates.

    bench --site <site> execute custom_reports.setup.install.enable_all
    bench --site <site> execute custom_reports.setup.install.install_templates
"""

import json
import os

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from custom_reports.constants import SETTINGS_DOCTYPE, TEMPLATE_DOCTYPE

PRINT_TEMPLATE = '{% include "custom_reports/templates/print/custom_report.html" %}'
SEEDED_KEY = "custom_reports_seeded_templates"


def report_fields():
	"""Added to every enabled DocType (all prefixed cr_)."""
	return [
		dict(fieldname="cr_sb_report", fieldtype="Section Break", label="Report Content", collapsible=0),
		dict(fieldname="cr_template", fieldtype="Link", label="Start from Template", options=TEMPLATE_DOCTYPE,
			 description="Pick a template to fill the report. You can change everything afterwards."),
		dict(fieldname="cr_header_text", fieldtype="Small Text", label="Header Title (next to the logo)",
			 description="Printed on the right of the logo on every page. Placeholders like {{customer_name}} work. "
						 "Empty = the text from Custom Reports Settings."),
		dict(fieldname="cr_editor", fieldtype="HTML", label="Editor"),
		dict(fieldname="cr_sb_raw", fieldtype="Section Break", label="Advanced: Report Block Table", collapsible=1),
		dict(fieldname="cr_blocks", fieldtype="Table", label="Report Blocks", options="Custom Report Block"),
	]


def print_format_name(doctype):
	return f"Custom Report - {doctype}"[:140]


def enable_doctype(doctype, set_default=False):
	if not frappe.db.exists("DocType", doctype):
		return None
	meta = frappe.get_meta(doctype)
	if meta.istable or meta.issingle:
		frappe.msgprint(f"{doctype}: child tables and single DocTypes are not supported")
		return None

	fields = report_fields()
	last = next((df.fieldname for df in reversed(meta.fields) if not df.fieldname.startswith("cr_")), None)
	prev = last
	for df in fields:
		if prev:
			df["insert_after"] = prev
		prev = df["fieldname"]

	if frappe.db.get_value("DocType", doctype, "custom"):
		dt = frappe.get_doc("DocType", doctype)
		have = {d.fieldname for d in dt.fields}
		changed = False
		for df in fields:
			if df["fieldname"] not in have:
				dt.append("fields", {k: v for k, v in df.items() if k != "insert_after"})
				changed = True
		if changed:
			dt.save()
	else:
		create_custom_fields({doctype: fields}, update=True)

	name = print_format_name(doctype)
	if frappe.db.exists("Print Format", name):
		pf = frappe.get_doc("Print Format", name)
	else:
		pf = frappe.new_doc("Print Format")
		pf.name = name
		pf.__newname = name
	pf.update({
		"doc_type": doctype, "module": "Custom Reports", "standard": "No", "custom_format": 1,
		"print_format_type": "Jinja", "html": PRINT_TEMPLATE, "disabled": 0,
	})
	pf.flags.ignore_permissions = True
	pf.save() if not pf.is_new() else pf.insert()

	if set_default:
		from frappe.custom.doctype.property_setter.property_setter import make_property_setter

		make_property_setter(doctype, None, "default_print_format", name, "Data", for_doctype=True)
	frappe.clear_cache(doctype=doctype)
	return name


def enable_all():
	if not frappe.db.exists("DocType", SETTINGS_DOCTYPE):
		return
	settings = frappe.get_single(SETTINGS_DOCTYPE)
	for row in settings.get("doctypes") or []:
		if not row.document_type:
			continue
		name = enable_doctype(row.document_type, set_default=row.set_default)
		if name and row.print_format != name:
			frappe.db.set_value(row.doctype, row.name, "print_format", name, update_modified=False)
	frappe.clear_cache()


def install_templates(overwrite=False, only_new=False):
	folder = os.path.join(os.path.dirname(__file__), "templates")
	try:
		seeded = set(json.loads(frappe.db.get_default(SEEDED_KEY) or "[]"))
	except Exception:
		seeded = set()
	if only_new and not frappe.db.count(TEMPLATE_DOCTYPE):
		only_new = False
	for fname in sorted(os.listdir(folder)):
		if not fname.endswith(".json"):
			continue
		with open(os.path.join(folder, fname)) as fh:
			data = json.load(fh)
		data.pop("doctype", None)
		name = data["template_name"]
		if frappe.db.exists(TEMPLATE_DOCTYPE, name):
			seeded.add(name)
			if not overwrite:
				continue
			frappe.delete_doc(TEMPLATE_DOCTYPE, name, force=True)
		elif only_new and name in seeded:
			continue
		doc = frappe.get_doc({"doctype": TEMPLATE_DOCTYPE, **data})
		doc.owner = "Administrator"
		doc.insert(ignore_permissions=True)
		seeded.add(name)
		print(f"[custom_reports] installed template: {name}")
	frappe.db.set_default(SEEDED_KEY, json.dumps(sorted(seeded)))


def after_install():
	install_templates()


HEADER_DEFAULTS = {
	"show_header": 1, "logo_height": 14, "header_line_color": "#C9D3DE",
	"header_text": "Maintenance Contract — {{supplier_name}} / {{customer_name}}",
}


def set_header_defaults():
	"""Single DocTypes don't get defaults for fields added later – set them once."""
	if not frappe.db.exists("DocType", SETTINGS_DOCTYPE) or frappe.db.get_default("custom_reports_header_defaults"):
		return
	# read tabSingles directly: a missing Check field would otherwise read as 0
	have = {r[0]: r[1] for r in frappe.db.sql(
		"select field, value from `tabSingles` where doctype=%s", SETTINGS_DOCTYPE)}
	for k, v in HEADER_DEFAULTS.items():
		if have.get(k) in (None, ""):
			frappe.db.set_value(SETTINGS_DOCTYPE, None, k, v, update_modified=False)
	frappe.db.set_default("custom_reports_header_defaults", "1")


def after_migrate():
	set_header_defaults()
	enable_all()
	install_templates(only_new=True)
