# if any(records.mapped('carrier_tracking_ref')):
#     raise Warning("Hay transferencias con TRACKING!!!")

# carriers = records.mapped('carrier_id')
# if len(carriers) != 1 or carriers[0].delivery_type != 'gls_asm':
#     raise Warning("Solo disponible para GLS.")

# res = carriers[0].gls_asm_send_shipping(records)
# for picking, vals in zip(records, res):
#     if vals.get('tracking_number') and not picking.carrier_tracking_ref:
#         picking.write({'carrier_tracking_ref': vals['tracking_number']})


if any(records.mapped('carrier_tracking_ref')):
    raise Warning("Hay transferencias con TRACKING!!!")

carriers = records.mapped('carrier_id')
if len(carriers) != 1 or carriers[0].delivery_type != 'gls_asm':
    raise Warning("Solo disponible para GLS.")

res = carriers[0].gls_asm_send_shipping(records)
for picking, vals in zip(records, res):
    if vals.get('tracking_number') and not picking.carrier_tracking_ref:
        picking.write({
            'carrier_tracking_ref': vals['tracking_number'],
            'carrier_id': carriers[0].id,
        })
