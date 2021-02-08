# -*- coding: utf-8 -*-
import datetime
from odoo import http

class Main(http.Controller):
    @http.route(['/my/dashboard/orders', '/my/dashboard/orders/page/<int:page>'], 
        type='http', auth='public', website=True)
    def index(self, page=1, date_begin=None, **kwargs):
        work_stages = {
            'bongkar': 'Pembongkaran',
            'ketok': 'Ketok',
            'dempul': 'Dempul',
            'epoxy': 'Epoxy',
            'cat': 'Pengecatan',
            'poles': 'Poles',
            'part_wait': 'Tunggu Part',
            'pasang': 'Pemasangan',
            'finishing': 'Finishing',
            'done': 'Selesai',
            'delivered': 'Delivered'
        }
        status_included = {'confirmed': 'Confirmed', 'under_repair': 'Under Repair', 'ready': 'Repair Done'}
        rekap = {status_included[x]: 0 for x in status_included}
        Order = http.request.env['service.order']
        if not date_begin:
            date_begin = datetime.date(2021, 1, 1)
        for status in status_included:
            rekap[status_included[status]] = Order.sudo().search_count([('state', '=', status), ('register_date', '>=', date_begin)])
        domain = [('state', 'in', [x for x in status_included]), ('register_date', '>=', date_begin)]
        order_count = Order.sudo().search_count(domain)

        pager = http.request.website.pager(
            url='/my/dashboard/orders',
            url_args={'date_begin': date_begin},
            total=order_count,
            page=page,
            step=10
        )
        results = Order.sudo().search(domain, order='state desc', limit=10, offset=pager['offset'])
        
        item = {}
        orders = []
        for res in results:
            item['no_plat'] = res.equipment_id.name
            item['state'] = status_included[res.state]
            item['work_stage'] = work_stages[res.work_stage]
            item['register_date'] = res.register_date
            item['planned_date'] = res.planned_date
            item['overdue'] = ''
            if res.state != 'ready' and res.planned_date and res.planned_date < datetime.date.today():
                item['overdue'] = 'Overdue'
            orders.append(item)
            item = {}

        return http.request.render('zdg_dashboard.portal_my_orders', {
            'rekap': rekap,
            'orders': orders,
            'pager': pager
        })