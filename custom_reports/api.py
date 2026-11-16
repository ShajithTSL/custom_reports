"""Server helpers: templates, previews, photo rotation."""

import base64
import json

import frappe
from frappe import _

from custom_reports.constants import BLOCK_FIELDS, TEMPLATE_DOCTYPE
from custom_reports.setup.install import PRINT_TEMPLATE, print_format_name


def _enabled(doctype):
	rows = frappe.get_cached_doc("Custom Reports Settings").get("doctypes") or []
	return any(r.document_type == doctype for r in rows)


def _doc_from_client(doc):
	if isinstance(doc, str):
		doc = json.loads(doc)
	dt = (doc or {}).get("doctype")
	if not dt or not _enabled(dt):
		frappe.throw(_("Custom Reports is not enabled for this document type"))
	frappe.has_permission(dt, "read", throw=True)
	return frappe.get_doc(doc)


# ----------------------------------------------------------------------------- templates
@frappe.whitelist()
def get_template_list(doctype=None, search=None, show_all=0, limit=5):
	"""Empty-document picker: the user's own templates (latest 5), else Administrator's.
	show_all / search: every template. Templates for other DocTypes are left out."""
	frappe.has_permission(TEMPLATE_DOCTYPE, "read", throw=True)
	fields = ["name", "reference_doctype", "description", "modified", "owner"]
	base = [["disabled", "=", 0]]
	if doctype:
		base.append(["reference_doctype", "in", [doctype, ""]])  # "" also matches empty (NULL)
	user = frappe.session.user

	def count(extra=None):
		return len(frappe.get_all(TEMPLATE_DOCTYPE, filters=base + (extra or []), pluck="name"))

	total_all = count()
	search = (search or "").strip()
	if search or int(show_all or 0):
		or_filters = [["name", "like", f"%{search}%"], ["description", "like", f"%{search}%"]] if search else None
		items = frappe.get_all(TEMPLATE_DOCTYPE, filters=base, or_filters=or_filters, fields=fields,
							   order_by="modified desc", limit_page_length=200)
		return {"scope": "all", "items": items, "total_scope": len(items), "total_all": total_all}

	mine = count([["owner", "=", user]]) if user != "Administrator" else 0
	scope = "mine" if mine else "company"
	extra = [["owner", "=", user]] if mine else [["owner", "=", "Administrator"]]
	items = frappe.get_all(TEMPLATE_DOCTYPE, filters=base + extra, fields=fields, order_by="modified desc",
						   limit_page_length=int(limit or 5))
	if not items:
		items = frappe.get_all(TEMPLATE_DOCTYPE, filters=base, fields=fields, order_by="modified desc",
							   limit_page_length=int(limit or 5))
	return {"scope": scope, "items": items, "total_scope": count(extra) or len(items), "total_all": total_all}


@frappe.whitelist()
def save_as_template(source_doctype, source_name, template_name, for_this_doctype=1, description=None):
	"""Save a document's blocks as a reusable template (photos are not copied)."""
	src = frappe.get_doc(source_doctype, source_name)
	src.check_permission("read")
	if frappe.db.exists(TEMPLATE_DOCTYPE, template_name):
		frappe.throw(_("Template {0} already exists").format(frappe.bold(template_name)))
	tpl = frappe.new_doc(TEMPLATE_DOCTYPE)
	tpl.template_name = template_name
	tpl.reference_doctype = source_doctype if int(for_this_doctype or 0) else None
	tpl.description = description
	tpl.header_text = src.get("cr_header_text")
	for r in src.get("cr_blocks") or []:
		row = {f: r.get(f) for f in BLOCK_FIELDS if r.get(f) is not None}
		row.pop("image", None)
		tpl.append("blocks", row)
	tpl.insert()
	return tpl.name


@frappe.whitelist()
def update_template(source_doctype, source_name, template_name):
	"""Overwrite an existing template's blocks with this document's blocks."""
	src = frappe.get_doc(source_doctype, source_name)
	src.check_permission("read")
	tpl = frappe.get_doc(TEMPLATE_DOCTYPE, template_name)
	tpl.check_permission("write")
	tpl.set("blocks", [])
	tpl.header_text = src.get("cr_header_text")
	for r in src.get("cr_blocks") or []:
		row = {f: r.get(f) for f in BLOCK_FIELDS if r.get(f) is not None}
		row.pop("image", None)
		tpl.append("blocks", row)
	tpl.save()
	return tpl.name


