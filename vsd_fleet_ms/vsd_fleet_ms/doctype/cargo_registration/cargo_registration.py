# Copyright (c) 2023, VV SYSTEMS DEVELOPER LTD and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from operator import mul
import frappe
import time
import datetime
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
import json
from frappe.utils import nowdate, cstr, cint, flt, comma_or, now
from frappe import _, msgprint
from vsd_fleet_ms.utils.dimension import set_dimension

class CargoRegistration(Document):
	pass


@frappe.whitelist()
def create_sales_invoice(doc, rows):
    doc = frappe.get_doc(json.loads(doc))
    rows = json.loads(rows)
    if not rows:
        return
    items = []
    item_row_per = []
    for row in rows:
        description = ""
        trip_info = None
        if row["transporter_type"] == "In House":
            description += "<b>VEHICLE NUMBER: " + row["assigned_truck"]
            trip_info = "<BR>TRIP: " + row["created_trip"]
        elif row["transporter_type"] == "Sub-Contractor":
            description += "<b>VEHICLE NUMBER: " + row["truck_number"]
            description += "<br><b>DRIVER NAME: " + row["driver_name"]
        if row["cargo_route"]:
            description += "<BR>ROUTE: " + row["cargo_route"]
        if trip_info:
            description += trip_info
        item = frappe._dict({
                "item_code": row["service_item"],
                "qty": 1,
                "uom": frappe.get_value("Item", row["service_item"], "stock_uom"),
                "rate": row["rate"],
                "description": description,
            }
        )
        item_row_per.append([row, item])
        items.append(item)
        
    invoice = frappe.get_doc(
        dict(
            doctype="Sales Invoice",
            customer=doc.customer,
            currency=row["currency"],
            posting_date=nowdate(),
            company=doc.company,
            items=items,
        ),
    )

    set_dimension(doc, invoice, src_child=row)
    invoice.items = []
    for i in item_row_per:
        set_dimension(doc, invoice, src_child=i[0], tr_child=i[1])
        invoice.append("items", i[1])
    
    frappe.flags.ignore_account_permission = True
    invoice.set_taxes()
    invoice.set_missing_values()
    invoice.flags.ignore_mandatory = True
    invoice.calculate_taxes_and_totals()
    invoice.insert(ignore_permissions=True)
    for item in doc.cargo_details:
        if item.name in [i["name"] for i in rows]:
            item.invoice = invoice.name
            # if item.transporter_type == "In House":
            #     trip = frappe.get_doc("Trips", item.created_trip)
            #     trip.invoice_number = invoice.name
            #     trip.save()
    doc.save()
           
        
    frappe.msgprint(_("Sales Invoice {0} Created").format(invoice.name), alert=True)
    return invoice