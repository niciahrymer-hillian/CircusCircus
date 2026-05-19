import unittest

from forum import create_app


class BlueprintRegistrationTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.app = create_app()

	def test_expected_routes_are_registered(self):
		rules = {rule.rule: rule.endpoint for rule in self.app.url_map.iter_rules()}
		self.assertEqual(rules.get('/action_login'), 'auth.action_login')
		self.assertEqual(rules.get('/action_logout'), 'auth.action_logout')
		self.assertEqual(rules.get('/action_createaccount'), 'auth.action_createaccount')
		self.assertEqual(rules.get('/addpost'), 'posts.addpost')
		self.assertEqual(rules.get('/viewpost'), 'posts.viewpost')
		self.assertEqual(rules.get('/action_post'), 'posts.action_post')
		self.assertEqual(rules.get('/action_comment'), 'comments.comment')
		self.assertEqual(rules.get('/subforum'), 'routes.subforum')

	def test_expected_methods_for_moved_routes(self):
		rules = {rule.rule: rule for rule in self.app.url_map.iter_rules()}
		self.assertIn('POST', rules['/action_login'].methods)
		self.assertIn('POST', rules['/action_createaccount'].methods)
		self.assertIn('POST', rules['/action_post'].methods)
		self.assertIn('POST', rules['/action_comment'].methods)
		self.assertIn('GET', rules['/action_comment'].methods)


if __name__ == '__main__':
	unittest.main()
