from odoo import fields, models, api, _
from datetime import datetime, timedelta
import pytz
from odoo.exceptions import UserError


class IrSequence(models.Model):
    """ Sequence model.

    The sequence model allows to define and use so-called sequence objects.
    Such objects are used to generate unique identifiers in a transaction-safe
    way.

    """
    _inherit = 'ir.sequence'


    def _get_prefix_suffix(self, date=None, date_range=None):
        def _interpolate(s, d):
            return (s % d) if s else ''

        def _interpolation_dict():
            # print('self._context', self._context)
            now = range_date = effective_date = datetime.now(pytz.timezone(self._context.get('tz') or 'UTC'))
            if date or self._context.get('ir_sequence_date'):
                effective_date = fields.Datetime.from_string(date or self._context.get('ir_sequence_date'))
            if date_range or self._context.get('ir_sequence_date_range'):
                range_date = fields.Datetime.from_string(date_range or self._context.get('ir_sequence_date_range'))

            sequences = {
                'year': '%Y', 'month': '%m', 'day': '%d', 'y': '%y', 'doy': '%j', 'woy': '%W',
                'weekday': '%w', 'h24': '%H', 'h12': '%I', 'min': '%M', 'sec': '%S'
            }
            res = {}
            for key, format in sequences.items():
                res[key] = effective_date.strftime(format)
                res['range_' + key] = range_date.strftime(format)
                res['next_' + key] = str(int(range_date.strftime(format))+1)
                res['current_' + key] = now.strftime(format)

            return res

        self.ensure_one()
        d = _interpolation_dict()
        # print('d###########', d)
        try:
            interpolated_prefix = _interpolate(self.prefix, d)
            interpolated_suffix = _interpolate(self.suffix, d)
        except ValueError:
            raise UserError(_('Invalid prefix or suffix for sequence %r', self.name))
        return interpolated_prefix, interpolated_suffix

    def get_next_char(self, number_next):
        interpolated_prefix, interpolated_suffix = self._get_prefix_suffix()
        return interpolated_prefix + '%%0%sd' % self.padding % number_next + interpolated_suffix
