/** @odoo-module */
import PublicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

PublicWidget.registry.featured_fashion_products = PublicWidget.Widget.extend({
    selector: ".feature-fashion",

    async willStart() {
        this.productsRow = this.$target.find('#fashion-products-row');
        let products = [];
        try {
            products = await rpc('/featured_products/', {});
        } catch {
            // fallback to empty
        }
        this.products = Array.isArray(products) ? products : [];
        return Promise.resolve();
    },

    start() {
        if (!this.productsRow.length) {
            return;
        }
        if (!this.products.length) {
            this.productsRow.html(
                `<div class="col-12 text-center text-muted">No featured products available</div>`
            );
            return;
        }
        let html = '';
        this.products.forEach(product => {
            html += `<div class="col-lg-4 mb-5">
                <div class="d-flex align-items-center">
                    <div class="img-container mr-3 rounded">
                        <img class="fashion-image rounded" style="width:100px;height:80px;object-fit:cover;" src="data:image/png;base64,${product.image_512 || ''}"/>
                    </div>
                    <div>
                        <h5 class="mb-0">${product.name}</h5>
                    </div>
                </div>
            </div>`;
        });
        this.productsRow.html(html);
    },
});

export default PublicWidget.registry.featured_fashion_products;
