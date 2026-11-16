app_name = "custom_reports"
app_title = "Custom Reports"
app_publisher = "Custom Reports"
app_description = "Customizable, block-based report and contract PDFs for any DocType"
app_email = ""
app_license = "MIT"

# The editor works on every DocType listed in "Custom Reports Settings", so it is loaded desk-wide
# (plain files: no `bench build` needed after an update, `bench clear-cache` is enough).
app_include_js = [
	"/assets/custom_reports/js/cr_editor.js",
	"/assets/custom_reports/js/cr_form.js",
]

# tells the browser which DocTypes have the editor
extend_bootinfo = "custom_reports.boot.boot_session"

# {{fieldname}} placeholders and helpers usable in the print template
jinja = {"methods": ["custom_reports.utils.fill", "custom_reports.utils.data_rows", "custom_reports.utils.header_logo"]}

after_install = "custom_reports.setup.install.after_install"
after_migrate = "custom_reports.setup.install.after_migrate"
