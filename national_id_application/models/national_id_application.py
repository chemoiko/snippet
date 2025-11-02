from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools import html2plaintext
from odoo.osv import expression
import logging

_logger = logging.getLogger(__name__)


class NationalIDApplication(models.Model):
    """National ID Application with 3-stage approval workflow"""
    _name = 'national.id.application'
    _description = 'National ID Application'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # Enables chatter
    _order = "id desc"

    # Basic applicant information
    name = fields.Char(string="Full Name", required=True)
    dob = fields.Date(string="Date of Birth", required=True)
    gender = fields.Selection(
        [('male', 'Male'), ('female', 'Female')], string="Gender", required=True)
    address = fields.Char(string="Address", required=True)
    marital_status = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
    ], string="Marital Status")
    nationality = fields.Selection([
        ('ugandan', 'Ugandan'),
        ('kenyan', 'Kenyan'),
        ('tanzanian', 'Tanzanian'),
        ('rwandan', 'Rwandan'),
        ('burundian', 'Burundian'),
        ('south_sudanese', 'South Sudanese'),
        ('drc', 'DR Congolese'),
        ('other', 'Other'),
    ], string="Nationality")
    phone = fields.Char(string="Phone Number", required=True)
    next_of_kin = fields.Char(string="Next of Kin Name")
    next_of_kin_phone = fields.Char(string="Next of Kin Phone")
    email = fields.Char(string="Email", required=True)

    # Documents
    photo = fields.Image(string="Photo", max_width=1024, max_height=1024)
    lc_letter = fields.Binary(string="Letter of Consent")

    # System fields
    tracking_number = fields.Char(
        string="Tracking Number", readonly=True, copy=False, default="New")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verified', 'Verified'),
        ('senior_approved', 'Senior Approved'),
        ('final_approved', 'Final Approved'),
        ('rejected', 'Rejected')
    ], default='draft', tracking=True, string="Status")
    application_date = fields.Datetime(
        string="Application Date", default=fields.Datetime.now)

    # Verification workflow fields
    verified_status = fields.Boolean(string="Verified Status")
    verification_result = fields.Selection([
        ('pending', 'Pending'),
        ('pass', 'Pass'),
        ('fail', 'Fail')
    ], string="Verification Result", default='pending')
    name_match = fields.Boolean(string="Name Match")
    address_match = fields.Boolean(string="Address Match")
    photo_quality = fields.Selection([
        ('good', 'Good'),
        ('acceptable', 'Acceptable'),
        ('poor', 'Poor')
    ], string="Photo Quality")
    lc_present = fields.Boolean(string="LC Letter Present")
    lc_valid = fields.Boolean(string="LC Letter Valid")

    # Approval notes
    verification_notes = fields.Text(
        string="Verification Notes", tracking=True)
    senior_approver_notes = fields.Text(
        string="Senior Approver Notes", tracking=True)
    final_approver_notes = fields.Text(
        string="Final Approver Notes", tracking=True)

    # Audit trail
    verified_by = fields.Many2one(
        'res.users', string="Last Action By", readonly=True, copy=False)
    verified_on = fields.Datetime(
        string="Last Action On", readonly=True, copy=False)

    # Computed fields for UI permissions
    fields_readonly = fields.Boolean(
        string='Fields Readonly',
        compute='_compute_fields_readonly',
        store=False
    )

    @api.model
    def _get_default_tracking_number(self):
        """Generate unique tracking number (NID00001)"""
        return self.env["ir.sequence"].next_by_code("national.id.application")

    @api.model
    def create(self, vals):
        """Create new application with auto-generated tracking number and send acknowledgment email"""
        # Normalize names
        if vals.get('name'):
            vals['name'] = vals['name'].strip().title()
        if vals.get('next_of_kin'):
            vals['next_of_kin'] = vals['next_of_kin'].strip().title()

        # Generate tracking number
        if vals.get('tracking_number', 'New') == 'New':
            vals['tracking_number'] = self._get_default_tracking_number()

        record = super(NationalIDApplication, self).create(vals)
        # Send acknowledgment email
        record.send_ack_email()

        return record

    def copy(self, default=None):
        """Duplicate application with new tracking number and reset state"""
        default = dict(default or {})
        self.ensure_one()
        default.update({
            "state": "draft",
            "tracking_number": self._get_default_tracking_number()
        })
        return super(NationalIDApplication, self).copy(default)

    def send_ack_email(self):
        """Send acknowledgment email to applicant"""
        template = self.env.ref(
            'national_id_application.national_ack_email_template')
        template.send_mail(self.id, force_send=True)

    def action_verify(self):
        """Verify application - validate required fields and move to verified state"""
        # Check all required verification fields
        missing_fields = []
        if not self.verification_notes:
            missing_fields.append("Verification Notes")
        if not self.name_match:
            missing_fields.append("Name Match")
        if not self.address_match:
            missing_fields.append("Address Match")
        if not self.photo_quality:
            missing_fields.append("Photo Quality")
        if not self.lc_present:
            missing_fields.append("LC Letter Present")
        if self.lc_present and not self.lc_valid:
            missing_fields.append("LC Letter Valid")

        if missing_fields:
            raise UserError(
                f"The following verification fields are required: {', '.join(missing_fields)}")

        # Update application status
        self.write({
            'state': 'verified',
            'verified_status': True,
            'verification_result': 'pass' if (self.name_match and self.address_match) else 'pending',
            'verified_by': self.env.user.id,
            'verified_on': fields.Datetime.now()
        })

        # Send notification email
        tmpl = self.env.ref(
            'national_id_application.template_verification_done', raise_if_not_found=False)
        if tmpl:
            tmpl.send_mail(self.id, force_send=True)

    def action_senior_approve(self):
        """Senior approval - requires notes and moves to senior_approved state"""
        if not self.senior_approver_notes:
            raise UserError(
                "Senior approver notes are required to approve the application.")

        # Update status and audit trail
        self.write({
            'state': 'senior_approved',
            'verified_by': self.env.user.id,
            'verified_on': fields.Datetime.now()
        })

        # Log to chatter
        self.message_post(
            body=f"Application approved by senior approver {self.env.user.name}",
            message_type='notification'
        )

        # Send notification email
        tmpl = self.env.ref(
            'national_id_application.template_senior_done', raise_if_not_found=False)
        if tmpl:
            tmpl.send_mail(self.id, force_send=True)

    def action_final_approve(self):
        """Final approval - requires notes and completes the application process"""
        if not self.final_approver_notes:
            raise UserError(
                "Final approver notes are required to give final approval.")

        # Complete the application
        self.write({
            'state': 'final_approved',
            'verified_by': self.env.user.id,
            'verified_on': fields.Datetime.now()
        })

        # Log to chatter
        self.message_post(
            body=f"Application finally approved by {self.env.user.name}",
            message_type='notification'
        )

        # Send completion email
        tmpl = self.env.ref(
            'national_id_application.template_final_done', raise_if_not_found=False)
        if tmpl:
            tmpl.send_mail(self.id, force_send=True)

    def action_reject(self):
        """Reject application at any stage"""
        self.write({
            'state': 'rejected',
            'verified_by': self.env.user.id,
            'verified_on': fields.Datetime.now()
        })

        # Log to chatter
        self.message_post(
            body=f"Application rejected by {self.env.user.name}",
            message_type='notification'
        )

    def action_view_photo(self):
        """Open applicant photo in new window"""
        self.ensure_one()
        if not self.photo:
            raise UserError("No photo uploaded.")
        url = f"/web/image?model={self._name}&id={self.id}&field=photo"
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    def action_view_lc_letter(self):
        """Open LC letter document in new window"""
        self.ensure_one()
        if not self.lc_letter:
            raise UserError("No letter of consent uploaded.")
        url = f"/web/content?model={self._name}&id={self.id}&field=lc_letter&filename=lc_letter"
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    @api.depends('state')
    def _compute_fields_readonly(self):
        """Single computed field for all readonly logic"""
        for record in self:
            user = self.env.user

            # Check user groups
            is_verifier = user.has_group(
                'national_id_application.group_verification_user')
            is_senior = user.has_group(
                'national_id_application.group_senior_user')
            is_final = user.has_group(
                'national_id_application.group_final_user')

            # Default to not readonly
            readonly = False

            # OPTION 1: Hierarchy-based (recommended)
            # User gets permissions of their HIGHEST level group
            if is_final:
                # Final users can edit until final_approved/rejected
                readonly = record.state in ['final_approved', 'rejected']
            elif is_senior:
                # Senior users can edit until senior_approved or higher
                readonly = record.state in [
                    'senior_approved', 'final_approved', 'rejected']
            elif is_verifier:
                # Verifier users can edit until verified or higher
                readonly = record.state in [
                    'verified', 'senior_approved', 'final_approved', 'rejected']

            record.fields_readonly = readonly
