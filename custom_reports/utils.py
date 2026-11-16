"""Placeholders: {{fieldname}} in block text is replaced by the document's value when printing.

  {{customer_name}}            a field on the document
  {{customer.customer_group}}  a field of a linked document (follow a Link field)
  {{items[2].model}}           a child-table row (counted from 1; -1 = last row)
  {{today}}                    today's date
A placeholder whose value is empty prints as a blank line ( __________ ), handy for "Name: {{signatory}}".
"""

import re

import frappe
from frappe.utils import escape_html, formatdate, nowdate, strip_html

PH_RE = re.compile(r"\{\{\s*([A-Za-z0-9_\.\[\]\-]+)\s*\}\}")
SEG_RE = re.compile(r"^([A-Za-z0-9_]+)(?:\[(-?\d+)\])?$")
BLANK = "__________"


def _fmt(doc, fieldname):
	v = doc.get(fieldname)
	if v in (None, ""):
		return ""
	try:
		out = doc.get_formatted(fieldname)
	except Exception:
		out = v
	out = str(out if out not in (None, "") else v)
	return strip_html(out).strip() if "<" in out else out.strip()


def resolve(doc, path):
	if path == "today":
		return formatdate(nowdate())
	if path == "name":
		return doc.name or ""
	cur = doc
	segs = path.split(".")
	for i, seg in enumerate(segs):
		m = SEG_RE.match(seg)
		if not m or cur is None:
			return ""
		name, idx = m.group(1), m.group(2)
		last = i == len(segs) - 1
		df = cur.meta.get_field(name) if hasattr(cur, "meta") else None
		if name == "name" and last:
			return cur.name or ""
		if not df:
			return ""
		if df.fieldtype in ("Table", "Table MultiSelect"):
			rows = cur.get(name) or []
			k = int(idx) if idx else 1
			k = k - 1 if k > 0 else k
			if not rows or not (-len(rows) <= k < len(rows)):
				return ""
			cur = rows[k]
			if last:
				return ""
			continue
		if last:
			return _fmt(cur, name)
		if df.fieldtype in ("Link", "Dynamic Link"):
			val = cur.get(name)
			dt = df.options if df.fieldtype == "Link" else cur.get(df.options)
			if not val or not dt or not frappe.db.exists(dt, val):
				return ""
			cur = frappe.get_cached_doc(dt, val)
			if not frappe.has_permission(dt, "read", cur):
				return ""
		else:
			return ""
	return ""


def fill(doc, text, escape=True, blank=BLANK):
	"""Replace {{placeholders}} in text (HTML from the editor, or plain lines)."""
	if not text or "{{" not in str(text):
		return text or ""

	def sub(m):
		v = resolve(doc, m.group(1))
		if not v:
			return blank
		return escape_html(v) if escape else v

	return PH_RE.sub(sub, str(text))


def data_rows(doc, source, col_fields):
	"""Rows for a Data Table block: list of lists of formatted cell values."""
	rows = doc.get(source) or [] if source else []
	fields = [c.strip() for c in (col_fields or "").split(",") if c.strip()]
	out = []
	for i, r in enumerate(rows, 1):
		out.append([str(i) if f in ("#", "idx", "no") else _fmt(r, f) for f in fields])
	return out


@frappe.whitelist()
def get_fields(doctype):
	"""Fields offered in the editor's 'Insert field' list."""
	frappe.has_permission(doctype, "read", throw=True)
	skip = {"Section Break", "Column Break", "Tab Break", "HTML", "Button", "Fold", "Heading", "Image"}
	meta = frappe.get_meta(doctype)
	out = [{"fieldname": "name", "label": "ID / Name", "fieldtype": "Data"}, {"fieldname": "today", "label": "Today's date", "fieldtype": "Date"}]
	for df in meta.fields:
		if df.fieldtype in skip or df.fieldname.startswith("cr_"):
			continue
		row = {"fieldname": df.fieldname, "label": df.label or df.fieldname, "fieldtype": df.fieldtype}
		if df.fieldtype in ("Table", "Table MultiSelect"):
			row["children"] = [{"fieldname": c.fieldname, "label": c.label or c.fieldname, "fieldtype": c.fieldtype}
							   for c in frappe.get_meta(df.options).fields if c.fieldtype not in skip]
		out.append(row)
	return out


def header_logo(doc, logo=None):
	"""Logo for the page header: the uploaded one, else the document's Company logo,
	else the default Company's logo, else the site logo (Navbar / Website Settings)."""
	if logo:
		return logo
	try:
		company = doc.get("company") if doc else None
		if not company:
			company = frappe.defaults.get_global_default("company") or frappe.db.get_single_value("Global Defaults", "default_company")
		if company and frappe.db.exists("DocType", "Company") and frappe.get_meta("Company").has_field("company_logo"):
			img = frappe.db.get_value("Company", company, "company_logo")
			if img:
				return img
		for dt, f in (("Navbar Settings", "app_logo"), ("Website Settings", "app_logo"), ("Website Settings", "banner_image")):
			if frappe.db.exists("DocType", dt) and frappe.get_meta(dt).has_field(f):
				img = frappe.db.get_single_value(dt, f)
				if img:
					return img
	except Exception:
		pass
	return None
