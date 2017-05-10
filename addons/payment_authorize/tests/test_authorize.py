# -*- coding: utf-8 -*-

import hashlib
import hmac
import time
import urllib.parse
import unittest
from lxml import objectify

import odoo
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment.tests.common import PaymentAcquirerCommon
from odoo.addons.payment_authorize.controllers.main import AuthorizeController
from odoo.tools import mute_logger


@odoo.tests.common.at_install(True)
@odoo.tests.common.post_install(True)
class AuthorizeCommon(PaymentAcquirerCommon):

    def setUp(self):
        super(AuthorizeCommon, self).setUp()
        # authorize only support USD in test environment
        self.currency_usd = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)[0]
        # get the authorize account
        self.authorize = self.env.ref('payment.payment_acquirer_authorize')
        # Be sure to be in 'capture' mode
        self.authorize.auto_confirm = 'confirm_so'


@odoo.tests.common.at_install(True)
@odoo.tests.common.post_install(True)
class AuthorizeForm(AuthorizeCommon):

    def _authorize_generate_hashing(self, values):
        data = '^'.join([
            values['x_login'],
            values['x_fp_sequence'],
            values['x_fp_timestamp'],
            values['x_amount'],
        ]) + '^'
        return hmac.new(str(values['x_trans_key']), data, hashlib.md5).hexdigest()

    def test_10_Authorize_form_render(self):
        self.assertEqual(self.authorize.environment, 'test', 'test without test environment')

        # ----------------------------------------
        # Test: button direct rendering
        # ----------------------------------------
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        form_values = {
            'x_login': self.authorize.authorize_login,
            'x_trans_key': self.authorize.authorize_transaction_key,
            'x_amount': '320.0',
            'x_show_form': 'PAYMENT_FORM',
            'x_type': 'AUTH_CAPTURE',
            'x_method': 'CC',
            'x_fp_sequence': '%s%s' % (self.authorize.id, int(time.time())),
            'x_version': '3.1',
            'x_relay_response': 'TRUE',
            'x_fp_timestamp': str(int(time.time())),
            'x_relay_url': '%s' % urllib.parse.urljoin(base_url, AuthorizeController._return_url),
            'x_cancel_url': '%s' % urllib.parse.urljoin(base_url, AuthorizeController._cancel_url),
            'return_url': None,
            'x_currency_code': 'USD',
            'x_invoice_num': 'SO004',
            'x_first_name': 'Norbert',
            'x_last_name': 'Buyer',
            'x_address': 'Huge Street 2/543',
            'x_city': 'Sin City',
            'x_zip': '1000',
            'x_country': 'Belgium',
            'x_phone': '0032 12 34 56 78',
            'x_email': 'norbert.buyer@example.com',
            'x_state': None,
            'x_ship_to_first_name': 'Norbert',
            'x_ship_to_last_name': 'Buyer',
            'x_ship_to_address': 'Huge Street 2/543',
            'x_ship_to_city': 'Sin City',
            'x_ship_to_zip': '1000',
            'x_ship_to_country': 'Belgium',
            'x_ship_to_phone': '0032 12 34 56 78',
            'x_ship_to_email': 'norbert.buyer@example.com',
            'x_ship_to_state': None,
        }

        form_values['x_fp_hash'] = self._authorize_generate_hashing(form_values)
        # render the button
        res = self.authorize.render('SO004', 320.0, self.currency_usd.id, values=self.buyer_values)
        # check form result
        tree = objectify.fromstring(res)
        self.assertEqual(tree.get('action'), 'https://test.authorize.net/gateway/transact.dll', 'Authorize: wrong form POST url')
        for el in tree.iterfind('input'):
            values = list(el.values())
            if values[1] in ['submit', 'x_fp_hash', 'return_url', 'x_state', 'x_ship_to_state']:
                continue
            self.assertEqual(
                str(values[2], "utf-8"),
                form_values[values[1]],
                'Authorize: wrong value for input %s: received %s instead of %s' % (values[1], values[2], form_values[values[1]])
            )

    @mute_logger('odoo.addons.payment_authorize.models.payment', 'ValidationError')
    def test_20_authorize_form_management(self):
        # be sure not to do stupid thing
        self.assertEqual(self.authorize.environment, 'test', 'test without test environment')

        # typical data posted by authorize after client has successfully paid
        authorize_post_data = {
            'return_url': '/shop/payment/validate',
            'x_MD5_Hash': '7934485E1C105940BE854208D10FAB4F',
            'x_account_number': 'XXXX0027',
            'x_address': 'Huge Street 2/543',
            'x_amount': '320.00',
            'x_auth_code': 'E4W7IU',
            'x_avs_code': 'Y',
            'x_card_type': 'Visa',
            'x_cavv_response': '2',
            'x_city': 'Sun City',
            'x_company': '',
            'x_country': 'Belgium',
            'x_cust_id': '',
            'x_cvv2_resp_code': '',
            'x_description': '',
            'x_duty': '0.00',
            'x_email': 'norbert.buyer@example.com',
            'x_fax': '',
            'x_first_name': 'Norbert',
            'x_freight': '0.00',
            'x_invoice_num': 'SO004',
            'x_last_name': 'Buyer',
            'x_method': 'CC',
            'x_phone': '0032 12 34 56 78',
            'x_po_num': '',
            'x_response_code': '1',
            'x_response_reason_code': '1',
            'x_response_reason_text': 'This transaction has been approved.',
            'x_ship_to_address': 'Huge Street 2/543',
            'x_ship_to_city': 'Sun City',
            'x_ship_to_company': '',
            'x_ship_to_country': 'Belgium',
            'x_ship_to_first_name': 'Norbert',
            'x_ship_to_last_name': 'Buyer',
            'x_ship_to_state': '',
            'x_ship_to_zip': '1000',
            'x_state': '',
            'x_tax': '0.00',
            'x_tax_exempt': 'FALSE',
            'x_test_request': 'false',
            'x_trans_id': '2217460311',
            'x_type': 'auth_capture',
            'x_zip': '1000'
        }

        # should raise error about unknown tx
        with self.assertRaises(ValidationError):
            self.env['payment.transaction'].form_feedback(authorize_post_data, 'authorize')

        tx = self.env['payment.transaction'].create({
            'amount': 320.0,
            'acquirer_id': self.authorize.id,
            'currency_id': self.currency_usd.id,
            'reference': 'SO004',
            'partner_name': 'Norbert Buyer',
            'partner_country_id': self.country_france.id})
        # validate it
        self.env['payment.transaction'].form_feedback(authorize_post_data, 'authorize')
        # check state
        self.assertEqual(tx.state, 'done', 'Authorize: validation did not put tx into done state')
        self.assertEqual(tx.acquirer_reference, authorize_post_data.get('x_trans_id'), 'Authorize: validation did not update tx payid')

        # reset tx
        tx.write({'state': 'draft', 'date_validate': False, 'acquirer_reference': False})

        # simulate an error
        authorize_post_data['x_response_code'] = '3'
        self.env['payment.transaction'].form_feedback(authorize_post_data, 'authorize')
        # check state
        self.assertEqual(tx.state, 'error', 'Authorize: erroneous validation did not put tx into error state')

    @unittest.skip("Authorize s2s test disabled: We do not want to overload Authorize.net with runbot's requests")
    def test_30_authorize_s2s(self):
        # be sure not to do stupid thing
        authorize = self.authorize
        self.assertEqual(authorize.environment, 'test', 'test without test environment')

        # add credential
        # FIXME: put this test in master-nightly on odoo/odoo + create sandbox account
        authorize.write({
            'authorize_transaction_key': '',
            'authorize_login': '',
        })
        self.assertTrue(authorize.authorize_test_credentials, 'Authorize.net: s2s authentication failed')

        # create payment meethod
        payment_token = self.env['payment.token'].create({
            'acquirer_id': authorize.id,
            'partner_id': self.buyer_id,
            'cc_number': '4111 1111 1111 1111',
            'cc_expiry': '02 / 26',
            'cc_brand': 'visa',
            'cc_cvc': '111',
            'cc_holder_name': 'test',
        })

        # create normal s2s transaction
        transaction = self.env['payment.transaction'].create({
            'amount': 500,
            'acquirer_id': authorize.id,
            'type': 'server2server',
            'currency_id': self.currency_usd.id,
            'reference': 'test_ref_%s' % odoo.fields.Date.today(),
            'payment_token_id': payment_token.id,
            'partner_id': self.buyer_id,

        })
        transaction.authorize_s2s_do_transaction()
        self.assertEqual(transaction.state, 'done',)

        # switch to 'authorize only'
        # create authorize only s2s transaction & capture it
        self.authorize.auto_confirm = 'authorize'
        transaction = self.env['payment.transaction'].create({
            'amount': 500,
            'acquirer_id': authorize.id,
            'type': 'server2server',
            'currency_id': self.currency_usd.id,
            'reference': 'test_%s' % int(time.time()),
            'payment_token_id': payment_token.id,
            'partner_id': self.buyer_id,

        })
        transaction.authorize_s2s_do_transaction()
        self.assertEqual(transaction.state, 'authorized')
        transaction.action_capture()
        self.assertEqual(transaction.state, 'done')

        # create authorize only s2s transaction & void it
        self.authorize.auto_confirm = 'authorize'
        transaction = self.env['payment.transaction'].create({
            'amount': 500,
            'acquirer_id': authorize.id,
            'type': 'server2server',
            'currency_id': self.currency_usd.id,
            'reference': 'test_%s' % int(time.time()),
            'payment_token_id': payment_token.id,
            'partner_id': self.buyer_id,

        })
        transaction.authorize_s2s_do_transaction()
        self.assertEqual(transaction.state, 'authorized')
        transaction.action_void()
        self.assertEqual(transaction.state, 'cancel')
