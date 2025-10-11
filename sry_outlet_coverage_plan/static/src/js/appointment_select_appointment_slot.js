odoo.define('sry_outlet_coverage_plan.select_appointment_slot', function (require) {
'use strict';

var core = require('web.core');
var publicWidget = require('web.public.widget');
var qweb = core.qweb;

publicWidget.registry.appointmentSlotSelect = publicWidget.Widget.extend({
    selector: '.o_merchandiser_schedule',
    events: {
        'click .o_js_calendar_navigate': '_onCalendarNavigate',
        'click .o_js_find_outlet': '_onFindOutlet',
        'click .o_js_find_merchandiser': '_onFindMerch',
        'click .js_merch_visit_only_filter': '_onFilterVisitOnly',
        'click .js_merch_deliveries_only_filter': '_onFilterDeliveriesOnly',
        'click .js_merch_visit_deliveries_filter': '_onFilterVisitDeliveries',
        'click .o_js_merch_or_saleperson_merch': '_onMerchORSalePersonMerch',
        'click .o_js_merch_or_saleperson_sale': '_onMerchORSalePersonSale',
        'click .o_js_key_account_executive': '_onKeyAccountExecutive',
        'click .o_js_find_key_account_executive': '_onFindKeyAccountExecutive',

    },

    _onFindKeyAccountExecutive: function (ev) {
       const key_account_executive_name = this.$("input[name='key_account_executive_name']").val();
       const merch_or_saleperson = this.$("input[name='merch_or_saleperson']").val();
       const current_display_type = this.$("input[name='current_display_type']").val();

       this._rpc({
                route: `/my/merchandiser_schedule_search`,
                params: {
                    key_account_executive_name: key_account_executive_name,
                    display_type: current_display_type,
                    merch_or_saleperson: merch_or_saleperson
                },
            }).then(function (data) {
                if (data) {
                    self.$("#merchandiser_schedule_data").replaceWith(data);
                }
            });
    },


    _onKeyAccountExecutive: function (ev) {
       const current_display_type = this.$("input[name='current_display_type']").val();
       this._rpc({
                route: `/my/merchandiser_schedule_search`,
                params: {
                    merch_or_saleperson: 'key_account_executive',
                    display_type: current_display_type,
                },
            }).then(function (data) {
                if (data) {
                    self.$("#merchandiser_schedule_data").replaceWith(data);
                }
            });
    },


    _onMerchORSalePersonSale: function (ev) {
       const current_display_type = this.$("input[name='current_display_type']").val();
       this._rpc({
                route: `/my/merchandiser_schedule_search`,
                params: {
                    merch_or_saleperson: 'sale',
                    display_type: current_display_type,
                },
            }).then(function (data) {
                if (data) {
                    self.$("#merchandiser_schedule_data").replaceWith(data);
                }
            });
    },

    _onMerchORSalePersonMerch: function (ev) {
       const current_display_type = this.$("input[name='current_display_type']").val();
       this._rpc({
                route: `/my/merchandiser_schedule_search`,
                params: {
                    merch_or_saleperson: 'merch',
                    display_type: current_display_type,
                },
            }).then(function (data) {
                if (data) {
                    self.$("#merchandiser_schedule_data").replaceWith(data);
                }
            });
    },

    _onFilterDeliveriesOnly: function (ev) {

       const merch_or_saleperson = this.$("input[name='merch_or_saleperson']").val();

       this._rpc({
                route: `/my/merchandiser_schedule_search`,
                params: {
                    display_type: 'deliveries_only',
                    merch_or_saleperson : merch_or_saleperson
                },
            }).then(function (data) {
                if (data) {
                    self.$("#merchandiser_schedule_data").replaceWith(data);
                }
            });
    },

    _onFilterVisitDeliveries: function (ev) {

       const merch_or_saleperson = this.$("input[name='merch_or_saleperson']").val();

       this._rpc({
                route: `/my/merchandiser_schedule_search`,
                params: {
                    display_type: 'visit_deliveries',
                    merch_or_saleperson : merch_or_saleperson
                },
            }).then(function (data) {
                if (data) {
                    self.$("#merchandiser_schedule_data").replaceWith(data);
                }
            });
    },


    _onFilterVisitOnly: function (ev) {

       const merch_or_saleperson = this.$("input[name='merch_or_saleperson']").val();

       this._rpc({
                route: `/my/merchandiser_schedule_search`,
                params: {
                    display_type: 'visit_only',
                    merch_or_saleperson : merch_or_saleperson
                },
            }).then(function (data) {
                if (data) {
                    self.$("#merchandiser_schedule_data").replaceWith(data);
                }
            });
    },


    _onCalendarNavigate: function (ev) {
        var parent = this.$('.o_delivery_plan_month:not(.d-none)');
        let monthID = parseInt(parent.attr('id').split('-')[1]);
        monthID += ((this.$(ev.currentTarget).attr('id') === 'nextCal') ? 1 : -1);
        parent.addClass('d-none');
        this.$(`div#month-${monthID}`).removeClass('d-none');
    },


    _onFindOutlet: function (ev) {
       const outlet_name = this.$("input[name='outlet_name']").val();
       const merch_or_saleperson = this.$("input[name='merch_or_saleperson']").val();
       const current_display_type = this.$("input[name='current_display_type']").val();

       this._rpc({
                route: `/my/merchandiser_schedule_search`,
                params: {
                    outlet_name: outlet_name,
                    display_type: current_display_type,
                    merch_or_saleperson : merch_or_saleperson
                },
            }).then(function (data) {
                if (data) {
                    self.$("#merchandiser_schedule_data").replaceWith(data);
                }
            });
    },


    _onFindMerch: function (ev) {
       const merchandiser_name = this.$("input[name='merchandiser_name']").val();
       const merch_or_saleperson = this.$("input[name='merch_or_saleperson']").val();
       const current_display_type = this.$("input[name='current_display_type']").val();

       this._rpc({
                route: `/my/merchandiser_schedule_search`,
                params: {
                    merchandiser_name: merchandiser_name,
                    display_type: current_display_type,
                    merch_or_saleperson: merch_or_saleperson
                },
            }).then(function (data) {
                if (data) {
                    self.$("#merchandiser_schedule_data").replaceWith(data);
                }
            });
    },

});
});
