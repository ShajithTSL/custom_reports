# Custom Reports – customizable contract & report PDFs for Frappe / ERPNext

Build documents such as a **Maintenance Contract** out of blocks (title, numbered headings, clauses 5.1 / 5.2, text, tables, signatures, annexes, photos), drag them into order, fill values from the document with `{{fieldname}}` placeholders, and save layouts as **templates** for later.

Works on any DocType you enable – e.g. your existing contract DocType. Frappe / ERPNext v14 and v15.

## Install / update

Copy `custom_reports.zip` to the server, log in as the bench user (`sudo su - frappe`) and run:

```bash
unzip -o custom_reports.zip -d ~ && bash ~/custom_reports/install.sh
```

The same command updates the app later.

## Set up (once)

1. Open **Custom Reports Settings**.
2. Under **Enabled DocTypes**, add your contract DocType (tick *Make Default Print Format* if you like) and **Save**.
3. Reload the browser (Ctrl+Shift+R).

The DocType now has a **Report Content** section with the visual editor, a **Start from Template** field, and a print format **Custom Report - <DocType>**.

*Header* (same page, printed on every page): **Company Logo** on the left, italic **Header Text** on the right (placeholders allowed, e.g. `Maintenance Contract — {{supplier_name}} / {{customer_name}}`), logo height and line colour. Each row under *Enabled DocTypes* can have its own logo / header text for a different company. Each document also has a **Header Title (next to the logo)** field above the editor – fill it to change the title for that document only; it is saved with *Save as Template* and filled in when the template is loaded. No logo uploaded → the Company logo (from the document's Company, or the default Company) is used. Untick *Show Header* to print without it.

*Look* (same page): serif or sans-serif font, text size and table text size (headings grow with the text size), heading/table colour, accent line colour, capital headings, footer text, page numbers.

## Writing a contract

1. Open a contract. If it is empty, pick a template from the list (your 5 latest – or the company's if you have none; *Show all* / search for more) – e.g. **Maintenance Contract - Standard**.
2. Edit in the editor: click text to type, drag ⋮⋮ to reorder, ↑ ↓ ⧉ ✕ on each block, tick several blocks to delete them at once, **+ insert** between blocks.
3. **{ } Insert field** puts `{{fieldname}}` at the cursor – replaced by the contract's value when printing.
4. **Live Preview** / **PDF Preview** show the result; **Report ▸ Print / PDF** opens the print view.

### Blocks

| Block | Prints as |
|---|---|
| Title | big centred title, italic subtitle, accent line, small note – e.g. MAINTENANCE CONTRACT |
| Part title | centred title with line – e.g. ANNEXES |
| Heading | `1. DEFINITIONS` – numbered, with a line under it |
| Sub heading | `1.1 Title` or (tick *no number*) e.g. *Supplier*, *Annex A — …* |
| Clause 1.1 | `5.1 Supplier Termination Right: text…` – number + optional bold lead-in + rich text |
| Text | paragraphs, bullet lists, bold … |
| 2-column row | label / value table |
| Table row (up to 8 columns) | any table – the number of column headers on the first row sets the columns (KPIs, equipment lists) |
| Table from child table | rows come straight from a child table of the document (e.g. the equipment list): child-table fieldname + column fieldnames (`#` = row number) |
| Signatures | intro line + two signature columns (e.g. SUPPLIER / CUSTOMER) with signature line and *Name / Title / Date* lines |
| Photos, Space, Page break | as in TSL Reports |

Headings keep their content on one page unless *page break* is ticked.

### Placeholders

| Write | Prints |
|---|---|
| `{{customer_name}}` | a field of the contract |
| `{{customer.customer_group}}` | a field of a linked document |
| `{{items[1].model}}` | a child-table row (from 1; `-1` = last) |
| `{{today}}`, `{{name}}` | today's date, document ID |

Empty values print as a blank line `__________` (in signature lines: nothing).

The starter template uses these names – rename them to your DocType's fieldnames (shown in **Insert field**):
`contract_date, supplier_name, supplier_address, supplier_signatory, supplier_signatory_title, customer_name, customer_address, start_date, contract_period, annual_fee, quotation_no, quotation_date, customer_signatory, customer_signatory_title` and the child table `items` with `description, model, contract_type, start_date, end_date`.

## Templates

* **Report ▸ Save as Template** – saves the current layout (optionally only for this DocType).
* **Report ▸ Update Template** – overwrites the template you started from with your changes.
* **Custom Report Template** list – edit templates with the same editor; *For DocType* empty = offered everywhere.
# custom_reports
