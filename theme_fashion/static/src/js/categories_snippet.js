/** @odoo-module **/
import PublicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

PublicWidget.registry.categories_snippet = PublicWidget.Widget.extend({
    selector: ".categories-snippet",

    async willStart() {
        this.categoriesRow = this.$target.find('#categories-row');
        let categories = [];
        try {
            categories = await rpc('/public_categories/', {});
        } catch {
            // fallback to empty
        }
        this.categories = Array.isArray(categories) ? categories : [];
        return Promise.resolve();
    },

    start() {
        if (!this.categoriesRow.length) return;
        if (!this.categories.length) {
            this.categoriesRow.html(`<div class="col-12 text-center text-muted">No categories available</div>`);
            return;
        }
        let html = '';
        this.categories.forEach(category => {
            html += `<div class="col-lg-3 mb-3">
                <div class="border p-2 rounded text-center">
                    <h6 class="mb-1">${category.name}</h6>
                </div>
            </div>`;
        });
        this.categoriesRow.html(html);
    }
});

export default PublicWidget.registry.categories_snippet;
