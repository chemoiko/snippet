{
    "name": "Purchase Request",
    "version": "18.0.2.3.1",
    "category": "Purchase Management",  # optional; you can remove it
    "depends": ["purchase_stock"],
    "data": [
        "security/purchase_request.xml",
        "security/ir.model.access.csv",
        "data/purchase_request_sequence.xml",
        "data/purchase_request_data.xml",
        "wizard/purchase_request_line_make_purchase_order_view.xml",
        "views/purchase_request_view.xml",
        "views/purchase_request_line_view.xml",
       
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": True,
}