from odoo import api, fields, models  # pyright: ignore[reportMissingImports]
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    # Override partner_id to make it optional for RFQs
    partner_id = fields.Many2one(
        "res.partner",
        string="Vendor",
        required=False,  # Remove the required constraint
        index=True,
        change_default=True,
        tracking=True,
        check_company=True,
        help="You can find a vendor by its Name, TIN, Email or Internal Reference.",
    )

    rfq_vendor_ids = fields.One2many("purchase.rfq.vendor", "rfq_id", string="Vendors")
    bid_ids = fields.One2many("purchase.rfq.bid", "rfq_id", string="Bids")
    bid_count = fields.Integer(string="Bid Count", compute="_compute_bid_count")

    @api.depends("bid_ids")
    def _compute_bid_count(self):
        for order in self:
            order.bid_count = len(order.bid_ids)

    def button_confirm(self):
        # Ensure we have a primary vendor before confirming
        for order in self:
            if not order.partner_id:
                # If no primary vendor, check if we have any vendors in the RFQ
                if not order.rfq_vendor_ids:
                    raise ValidationError(
                        "Cannot confirm RFQ without any vendors. Please add vendors first."
                    )
                # Auto-select the first vendor as primary if none selected
                order.partner_id = order.rfq_vendor_ids[0].partner_id

        res = super().button_confirm()

        # Clean up non-winning vendors after confirmation
        for order in self:
            winner = order.partner_id
            if winner and order.rfq_vendor_ids:
                others = order.rfq_vendor_ids.filtered(
                    lambda v: v.partner_id.id != winner.id
                )
                if others:
                    others.unlink()
        return res

    @api.constrains("partner_id", "rfq_vendor_ids", "state")
    def _check_vendor_requirements(self):
        """Ensure RFQ has at least one vendor when being sent"""
        for order in self:
            if (
                order.state == "sent"
                and not order.partner_id
                and not order.rfq_vendor_ids
            ):
                raise ValidationError(
                    "RFQ must have either a primary vendor or vendors in the multi-vendor list before sending."
                )


class PurchaseRfqVendor(models.Model):
    _name = "purchase.rfq.vendor"
    _description = "RFQ Vendor"
    _order = "sequence, id"

    rfq_id = fields.Many2one(
        "purchase.order", string="RFQ", required=True, ondelete="cascade"
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Vendor",
        required=True,
        domain=[("supplier_rank", ">=", 0)],
    )
    sequence = fields.Integer(string="Sequence", default=10)

    _sql_constraints = [
        (
            "uniq_rfq_partner",
            "unique(rfq_id, partner_id)",
            "This vendor is already linked to this RFQ.",
        )
    ]


class PurchaseRfqBid(models.Model):
    _name = "purchase.rfq.bid"
    _description = "RFQ Bid"

    rfq_id = fields.Many2one(
        "purchase.order", string="RFQ", required=True, ondelete="cascade"
    )
    vendor_id = fields.Many2one(
        "res.partner",
        string="Vendor",
        required=True,
        domain=[("supplier_rank", ">=", 0)],
    )
    bid_date = fields.Datetime(string="Bid Date", default=fields.Datetime.now)
    bid_deadline = fields.Datetime(string="Bid Deadline")
    rfq_line_id = fields.Many2one(
        "purchase.order.line", string="RFQ Line", domain="[('order_id', '=', rfq_id)]"
    )
    product_id = fields.Many2one(
        "product.product",
        string="Product",
        related="rfq_line_id.product_id",
        store=True,
        readonly=True,
    )
    product_qty = fields.Float(string="Quantity", default=1.0)
    price_total = fields.Monetary(string="Offer")
    price_unit = fields.Float(string="Unit Price")  # <-- add this
    date_expected = fields.Date(string="Expected Arrival")
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    note = fields.Text()
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("review", "Review"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("won", "Won"),
            ("lost", "Lost"),
        ],
        default="draft",
        tracking=True,
        string="Status",
    )

    # Notes
    officer_notes = fields.Text(string="Officer Notes", help="Notes from bid officer")

    admin_notes = fields.Text(
        string="Admin Notes",
        help="Admin review feedback and approval notes",
        groups="purchase_rfq_multi_vendor.group_bid_admin",
    )

    _sql_constraints = [
        (
            "uniq_rfq_vendor",
            "unique(rfq_id, vendor_id)",
            "This vendor already has a bid on this RFQ.",
        )
    ]

    # price_total is manually editable; no compute

    def _apply_won_side_effects(self):
        # Apply side-effects of a bid being marked as won without rewriting state again
        for bid in self:
            if not bid.rfq_id:
                continue
            other_bids = bid.rfq_id.bid_ids.filtered(lambda b: b.id != bid.id)
            if other_bids:
                other_bids.write({"state": "lost"})
            link_model = self.env["purchase.rfq.vendor"]
            if not bid.rfq_id.rfq_vendor_ids.filtered(
                lambda v: v.partner_id.id == bid.vendor_id.id
            ):
                link_model.create(
                    {
                        "rfq_id": bid.rfq_id.id,
                        "partner_id": bid.vendor_id.id,
                    }
                )
            # Set the winning vendor as the primary vendor
            bid.rfq_id.partner_id = bid.vendor_id.id

    def action_set_won(self):
        # Approve selected bid(s) and show toast notification
        for bid in self:
            if not bid.rfq_id:
                continue
            if bid.state != "won":
                bid.with_context(skip_won_hook=True).write({"state": "won"})
            bid._apply_won_side_effects()

        # Show success toast using bus notification (no page reload needed)
        if len(self) == 1:
            bid = self[0]
            vendor_name = bid.vendor_id.display_name or "Vendor"
            rfq_name = bid.rfq_id.name or "RFQ"
            message = f"{vendor_name} selected as winner for {rfq_name}."
        else:
            message = "Selected bid(s) approved as winner."

        # Send notification via bus
        self.env["bus.bus"]._sendone(
            self.env.user.partner_id,
            "simple_notification",
            {
                "title": "Bid Approved",
                "message": message,
                "type": "success",
            },
        )

    def write(self, vals):
        res = super().write(vals)
        if (
            "state" in vals
            and vals["state"] == "won"
            and not self.env.context.get("skip_won_hook")
        ):
            for rec in self.filtered(lambda r: r.state == "won"):
                rec._apply_won_side_effects()
        return res

    def action_set_lost(self):
        for bid in self:
            if bid.state != "lost":
                bid.write({"state": "lost"})

    def action_submit_review(self):
        """Submit bid for review (draft -> review)"""
        for bid in self:
            if bid.state != "draft":
                raise ValidationError("Only draft bids can be submitted for review.")
            bid.write({"state": "review"})

    def action_approve(self):
        """Approve bid (review -> approved)"""
        for bid in self:
            if bid.state != "review":
                raise ValidationError("Only bids in review state can be approved.")
            bid.write({"state": "approved"})

    def action_reject(self):
        """Reject bid (review -> rejected)"""
        for bid in self:
            if bid.state != "review":
                raise ValidationError("Only bids in review state can be rejected.")
            bid.write({"state": "rejected"})

    def action_reset_to_draft(self):
        """Reset bid to draft state (approved/rejected -> draft)"""
        for bid in self:
            if bid.state not in ("approved", "rejected"):
                raise ValidationError(
                    "Only approved or rejected bids can be reset to draft."
                )
            bid.write({"state": "draft"})
