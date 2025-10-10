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
        "views/snippets/feature_fashion.xml",
        "views/snippets/snippets.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "theme_fashion/static/src/js/featured_fashion.js",
        ],
    },
    "images": [],
    "license": "LGPL-3",
}
