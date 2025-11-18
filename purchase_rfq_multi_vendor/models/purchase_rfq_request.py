from odoo import _, api, fields, models  # pyright: ignore[reportMissingImports]
from odoo.exceptions import ValidationError  # pyright: ignore[reportMissingImports]


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
        string="Reference",
        compute="_compute_rfq_index",
        store=True,
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

    @api.depends("name")
    def _compute_rfq_index(self):
        for request in self:
            request.rfq_index = request.name or _("RFQ")

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

    def action_open_winning_bid(self):
        self.ensure_one()
        winning_bid = self.winning_bid_id
        if not winning_bid:
            return self.action_view_bids()
        return {
            "type": "ir.actions.act_window",
            "name": _("Winning Bid"),
            "res_model": "purchase.rfq.bid",
            "view_mode": "form",
            "res_id": winning_bid.id,
            "target": "current",
            "context": {"default_rfq_request_id": self.id},
        }

    def action_generate_purchase_order(self):
        for request in self:
            request._ensure_purchase_order()
        return True

    def _ensure_purchase_order(self, winning_bid=None):
        self.ensure_one()
        winning_bid = winning_bid or self.winning_bid_id
        partner = winning_bid.vendor_id if winning_bid else self.primary_vendor_id
        if not partner:
            raise ValidationError(
                _("Select a winning vendor before generating a purchase order.")
            )

        if self.purchase_order_id:
            if partner and self.purchase_order_id.partner_id != partner:
                self.purchase_order_id.partner_id = partner.id
            return self.purchase_order_id

        order_vals = self._prepare_purchase_order_vals(partner, winning_bid)
        purchase_order = self.env["purchase.order"].create(order_vals)
        self.purchase_order_id = purchase_order
        self.state = "po_created"
        purchase_order.message_post(
            body=_("Purchase order created from RFQ %s") % (self.rfq_index or self.name)
        )
        return purchase_order

    def _prepare_purchase_order_vals(self, partner, winning_bid=None):
        self.ensure_one()
        order_lines = self._prepare_purchase_order_line_vals(winning_bid)
        if not order_lines:
            raise ValidationError(_("Add at least one product line to the RFQ."))

        return {
            "partner_id": partner.id,
            "company_id": self.company_id.id,
            "currency_id": self.currency_id.id,
            "origin": self.rfq_index or self.name,
            "rfq_request_id": self.id,
            "order_line": order_lines,
        }

    def _prepare_purchase_order_line_vals(self, winning_bid=None):
        self.ensure_one()
        lines = []
        if self.line_ids:
            for line in self.line_ids:
                product = line.product_id
                description = line.name or (product and product.display_name) or ""
                uom = line.product_uom_id or (
                    product and (product.uom_po_id or product.uom_id)
                )
                qty = line.product_qty or 1.0
                price = (
                    winning_bid._get_price_for_request_line(line)
                    if winning_bid
                    else 0.0
                )
                date_planned = line.expected_date or fields.Date.context_today(self)

                line_vals = {
                    "name": description,
                    "product_id": product.id if product else False,
                    "product_qty": qty,
                    "product_uom": uom.id if uom else False,
                    "price_unit": price,
                    "date_planned": date_planned,
                }
                lines.append((0, 0, line_vals))
        elif winning_bid and winning_bid.line_ids:
            for bid_line in winning_bid.line_ids:
                product = bid_line.product_id
                description = bid_line.name or (product and product.display_name) or ""
                uom = product.uom_po_id if product else False
                line_vals = {
                    "name": description,
                    "product_id": product.id if product else False,
                    "product_qty": bid_line.product_qty or 1.0,
                    "product_uom": uom.id if uom else False,
                    "price_unit": bid_line.price_unit or 0.0,
                    "date_planned": bid_line.date_expected
                    or fields.Date.context_today(self),
                }
                lines.append((0, 0, line_vals))
        return lines


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
