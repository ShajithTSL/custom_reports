# Copyright (c) 2026

from frappe.model.document import Document


class CustomReportsSettings(Document):
	def on_update(self):
		from custom_reports.setup.install import enable_all

		enable_all()
