# -*- coding: utf-8 -*-
from odoo import fields, models

class ServiceWarninMessageWizard(models.TransientModel):
    _name = 'service.warning.message.wizard'
    _description = 'To Show warning message'

    def wizard_confirm(self):
        return {'type': 'ir.actions.act_window_close'}