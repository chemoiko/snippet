from odoo import http


class FeaturedFashion(http.Controller):
    @http.route("/featured_products/", auth="public", type="json", methods=["POST"])
    def featured_products(self, **kwargs):
        products = http.request.env["product.template"].search_read(
            [],
            [
                "name",
                "image_512",
                "website_url",
                "website_sequence",
                "public_categ_ids",
            ],
            order="website_sequence asc",
            limit=3,
        )
        return products

    @http.route("/latest_products/", auth="public", type="json", methods=["POST"])
    def latest_products(self, **kwargs):
        products = http.request.env["product.template"].search_read(
            [("is_published", "=", True)],
            ["name", "image_512", "website_url", "website_sequence"],
            order="create_date desc",
            limit=4,
        )
        return products

    @http.route("/public_categories/", auth="public", type="json", methods=["POST"])
    def public_categories(self, **kwargs):
        # Public categories: filter for "website_published" if needed
        categories = http.request.env["product.public.category"].search_read(
            [],
            ["name"],
            order="create_date desc",
            limit=4,
        )
        return categories
