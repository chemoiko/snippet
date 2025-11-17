from odoo import _, api, fields, models  # pyright: ignore[reportMissingImports]


class PurchaseRfqRequest(models.Model):
    _name = "purchase.rfq.request"
    _description = "RFQ Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(
        string="Reference",
        default=lambda self: _("New"),
        copy=False,
        tracking=True,
        required=True,
    )
    rfq_index = fields.Char(
        string="RFQ Number",
        compute="_compute_rfq_index",
        store=False,
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    requester_id = fields.Many2one(
        "res.users",
        string="Requested By",
        default=lambda self: self.env.user,
        tracking=True,
    )
    description = fields.Text(string="Purpose / Notes", tracking=True)
    bid_deadline = fields.Datetime(string="Bid Deadline", tracking=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("review", "In Review"),
            ("awarded", "Awarded"),
            ("po_created", "PO Created"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )
    rfq_vendor_ids = fields.Many2many(
        "res.partner",
        "purchase_rfq_request_vendor_rel",
        "request_id",
        "partner_id",
        domain=[("supplier_rank", ">=", 0)],
        string="Invited Vendors",
        tracking=True,
    )
    primary_vendor_id = fields.Many2one(
        "res.partner",
        string="Preferred Vendor",
        domain=[("supplier_rank", ">=", 0)],
        tracking=True,
    )
    winning_bid_id = fields.Many2one(
        "purchase.rfq.bid",
        string="Winning Bid",
        copy=False,
        tracking=True,
    )
    bid_ids = fields.One2many(
        "purchase.rfq.bid",
        "rfq_request_id",
        string="Bids",
    )
    bid_count = fields.Integer(
        string="Bid Count",
        compute="_compute_bid_count",
        store=False,
    )
    purchase_order_id = fields.Many2one(
        "purchase.order",
        string="Generated Purchase Order",
        copy=False,
        tracking=True,
    )
    purchase_order_state = fields.Selection(
        related="purchase_order_id.state",
        string="PO Status",
        readonly=True,
    )
    line_ids = fields.One2many(
        "purchase.rfq.request.line",
        "request_id",
        string="Requested Products",
    )

    def _compute_bid_count(self):
        for request in self:
            request.bid_count = len(request.bid_ids)

    def _compute_rfq_index(self):
        for request in self:
            request.rfq_index = f"RFQ{request.id:04d}" if request.id else _("RFQ")

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for values in vals_list:
            if not values.get("name") or values["name"] == _("New"):
                values["name"] = sequence.next_by_code("purchase.rfq.request") or _(
                    "New"
                )
        return super().create(vals_list)

    def action_view_bids(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Bids"),
            "res_model": "purchase.rfq.bid",
            "view_mode": "kanban,list,form",
            "domain": [("rfq_request_id", "=", self.id)],
            "context": {
                "default_rfq_request_id": self.id,
                "search_default_rfq_request_id": self.id,
            },
        }

    def action_open_related_po(self):
        self.ensure_one()
        if not self.purchase_order_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "name": _("Purchase Order"),
            "res_model": "purchase.order",
            "view_mode": "form",
            "res_id": self.purchase_order_id.id,
            "target": "current",
        }


class PurchaseRfqRequestLine(models.Model):
    _name = "purchase.rfq.request.line"
    _description = "RFQ Request Line"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    request_id = fields.Many2one(
        "purchase.rfq.request",
        string="RFQ Request",
        required=True,
        ondelete="cascade",
    )
    product_id = fields.Many2one(
        "product.product",
        string="Product",
        domain=[("purchase_ok", "=", True)],
    )
    name = fields.Text(string="Description")
    product_qty = fields.Float(string="Quantity", default=1.0)
    product_uom_id = fields.Many2one(
        "uom.uom",
        string="Unit of Measure",
        domain="[('category_id', '=', product_id.uom_id.category_id)]",
    )
    expected_date = fields.Date(string="Expected Date")
    notes = fields.Text(string="Notes")
