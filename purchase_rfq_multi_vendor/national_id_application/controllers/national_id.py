from odoo import http
from odoo.http import request
import base64


class NationalIDController(http.Controller):

    @http.route("/national-id/apply", type="http", auth="public", website=True)
    def application_form(self, **kw):
        return request.render(
            "national_id_application.national_id_form_template",
            {"errors": {}, "values": {}},
        )

    @http.route(
        "/national-id/submit",
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=False,
    )
    def application_submit(self, **post):
        """Process National ID application form submission"""
        # Extract form data
        surname = (post.get("surname") or "").strip()
        first_name = (post.get("first_name") or "").strip()
        dob = post.get("dob") or ""
        gender = post.get("gender") or ""
        marital_status = post.get("marital_status") or False
        nationality = post.get("nationality") or False
        address = (post.get("address") or "").strip()
        phone = (post.get("phone") or "").strip()
        email = (post.get("email") or "").strip()
        nok_surname = (post.get("next_of_kin_surname") or "").strip()
        nok_first_name = (post.get("next_of_kin_first_name") or "").strip()
        nok_phone = (post.get("next_of_kin_phone") or "").strip()

        # Process file uploads
        photo_file = post.get("photo")
        lc_letter_file = post.get("lc_letter")
        photo = base64.b64encode(photo_file.read()) if photo_file else False
        lc_letter = base64.b64encode(lc_letter_file.read()) if lc_letter_file else False

        # Combine name fields
        full_name = f"{surname} {first_name}".strip()
        next_of_kin_combined = f"{nok_surname} {nok_first_name}".strip()

        # Create application record
        record = (
            request.env["national.id.application"]
            .sudo()
            .create(
                {
                    "name": full_name,
                    "dob": dob,
                    "gender": gender,
                    "marital_status": marital_status,
                    "nationality": nationality,
                    "address": address,
                    "phone": phone,
                    "email": email,
                    "next_of_kin": next_of_kin_combined,
                    "next_of_kin_phone": nok_phone,
                    "photo": photo,
                    "lc_letter": lc_letter,
                }
            )
        )

        # Show success page with tracking number
        return request.render(
            "national_id_application.application_success",
            {"tracking_number": record.tracking_number},
        )
