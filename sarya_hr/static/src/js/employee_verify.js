/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.EmployeeVerificationForm = publicWidget.Widget.extend({
    selector: '.o_employee_verification_form',
    template: 'sarya_hr.portal_employee_verify_template',
    events: {
        'click .toggleRequired': '_FormRequiredCheck',
        'click .o_submit_btn': '_onSubmitButtonClick',
        'change #department_id': '_onOtherDepartmentSelect',
        'change #designation_id': '_onOtherDesignationSelect',
        'click .SameAsCurrent': '_SameAsCurrentAddress',
    },
    start: function (){
        var def = this._super.apply(this, arguments);
        console.log("LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLL");
        console.log("LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLL");
        console.log("LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLL");
        return def;
    },
    _FormRequiredCheck: function (ev) {
        console.log("Inside toggle required.");
        var is_pf_eligible_checkbox = document.getElementById('is_pf_eligible');
        var UAN = document.getElementById('on_pf_eligible');
//        var is_esic_applicable_checkbox = document.getElementById('is_esic_applicable');
//        var pf_number_input = document.getElementById('pf_number');
//        var l10n_in_esic_number_input = document.getElementById('l10n_in_esic_number');

        if (is_pf_eligible_checkbox.checked) {
            console.log('Other - if')
            UAN.style.display = "block";
        } else {
            UAN.style.display = "none";
        }

//        ESIC
//        if (is_esic_applicable_checkbox.checked) {
//            l10n_in_esic_number_input.setAttribute('required', 'Fill ESIC Number');
//        } else {
//            l10n_in_esic_number_input.removeAttribute('required');
//        }
    },

    _onSubmitButtonClick: function (ev) {
        const AadhaarFileInput = this.el.querySelector('input[name="aadhaar_attachment"]');
        const PanFileInput = this.el.querySelector('input[name="pan_attachment"]');
        const AadhaarFile = AadhaarFileInput?.files[0];
        const PanFile = PanFileInput?.files[0];

//        if (!AadhaarFile || AadhaarFile.type !== 'application/pdf') {
//            ev.preventDefault();
//            alert('Please upload a valid Aadhaar PDF file.');
//        }
//
//        if (!PanFile || PanFile.type !== 'application/pdf') {
//            ev.preventDefault();
//            alert('Please upload a valid PAN PDF file.');
//        }

        const genderValue = this.el.querySelector('#gender')?.value;

        if (!genderValue) {
            ev.preventDefault();
            alert('Please select your gender.');
        }

        var has_passport = document.getElementById('has_passport');
        var passport_copy = this.el.querySelector('#passport_copy')?.value;

        if (has_passport.checked && !passport_copy) {
            ev.preventDefault();
            alert('Please Upload your Passport');
        }
},

    _onOtherDepartmentSelect: function(ev) {
        var deptSelect = document.getElementById("department_id");
        console.log('deptSelect', deptSelect)
        var otherDiv = document.getElementById("other_department_div");
        console.log('otherDiv.style.display', otherDiv.style.display)
        console.log('this.value', this.value)
        const selectedValue = ev.currentTarget.value;
        console.log('selectedValue', selectedValue)
        if (selectedValue === "other") {
            otherDiv.style.display = "block";
        } else {
            otherDiv.style.display = "none";
        }
    },

    _onOtherDesignationSelect: function(ev) {
        var desgSelect = document.getElementById("designation_id");
        var otherDiv = document.getElementById("other_designation_div");
        const selectedValue = ev.currentTarget.value;
        if (selectedValue === "other") {
            otherDiv.style.display = "block";
        } else {
            otherDiv.style.display = "none";
        }
    },

    _SameAsCurrentAddress: function(ev) {
        var is_same_as_current_address = document.getElementById('same_as_current');
        console.log('is_same_as_current_address', is_same_as_current_address);

        if (is_same_as_current_address.checked) {
            console.log('document.getElementById', document.getElementById('current_street').value);
            document.getElementById('permanent_street').value = document.getElementById('current_street').value;
            document.getElementById('permanent_city').value = document.getElementById('current_city').value;
            document.getElementById('permanent_state').value = document.getElementById('state_id').value;
            document.getElementById('permanent_zip').value = document.getElementById('current_zip').value;
            document.getElementById('permanent_country').value = document.getElementById('country_id').value;
        } else {
            document.getElementById('permanent_street').value = '';
            document.getElementById('permanent_city').value = '';
            document.getElementById('permanent_state').value = '';
            document.getElementById('permanent_zip').value = '';
            document.getElementById('permanent_country').value = '';
        }
    },


});
export default publicWidget.registry.EmployeeVerificationForm;
//publicWidget.registry.EmployeeVerificationForm = EmployeeVerificationForm;