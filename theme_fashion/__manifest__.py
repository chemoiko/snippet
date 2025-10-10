# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Fashion Theme",
    "description": "Fashion website theme",
    "category": "Theme",
    "sequence": 1000,
    "version": "1.0",
    "depends": ["website"],
    "data": [
        "views/snippets/trusted_brands_initializer.xml",
        "views/snippets/feature_fashion.xml",
        "views/snippets/snippets.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "theme_fashion/static/src/js/featured_fashion.js",
            "theme_fashion/static/src/js/latest_products_carousel.js",
            "theme_fashion/static/src/js/categories_snippet.js",
        ],
    },
    "images": [],
    "license": "LGPL-3",
}
