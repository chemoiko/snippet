/** @odoo-module **/
import PublicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

PublicWidget.registry.latest_products_carousel = PublicWidget.Widget.extend({
    selector: ".latest-products-carousel",

    async willStart() {
        this.carouselRow = this.$target.find('#latest-products-row');
        let products = [];
        try {
            products = await rpc('/latest_products/', {});
        } catch {
            // fallback to empty
        }
        this.products = Array.isArray(products) ? products : [];
        return Promise.resolve();
    },

    start() {
        if (!this.carouselRow.length) return;
        if (!this.products.length) {
            this.carouselRow.html(`<div class="col-12 text-center text-muted">No latest products available</div>`);
            return;
        }
        let indicators = '', slides = '';
        this.products.forEach((product, idx) => {
            indicators += `<button type="button" data-bs-target="#latestProductCarousel" data-bs-slide-to="${idx}"${idx === 0 ? ' class="active"' : ''}></button>`;
            slides += `<div class="carousel-item${idx === 0 ? ' active' : ''}">
                <div class="d-flex align-items-center justify-content-center" style="height:200px;">
                    <img class="rounded" style="width:320px;height:220px;object-fit:cover;" src="data:image/png;base64,${product.image_512 || ''}"/>
                    <div class="ms-3">
                        <h5 class="mb-0">${product.name}</h5>
                        <div class="text-muted">Seq: ${product.website_sequence}</div>
                    </div>
                </div>
            </div>`;
        });
        const html = `
        <div id="latestProductCarousel" class="carousel carousel-dark slide" data-bs-ride="carousel">
            <div class="carousel-indicators">${indicators}</div>
            <div class="carousel-inner">${slides}</div>
            <button class="carousel-control-prev" type="button" data-bs-target="#latestProductCarousel" data-bs-slide="prev">
                <span class="carousel-control-prev-icon"></span>
            </button>
            <button class="carousel-control-next" type="button" data-bs-target="#latestProductCarousel" data-bs-slide="next">
                <span class="carousel-control-next-icon"></span>
            </button>
        </div>`;
        this.carouselRow.html(html);
    }
});

export default PublicWidget.registry.latest_products_carousel;
