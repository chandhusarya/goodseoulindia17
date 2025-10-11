from odoo import fields, models, api, _
from dateutil.relativedelta import relativedelta

# Used for displaying the days and reversing selection -> integer
DAY_SELECT_VALUES = [str(i) for i in range(1, 29)] + ['last']
DAY_SELECT_SELECTION_NO_LAST = tuple(zip(DAY_SELECT_VALUES, (str(i) for i in range(1, 29))))
MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']

def _get_selection_days(self):
    return DAY_SELECT_SELECTION_NO_LAST + (("last", _("last day")),)


class AccrualPlanLevel(models.Model):
    _inherit = "hr.leave.accrual.level"

    frequency = fields.Selection(selection_add=[('quarterly', 'Quarterly')],
                                 ondelete={'quarterly': 'set default'})

    first_quarter_day = fields.Integer(default=1)
    first_quarter_day_display = fields.Selection(
        _get_selection_days, compute='_compute_days_display', inverse='_inverse_first_quarter_day_display')
    first_quarter_month = fields.Selection([
        ('jan', 'January'),
        ('feb', 'February'),
        ('mar', 'March'),
    ], default="jan")

    second_quarter_day = fields.Integer(default=1)
    second_quarter_day_display = fields.Selection(
        _get_selection_days, compute='_compute_days_display', inverse='_inverse_second_quarter_day_display')
    second_quarter_month = fields.Selection([
        ('apr', 'April'),
        ('may', 'May'),
        ('jun', 'June'),
    ], default="apr")

    third_quarter_day = fields.Integer(default=1)
    third_quarter_day_display = fields.Selection(
        _get_selection_days, compute='_compute_days_display', inverse='_inverse_third_quarter_day_display')
    third_quarter_month = fields.Selection([
        ('jul', 'July'),
        ('aug', 'August'),
        ('sep', 'September'),
    ], default="jul")


    fourth_quarter_day = fields.Integer(default=1)
    fourth_quarter_day_display = fields.Selection(
        _get_selection_days, compute='_compute_days_display', inverse='_inverse_fourth_quarter_day_display')
    fourth_quarter_month = fields.Selection([
        ('oct', 'October'),
        ('nov', 'November'),
        ('dec', 'December')
    ], default="oct")

    _sql_constraints = [
        ('check_dates',
         "CHECK( (frequency IN ('daily', 'hourly')) or"
         "(week_day IS NOT NULL AND frequency = 'weekly') or "
         "(first_day > 0 AND second_day > first_day AND first_day <= 31 AND second_day <= 31 AND frequency = 'bimonthly') or "
         "(first_day > 0 AND first_day <= 31 AND frequency = 'monthly')or "
         "(first_month_day > 0 AND first_month_day <= 31 AND second_month_day > 0 AND second_month_day <= 31 AND frequency = 'biyearly') or "
         "(yearly_day > 0 AND yearly_day <= 31 AND frequency = 'yearly') or "
         "(first_quarter_day > 0 AND first_quarter_day <= 31 AND second_quarter_day > 0 AND second_quarter_day <= 31 AND third_quarter_day > 0 AND third_quarter_day <= 31 AND fourth_quarter_day > 0 AND fourth_quarter_day <= 31 AND frequency = 'quarterly'))",
         "The dates you've set up aren't correct. Please check them."),
        ('start_count_check', "CHECK( start_count >= 0 )", "You can not start an accrual in the past."),
        ('added_value_greater_than_zero', 'CHECK(added_value > 0)',
         'You must give a rate greater than 0 in accrual plan levels.')
    ]

    @api.depends('first_day', 'second_day', 'first_month_day', 'second_month_day', 'yearly_day')
    def _compute_days_display(self):
        days_select = _get_selection_days(self)
        for level in self:
            level.first_day_display = days_select[min(level.first_day - 1, 28)][0]
            level.second_day_display = days_select[min(level.second_day - 1, 28)][0]
            level.first_month_day_display = days_select[min(level.first_month_day - 1, 28)][0]
            level.second_month_day_display = days_select[min(level.second_month_day - 1, 28)][0]
            level.yearly_day_display = days_select[min(level.yearly_day - 1, 28)][0]
            level.first_quarter_day_display = days_select[min(level.first_quarter_day - 1, 28)][0]
            level.second_quarter_day_display = days_select[min(level.second_quarter_day - 1, 28)][0]
            level.third_quarter_day_display = days_select[min(level.third_quarter_day - 1, 28)][0]
            level.fourth_quarter_day_display = days_select[min(level.fourth_quarter_day - 1, 28)][0]

    def _inverse_first_quarter_day_display(self):
        for level in self:
            if level.first_quarter_day_display == 'last':
                level.first_quarter_day = 31
            else:
                level.first_quarter_day = DAY_SELECT_VALUES.index(level.first_quarter_day_display) + 1

    def _inverse_second_quarter_day_display(self):
        for level in self:
            if level.second_quarter_day_display == 'last':
                level.second_quarter_day = 31
            else:
                level.second_quarter_day = DAY_SELECT_VALUES.index(level.second_quarter_day_display) + 1

    def _inverse_third_quarter_day_display(self):
        for level in self:
            if level.third_quarter_day_display == 'last':
                level.third_quarter_day = 31
            else:
                level.third_quarter_day = DAY_SELECT_VALUES.index(level.third_quarter_day_display) + 1

    def _inverse_fourth_quarter_day_display(self):
        for level in self:
            if level.fourth_quarter_day_display == 'last':
                level.fourth_quarter_day = 31
            else:
                level.fourth_quarter_day = DAY_SELECT_VALUES.index(level.fourth_quarter_day_display) + 1

    def _get_next_date(self, last_call):
        """
        Returns the next date with the given last call
        """
        self.ensure_one()
        if self.frequency in ['hourly', 'daily']:
            return last_call + relativedelta(days=1)
        elif self.frequency == 'weekly':
            daynames = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
            weekday = daynames.index(self.week_day)
            return last_call + relativedelta(days=1, weekday=weekday)
        elif self.frequency == 'bimonthly':
            first_date = last_call + relativedelta(day=self.first_day)
            second_date = last_call + relativedelta(day=self.second_day)
            if last_call < first_date:
                return first_date
            elif last_call < second_date:
                return second_date
            else:
                return last_call + relativedelta(months=1, day=self.first_day)
        elif self.frequency == 'monthly':
            date = last_call + relativedelta(day=self.first_day)
            if last_call < date:
                return date
            else:
                return last_call + relativedelta(months=1, day=self.first_day)
        elif self.frequency == 'biyearly':
            first_month = MONTHS.index(self.first_month) + 1
            second_month = MONTHS.index(self.second_month) + 1
            first_date = last_call + relativedelta(month=first_month, day=self.first_month_day)
            second_date = last_call + relativedelta(month=second_month, day=self.second_month_day)
            if last_call < first_date:
                return first_date
            elif last_call < second_date:
                return second_date
            else:
                return last_call + relativedelta(years=1, month=first_month, day=self.first_month_day)
        elif self.frequency == 'yearly':
            month = MONTHS.index(self.yearly_month) + 1
            date = last_call + relativedelta(month=month, day=self.yearly_day)
            if last_call < date:
                return date
            else:
                return last_call + relativedelta(years=1, month=month, day=self.yearly_day)
        elif self.frequency == 'quarterly':
            first_quarter_month = MONTHS.index(self.first_quarter_month) + 1
            second_quarter_month = MONTHS.index(self.second_quarter_month) + 1
            third_quarter_month = MONTHS.index(self.third_quarter_month) + 1
            fourth_quarter_month = MONTHS.index(self.fourth_quarter_month) + 1
            first_date = last_call + relativedelta(month=first_quarter_month, day=self.first_quarter_day)
            second_date = last_call + relativedelta(month=second_quarter_month, day=self.second_quarter_day)
            third_date = last_call + relativedelta(month=third_quarter_month, day=self.third_quarter_day)
            fourth_date = last_call + relativedelta(month=fourth_quarter_month, day=self.fourth_quarter_day)
            # print("**********_get_previous_date***********")
            # print("last_call", last_call)
            # print("first_date", first_date)
            # print("second_date", second_date)
            # print("third_date", third_date)
            # print("fourth_date", fourth_date)
            if last_call < first_date:
                return first_date
            elif last_call < second_date:
                return second_date
            elif last_call < third_date:
                return third_date
            elif last_call < fourth_date:
                return fourth_date
            else:
                return last_call + relativedelta(years=1, month=first_quarter_month, day=self.first_quarter_day)
        else:
            return False

    def _get_previous_date(self, last_call):
        """
        Returns the date a potential previous call would have been at
        For example if you have a monthly level giving 16/02 would return 01/02
        Contrary to `_get_next_date` this function will return the 01/02 if that date is given
        """
        self.ensure_one()
        if self.frequency in ['hourly', 'daily']:
            return last_call
        elif self.frequency == 'weekly':
            daynames = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
            weekday = daynames.index(self.week_day)
            return last_call + relativedelta(days=-6, weekday=weekday)
        elif self.frequency == 'bimonthly':
            second_date = last_call + relativedelta(day=self.second_day)
            first_date = last_call + relativedelta(day=self.first_day)
            if last_call >= second_date:
                return second_date
            elif last_call >= first_date:
                return first_date
            else:
                return last_call + relativedelta(months=-1, day=self.second_day)
        elif self.frequency == 'monthly':
            date = last_call + relativedelta(day=self.first_day)
            if last_call >= date:
                return date
            else:
                return last_call + relativedelta(months=-1, day=self.first_day)
        elif self.frequency == 'biyearly':
            first_month = MONTHS.index(self.first_month) + 1
            second_month = MONTHS.index(self.second_month) + 1
            first_date = last_call + relativedelta(month=first_month, day=self.first_month_day)
            second_date = last_call + relativedelta(month=second_month, day=self.second_month_day)
            if last_call >= second_date:
                return second_date
            elif last_call >= first_date:
                return first_date
            else:
                return last_call + relativedelta(years=-1, month=second_month, day=self.second_month_day)
        elif self.frequency == 'yearly':
            month = MONTHS.index(self.yearly_month) + 1
            year_date = last_call + relativedelta(month=month, day=self.yearly_day)
            if last_call >= year_date:
                return year_date
            else:
                return last_call + relativedelta(years=-1, month=month, day=self.yearly_day)
        elif self.frequency == 'quarterly':
            first_quarter_month = MONTHS.index(self.first_quarter_month) + 1
            second_quarter_month = MONTHS.index(self.second_quarter_month) + 1
            third_quarter_month = MONTHS.index(self.third_quarter_month) + 1
            fourth_quarter_month = MONTHS.index(self.fourth_quarter_month) + 1
            first_date = last_call + relativedelta(month=first_quarter_month, day=self.first_quarter_day)
            second_date = last_call + relativedelta(month=second_quarter_month, day=self.second_quarter_day)
            third_date = last_call + relativedelta(month=third_quarter_month, day=self.third_quarter_day)
            fourth_date = last_call + relativedelta(month=fourth_quarter_month, day=self.fourth_quarter_day)
            # print("**********_get_previous_date***********")
            # print("last_call", last_call)
            # print("first_date", first_date)
            # print("second_date", second_date)
            # print("third_date", third_date)
            # print("fourth_date", fourth_date)
            if last_call >= fourth_date:
                return fourth_date
            elif last_call >= third_date:
                return third_date
            elif last_call >= second_date:
                return second_date
            elif last_call >= first_date:
                return first_date
            else:
                return last_call + relativedelta(years=-1, month=fourth_quarter_month, day=self.fourth_quarter_day)
        else:
            return False