# ----------------------------------------------------------------------------- previews
PREVIEW_CSS = """<style>
  html, body { background:#e9ecef !important; margin:0; }
  .print-format-gutter { padding:12px 0 !important; margin:0 !important; background:transparent !important; }
  .print-format { background:#fff !important; width:210mm !important; max-width:100% !important; min-height:297mm;
                  margin:12px auto !important; padding:12mm 16mm !important; box-sizing:border-box;
                  box-shadow:0 1px 6px rgba(0,0,0,.15) !important; }
</style>"""


def _render(d):
	return frappe.render_template(PRINT_TEMPLATE, {"doc": d})


@frappe.whitelist()
def preview_html(doc):
	d = _doc_from_client(doc)
	try:
		html = frappe.get_print(d.doctype, d.name, print_format_name(d.doctype), doc=d, no_letterhead=1)
		if html and "print-format" in html:
			return html.replace("</head>", PREVIEW_CSS + "</head>", 1) if "</head>" in html else PREVIEW_CSS + html
	except Exception:
		frappe.log_error(title="custom_reports: preview_html via get_print failed")
	return f'<!DOCTYPE html><html><head><meta charset="utf-8">{PREVIEW_CSS}</head><body><div class="print-format">{_render(d)}</div></body></html>'


@frappe.whitelist()
def preview_pdf(doc):
	d = _doc_from_client(doc)
	try:
		pdf = frappe.get_print(d.doctype, d.name, print_format_name(d.doctype), doc=d, as_pdf=True, no_letterhead=1)
	except Exception:
		frappe.log_error(title="custom_reports: preview_pdf via get_print failed")
		from frappe.utils.pdf import get_pdf

		pdf = get_pdf(f'<div class="print-format">{_render(d)}</div>')
	return base64.b64encode(pdf).decode()


# ----------------------------------------------------------------------------- photos
@frappe.whitelist()
def rotate_image(file_url, degrees=90, doctype=None, docname=None):
	"""Rotate a photo (and fix phone EXIF orientation); saves a rotated copy and returns its URL."""
	from io import BytesIO

	from PIL import Image, ImageOps

	degrees = int(degrees) % 360
	name = frappe.db.get_value("File", {"file_url": file_url}, "name")
	if not name:
		frappe.throw(_("File not found: {0}").format(file_url))
	src = frappe.get_doc("File", name)
	img = Image.open(BytesIO(src.get_content()))
	fmt = (img.format or "JPEG").upper()
	img = ImageOps.exif_transpose(img)
	if degrees:
		img = img.rotate(-degrees, expand=True)
	if fmt not in ("PNG", "WEBP", "GIF"):
		fmt = "JPEG"
		if img.mode not in ("RGB", "L"):
			img = img.convert("RGB")
	out = BytesIO()
	img.save(out, format=fmt, **({"quality": 90} if fmt == "JPEG" else {}))
	base = (src.file_name or "photo").rsplit(".", 1)[0].split("_rot")[0]
	ext = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp", "GIF": "gif"}[fmt]
	attach = docname and not str(docname).startswith("new-")
	new = frappe.get_doc({
		"doctype": "File", "file_name": f"{base}_rot{frappe.generate_hash(length=6)}.{ext}", "content": out.getvalue(),
		"is_private": src.is_private, "attached_to_doctype": doctype if attach else None,
		"attached_to_name": docname if attach else None,
	})
	new.insert(ignore_permissions=True)
	return new.file_url


@frappe.whitelist()
def fill_images(doc):
	"""Photo blocks with 'Take Photo From' and no photo yet: return the image from that field."""
	from custom_reports.utils import resolve

	d = _doc_from_client(doc)
	out = []
	for b in d.get("cr_blocks") or []:
		if b.block_type == "Image" and b.get("image_from") and not b.get("image"):
			path = b.image_from.strip()
			# raw value (a file URL), not the formatted one
			parts = path.split(".")
			val = d.get(parts[0]) if len(parts) == 1 else None
			if val is None:
				val = resolve(d, path)
			if val:
				out.append({"name": b.name, "image": str(val)})
	return out
