# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Anfas Faisal K (odoo@cybrosys.info)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
import io
import json
import xlsxwriter
from odoo import models
from odoo.tools import date_utils


class AccountMove(models.Model):
    """Inherits the account move model"""
    _inherit = 'mrp.bom'

    # def populate_flattened_components(self, pdf_lines=None, parent_line=None):
    #     """
    #     Recursively populate mrp.bom.component.line from _get_pdf_line data.
    #     If pdf_lines is None, calls _get_pdf_line internally.
    #     """
    #     self.ensure_one()
    #     print("SELLLLFFFFFFF", self)
    #
    #     if pdf_lines is None:
    #         pdf_lines = self.env['report.mrp.report_bom_structure']._get_pdf_line(self.id)
    #     print("pdf_lines", pdf_lines)
    #     component_lines = []
    #
    #     def _recurse(lines, parent=None):
    #         print("lines>>>>>>>>>>>>>>>>>", lines)
    #         for line in lines:
    #             if line.get('type') in ('component', 'bom'):
    #                 record = self.env['mrp.bom.component.line'].create({
    #                     'bom_id': self.id,
    #                     'product_id': line.get('product_id'),
    #                     'quantity': line.get('quantity'),
    #                     # 'uom_id': line.get('uom').id if line.get('uom') else False,
    #                     'parent_id': parent.id if parent else False,
    #                     'level': line.get('level', 0),
    #                     'bom_cost': line.get('bom_cost', 0.0),
    #                     'prod_cost': line.get('prod_cost', 0.0),
    #                     'route_type': line.get('route_type'),
    #                     'route_name': line.get('route_name'),
    #                     'link_id': line.get('link_id'),
    #                 })
    #                 component_lines.append(record)
    #
    #                 # Recurse into nested components
    #                 nested_components = line.get('components', [])
    #                 if nested_components:
    #                     print("nested_components", nested_components)
    #                     print("-")
    #                     print("-")
    #                     print("-")
    #                     print("-")
    #                     _recurse(nested_components, parent=record)
    #
    #     _recurse(pdf_lines.get('lines'), parent=parent_line)
    #     return component_lines
    def populate_flattened_components(self, pdf_lines=None):
        """
        Populate mrp.bom.component.line from _get_pdf_line data for this BOM.
        This deletes existing component lines for this top-level BOM and recreates them.
        Returns list of created records.
        """
        self.ensure_one()
        ComponentModel = self.env['mrp.bom.component.line']

        # 1) Remove old cached lines for this top-level BOM to keep it idempotent
        old = ComponentModel.search([('bom_id', '=', self.id)])
        if old:
            old.unlink()

        # 2) Get the pdf-like nested data (if not provided)
        if pdf_lines is None:
            # report.mrp.report_bom_structure._get_pdf_line expects either a BOM or list of BOMs
            pdf_lines = self.env['report.mrp.report_bom_structure']._get_pdf_line(self.id)

        created = []

        def _safe_id(val):
            """Return integer id if val is a record or an int-like, else False."""
            if not val:
                return False
            # Odoo recordset
            try:
                # If val is a recordset with id attribute
                return int(val.id)
            except Exception:
                # If val is integer already (or str int)
                try:
                    return int(val)
                except Exception:
                    return False

        def _recurse(nodes, parent_component=None):
            """
            nodes: list or dict representing the pdf structure
            parent_component: the created mrp.bom.component.line record (or None)
            """
            if not nodes:
                return

            # allow passing a single dict
            seq = nodes if isinstance(nodes, list) else [nodes]

            for node in seq:
                # Only handle types we care about
                if not isinstance(node, dict):
                    continue

                # skip anything that is not a 'component' or 'bom' (but you can change logic)
                if node.get('type') not in ('component', 'bom'):
                    # still recurse into components if present
                    if node.get('components'):
                        _recurse(node.get('components'), parent_component=parent_component)
                    continue

                # Extract safe scalar IDs from the node
                product_id = node.get('product_id') or _safe_id(node.get('product'))
                uom_id = _safe_id(node.get('uom'))
                # We keep bom_id on the saved line as the TOP-LEVEL BOM (self.id)
                top_bom_id = self.id
                # optional: there may be a nested 'bom' record on the node
                node_bom_id = node.get('bom_id') or _safe_id(node.get('bom'))

                vals = {
                    'bom_id': top_bom_id,
                    'product_id': product_id or False,
                    'quantity': node.get('quantity', 0.0) or 0.0,
                    'uom_id': uom_id or False,
                    'level': int(node.get('level', 0) or 0),
                    'bom_cost': float(node.get('bom_cost', 0.0) or 0.0),
                    'prod_cost': float(node.get('prod_cost', 0.0) or 0.0),
                    'route_type': node.get('route_type') or False,
                    'route_name': node.get('route_name') or False,
                    'link_id': node.get('link_id') or False,
                    # store the source BOM id of this node (if any) for reference
                    # 'source_bom_id': node_bom_id or False,
                }

                # add parent relation if present
                if parent_component:
                    vals['parent_id'] = parent_component.id

                # Create the component line
                comp_rec = ComponentModel.create(vals)
                created.append(comp_rec)

                # Recurse into nested components
                nested = node.get('components') or []
                if nested:
                    _recurse(nested, parent_component=comp_rec)

        # start recursion at the root pdf_lines
        _recurse(pdf_lines, parent_component=None)

        return created

    def load_flattened_components(self):
        bom = self
        print(bom, '==========================================================')
        bom.populate_flattened_components()


    def action_print_bom_structure(self):
        """Generate and export the BOM Structure Report in Excel format."""
        bom = self.env['mrp.bom'].browse(self.id)
        candidates = bom.product_id or bom.product_tmpl_id.product_variant_ids
        quantity = bom.product_qty
        for product_variant_id in candidates.ids:
            doc = self.env['report.mrp.report_bom_structure']._get_pdf_line(
                bom.id, product_id=product_variant_id,
                qty=quantity, unfolded=True)
        return {
            'type': 'ir.actions.report',
            'data': {'model': 'mrp.bom',
                     'options': json.dumps(doc,
                                           default=date_utils.json_default),
                     'output_format': 'xlsx',
                     'report_name': 'BoM Structure',
                     },
            'report_type': 'xlsx',
        }

    def get_xlsx_report(self, data, response):
        """ Generate an Excel report with BOM structure and cost."""
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        # Define cell formats
        head = workbook.add_format(
            {'align': 'left', 'bold': True, 'font_size': '20px'})
        format3 = workbook.add_format({'font_size': '15px', 'bold': True})
        format4 = workbook.add_format({'font_size': 10})
        format6 = workbook.add_format({'font_size': 10, 'bold': True})
        format7 = workbook.add_format({'font_size': 10, 'font_color': 'green'})
        format8 = workbook.add_format({'font_size': 10, 'font_color': 'red'})
        format9 = workbook.add_format({'font_size': 10, 'font_color': 'yellow'})
        # Check if there are components or lines in the data
        if data and data.get('components') or data.get('lines'):
            # Merge and format header cells
            sheet.merge_range('A1:F2', 'BoM Structure & Cost', head)
            sheet.merge_range('A4:Z5', data['name'], format3)
            # Merge and format cells for product information
            sheet.merge_range('A7:C7', 'Products', format6)
            sheet.merge_range('D7:E7', 'Quantity', format6)
            sheet.merge_range('F7:G7', 'Unit of Measure', format6)
            sheet.merge_range('H7:I7', 'Ready to Produce', format6)
            sheet.merge_range('J7:K7', 'Free to Use / On Hand', format6)
            sheet.merge_range('L7:M7', 'Availability', format6)
            sheet.merge_range('N7:O7', 'Lead Time', format6)
            sheet.merge_range('P7:Q7', 'Route', format6)
            sheet.merge_range('R7:S7', 'Product Cost', format6)
            sheet.merge_range('T7:U7', 'BOM Cost', format6)
            row_start = 9  # Starting row for data
            currency_symbol = self.env.user.company_id.currency_id.symbol
            # Iterate through lines in the data
            for index, value in enumerate(data.get('lines')):
                # Calculate leading spaces based on the level
                if value['level'] != 0:
                    space_td = '    ' * value['level']
                else:
                    space_td = '    '
                # Merge and format cells for product name
                sheet.merge_range('A8:C8', data['name'], format6)
                sheet.merge_range('D8:E8', data['quantity'], format4)
                sheet.merge_range(f'A{index + row_start}:C{index + row_start}',
                                  space_td + value['name'], format4)
                # Merge and format cells for quantity
                sheet.merge_range(f'D{index + row_start}:E{index + row_start}',
                                  value['quantity'], format4)
                # Merge and format cells for unit of measure
                if 'uom' in value:
                    sheet.merge_range(
                        f'F{index + row_start}:G{index + row_start}',
                        value['uom'], format4)
                # Merge and format cells for 'Ready to Produce'
                if 'producible_qty' in value:
                    sheet.merge_range('H8:I8', data['producible_qty'], format4)
                    sheet.merge_range(
                        f'H{index + row_start}:I{index + row_start}',
                        value['producible_qty'], format4)
                # Merge and format cells for 'Quantity Available / On Hand'
                if 'quantity_available' in value:
                    quantity_available_on_hand = \
                        f"{value['quantity_available']} / {value['quantity_on_hand']}"
                    sheet.merge_range(
                        'J8:K8', f"{data['quantity_available']} / "
                                 f"{data['quantity_on_hand']}", format4)
                    sheet.merge_range(
                        f'J{index + row_start}:K{index + row_start}',
                        quantity_available_on_hand, format4)
                # Merge and format cells for 'Availability'
                if 'availability_display' in value:
                    availability_main_text = data['availability_display']
                    availability_text = value['availability_display']
                    color_format_main = format7 if (
                            availability_main_text == 'Available') \
                        else (
                        format8 if availability_main_text == 'Not Available'
                        else format9)
                    color_format = format7 if availability_text == 'Available' \
                        else (format8 if availability_text == 'Not Available'
                              else format9)
                    sheet.merge_range(
                        'L8:M8', availability_main_text, color_format_main)
                    sheet.merge_range(
                        f'L{index + row_start}:M{index + row_start}',
                        availability_text, color_format)
                # Merge and format cells for 'Product Cost'
                if 'prod_cost' in value:
                    prod_cost_with_symbol = f"{currency_symbol} {data['prod_cost']} "
                    sheet.merge_range(
                        'R8:S8', prod_cost_with_symbol, format4)
                    sheet.merge_range(
                        f'R{index + row_start}:S{index + row_start}',
                        f"{currency_symbol} {value['prod_cost']}", format4)
                # Merge and format cells for 'BOM Cost'
                if 'bom_cost' in value:
                    bom_cost_with_symbol = f" {currency_symbol} {data['bom_cost']}"
                    sheet.merge_range(
                        'T8:U8', bom_cost_with_symbol, format4)
                    sheet.merge_range(
                        f'T{index + row_start}:U{index + row_start}',
                        f" {currency_symbol} {value['bom_cost']}", format4)
                # Merge and format cells for 'Route Info'
                if 'route_name' in value:
                    route_info = f"{value['route_name']} {value['route_detail']}"
                    sheet.merge_range(
                        f'P{index + row_start}:Q{index + row_start}',
                        route_info, format4)
                # Merge and format cells for 'Lead Time'
                if 'lead_time' in value:
                    lead_time = value['lead_time']
                    lead_time_days = f"{int(lead_time)} days" if lead_time != 0.0 else "0 days"
                    sheet.merge_range(
                        f'N{index + row_start}:O{index + row_start}',
                        lead_time_days, format4)
                # Check if 'prod_cost' is present in the data dictionary
                if 'prod_cost' in data:
                    prod_cost_with_symbol = f"{currency_symbol} {data['prod_cost']}"
                    bom_cost_with_symbol = f" {currency_symbol} {data['bom_cost']}"
                    sheet.merge_range(
                        f'D{index + row_start + 1}:E{index + row_start + 1}',
                        'UnitCost', format6)
                    sheet.merge_range(
                        f'T{index + row_start + 1}:U{index + row_start + 1}',
                        bom_cost_with_symbol, format4)
                    sheet.merge_range(
                        f'R{index + row_start + 1}:S{index + row_start + 1}',
                        prod_cost_with_symbol, format4)
        # Close the workbook, seek to the beginning, and stream the output
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
