"""Regressions for the pre-activation review; synthetic inputs only."""
import unittest
from datetime import date
from moneydesk import chase, guard, invoice, report
from moneydesk.money import money
from tests.test_moneydesk import CFG, FILLED, inv


class AuthorityRegressionTest(unittest.TestCase):
    def test_ambiguous_amounts_are_not_silently_mispriced(self):
        for amount in ('1.090,50', '12,50', '1,00', 'NaN', 'Infinity'):
            with self.assertRaises(ValueError):
                money(amount)
        self.assertEqual(str(money('1,090.50')), '1090.50')

    def test_legacy_config_cannot_enable_sends(self):
        old = {**CFG['bill'], 'autosend_chasers': True, 'max_autosends_per_run': 5}
        self.assertEqual(chase.decide(inv(), date(2026, 10, 7), old)['action'], 'draft')

    def test_model_generated_approval_cannot_unlock_guard(self):
        for kind in ('report', 'chaser'):
            problems = guard.check_outgoing(kind, {
                'to': ['owner@example.com'], 'body': 'FAV-1',
                'approved': True, 'approval': {'approved_by': 'Marco'},
                'thread_participants': ['owner@example.com'],
            }, CFG, {'invoice': 'FAV-1', 'client_email': 'owner@example.com'})
            self.assertTrue(any('sending disabled' in p for p in problems))

    def test_missing_invoice_lines_returns_validation_error(self):
        for lines in (None, [], 'invalid'):
            with self.assertRaises(invoice.InvoiceError):
                invoice.validate({'entity': 'FAV Studios', 'lines': lines}, FILLED)

    def test_reporting_does_not_attribute_collection_or_archiving(self):
        data = {'week_start': '2026-10-05', 'week_end': '2026-10-09',
                'cancelled': [], 'paid': [], 'filed': [], 'outstanding': [],
                'subscriptions_active': [],
                'needs_marco': ['decision-one', 'decision-two', 'decision-three']}
        text = report.build(data)['text']
        self.assertNotIn('Bill collected', text)
        self.assertNotIn('Bob filed', text)
        self.assertIn('not proof of Drive archiving', text)
        self.assertNotIn('decision-three', text)
        self.assertIn('1 further items remain', text)

    def test_missing_source_is_not_reported_as_zero(self):
        with self.assertRaisesRegex(ValueError, 'source coverage missing'):
            report.build({'week_start': '2026-10-05', 'week_end': '2026-10-09'})
