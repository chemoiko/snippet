{
    "name": "RFQ Many Vendor",
    "summary": "Allow a single RFQ to be assigned to multiple vendors",
    "version": "18.0.1.0.0",
    "author": "eli",
    "website": "",
    "license": "LGPL-3",
    "depends": ["purchase", "base", "mail"],
    "data": [
        "data/purchase_rfq_request_sequence.xml",
        "security/purchase_rfq_security.xml",
        "security/ir.model.access.csv",
        "views/bids.xml",
        "views/purchase_rfq_request_views.xml",
        # "views/purchase_rfq_multi_vendor_views.xml",
    ],
    "installable": True,
    "application": True,
}
